"""E00: single Z-Image transformer block microbenchmark on this M5 (synthetic random weights, same shapes/quantization
as the production q4 pack: dim 3840, 30 heads x 128, SwiGLU hidden 10240, MLX affine q4 group 64, bf16 activations).
Measures where per-step time goes and tests exact-equivalence rewrites. No mflux code or model files are touched."""
import json, statistics, sys, time
import mlx.core as mx
import mlx.nn as nn

D, H, HD, FF = 3840, 30, 128, 10240
L = int(sys.argv[1]) if len(sys.argv) > 1 else 4096 + 32
ACT = {"fp32": mx.float32, "bf16": mx.bfloat16}[sys.argv[2] if len(sys.argv) > 2 else "fp32"]  # production = fp32 (see e01)
REPS = 8
mx.random.seed(0)

def lin(i, o, bits):
    l = nn.Linear(i, o, bias=False)
    l.weight = (mx.random.normal((o, i)) * 0.02).astype(mx.bfloat16)
    return nn.QuantizedLinear.from_linear(l, group_size=64, bits=bits) if bits else l

def bench(fn, *args):
    for _ in range(2): mx.eval(fn(*args))
    mx.synchronize(); ts = []
    for _ in range(REPS):
        t = time.perf_counter(); mx.eval(fn(*args)); mx.synchronize(); ts.append(time.perf_counter() - t)
    return round(statistics.median(ts) * 1000, 2)

x = (mx.random.normal((1, L, D))).astype(ACT)
res = {"activations": str(ACT), "L": L, "reps": REPS, "mlx": mx.__version__, "device": mx.device_info()["architecture"]}
for bits in (4, 8, None):
    tag = f"q{bits}" if bits else "bf16"
    q, k, v, o = (lin(D, D, bits) for _ in range(4))
    w1, w3, w2 = lin(D, FF, bits), lin(D, FF, bits), lin(FF, D, bits)
    qkv = lin(D, 3 * D, bits); w13 = lin(D, 2 * FF, bits)
    res[f"{tag}.qkv_separate_ms"] = bench(lambda a: [q(a), k(a), v(a)], x)
    res[f"{tag}.qkv_fused_ms"] = bench(lambda a: qkv(a), x)
    res[f"{tag}.out_proj_ms"] = bench(lambda a: o(a), x)
    res[f"{tag}.ffn_w1w3_separate_ms"] = bench(lambda a: nn.silu(w1(a)) * w3(a), x)
    res[f"{tag}.ffn_w1w3_fused_ms"] = bench(lambda a: (lambda y: nn.silu(y[..., :FF]) * y[..., FF:])(w13(a)), x)
    hmid = mx.random.normal((1, L, FF)).astype(ACT)
    res[f"{tag}.ffn_w2_ms"] = bench(lambda a: w2(a), hmid)
qh = mx.random.normal((1, H, L, HD)).astype(ACT)
kh, vh = mx.random.normal((1, H, L, HD)).astype(ACT), mx.random.normal((1, H, L, HD)).astype(ACT)
zero_mask = mx.where(mx.ones((1, L), dtype=mx.bool_)[:, None, None, :], mx.array(0.0), mx.array(float("-inf"))).astype(ACT)
sdpa = mx.fast.scaled_dot_product_attention
res["sdpa_with_zero_mask_ms"] = bench(lambda a, b, c: sdpa(a, b, c, scale=HD ** -0.5, mask=zero_mask), qh, kh, vh)
res["sdpa_mask_none_ms"] = bench(lambda a, b, c: sdpa(a, b, c, scale=HD ** -0.5, mask=None), qh, kh, vh)
d = sdpa(qh, kh, vh, scale=HD ** -0.5, mask=zero_mask) - sdpa(qh, kh, vh, scale=HD ** -0.5, mask=None)
res["sdpa_mask_vs_none_max_abs_diff"] = float(mx.abs(d.astype(mx.float32)).max())
res["zero_mask_dtype"] = str(zero_mask.dtype)
print(json.dumps(res, indent=1))
