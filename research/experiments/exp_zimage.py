"""Unified Z-Image-Turbo experiment worker (research only; production photo-gen is untouched).

Runs the unmodified mflux 0.20.0 Turbo CLI main() with production arguments (--low-ram), plus optional,
independently switchable runtime patches applied only inside this process:

  --precision fp32|bf16      fp32 = production behaviour (default). bf16 = keep the DiT hidden stream in bf16:
                             pad tokens -> bf16, TimestepEmbedder output -> bf16, RoPE result cast back to the
                             input dtype (diffusers semantics), SDPA additive mask cast to q dtype.   [E02]
  --release-transformer      make --low-ram's transformer release effective before VAE decode (the compiled
                             predict closure otherwise keeps the DiT alive).                          [E06/VAE lifecycle]
  --mask-none                call SDPA with mask=None (the model's mask is always all-ones -> all-zeros additive). [E04a]
  --audit PATH               cross-step redundancy audit: record per-block/attention/FFN output deltas between
                             adjacent steps (disables mx.compile so Python hooks run every step).     [cache audit]
  --model DIR                model directory (default: stock q4 pack)
  --steps N --seed S --width W --height H --prompt P --out OUT

Prints one line: EXPRESULT {json}. Also records step times, phase times/peaks, dtypes, lifetime peak footprint.
"""
from __future__ import annotations

import argparse, ctypes, gc, hashlib, json, os, sys, time

ap = argparse.ArgumentParser()
ap.add_argument("--prompt", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--seed", type=int, default=42); ap.add_argument("--steps", type=int, default=9)
ap.add_argument("--width", type=int, default=1024); ap.add_argument("--height", type=int, default=1024)
ap.add_argument("--precision", choices=["fp32", "bf16"], default="fp32")
ap.add_argument("--release-transformer", action="store_true"); ap.add_argument("--mask-none", action="store_true")
ap.add_argument("--audit")
ap.add_argument("--model", help="model directory (default: the stock q4 pack); e.g. a composite with a substituted text_encoder")
A_ = ap.parse_args()
if A_.audit:
    os.environ["MLX_DISABLE_COMPILE"] = "1"

T0 = time.perf_counter()
import mlx.core as mx  # noqa: E402
import mflux.models.z_image.variants.z_image as zmod  # noqa: E402
from mflux.models.z_image.model.z_image_transformer import attention as AT, timestep_embedder as TE, feed_forward as FF, transformer_block as TB  # noqa: E402
from mflux.callbacks.callback_manager import CallbackManager  # noqa: E402
from mflux.callbacks.instances.memory_saver import MemorySaver  # noqa: E402
from mflux.models.z_image.cli import z_image_turbo_generate as cli  # noqa: E402

rec = {"args": vars(A_), "phases": {}, "dtypes": {}, "step_ts": [], "notes": []}
def dt(name, x): rec["dtypes"].setdefault(name, set()).add(str(x.dtype))

# ---------- precision patch (E02) ----------
if A_.precision == "bf16":
    o_te = TE.TimestepEmbedder.__call__
    TE.TimestepEmbedder.__call__ = lambda self, *a, **k: o_te(self, *a, **k).astype(mx.bfloat16)
    o_rope = AT.ZImageAttention._apply_rotary_emb
    AT.ZImageAttention._apply_rotary_emb = staticmethod(lambda x, f: o_rope(x, f).astype(x.dtype))
o_sdpa = AT.scaled_dot_product_attention
def sdpa(q, k, v, scale=None, mask=None):
    dt("sdpa_q", q)
    if A_.mask_none:
        mask = None
    elif mask is not None and A_.precision == "bf16":
        mask = mask.astype(q.dtype)
    return o_sdpa(q, k, v, scale=scale, mask=mask)
AT.scaled_dot_product_attention = sdpa
o_ff = FF.FeedForward.__call__
def ff(self, x): dt("ffn_in", x); return o_ff(self, x)
FF.FeedForward.__call__ = ff

o_init = zmod.ZImage.__init__
def init(self, *a, **k):
    o_init(self, *a, **k)
    if A_.precision == "bf16":
        t = self.transformer
        t.x_pad_token = t.x_pad_token.astype(mx.bfloat16); t.cap_pad_token = t.cap_pad_token.astype(mx.bfloat16)
zmod.ZImage.__init__ = init

# ---------- transformer lifetime patch (VAE lifecycle) ----------
if A_.release_transformer:
    def _predict(transformer):
        holder = {"t": transformer}
        def predict(latents, timestep, sigmas, text_encodings, negative_encodings, guidance):
            tr = holder["t"]
            noise = tr(timestep=timestep, x=latents, cap_feats=text_encodings, sigmas=sigmas)
            if negative_encodings is None:
                return noise
            neg = tr(timestep=timestep, x=latents, cap_feats=negative_encodings, sigmas=sigmas)
            return noise + guidance * (noise - neg)
        from mflux.utils.apple_silicon import AppleSiliconUtil
        holder["fn"] = predict if AppleSiliconUtil.is_m1_or_m2() else mx.compile(predict)
        def call(*a, **k): return holder["fn"](*a, **k)
        def release():  # drop the model reference AND the compiled graph (which may hold weights as constants)
            holder.clear(); gc.collect(); mx.clear_cache()
        call.release = release
        _LIVE["predict"] = call
        return call
    _LIVE: dict = {}
    zmod.ZImage._predict = staticmethod(_predict)
    o_after = MemorySaver.call_after_loop
    def after(self, *a, **k):
        r = o_after(self, *a, **k)
        if not self.keep_transformer and "predict" in _LIVE:
            _LIVE.pop("predict").release()
        return r
    MemorySaver.call_after_loop = after

# ---------- cross-step audit hooks ----------
if A_.audit:
    AUD = {"block_resid": {}, "attn_out": {}, "ffn_out": {}}  # block_out omitted: ~1 GB saved; the residual carries the cache-relevant signal  # key -> prev tensor (bf16)
    STATS = []  # rows: step, kind, block, rel_delta, token p50/p90/p99 rel delta
    STEP = {"i": -1}
    o_block = TB.ZImageTransformerBlock.__call__
    def blk(self, x, attn_mask, freqs_cis, t_emb):
        idx = BLOCK_IDS.get(id(self), -1)
        out = o_block(self, x, attn_mask, freqs_cis, t_emb)
        _delta("block_resid", idx, out - x)
        return out
    TB.ZImageTransformerBlock.__call__ = blk
    o_attn = AT.ZImageAttention.__call__
    def attn(self, hidden_states, *a, **k):
        out = o_attn(self, hidden_states, *a, **k); _delta("attn_out", BLOCK_IDS.get(id(self), -1), out); return out
    AT.ZImageAttention.__call__ = attn
    o_ff2 = FF.FeedForward.__call__
    def ff2(self, x):
        out = o_ff2(self, x); _delta("ffn_out", BLOCK_IDS.get(id(self), -1), out); return out
    FF.FeedForward.__call__ = ff2
    BLOCK_IDS: dict = {}
    def _delta(kind, idx, cur):
        if idx < 0:
            return
        cur = cur.astype(mx.float32)
        prev = AUD[kind].get(idx)
        if prev is not None and prev.shape == cur.shape:
            d = mx.abs(cur - prev)
            rel = float((mx.sqrt((d * d).sum()) / (mx.sqrt((cur * cur).sum()) + 1e-12)).item())
            tok = mx.sqrt((d * d).sum(axis=-1)) / (mx.sqrt((cur * cur).sum(axis=-1)) + 1e-12)  # per-token rel delta
            tok = mx.sort(tok.reshape(-1))
            n = tok.shape[0]
            q = lambda p: float(tok[min(n - 1, int(p * n))].item())
            STATS.append({"step": STEP["i"], "kind": kind, "block": idx, "rel": round(rel, 5),
                          "tok_p10": round(q(.10), 4), "tok_p50": round(q(.5), 4), "tok_p90": round(q(.9), 4), "tok_p99": round(q(.99), 4)})
        AUD[kind][idx] = cur.astype(mx.bfloat16); mx.eval(AUD[kind][idx])
    o_init2 = zmod.ZImage.__init__
    def init2(self, *a, **k):
        o_init2(self, *a, **k)
        t = self.transformer
        for i, b in enumerate(list(t.noise_refiner) + list(t.layers)):  # 0-1 noise refiner, 2-31 main layers
            BLOCK_IDS[id(b)] = i; BLOCK_IDS[id(b.attention)] = i; BLOCK_IDS[id(b.feed_forward)] = i
    zmod.ZImage.__init__ = init2

# ---------- phase timing + step timing ----------
def phase(name, fn):
    def w(*a, **k):
        mx.synchronize(); mx.reset_peak_memory(); s = time.perf_counter(); act0 = mx.get_active_memory()
        out = fn(*a, **k)
        if isinstance(out, tuple): mx.eval([x for x in out if isinstance(x, mx.array)])
        elif isinstance(out, mx.array): mx.eval(out)
        mx.synchronize()
        rec["phases"][name] = {"s": round(time.perf_counter() - s, 3), "mlx_peak_gb": round(mx.get_peak_memory() / 1e9, 3),
                               "active_before_gb": round(act0 / 1e9, 3), "active_after_gb": round(mx.get_active_memory() / 1e9, 3)}
        return out
    return w
zmod.ZImage._encode_prompts = phase("text_encode", zmod.ZImage._encode_prompts)
zmod.ZImage._decode_latents = phase("vae_decode", zmod.ZImage._decode_latents)
zmod.ZImage.generate_image = phase("generate", zmod.ZImage.generate_image)

class StepTimer:
    def call_before_loop(self, *a, **k): rec["step_ts"].append(time.perf_counter())
    def call_in_loop(self, *a, **k):
        rec["step_ts"].append(time.perf_counter())
        if A_.audit: STEP["i"] += 1
    def call_after_loop(self, *a, **k): rec["step_ts"].append(time.perf_counter())
o_reg = CallbackManager.register_callbacks
def reg(*a, **k):
    r = o_reg(*a, **k); k.get("model", a[1] if len(a) > 1 else None).callbacks.register(StepTimer()); return r
CallbackManager.register_callbacks = staticmethod(reg)

def footprint_gb():
    try:
        lib = ctypes.CDLL("/usr/lib/libproc.dylib")
        class RI(ctypes.Structure): _fields_ = [("u", ctypes.c_uint8 * 16)] + [(f"f{i}", ctypes.c_uint64) for i in range(40)]
        r = RI()
        return round(r.f28 / 1e9, 3) if lib.proc_pid_rusage(os.getpid(), 4, ctypes.byref(r)) == 0 else None
    except Exception:
        return None

root = os.path.expanduser("~/Dev/photo-gen")
sys.argv = ["mflux-generate-z-image-turbo", "--model", A_.model or f"{root}/models/mflux/z-image-turbo-mflux-q4", "--base-model", "z-image-turbo",
            f"--prompt={A_.prompt}", "--width", str(A_.width), "--height", str(A_.height), "--steps", str(A_.steps),
            "--seed", str(A_.seed), "--low-ram", "--output", A_.out]
cli.main()
ts = rec.pop("step_ts")
rec["step_s"] = [round(b - a, 3) for a, b in zip(ts[1:], ts[2:])]
p = rec["phases"]
rec["denoise_s"] = round(p["generate"]["s"] - p["text_encode"]["s"] - p["vae_decode"]["s"], 3)
rec["process_s"] = round(time.perf_counter() - T0, 3)
rec["peak_footprint_gb"] = footprint_gb()
rec["dtypes"] = {k: sorted(v) for k, v in rec["dtypes"].items()}
from PIL import Image  # noqa: E402
with Image.open(A_.out) as im:
    rec["pixel_sha256"] = hashlib.sha256(im.convert("RGB").tobytes()).hexdigest()
if A_.audit:
    json.dump(STATS, open(A_.audit, "w"))
    rec["audit_rows"] = len(STATS)
print("EXPRESULT " + json.dumps(rec))
