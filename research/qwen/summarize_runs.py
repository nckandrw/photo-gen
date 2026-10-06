"""Summarize research/qwen/runs/<id>/ (any mode) into one row per run: identity, timings, phases, memory, monitor.

Usage: python3 research/qwen/summarize_runs.py [run_id_prefix ...] > table.json   (stdlib only)
Sources per mode: app -> result.json (+ data/jobs/<job>/worker-result.json); worker0/1 -> worker/identity.json +
worker/worker-result.json; plain/sdcpp -> console.log (/usr/bin/time -l). Monitor: monitor.csv (1 Hz)."""
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "research" / "qwen" / "runs"


def monitor(d: Path) -> dict:
    p = d / "monitor.csv"
    if not p.exists():
        return {}
    rows = list(csv.DictReader(p.open()))
    if not rows:
        return {}

    def col(k):
        return [float(r[k]) for r in rows if r.get(k) not in ("", None)]
    sw, pl, fr = col("swap_used_mb"), col("pressure_level"), col("free_pct")
    return {"samples": len(rows), "swap_start_mb": sw[0] if sw else None, "swap_max_mb": max(sw) if sw else None,
            "swap_growth_mb": round(max(sw) - sw[0], 1) if sw else None, "pressure_max": max(pl) if pl else None,
            "warn_samples": sum(1 for x in pl if x == 2), "critical_samples": sum(1 for x in pl if x == 4),
            "min_free_pct": min(fr) if fr else None, "proc_mem_max_gb": max(col("proc_mem_gb") or [0]),
            "wired_max_gb": max(col("wired_gb") or [0])}


def time_l(text: str) -> dict:
    out = {}
    for k, pat in (("real_s", r"([\d.]+) real"), ("peak_footprint_gb", r"(\d+)\s+peak memory footprint"),
                   ("max_rss_gb", r"(\d+)\s+maximum resident set size")):
        m = re.search(pat, text)
        if m:
            v = float(m.group(1))
            out[k] = round(v / 1e9, 3) if k != "real_s" else v
    return out


def worker_view(res: dict) -> dict:
    ph = res.get("phases") or {}
    st = res.get("step_seconds") or []
    return {"phases": {k: (v["seconds"] if isinstance(v, dict) else v) for k, v in ph.items()},
            "phase_mlx_peak_gb": {k: v["mlx_peak_gb"] for k, v in ph.items() if isinstance(v, dict)},
            "active_gb": res.get("active_gb"), "peak_footprint_gb": res.get("peak_footprint_gb"),
            "mlx_peak_gb": res.get("mlx_peak_gb"), "denoise_mlx_peak_gb": res.get("denoise_mlx_peak_gb"),
            "steps": len(st), "step0_s": st[0] if st else None,
            "step_median_s": sorted(st)[len(st) // 2] if st else None, "step_last_s": st[-1] if st else None,
            "defer": (res.get("defer_transformer_load") or {}).get("installed")}


rows = []
for d in sorted(RUNS.iterdir()):
    if not d.is_dir() or (sys.argv[1:] and not any(d.name.startswith(p) for p in sys.argv[1:])):
        continue
    cond = (d / "conditions.txt").read_text() if (d / "conditions.txt").exists() else ""
    mode = (re.search(r"mode=(\S+)", cond) or [None, None])[1]
    row = {"run": d.name, "mode": mode, "res": (re.search(r"res=(\d+)", cond) or [None, None])[1],
           "aborted": "ABORT" in cond, "power": "AC" if "AC Power" in cond else ("battery" if "Battery" in cond else None),
           "monitor": monitor(d)}
    m = re.search(r"wall_s=(\d+) rc=(-?\d+)", cond)
    if m:
        row.update({"harness_wall_s": int(m.group(1)), "rc": int(m.group(2))})
    if mode == "app" and (d / "result.json").exists():
        try:
            j = json.loads((d / "result.json").read_text())
            row.update({"pixel_sha256": j.get("pixel_sha256"), "job_id": j.get("job_id"),
                        "generation_seconds": j.get("generation_seconds"), "status": j.get("status")})
            wr = ROOT / "data" / "jobs" / j["job_id"] / "worker-result.json"
            if wr.exists():
                row.update(worker_view(json.loads(wr.read_text())))
        except (ValueError, KeyError):
            row["status"] = "unparsable result.json"
    elif mode in ("worker0", "worker1") and (d / "worker" / "identity.json").exists():
        i = json.loads((d / "worker" / "identity.json").read_text())
        row.update({"pixel_sha256": i.get("pixel_sha256"), "generation_seconds": i.get("wall_seconds"),
                    "rgba_sha256": (i.get("output_alpha") or {}).get("rgba_sha256")})
        wr = d / "worker" / "worker-result.json"
        if wr.exists():
            row.update(worker_view(json.loads(wr.read_text())))
    elif mode in ("plain", "sdcpp") and (d / "console.log").exists():
        row.update(time_l((d / "console.log").read_text(errors="replace")))
    rows.append(row)
print(json.dumps(rows, indent=1))
