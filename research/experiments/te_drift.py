"""Text-encoder conditioning drift: how much does a modified TE change what the DiT receives?
Encodes each prompt with the stock q4 TE and a candidate q4 TE (same tokenizer/chat template: the stock pack's),
and compares the conditioning tensors cap_feats [T, 2560] token-by-token.
Metrics per prompt: mean/min per-token cosine similarity, relative L2 ||B-A||/||A||, cosine of mean-pooled vectors.
No images are generated. Usage: te_drift.py <stock_pack_dir> <candidate_te_dir> <prompts.json> <out.json>
prompts.json: {"set_name": {"id": "prompt", ...}, ...}"""
import json, sys
import mlx.core as mx
from mflux.models.common.config.model_config import ModelConfig
from mflux.models.common.tokenizer.tokenizer_loader import TokenizerLoader
from mflux.models.z_image.model.z_image_text_encoder.prompt_encoder import PromptEncoder
from mflux.models.z_image.model.z_image_text_encoder.text_encoder import TextEncoder
from mflux.models.z_image.weights.z_image_weight_definition import ZImageWeightDefinition
import mlx.nn as nn

stock_dir, cand_dir, prompts_path, out_path = sys.argv[1:5]

def load_te(te_dir):
    te = TextEncoder()
    nn.quantize(te, group_size=64, bits=4, class_predicate=lambda p, m: hasattr(m, "to_quantized"))
    ws = {}
    import glob
    for f in sorted(glob.glob(f"{te_dir}/*.safetensors")):
        ws.update(mx.load(f))
    te.load_weights(list(ws.items()), strict=False)
    mx.eval(te.parameters())
    return te

tok = TokenizerLoader.load_all(definitions=ZImageWeightDefinition.get_tokenizers(), model_path=stock_dir)["z_image"]
A, B = load_te(f"{stock_dir}/text_encoder"), load_te(cand_dir)
prompts = json.load(open(prompts_path))
rows = []
for set_name, items in prompts.items():
    for pid, p in items.items():
        a = PromptEncoder.encode_prompt(prompt=p, tokenizer=tok, text_encoder=A).astype(mx.float32)
        b = PromptEncoder.encode_prompt(prompt=p, tokenizer=tok, text_encoder=B).astype(mx.float32)
        cos = (a * b).sum(-1) / (mx.linalg.norm(a, axis=-1) * mx.linalg.norm(b, axis=-1) + 1e-12)
        rel = mx.linalg.norm(b - a) / (mx.linalg.norm(a) + 1e-12)
        pa, pb = a.mean(0), b.mean(0)
        pooled = (pa * pb).sum() / (mx.linalg.norm(pa) * mx.linalg.norm(pb) + 1e-12)
        rows.append({"set": set_name, "id": pid, "tokens": a.shape[0], "tok_cos_mean": round(float(cos.mean()), 5),
                     "tok_cos_min": round(float(cos.min()), 5), "rel_l2": round(float(rel), 5), "pooled_cos": round(float(pooled), 5)})
        print(rows[-1], flush=True)
agg = {}
for s in prompts:
    r = [x for x in rows if x["set"] == s]
    agg[s] = {k: round(sum(x[k] for x in r) / len(r), 5) for k in ("tok_cos_mean", "tok_cos_min", "rel_l2", "pooled_cos")}
json.dump({"per_prompt": rows, "by_set": agg}, open(out_path, "w"), indent=1)
print(json.dumps(agg, indent=1))
