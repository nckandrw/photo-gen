"""Stage B objective metrics + timing summary (step-count quality gate).

grid16: row+column averaged 1-D |rfft| of mean-removed luminance; value at the
16-px period (bin n/16) divided by the median of bins n/16 +/- 4..8.
NOTE: the Stage A grid16 implementation was run inline and not preserved. This is
the best of 64 variants fitted against all 144 Stage A per-image values in
benchmark.csv: mean |error| 0.086, max |error| 0.46. It is NOT the Stage A code, so
Stage A images are re-scored here with the same code for a like-for-like
comparison. lapvar (4-neighbour Laplacian variance) reproduces Stage A exactly.
"""
import json, csv, statistics as st, sys
import numpy as np
from PIL import Image

def lum(p): return np.asarray(Image.open(p).convert("L"), dtype=np.float64)

def grid16(y):
    y = y - y.mean(); k = y.shape[0] // 16
    F = np.abs(np.fft.rfft(y, axis=1)).mean(0) + np.abs(np.fft.rfft(y, axis=0)).mean(1)
    return float(F[k] / np.median(np.r_[F[k-8:k-3], F[k+4:k+9]]))

def lapvar(y):
    l = -4*y[1:-1,1:-1] + y[:-2,1:-1] + y[2:,1:-1] + y[1:-1,:-2] + y[1:-1,2:]
    return float(l.var())

def load(path): return [json.loads(l) for l in open(path)]

def row(r, workdir):
    res = r["res"]; m = r["meta"]
    y = lum(f"{workdir}/{r['tag']}.png")
    return {"res": m["res"], "tag": r["tag"], "steps": m["steps"], "pid": m["pid"], "seed": m["seed"],
            "start": r["start"], "wall_s": r["wall_s"], "denoise_s": round(res["phases"]["denoise_seconds"], 3),
            "vae_s": res["phases"]["vae_decode"]["seconds"],
            "per_step_s": round(res["phases"]["denoise_seconds"] / m["steps"], 3),
            "peak_gb": res["peak_footprint_gb"],
            "swap_growth_mb": round(r["sys"]["swap_max_mb"] - r["sys"]["swap_start_mb"], 1),
            "pressure": r["sys"]["pressure_max"], "grid16": round(grid16(y), 2), "lapvar": round(lapvar(y), 1),
            "pixel_sha256": r["pixel_sha256"], "rc": r["rc"]}

if __name__ == "__main__":
    lo, hi = sys.argv[1], sys.argv[2]   # e.g. 5 8  (arms)
    rows, summary = [], {}
    for res in (512, 768, 1024):
        rs = [row(r, f"work-B-{res}") for r in load(f"results-B-{res}.jsonl")]
        rows += rs
        by = {(r["pid"], r["seed"], r["steps"]): r for r in rs}
        pairs = [(by[(p, s, int(lo))], by[(p, s, int(hi))]) for (p, s, n) in by if n == int(hi)]
        dr = [a["denoise_s"] / b["denoise_s"] for a, b in pairs]
        wr = [a["wall_s"] / b["wall_s"] for a, b in pairs]
        lr = [a["lapvar"] / b["lapvar"] for a, b in pairs]
        arms = {}
        for n in (lo, hi):
            a = [r for r in rs if r["steps"] == int(n)]
            arms[n] = {"denoise_med": round(st.median(r["denoise_s"] for r in a), 2),
                       "wall_med": round(st.median(r["wall_s"] for r in a), 2),
                       "per_step_med": round(st.median(r["per_step_s"] for r in a), 3),
                       "vae_med": round(st.median(r["vae_s"] for r in a), 3),
                       "peak_max": max(r["peak_gb"] for r in a),
                       "swap_growth_max_mb": max(r["swap_growth_mb"] for r in a),
                       "pressure_max": max(r["pressure"] for r in a),
                       "grid16_max": max(r["grid16"] for r in a), "grid16_med": round(st.median(r["grid16"] for r in a), 2),
                       "rc_nonzero": sum(r["rc"] != 0 for r in a), "n": len(a)}
        summary[res] = {f"paired_denoise_ratio_{lo}_{hi}": {"median": round(st.median(dr), 3), "min": round(min(dr), 3), "max": round(max(dr), 3)},
                        f"paired_wall_ratio_{lo}_{hi}": round(st.median(wr), 3),
                        f"lapvar_ratio_{lo}_{hi}_median": round(st.median(lr), 3), "n_pairs": len(pairs), "arms": arms}
        # Stage A re-score with the same grid16 code (like-for-like)
        a_rows = [json.loads(l) for l in open(f"results-A-{res}.jsonl")]
        g = {4: [], 8: []}
        for r in a_rows:
            g[r["meta"]["steps"]].append(grid16(lum(f"work-{res}/{r['tag']}.png")))
        summary[res]["stageA_grid16_rescored"] = {str(k): {"max": round(max(v), 2), "med": round(st.median(v), 2)} for k, v in g.items()}
    cold = []
    for r in load("results-B-cold.jsonl"):
        cold.append(row(r, "work-B-cold"))
    summary["cold_5step"] = {c["res"]: {"wall_s": c["wall_s"], "denoise_s": c["denoise_s"], "peak_gb": c["peak_gb"], "pixel_sha256": c["pixel_sha256"]} for c in cold}
    with open("benchmark-B.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows + cold)
    json.dump(summary, open("metrics-summary-B.json", "w"), indent=1)
    print(json.dumps(summary, indent=1))
