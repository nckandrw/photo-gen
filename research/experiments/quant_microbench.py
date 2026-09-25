"""Quantization-format microbenchmark (quantization-map.md). Synthetic weights, production DiT shapes, one block's
linears (Q, K, V, O: 3840->3840; w1, w3: 3840->10240; w2: 10240->3840). No model files are touched.

Usage: quant_microbench.py <fp32|bf16> <L> <out.json>
For each format: median ms for the 7 linears of one block, effective TFLOPS, bits/weight incl. scales/biases,
and the max relative error of the quantized weights vs the source weights (a format-intrinsic error on Gaussian
weights; it is NOT an image-quality measure).
"""
import json, statistics, sys, time
import mlx.core as mx
import mlx.nn as nn

act = {"fp32": mx.float32, "bf16": mx.bfloat16}[sys.argv[1]]; L = int(sys.argv[2]); out = sys.argv[3]
D, FF = 3840, 10240
SHAPES = [(D, D)] * 4 + [(D, FF), (D, FF), (FF, D)]
FORMATS = [("bf16-weights", None, None, None)] + \
    [(f"affine-b{b}-g{g}", "affine", b, g) for b in (3, 4, 5, 6, 8) for g in (32, 64, 128)] + \
    [("mxfp4", "mxfp4", 4, 32), ("nvfp4", "nvfp4", 4, 16), ("mxfp8", "mxfp8", 8, 32)]
mx.random.seed(0)
x = {D: mx.random.normal((1, L, D)).astype(act), FF: mx.random.normal((1, L, FF)).astype(act)}
res = {"act": sys.argv[1], "L": L, "mlx": mx.__version__, "device": mx.device_info()["architecture"], "formats": {}}
flops = sum(2 * L * i * o for i, o in SHAPES)

def bench(fn, reps=6):
    for _ in range(2): mx.eval(fn())
    mx.synchronize(); ts = []
    for _ in range(reps):
        t = time.perf_counter(); mx.eval(fn()); mx.synchronize(); ts.append(time.perf_counter() - t)
    return statistics.median(ts)

for name, mode, bits, gs in FORMATS:
    try:
        layers, bpw, err = [], [], []
        for i, o in SHAPES:
            l = nn.Linear(i, o, bias=False); w = (mx.random.normal((o, i)) * 0.02).astype(mx.bfloat16); l.weight = w
            if mode is None:
                layers.append(l); bpw.append(16.0); continue
            ql = nn.QuantizedLinear.from_linear(l, group_size=gs, bits=bits, mode=mode)
            layers.append(ql)
            nbytes = sum(v.nbytes for v in (ql.weight, ql.scales, getattr(ql, "biases", None)) if v is not None)
            bpw.append(8 * nbytes / (i * o))
            if len(err) < 1:  # format-intrinsic weight error on the first shape
                wd = mx.dequantize(ql.weight, ql.scales, getattr(ql, "biases", None), group_size=gs, bits=bits, mode=mode)
                err.append(float((mx.abs(wd.astype(mx.float32) - w.astype(mx.float32)).mean() / mx.abs(w.astype(mx.float32)).mean()).item()))
        mx.eval([lay.parameters() for lay in layers])
        fn = lambda: [lay(x[s[0]]) for lay, s in zip(layers, SHAPES)]
        t = bench(fn)
        res["formats"][name] = {"block_linears_ms": round(t * 1000, 2), "tflops": round(flops / t / 1e12, 2),
                                "bits_per_weight": round(statistics.mean(bpw), 3),
                                "weight_rel_mean_abs_err": round(err[0], 5) if err else 0.0}
    except Exception as e:  # a format/kernel may be unsupported for this dtype: record, don't hide
        res["formats"][name] = {"error": f"{type(e).__name__}: {e}"}
    print(name, res["formats"][name], flush=True)
    del layers
json.dump(res, open(out, "w"), indent=1)
