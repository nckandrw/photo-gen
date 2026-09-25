"""Op-level profile of ONE real mflux ZImageTransformerBlock at production shapes (kernel-profile.md).

Synthetic weights (N(0, 0.02)), MLX affine q4 group 64 on every Linear (as in the q4 pack, incl. adaLN).
Precision modes mirror production:
  fp32: activations, t_emb and RoPE tables float32 (REFERENCE)
  bf16: activations, t_emb and RoPE tables bfloat16 (FAST; what _apply_bf16_stream achieves)
Usage: op_profile.py <fp32|bf16> <L> <out.json> [capture_dir]
  Measures: block uncompiled vs mx.compile'd; each sub-op in isolation (each forced to materialise, so
  isolated sums over-count fused elementwise work); analytic FLOPs and bytes per op.
  capture_dir (needs MTL_CAPTURE_ENABLED=1): one uncompiled and one compiled block forward are captured to
  <capture_dir>/block-{uncompiled,compiled}-<prec>.gputrace for kernel counting.
"""
import json, os, statistics, sys, time
import mlx.core as mx
import mlx.nn as nn
from mflux.models.z_image.model.z_image_transformer.transformer_block import ZImageTransformerBlock
from mflux.models.z_image.model.z_image_transformer.attention import ZImageAttention

prec, L, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
cap = sys.argv[4] if len(sys.argv) > 4 else None
A = {"fp32": mx.float32, "bf16": mx.bfloat16}[prec]
D, H, HD, FF = 3840, 30, 128, 10240
mx.random.seed(0)
blk = ZImageTransformerBlock(dim=D, n_heads=H)
for _, m in blk.named_modules():
    if isinstance(m, nn.Linear):
        m.weight = (mx.random.normal(m.weight.shape) * 0.02).astype(mx.bfloat16)
        if "bias" in m: m.bias = mx.zeros(m.bias.shape, dtype=mx.bfloat16)
nn.quantize(blk, group_size=64, bits=4)
mx.eval(blk.parameters())
x = mx.random.normal((1, L, D)).astype(A)
t_emb = mx.random.normal((1, 256)).astype(A)
freqs = mx.stack([mx.cos(mx.random.uniform(shape=(L, HD // 2)) * 6.28), mx.sin(mx.random.uniform(shape=(L, HD // 2)) * 6.28)], -1).astype(A)
mask = mx.ones((1, L), dtype=mx.bool_)

def bench(fn, reps=8):
    for _ in range(3): mx.eval(fn())
    mx.synchronize(); ts = []
    for _ in range(reps):
        t = time.perf_counter(); mx.eval(fn()); mx.synchronize(); ts.append(time.perf_counter() - t)
    return round(statistics.median(ts) * 1000, 3)

full = lambda: blk(x, mask, freqs, t_emb)
cfull = mx.compile(lambda a: blk(a, mask, freqs, t_emb))
res = {"prec": prec, "L": L, "mlx": mx.__version__, "device": mx.device_info()["architecture"],
       "block_uncompiled_ms": bench(full), "block_compiled_ms": bench(lambda: cfull(x))}

# ---- sub-ops, in execution order (each materialised) ----
at = blk.attention
mod = mx.expand_dims(blk.adaLN_modulation[0](t_emb), 1); s_msa, g_msa, s_mlp, g_mlp = mx.split(mod, 4, axis=2)
s_msa, s_mlp, g_msa, g_mlp = 1 + s_msa, 1 + s_mlp, mx.tanh(g_msa), mx.tanh(g_mlp)
xn = blk.attention_norm1(x) * s_msa
q, k, v = at.to_q(xn), at.to_k(xn), at.to_v(xn)
qh = at.norm_q(q.reshape(1, L, H, HD)); kh = at.norm_k(k.reshape(1, L, H, HD))
qr, kr = ZImageAttention._apply_rotary_emb(qh, freqs), ZImageAttention._apply_rotary_emb(kh, freqs)
qt, kt, vt = (mx.transpose(a, (0, 2, 1, 3)) for a in (qr, kr, v.reshape(1, L, H, HD)))
amask = mx.where(mask[:, None, None, :], mx.array(0.0), mx.array(float("-inf")))
o = mx.fast.scaled_dot_product_attention(qt, kt, vt, scale=at.scale, mask=amask)
o2 = mx.transpose(o, (0, 2, 1, 3)).reshape(1, L, D)
ao = at.to_out[0](o2)
xm = x + g_msa * blk.attention_norm2(ao)
fn_in = blk.ffn_norm1(xm) * s_mlp
h1, h3 = blk.feed_forward.w1(fn_in), blk.feed_forward.w3(fn_in)
hh = nn.silu(h1) * h3
f = blk.feed_forward.w2(hh)
mx.eval(mod, xn, q, k, v, qh, kh, qr, kr, qt, kt, vt, o, o2, ao, xm, fn_in, h1, h3, hh, f)
isz = 4 if prec == "fp32" else 2
T = L * D  # tokens x dim elements
ops = [  # name, fn, flops, bytes (activations read+write; q4 weights at 0.5625 B/param incl. scales+biases)
    ("adaLN_linear(256->4D)", lambda: blk.adaLN_modulation[0](t_emb), 2 * 256 * 4 * D, 256 * 4 * D * 0.5625),
    ("rmsnorm1*scale", lambda: blk.attention_norm1(x) * s_msa, 5 * T, 2 * T * isz),
    ("q_proj", lambda: at.to_q(xn), 2 * L * D * D, 2 * T * isz + D * D * 0.5625),
    ("k_proj", lambda: at.to_k(xn), 2 * L * D * D, 2 * T * isz + D * D * 0.5625),
    ("v_proj", lambda: at.to_v(xn), 2 * L * D * D, 2 * T * isz + D * D * 0.5625),
    ("qk_rmsnorm", lambda: [at.norm_q(q.reshape(1, L, H, HD)), at.norm_k(k.reshape(1, L, H, HD))], 10 * T, 4 * T * isz),
    ("rope_qk", lambda: [ZImageAttention._apply_rotary_emb(qh, freqs), ZImageAttention._apply_rotary_emb(kh, freqs)], 6 * T, 4 * T * isz + L * HD * isz),
    ("transpose_qkv", lambda: [mx.contiguous(a) for a in (qt, kt, vt)], 0, 6 * T * isz),
    ("sdpa(mask as mflux)", lambda: mx.fast.scaled_dot_product_attention(qt, kt, vt, scale=at.scale, mask=amask), 4 * H * L * L * HD, 4 * T * isz),
    ("sdpa(mask=None)", lambda: mx.fast.scaled_dot_product_attention(qt, kt, vt, scale=at.scale, mask=None), 4 * H * L * L * HD, 4 * T * isz),
    ("transpose_out", lambda: mx.contiguous(mx.transpose(o, (0, 2, 1, 3))), 0, 2 * T * isz),
    ("out_proj", lambda: at.to_out[0](o2), 2 * L * D * D, 2 * T * isz + D * D * 0.5625),
    ("attn_residual(norm2,gate,add)", lambda: x + g_msa * blk.attention_norm2(ao), 7 * T, 3 * T * isz),
    ("rmsnorm_ffn*scale", lambda: blk.ffn_norm1(xm) * s_mlp, 5 * T, 2 * T * isz),
    ("ffn_w1", lambda: blk.feed_forward.w1(fn_in), 2 * L * D * FF, (T + L * FF) * isz + D * FF * 0.5625),
    ("ffn_w3", lambda: blk.feed_forward.w3(fn_in), 2 * L * D * FF, (T + L * FF) * isz + D * FF * 0.5625),
    ("silu*mul", lambda: nn.silu(h1) * h3, 5 * L * FF, 3 * L * FF * isz),
    ("ffn_w2", lambda: blk.feed_forward.w2(hh), 2 * L * FF * D, (T + L * FF) * isz + D * FF * 0.5625),
    ("ffn_residual(norm2,gate,add)", lambda: xm + g_mlp * blk.ffn_norm2(f), 7 * T, 3 * T * isz),
]
rows = []
for name, fn, fl, by in ops:
    ms = bench(fn)
    rows.append({"op": name, "ms": ms, "gflop": round(fl / 1e9, 2), "mbytes": round(by / 1e6, 1),
                 "tflops": round(fl / (ms / 1e3) / 1e12, 2) if fl else None, "gbps": round(by / (ms / 1e3) / 1e9, 1)})
    print(rows[-1], flush=True)
res["ops"] = rows
res["isolated_sum_ms_excl_maskNone"] = round(sum(r["ms"] for r in rows if r["op"] != "sdpa(mask=None)"), 2)
if cap:
    os.makedirs(cap, exist_ok=True)
    for tag, fn in (("uncompiled", full), ("compiled", lambda: cfull(x))):
        p = f"{cap}/block-{tag}-{prec}-L{L}.gputrace"
        mx.metal.start_capture(p); mx.eval(fn()); mx.synchronize(); mx.metal.stop_capture()
        res[f"capture_{tag}"] = p
json.dump(res, open(out, "w"), indent=1)
print(json.dumps({k: v for k, v in res.items() if k != "ops"}))
