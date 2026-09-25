"""Phase 3 block probe (research only; block-sensitivity-map.md, kernel-profile.md).

Wraps the UNMODIFIED production worker (photogen.runtimes.mflux_zimage_worker.main) and replaces the
__call__ of ZImageTransformerBlock / ZImageContextBlock with an instrumented copy of the same math.
mx.compile is disabled (MLX_DISABLE_COMPILE=1) so Python hooks run every step. Outputs of this harness are
therefore NOT comparable with production timings or hashes; every run records an uncompiled baseline.

Request extra field "probe": {"mode": ..., "out": path, ...}
  stats                      per (step, block): in/out RMS, out variance, residual/attention/FFN relative
                             contribution, cosine(in, out)
  time                       per (step, block): synchronised wall time of attention half, FFN half, total
  perturb block=<id> kind=skip|scale [scale=0.9]
                             skip: the block returns its input (update x0); scale: in + s*(out-in).
                             Applied at every step. Measurement only; no model file is changed.
  ffn_calib calib_out=<npz>  per block: mean over steps/tokens of |silu(w1 z) * w3 z| per FFN hidden channel
                             (inputs for group-aligned FFN pruning scores; ffn-reduction-design.md)
  none                       uncompiled baseline (hooks installed, no measurement, no perturbation)
Block ids: nr0, nr1 (noise refiner), cr0, cr1 (context refiner), L0..L29 (main layers).
"""
import json
import os
import sys
import time

os.environ["MLX_DISABLE_COMPILE"] = "1"

import mlx.core as mx  # noqa: E402
import mlx.nn as nn  # noqa: E402
from mflux.models.z_image.model.z_image_transformer import context_block as CB  # noqa: E402
from mflux.models.z_image.model.z_image_transformer import transformer_block as TB  # noqa: E402
from mflux.models.z_image.variants import z_image as zmod  # noqa: E402
from photogen.runtimes import mflux_zimage_worker as worker  # noqa: E402

IDS: dict = {}
ROWS: list = []
STEP = {"i": -1, "last_first_block": None}
CFG: dict = {}
CALIB: dict = {}  # ffn_calib: block -> sum over calls of mean |hidden activation| per channel [10240]
CALIB_N: dict = {}


def _f(x):
    return x.astype(mx.float32)


def _norm(x):
    return mx.sqrt((_f(x) ** 2).sum())


def _step_for(bid):
    # a new step starts each time the first noise-refiner block runs
    if bid == "nr0":
        STEP["i"] += 1
    return STEP["i"]


def _record(bid, x_in, x_mid, x_out, attn_c, ffn_c):
    m = CFG["mode"]
    if m != "stats":
        return
    n_in, n_mid = _norm(x_in), _norm(x_mid)
    vals = mx.stack([
        mx.sqrt((_f(x_in) ** 2).mean()), mx.sqrt((_f(x_out) ** 2).mean()), mx.var(_f(x_out)),
        _norm(x_out - x_in) / (n_in + 1e-12), _norm(attn_c) / (n_in + 1e-12), _norm(ffn_c) / (n_mid + 1e-12),
        (_f(x_in) * _f(x_out)).sum() / (n_in * _norm(x_out) + 1e-12)])
    v = [float(a) for a in vals.tolist()]
    ROWS.append({"step": STEP["i"], "block": bid, "in_rms": v[0], "out_rms": v[1], "out_var": v[2],
                 "resid_rel": v[3], "attn_rel": v[4], "ffn_rel": v[5], "cos_in_out": v[6]})


def _perturb(bid, x_in, x_out):
    if CFG["mode"] != "perturb" or CFG["block"] != bid:
        return x_out
    if CFG["kind"] == "skip":
        return x_in
    return x_in + CFG.get("scale", 0.9) * (x_out - x_in)


def _sync_t():
    mx.synchronize()
    return time.perf_counter()


def block_call(self, x, attn_mask, freqs_cis, t_emb):
    bid = IDS.get(id(self), "?")
    _step_for(bid)
    timing = CFG["mode"] == "time"
    if timing:
        mx.eval(x); t0 = _sync_t()
    modulation = mx.expand_dims(self.adaLN_modulation[0](t_emb), axis=1)
    scale_msa, gate_msa, scale_mlp, gate_mlp = mx.split(modulation, 4, axis=2)
    scale_msa = 1.0 + scale_msa
    scale_mlp = 1.0 + scale_mlp
    gate_msa = mx.tanh(gate_msa)
    gate_mlp = mx.tanh(gate_mlp)
    attn_out = self.attention(self.attention_norm1(x) * scale_msa, attention_mask=attn_mask, freqs_cis=freqs_cis)
    attn_c = gate_msa * self.attention_norm2(attn_out)
    x_mid = x + attn_c
    if timing:
        mx.eval(x_mid); t1 = _sync_t()
    ffn_in = self.ffn_norm1(x_mid) * scale_mlp
    if CFG["mode"] == "ffn_calib":  # same math as FeedForward.__call__, with the hidden activation exposed
        ff = self.feed_forward
        h = nn.silu(ff.w1(ffn_in)) * ff.w3(ffn_in)
        ffn_out = ff.w2(h)
        a = mx.abs(_f(h)).mean(axis=(0, 1))
        CALIB[bid] = a if bid not in CALIB else CALIB[bid] + a
        mx.eval(CALIB[bid]); CALIB_N[bid] = CALIB_N.get(bid, 0) + 1
    else:
        ffn_out = self.feed_forward(ffn_in)
    ffn_c = gate_mlp * self.ffn_norm2(ffn_out)
    x_out = x_mid + ffn_c
    if timing:
        mx.eval(x_out); t2 = _sync_t()
        ROWS.append({"step": STEP["i"], "block": bid, "attn_s": t1 - t0, "ffn_s": t2 - t1, "total_s": t2 - t0,
                     "L": int(x.shape[1])})
    _record(bid, x, x_mid, x_out, attn_c, ffn_c)
    return _perturb(bid, x, x_out)


def context_call(self, x, attn_mask, freqs_cis):
    bid = IDS.get(id(self), "?")
    timing = CFG["mode"] == "time"
    if timing:
        mx.eval(x); t0 = _sync_t()
    attn_out = self.attention(self.attention_norm1(x), attention_mask=attn_mask, freqs_cis=freqs_cis)
    attn_c = self.attention_norm2(attn_out)
    x_mid = x + attn_c
    if timing:
        mx.eval(x_mid); t1 = _sync_t()
    ffn_out = self.feed_forward(self.ffn_norm1(x_mid))
    ffn_c = self.ffn_norm2(ffn_out)
    x_out = x_mid + ffn_c
    if timing:
        mx.eval(x_out); t2 = _sync_t()
        ROWS.append({"step": STEP["i"], "block": bid, "attn_s": t1 - t0, "ffn_s": t2 - t1, "total_s": t2 - t0,
                     "L": int(x.shape[1])})
    _record(bid, x, x_mid, x_out, attn_c, ffn_c)
    return _perturb(bid, x, x_out)


def install():
    TB.ZImageTransformerBlock.__call__ = block_call
    CB.ZImageContextBlock.__call__ = context_call
    o_init = zmod.ZImage.__init__

    def init(self, *a, **k):
        o_init(self, *a, **k)
        t = self.transformer
        for i, b in enumerate(t.noise_refiner): IDS[id(b)] = f"nr{i}"
        for i, b in enumerate(t.context_refiner): IDS[id(b)] = f"cr{i}"
        for i, b in enumerate(t.layers): IDS[id(b)] = f"L{i}"
    zmod.ZImage.__init__ = init


def run(req_path, res_path):
    req = json.load(open(req_path))
    probe = req.pop("probe")
    CFG.update(probe)
    install()
    clean = res_path + ".request-clean.json"
    json.dump(req, open(clean, "w"), indent=1)
    rc = worker.main(clean, res_path)
    res = json.load(open(res_path))
    res["probe"] = probe
    res["probe_rows"] = len(ROWS)
    res["mlx_disable_compile"] = os.environ.get("MLX_DISABLE_COMPILE")
    json.dump(res, open(res_path, "w"), indent=1)
    if probe.get("out"):
        json.dump(ROWS, open(probe["out"], "w"))
    if CFG["mode"] == "ffn_calib":
        import numpy as np
        np.savez(probe["calib_out"], **{b: np.array((v / CALIB_N[b]).tolist(), dtype=np.float32) for b, v in CALIB.items()})
    return rc


if __name__ == "__main__":
    sys.exit(run(sys.argv[1], sys.argv[2]))
