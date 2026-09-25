"""E09: timing proxy for TMP-style FFN width pruning (-37.5%: 10240 -> 6400) on this M5.
Synthetic random weights, MLX affine q4 group 64, activations fp32 (production) and bf16 (E02). Full block = QKV+SDPA+O+FFN."""
import json, statistics, time, sys
import mlx.core as mx, mlx.nn as nn
D, H, HD, L = 3840, 30, 128, 4128
def lin(i, o):
    l = nn.Linear(i, o, bias=False); l.weight = (mx.random.normal((o, i)) * 0.02).astype(mx.bfloat16)
    return nn.QuantizedLinear.from_linear(l, group_size=64, bits=4)
def bench(fn, reps=8):
    for _ in range(2): mx.eval(fn())
    mx.synchronize(); ts = []
    for _ in range(reps):
        t = time.perf_counter(); mx.eval(fn()); mx.synchronize(); ts.append(time.perf_counter() - t)
    return round(statistics.median(ts) * 1000, 2)
res = {}
for act_name, act in (("fp32", mx.float32), ("bf16", mx.bfloat16)):
    x = mx.random.normal((1, L, D)).astype(act)
    q, k, v, o = (lin(D, D) for _ in range(4))
    for ff in (10240, 6400):
        w1, w3, w2 = lin(D, ff), lin(D, ff), lin(ff, D)
        def block():
            qq, kk, vv = (m(x).reshape(1, L, H, HD).transpose(0, 2, 1, 3) for m in (q, k, v))
            a = mx.fast.scaled_dot_product_attention(qq, kk, vv, scale=HD ** -0.5).transpose(0, 2, 1, 3).reshape(1, L, D)
            h = x + o(a)
            return h + w2(nn.silu(w1(h)) * w3(h))
        res[f"{act_name}.ffn{ff}.block_ms"] = bench(block)
    res[f"{act_name}.block_speedup_pct"] = round(100 * (1 - res[f"{act_name}.ffn6400.block_ms"] / res[f"{act_name}.ffn10240.block_ms"]), 1)
print(json.dumps(res, indent=1))
