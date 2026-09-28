"""Group-aligned structured FFN-width reduction (research only; ffn-reduction-design.md).

Wraps the UNMODIFIED production worker. After the model loads, each selected block's SwiGLU FFN keeps only
whole 64-channel hidden groups:
  w1, w3 (q4, [10240 -> rows]):  keep rows of the kept channels          (weight/scales/biases row slice)
  w2     (q4, input dim 10240):  keep the kept groups' packed columns      (8 uint32 per 64-channel group)
                                 and their scale/bias columns
Every kept weight, scale and bias is bit-identical to the q4 pack: no requantization, no tensor edits
beyond selection. mx.compile stays ON (production-like timing). Nothing on disk is modified.

Request extra field "ffn_prune": {"keep_frac": 0.8, "scores": "<npz from p3_block_probe ffn_calib>",
                                  "blocks": "main+nr" (default) | "main"}
keep_frac = 1.0 is the identity control (must reproduce the production hash).
Group score = sum over the group's channels of calib_mean|h_j| * ||w2[:, j]||_2 (w2 dequantized).
"""
import json
import sys

import mlx.core as mx
import numpy as np
from mflux.models.z_image.variants import z_image as zmod
from photogen.runtimes import mflux_zimage_worker as worker

G = 64
INFO: dict = {}


def _slice_ffn(ff, keep_groups):
    kg = mx.array(np.array(sorted(keep_groups), dtype=np.int32))
    ch = (kg[:, None] * G + mx.arange(G)[None, :]).reshape(-1)
    for name in ("w1", "w3"):
        lin = getattr(ff, name)
        lin.weight, lin.scales, lin.biases = lin.weight[ch], lin.scales[ch], lin.biases[ch]
    w2 = ff.w2
    per = G * w2.bits // 32  # uint32 words per group along the input dim
    cols = (kg[:, None] * per + mx.arange(per)[None, :]).reshape(-1)
    w2.weight, w2.scales, w2.biases = w2.weight[:, cols], w2.scales[:, kg], w2.biases[:, kg]
    mx.eval(ff.w1.weight, ff.w3.weight, w2.weight, w2.scales, w2.biases)


def _group_scores(ff, calib):
    w2 = ff.w2
    wd = mx.dequantize(w2.weight, w2.scales, w2.biases, group_size=w2.group_size, bits=w2.bits).astype(mx.float32)
    coln = np.array(mx.sqrt((wd * wd).sum(axis=0)).tolist(), dtype=np.float64)  # ||w2[:, j]||
    s = calib.astype(np.float64) * coln
    return s.reshape(-1, G).sum(axis=1)


def install(cfg):
    frac, scores = float(cfg["keep_frac"]), np.load(cfg["scores"]) if cfg.get("scores") else None
    which = cfg.get("blocks", "main+nr")
    o_init = zmod.ZImage.__init__

    def init(self, *a, **k):
        o_init(self, *a, **k)
        t = self.transformer
        blocks = [(f"L{i}", b) for i, b in enumerate(t.layers)]
        if which == "main+nr":
            blocks += [(f"nr{i}", b) for i, b in enumerate(t.noise_refiner)]
        for bid, b in blocks:
            ng = b.feed_forward.w1.weight.shape[0] // G
            nk = int(round(frac * ng))
            if nk >= ng:
                INFO[bid] = ng; continue  # identity: arrays untouched
            gs = _group_scores(b.feed_forward, scores[bid])
            keep = np.argsort(-gs)[:nk]
            _slice_ffn(b.feed_forward, keep.tolist())
            INFO[bid] = nk
        # The replaced full-width arrays would otherwise stay in MLX's buffer cache and inflate the measured
        # peak footprint (smoke test 2026-09-28: k=0.8 showed 5.89 GB vs 5.41 GB at k=1.0).
        import gc
        gc.collect()
        mx.clear_cache()
        # Exact resident DiT weight bytes after slicing: the memory metric for this sweep. The lifetime peak
        # footprint is confounded by the load-time transient (full + sliced copies briefly coexist).
        from mlx.utils import tree_flatten
        INFO["_dit_weight_bytes"] = int(sum(v.nbytes for _, v in tree_flatten(t.parameters())))
    zmod.ZImage.__init__ = init


def run(req_path, res_path):
    req = json.load(open(req_path))
    cfg = req.pop("ffn_prune")
    install(cfg)
    clean = res_path + ".request-clean.json"
    json.dump(req, open(clean, "w"), indent=1)
    rc = worker.main(clean, res_path)
    res = json.load(open(res_path))
    groups = {b: n for b, n in INFO.items() if not b.startswith("_")}
    res["ffn_prune"] = {**cfg, "groups_kept": groups, "hidden_width_kept": {b: n * G for b, n in groups.items()},
                        "dit_weight_bytes": INFO.get("_dit_weight_bytes")}
    json.dump(res, open(res_path, "w"), indent=1)
    return rc


if __name__ == "__main__":
    sys.exit(run(sys.argv[1], sys.argv[2]))
