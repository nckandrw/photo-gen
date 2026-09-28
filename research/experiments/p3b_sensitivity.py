#!/usr/bin/env python3
"""Block-sensitivity analysis (block-sensitivity-map.md): PSNR/SSIM of each perturbed image vs its uncompiled baseline."""
import json, os, sys, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pair_metrics import lum, psnr, ssim
out = {}
for res, path, work in ((512, "p3b/results-sens-512.jsonl", "p3b/work-sens512"), (1024, "p3b/results-sens-1024.jsonl", "p3b/work-sens1024")):
    rows = [json.loads(l) for l in open(path)]
    img = lambda tag: f"{work}/{tag}.png"
    base = {r["meta"]["pid"]: r["tag"] for r in rows if r["meta"]["mode"] == "none"}
    res_rows = []
    for r in rows:
        m = r["meta"]
        if m["mode"] != "perturb": continue
        b = img(base[m["pid"]]); p = img(r["tag"])
        ps, _ = psnr(b, p)
        res_rows.append({"block": m["block"], "kind": m["kind"], "pid": m["pid"], "psnr": round(ps, 2), "ssim": round(ssim(lum(b), lum(p)), 4),
                         "identical": r["pixel_sha256"] == next(x["pixel_sha256"] for x in rows if x["tag"] == base[m["pid"]])})
    out[res] = res_rows
    print(f"{res}: {len(res_rows)} perturbed images scored", flush=True)
json.dump(out, open("p3b/sensitivity-metrics.json", "w"), indent=1)
