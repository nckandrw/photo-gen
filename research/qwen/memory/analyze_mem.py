"""Tally the Phase 5 memory-lifetime A/B against research/qwen/memory/PROTOCOL.md §5 (mechanical; stdlib only).

Reads research/qwen/runs/M5-*/ (worker/identity.json, monitor.csv, conditions.txt) and the preflight JSONs; writes
research/qwen/memory/ab-summary.json and prints the per-stage table rows used in QWEN-MEMORY-LIFETIME.md."""
import csv
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / "research" / "qwen" / "runs"
G0 = {512: "bd548f1bf8cace9b", 1024: "792fdaa977a16567"}
STAGES = ["startup", "after_load", "after_text_encode", "after_vae_encode", "before_loop", "after_step0",
          "after_loop", "after_vae_decode", "end"]


def mon(d: Path) -> dict:
    rows = list(csv.DictReader((d / "monitor.csv").open()))
    sw = [float(r["swap_used_mb"]) for r in rows if r["swap_used_mb"]]
    pl = [float(r["pressure_level"]) for r in rows if r["pressure_level"]]
    fr = [float(r["free_pct"]) for r in rows if r["free_pct"]]
    return {"samples": len(rows), "swap_growth_gb": round((max(sw) - sw[0]) / 1024, 3), "warn": pl.count(2),
            "critical": pl.count(4), "min_free_pct": min(fr)}


def load(rid: str) -> dict:
    d = RUNS / rid
    i = json.loads((d / "worker" / "identity.json").read_text())
    ph = i["phases"] or {}
    return {"run": rid, "rc": i["rc"], "wall": i["wall_seconds"], "pixel": i["pixel_sha256"],
            "rgba": i["output_alpha"]["rgba_sha256"], "peak": i["peak_footprint_gb"], "mlx_peak": i["mlx_peak_gb"],
            "denoise_mlx_peak": i["denoise_mlx_peak_gb"], "denoise_active_max": i["denoise_active_gb_max"],
            "denoise_s": ph.get("denoise_seconds"), "decode_s": (ph.get("vae_decode") or {}).get("seconds"),
            "text_encode": ph.get("text_encode"), "vae_encode": ph.get("vae_encode"), "vae_decode": ph.get("vae_decode"),
            "load": ph.get("load"), "footprint": i["footprint_gb"], "active": i["active_gb"],
            "policy": i["memory_policy"], "aborted": "aborted=1" in (d / "conditions.txt").read_text(), **mon(d)}


def main() -> None:
    runs = {d.name: load(d.name) for d in sorted(RUNS.glob("M5-*")) if (d / "worker" / "identity.json").exists()}
    pairs = [("M5-512-E05-P0", "M5-512-E05-P2"), ("M5-512-E08c-P0", "M5-512-E08c-P2"),
             ("M5-1024-E05-P0a", "M5-1024-E05-P2a"), ("M5-1024-E05-P0b", "M5-1024-E05-P2b"),
             ("M5-1024-E08c-P0", "M5-1024-E08c-P2")]
    parity = [{"pair": p, "rgb": runs[p[0]]["pixel"] == runs[p[1]]["pixel"],
               "rgba": runs[p[0]]["rgba"] == runs[p[1]]["rgba"]} for p in pairs]
    g0 = {512: runs["M5-512-E05-P0"]["pixel"].startswith(G0[512]),
          1024: runs["M5-1024-E05-P0a"]["pixel"].startswith(G0[1024])}
    det = {"P0": runs["M5-1024-E05-P0a"]["pixel"] == runs["M5-1024-E05-P0b"]["pixel"],
           "P2": runs["M5-1024-E05-P2a"]["pixel"] == runs["M5-1024-E05-P2b"]["pixel"]}
    p1024 = pairs[2:]
    dpeak = [runs[a]["peak"] - runs[b]["peak"] for a, b in p1024]
    swap0 = statistics.median(runs[a]["swap_growth_gb"] for a, _ in p1024)
    swap2 = statistics.median(runs[b]["swap_growth_gb"] for _, b in p1024)
    wall0 = statistics.median(runs[a]["wall"] for a, _ in p1024)
    wall2 = statistics.median(runs[b]["wall"] for _, b in p1024)
    ddec = [runs[b]["decode_s"] - runs[a]["decode_s"] for a, b in p1024]
    p2 = [r for k, r in runs.items() if k.endswith(("P2", "P2a", "P2b"))]
    crit = {
        "1_parity": all(x["rgb"] and x["rgba"] for x in parity) and all(g0.values()),
        "2_determinism": all(det.values()),
        "3_reduction": statistics.median(dpeak) >= 0.75 and swap2 <= swap0,
        "4_runtime": wall2 <= 1.03 * wall0 and max(ddec) <= 3.0,
        "5_operational": all(r["rc"] == 0 and not r["aborted"] and r["critical"] == 0 for r in p2),
    }
    summary = {"parity": parity, "g0_match": g0, "determinism": det,
               "peak_reduction_1024_gb": [round(x, 3) for x in dpeak],
               "median_peak_reduction_1024_gb": round(statistics.median(dpeak), 3),
               "median_swap_growth_1024_gb": {"P0": swap0, "P2": swap2},
               "median_wall_1024_s": {"P0": wall0, "P2": wall2, "ratio": round(wall2 / wall0, 4)},
               "decode_delta_1024_s": [round(x, 3) for x in ddec], "criteria": crit,
               "verdict": "ADOPT" if all(crit.values()) else "NOT ADOPTED", "runs": runs}
    (Path(__file__).parent / "ab-summary.json").write_text(json.dumps(summary, indent=1))
    for k, r in runs.items():
        fp = r["footprint"]
        print(k, r["rc"], r["wall"], r["pixel"][:16], r["rgba"][:16], "peak", r["peak"], "mlx", r["mlx_peak"],
              "den_mlx", r["denoise_mlx_peak"], "swap+", r["swap_growth_gb"], "w/c", r["warn"], r["critical"],
              "| fp", [fp.get(s) for s in STAGES])
    print(json.dumps({k: v for k, v in summary.items() if k != "runs"}, indent=1))


if __name__ == "__main__":
    main()
