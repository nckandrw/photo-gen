"""Replace the candidate TE's rotary_emb.inv_freq (recomputed in-process, differs from the stock pack by 1 ulp)
with the stock pack's value, so the only differing tensors vs stock are the abliterated weights.
The original file is kept as 0.safetensors.pre-invfreq (not matched by *.safetensors). Usage: align_inv_freq.py <stock_te_dir> <cand_dir>"""
import glob, hashlib, os, struct, json, sys
import mlx.core as mx
stock_dir, cand = sys.argv[1:3]
stock = {}
for f in sorted(glob.glob(f"{stock_dir}/*.safetensors")): stock.update(mx.load(f))
src = f"{cand}/0.safetensors"
with open(src, "rb") as fh:
    n = struct.unpack("<Q", fh.read(8))[0]; meta = json.loads(fh.read(n)).get("__metadata__", {})
w = mx.load(src)
mx.eval(list(w.values()))  # materialize before the source file is renamed
k = "rotary_emb.inv_freq"
if bool(mx.array_equal(w[k], stock[k]).item()):
    print("already aligned"); sys.exit(0)
os.rename(src, src + ".pre-invfreq")
w[k] = stock[k]
meta["inv_freq"] = "copied from stock pack (align_inv_freq.py)"
mx.save_safetensors(src, w, metadata=meta)
diff = [x for x in stock if not bool(mx.array_equal(mx.load(src)[x], stock[x]).item())]
print(json.dumps({"sha256": hashlib.sha256(open(src, "rb").read()).hexdigest(), "differing_tensors": len(diff),
                  "differing_non_weight": [x for x in diff if not any(s in x for s in ("o_proj", "down_proj"))]}))
