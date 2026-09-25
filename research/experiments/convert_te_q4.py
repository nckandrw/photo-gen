"""Convert a Hugging Face Qwen3-4B-layout text encoder (e.g. an abliterated Z-Image TE) into the same MLX q4 format
as the stock mflux-community/z-image-turbo-mflux-q4 pack, then compare tensor-by-tensor against the stock pack.

Procedure (mirrors mflux 0.20.0's own loading/quantization path):
  1. key rename per mflux ZImageWeightMapping.get_text_encoder_mapping: 'model.<X>' -> '<X>'  (lm_head dropped: tied)
  2. cast to ModelConfig.precision (bf16)
  3. load into mflux's own TextEncoder module; nn.quantize(bits=4, group_size=64) with mflux's predicate
     (any module with .to_quantized, which includes embed_tokens)
  4. save as <out>/0.safetensors + model.safetensors.index.json with quantization_level metadata
Validation: every stock-pack key must exist with identical shape/dtype; tensors are classified
bit-identical vs different (unmodified tensors should be bit-identical if the converter matches mflux's procedure).

Usage: convert_te_q4.py <hf_src_dir> <out_dir> <stock_pack_text_encoder_dir> <report.json>
"""
import glob, hashlib, json, os, sys
import mlx.core as mx
import mlx.nn as nn
from mlx.utils import tree_flatten
from mflux.models.common.config.model_config import ModelConfig
from mflux.models.z_image.model.z_image_text_encoder.text_encoder import TextEncoder

src, out, stock_dir, report = sys.argv[1:5]
os.makedirs(out, exist_ok=True)

w = {}
for f in sorted(glob.glob(f"{src}/*.safetensors")):
    for k, v in mx.load(f).items():
        if k.startswith("lm_head."):
            continue
        if not k.startswith("model."):
            raise SystemExit(f"unexpected key {k}")
        w[k[len("model."):]] = v.astype(ModelConfig.precision)

te = TextEncoder()
expected = {k for k, _ in tree_flatten(te.parameters())}
missing = sorted(expected - set(w) - {"rotary_emb.inv_freq"})
unexpected = sorted(set(w) - expected)
if missing or unexpected:
    raise SystemExit(f"key mismatch: missing={missing[:5]} unexpected={unexpected[:5]}")
te.load_weights(list(w.items()), strict=False)
nn.quantize(te, group_size=64, bits=4, class_predicate=lambda p, m: hasattr(m, "to_quantized"))
params = dict(tree_flatten(te.parameters()))
mx.eval(params)
meta = {"quantization_level": "4", "mflux_version": "0.20.0", "converted_from": os.path.abspath(src),
        "procedure": "photo-gen research/experiments/convert_te_q4.py"}
mx.save_safetensors(f"{out}/0.safetensors", params, metadata=meta)
json.dump({"metadata": {"quantization_level": "4", "mflux_version": "0.20.0"},
           "weight_map": {k: "0.safetensors" for k in sorted(params)}}, open(f"{out}/model.safetensors.index.json", "w"), indent=2)

# ---- compare against the stock pack ----
stock = {}
for f in sorted(glob.glob(f"{stock_dir}/*.safetensors")):
    stock.update(mx.load(f))
res = {"identical": [], "different": [], "shape_or_dtype_mismatch": [], "missing_in_new": [], "extra_in_new": []}
for k, sv in stock.items():
    nv = params.get(k)
    if nv is None:
        res["missing_in_new"].append(k); continue
    if nv.shape != sv.shape or nv.dtype != sv.dtype:
        res["shape_or_dtype_mismatch"].append([k, list(sv.shape), str(sv.dtype), list(nv.shape), str(nv.dtype)]); continue
    (res["identical"] if bool(mx.array_equal(nv, sv).item()) else res["different"]).append(k)
res["extra_in_new"] = sorted(set(params) - set(stock))
summ = {k: len(v) for k, v in res.items()}
# group differing tensors by module type (e.g. self_attn.o_proj, mlp.down_proj)
from collections import Counter
kinds = Counter(".".join(k.split(".")[2:-1]) if k.startswith("layers.") else k.rsplit(".", 1)[0] for k in res["different"])
layers = sorted({int(k.split(".")[1]) for k in res["different"] if k.startswith("layers.")})
summary = {"counts": summ, "different_by_module": dict(kinds), "different_layers": layers,
           "output_sha256": hashlib.sha256(open(f"{out}/0.safetensors", "rb").read()).hexdigest()}
json.dump({"summary": summary, "detail": res}, open(report, "w"), indent=1)
print(json.dumps(summary, indent=1))
