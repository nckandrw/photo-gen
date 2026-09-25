#!/usr/bin/env python3
"""Phase 3 pair analysis (sigma audit and FAST gates). numpy + Pillow only.

  p3_analyze.py pairs   <results.jsonl> <armA> <armB> <out_pairs.json>
        pairs file for blind_stage.py: [[name, pathA, pathB], ...] in (seed, prompt) order (reveals no arm)
  p3_analyze.py summary <results.jsonl> <armA> <armB> <out.json>
        per pair: PSNR/SSIM (B vs A), Laplacian-variance ratio B/A, denoise/wall ratios B/A;
        per arm: medians of wall/denoise/VAE, footprint max, swap growth max, pressure max, rc
Arm = meta.arm. Pair key = (res, pid, seed).
"""
import json, statistics as st, sys
import numpy as np
from PIL import Image
sys.path.insert(0, __import__("os").path.dirname(__file__))
from pair_metrics import lum, psnr, ssim  # noqa: E402

def load(path):
    rows = [json.loads(l) for l in open(path)]
    by = {}
    for r in rows:
        m = r["meta"]; by.setdefault((m["res"], m["pid"], m["seed"]), {})[m["arm"]] = r
    return rows, by

def out_path(r, results_path):
    import os
    d = os.path.join(os.path.dirname(results_path), "work-" + str(r["meta"]["res"]))
    return os.path.join(d, r["tag"] + ".png")

def lapvar(p):
    y = lum(p)
    l = -4 * y[1:-1, 1:-1] + y[:-2, 1:-1] + y[2:, 1:-1] + y[1:-1, :-2] + y[1:-1, 2:]
    return float(l.var())

def main():
    mode, path, A, B, out = sys.argv[1:6]
    rows, by = load(path)
    keys = sorted(by, key=lambda k: (k[2], k[1]))
    keys = [k for k in keys if A in by[k] and B in by[k]]
    if mode == "pairs":
        json.dump([[f"{k[1]}-s{k[2]}", out_path(by[k][A], path), out_path(by[k][B], path)] for k in keys],
                  open(out, "w"), indent=1)
        print(f"{len(keys)} pairs -> {out}"); return
    pairs = []
    for k in keys:
        a, b = by[k][A], by[k][B]
        pa, pb = out_path(a, path), out_path(b, path)
        p, mad = psnr(pa, pb)
        da, db = a["res"]["phases"]["denoise_seconds"], b["res"]["phases"]["denoise_seconds"]
        pairs.append({"pair": f"{k[1]}-s{k[2]}", "psnr_db": round(p, 2), "ssim": round(ssim(lum(pa), lum(pb)), 4),
                      "lapvar_ratio_B_over_A": round(lapvar(pb) / max(lapvar(pa), 1e-9), 3),
                      "denoise_ratio_B_over_A": round(db / da, 4), "wall_ratio_B_over_A": round(b["wall_s"] / a["wall_s"], 4),
                      "first": "A" if a["start"] <= b["start"] else "B"})
    def arm(name):
        rs = [by[k][name] for k in keys]
        g = lambda f: [f(r) for r in rs if f(r) is not None]
        sw = [(r["sys"]["swap_max_mb"] or 0) - (r["sys"]["swap_start_mb"] or 0) for r in rs]
        return {"n": len(rs), "rc_nonzero": sum(r["rc"] != 0 for r in rs),
                "wall_median_s": round(st.median(g(lambda r: r["wall_s"])), 2),
                "denoise_median_s": round(st.median(g(lambda r: r["res"]["phases"]["denoise_seconds"])), 2),
                "vae_median_s": round(st.median(g(lambda r: r["res"]["phases"]["vae_decode"]["seconds"])), 3),
                "footprint_max_gb": max(g(lambda r: r["res"]["peak_footprint_gb"])),
                "footprint_mean_gb": round(st.mean(g(lambda r: r["res"]["peak_footprint_gb"])), 3),
                "swap_growth_max_mb": round(max(sw), 2), "pressure_max": max(g(lambda r: r["sys"]["pressure_max"])),
                "compile_calls": sorted(set(g(lambda r: r["res"].get("compile_calls"))))}
    dr = [p["denoise_ratio_B_over_A"] for p in pairs]; wr = [p["wall_ratio_B_over_A"] for p in pairs]
    summ = {"A": A, "B": B, "arms": {A: arm(A), B: arm(B)},
            "denoise_ratio_B_over_A": {"median": round(st.median(dr), 4), "min": min(dr), "max": max(dr)},
            "wall_ratio_B_over_A": {"median": round(st.median(wr), 4), "min": min(wr), "max": max(wr)},
            "psnr_db": {"median": round(st.median(p["psnr_db"] for p in pairs), 2), "min": min(p["psnr_db"] for p in pairs)},
            "ssim": {"median": round(st.median(p["ssim"] for p in pairs), 4), "min": min(p["ssim"] for p in pairs)},
            "lapvar_ratio": {"median": round(st.median(p["lapvar_ratio_B_over_A"] for p in pairs), 3),
                             "min": min(p["lapvar_ratio_B_over_A"] for p in pairs), "max": max(p["lapvar_ratio_B_over_A"] for p in pairs)},
            "pairs": pairs}
    json.dump(summ, open(out, "w"), indent=1)
    print(json.dumps({k: v for k, v in summ.items() if k != "pairs"}, indent=1))

if __name__ == "__main__":
    main()
