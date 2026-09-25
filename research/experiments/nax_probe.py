"""NAX runtime probe (nax-status.md Part 2). Synthetic weights, production shapes; no model files are touched.

Usage: nax_probe.py <fp32|bf16> <out.json> [capture_path.gputrace]
  Times one q4 linear (3840->3840, M=4128) and one SDPA (30x4128x128) with the given activation dtype.
  If a capture path is given, it wraps ONE execution of each op in mx.metal.start_capture/stop_capture
  (needs MTL_CAPTURE_ENABLED=1). Run with and without MLX_ENABLE_TF32=0 (the runtime NAX switch for fp32).
"""
import json, os, statistics, sys, time
import mlx.core as mx
import mlx.nn as nn

act = {"fp32": mx.float32, "bf16": mx.bfloat16}[sys.argv[1]]
out = sys.argv[2]; cap = sys.argv[3] if len(sys.argv) > 3 else None
D, L, H, HD = 3840, 4128, 30, 128
mx.random.seed(0)
l = nn.Linear(D, D, bias=False); l.weight = (mx.random.normal((D, D)) * 0.02).astype(mx.bfloat16)
q = nn.QuantizedLinear.from_linear(l, group_size=64, bits=4)
x = mx.random.normal((1, L, D)).astype(act)
qh, kh, vh = (mx.random.normal((1, H, L, HD)).astype(act) for _ in range(3))
sdpa = lambda: mx.fast.scaled_dot_product_attention(qh, kh, vh, scale=HD ** -0.5, mask=None)
mx.eval(q.parameters(), x, qh, kh, vh)

def bench(fn, reps=10):
    for _ in range(3): mx.eval(fn())
    mx.synchronize(); ts = []
    for _ in range(reps):
        t = time.perf_counter(); mx.eval(fn()); mx.synchronize(); ts.append(time.perf_counter() - t)
    return round(statistics.median(ts) * 1000, 3)

res = {"act": sys.argv[1], "MLX_ENABLE_TF32": os.environ.get("MLX_ENABLE_TF32", "(unset: default 1)"),
       "device": mx.device_info()["architecture"], "mlx": mx.__version__,
       "q4_linear_ms": bench(lambda: q(x)), "sdpa_ms": bench(sdpa)}
res["q4_linear_tflops"] = round(2 * L * D * D / (res["q4_linear_ms"] / 1000) / 1e12, 2)
ref = (x.astype(mx.float32) @ mx.dequantize(q.weight, q.scales, q.biases, group_size=64, bits=4).T.astype(mx.float32))
res["q4_linear_max_rel_err_vs_fp32_dequant"] = float((mx.abs(q(x).astype(mx.float32) - ref).max() / mx.abs(ref).max()).item())
if cap:
    mx.metal.start_capture(cap)
    mx.eval(q(x)); mx.eval(sdpa()); mx.synchronize()
    mx.metal.stop_capture()
    res["capture"] = cap
json.dump(res, open(out, "w"), indent=1)
print(json.dumps(res))
