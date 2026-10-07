"""G2 tally (protocol.md §7–§9), written and committed before any G2 output existed. Mechanical: it applies the
pre-registered thresholds to the FROZEN rater scores and the run records; it never re-scores anything.

Inputs:  research/qwen/runs/G2-*/ (result.json from `bin/photo-gen edit --json`, monitor.csv, conditions.txt; the job
         sidecar named by result.json), research/editing/real-world/g2/{SCORES-FROZEN.csv, key-unblinded.json}.
Outputs: benchmark.csv (one row per run), scores.csv (frozen scores + unblinded mapping), results-summary.json.

Usage: python3 research/editing/real-world/analyze_g2.py [--runs-only]   (stdlib only)"""
import csv
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RUNS = ROOT / "research" / "qwen" / "runs"
TASKS = {t["id"]: t for t in json.loads((HERE / "task-manifest.json").read_text())["tasks"]}
TEXT_ITEMS = [k for k, t in TASKS.items() if t["text"]]


def monitor(d: Path) -> dict:
    rows = list(csv.DictReader((d / "monitor.csv").open())) if (d / "monitor.csv").exists() else []
    sw = [float(r["swap_used_mb"]) for r in rows if r.get("swap_used_mb")]
    pl = [float(r["pressure_level"]) for r in rows if r.get("pressure_level")]
    fr = [float(r["free_pct"]) for r in rows if r.get("free_pct")]
    return {"samples": len(rows), "swap_start_mb": sw[0] if sw else None,
            "swap_growth_gb": round((max(sw) - sw[0]) / 1024, 3) if sw else None,
            "warn_samples": sum(1 for x in pl if x == 2), "critical_samples": sum(1 for x in pl if x == 4),
            "min_free_pct": min(fr) if fr else None}


def run_row(d: Path) -> dict:
    parts = d.name.split("-")  # G2-<budget>-<task>[-s2|-rep]
    budget, task = int(parts[1]), parts[2]
    kind = {"s2": "second_seed", "rep": "repeat"}.get(parts[3] if len(parts) > 3 else "", "primary")
    cond = (d / "conditions.txt").read_text() if (d / "conditions.txt").exists() else ""
    end = [ln for ln in cond.splitlines() if ln.startswith("wall_s=")]
    rc = int(end[-1].split("rc=")[1].split()[0]) if end else None
    aborted = int(end[-1].split("aborted=")[1].split()[0]) if end else None
    try:
        res = json.loads((d / "result.json").read_text())
    except (OSError, ValueError):
        res = {}
    meta = {}
    if res.get("metadata_path") and Path(res["metadata_path"]).exists():
        meta = json.loads(Path(res["metadata_path"]).read_text())
    ph = res.get("phases") or {}
    mem = res.get("memory") or {}
    row = {"run": d.name, "task": task, "budget": budget, "kind": kind, "seed": res.get("seed"),
           "status": res.get("status"), "rc": rc, "aborted": aborted, "job_id": res.get("job_id"),
           "backend_id": res.get("backend_id"), "configuration_id": meta.get("configuration_id"),
           "edit_id": meta.get("edit_id"), "input_pixel_sha256": (meta.get("input_image") or {}).get("pixel_sha256"),
           "pixel_sha256": res.get("pixel_sha256"), "rgba_sha256": (meta.get("output_alpha") or {}).get("rgba_sha256"),
           "width": meta.get("width"), "height": meta.get("height"), "output_path": res.get("output_path"),
           "wall_s": res.get("generation_seconds"), "denoise_s": ph.get("denoise_seconds"),
           "text_encode_s": (ph.get("text_encode") or {}).get("seconds"),
           "vae_encode_s": (ph.get("vae_encode") or {}).get("seconds"),
           "vae_decode_s": (ph.get("vae_decode") or {}).get("seconds"),
           "peak_footprint_gb": mem.get("peak_footprint_gb"), "mlx_peak_gb": mem.get("mlx_peak_gb"),
           "memory_policy": json.dumps((meta.get("execution") or {}).get("memory_policy"), sort_keys=True),
           **monitor(d)}
    return row


def runs() -> list[dict]:
    rows = [run_row(d) for d in sorted(RUNS.glob("G2-*")) if d.is_dir()]
    if rows:
        with (HERE / "benchmark.csv").open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    return rows


def effective(s: dict) -> tuple[str, str]:
    """Text failures count as real errors (protocol §6): on requested text -> adherence FAIL; on text that had to
    stay -> preservation FAIL."""
    adh, pres = s["adherence"], s["preservation"]
    t = TASKS[s["task"]]["text"]
    if s["text"] == "FAIL" and t == "change":
        adh = "FAIL"
    if s["text"] == "FAIL" and t == "preserve":
        pres = "FAIL"
    return adh, pres


def memory_class(rs: list[dict]) -> dict:
    walls = [r["wall_s"] for r in rs if r["wall_s"] is not None]
    growth = [r["swap_growth_gb"] for r in rs if r["swap_growth_gb"] is not None]
    crit = sum(r["critical_samples"] or 0 for r in rs)
    warn_frac = max((r["warn_samples"] or 0) / r["samples"] for r in rs if r["samples"])
    aborts = sum(1 for r in rs if r["aborted"])
    m = {"runs": len(rs), "median_wall_s": statistics.median(walls), "max_wall_s": max(walls),
         "critical_samples": crit, "median_swap_growth_gb": statistics.median(growth),
         "max_swap_growth_gb": max(growth), "max_warn_fraction": round(warn_frac, 3), "aborts": aborts,
         "median_peak_footprint_gb": statistics.median(r["peak_footprint_gb"] for r in rs if r["peak_footprint_gb"])}
    if m["median_wall_s"] <= 180 and crit == 0 and m["median_swap_growth_gb"] <= 0.25 and \
            m["max_swap_growth_gb"] <= 0.5 and warn_frac <= 0.05:
        m["class"] = "COMFORTABLE"
    elif m["median_wall_s"] <= 360 and crit == 0 and m["median_swap_growth_gb"] <= 1.0 and m["max_swap_growth_gb"] <= 2.0:
        m["class"] = "USABLE"
    elif m["median_wall_s"] <= 900 and crit == 0 and aborts == 0 and m["max_swap_growth_gb"] <= 4.0:
        m["class"] = "MARGINAL"
    else:
        m["class"] = "NOT PRACTICAL"
    return m


def gate(budget: int, rows: list[dict], scores: dict) -> dict:
    rs = [r for r in rows if r["budget"] == budget]
    prim = {r["task"]: r for r in rs if r["kind"] == "primary"}
    s_prim = [scores[(budget, t, "primary")] for t in sorted(prim)]
    eff = [effective(s) for s in s_prim]
    adh = [a for a, _ in eff]
    pres = [p for _, p in eff]
    fam: dict = {}
    for s in s_prim:
        if s["quality"] in ("MINOR", "MAJOR"):
            fam[s["quality_family"]] = fam.get(s["quality_family"], 0) + 1
    txt = [scores[(budget, t, "primary")]["text"] for t in TEXT_ITEMS if t in prim]
    s2 = [scores[(budget, r["task"], "second_seed")] for r in rs if r["kind"] == "second_seed"]
    s2_fails = sum((a == "FAIL") + (p == "FAIL") for a, p in (effective(s) for s in s2))
    reps = [r for r in rs if r["kind"] == "repeat"]
    det = [{"task": r["task"], "pixel_equal": r["pixel_sha256"] == prim[r["task"]]["pixel_sha256"],
            "rgba_equal": r["rgba_sha256"] == prim[r["task"]]["rgba_sha256"],
            "ids_equal": (r["configuration_id"], r["edit_id"]) == (prim[r["task"]]["configuration_id"],
                                                                   prim[r["task"]]["edit_id"])} for r in reps]
    ops_bad = [r["run"] for r in rs if r["rc"] != 0 or r["status"] != "completed" or r["aborted"]
               or (r["critical_samples"] or 0) > 0]
    c = {
        "A1": {"FAIL": adh.count("FAIL"), "PARTIAL": adh.count("PARTIAL")},
        "A2": {"FAIL": pres.count("FAIL"), "PARTIAL": pres.count("PARTIAL")},
        "A3": {"FAIL": sum(s["composition"] == "FAIL" for s in s_prim)},
        "A4": {"MAJOR": sum(s["quality"] == "MAJOR" for s in s_prim), "families": fam},
        "A5": {"FAIL": txt.count("FAIL"), "PARTIAL": txt.count("PARTIAL"), "items": len(txt)},
        "O": {"bad_runs": ops_bad, "runs": len(rs)},
        "D": det,
        "S": {"fail_marks": s2_fails, "items": len(s2)},
    }
    ok = {"A1": c["A1"]["FAIL"] == 0 and c["A1"]["PARTIAL"] <= 2,
          "A2": c["A2"]["FAIL"] == 0 and c["A2"]["PARTIAL"] <= 3,
          "A3": c["A3"]["FAIL"] <= 1,
          "A4": c["A4"]["MAJOR"] <= 1 and all(n < 6 for n in fam.values()),
          "A5": c["A5"]["FAIL"] == 0 and c["A5"]["PARTIAL"] <= 1,
          "O": not ops_bad,
          "D": all(x["pixel_equal"] and x["rgba_equal"] and x["ids_equal"] for x in det),
          "S": s2_fails <= 1}
    mc = memory_class(rs)
    g2_pass = all(ok.values())
    if g2_pass and mc["class"] in ("COMFORTABLE", "USABLE"):
        decision = "VALIDATED FOR LOCAL/PERSONAL USE"
    elif c["A1"]["FAIL"] >= 3 or c["A2"]["FAIL"] >= 3 or len(ops_bad) >= 2 or mc["class"] == "NOT PRACTICAL":
        decision = "REJECTED"
    else:
        decision = "EXPERIMENTAL"
    cfg_ids = sorted({r["configuration_id"] for r in rs if r["configuration_id"]})
    return {"budget": budget, "counts": c, "criteria": ok, "g2_pass": g2_pass, "memory": mc, "decision": decision,
            "configuration_ids": cfg_ids}


def main() -> None:
    rows = runs()
    if "--runs-only" in sys.argv:
        print(f"benchmark.csv: {len(rows)} runs")
        return
    g2 = HERE / "g2"
    key = json.loads((g2 / "key-unblinded.json").read_text())
    frozen = list(csv.DictReader((g2 / "SCORES-FROZEN.csv").open()))
    by_run = {r["run"]: r for r in rows}
    scores, out = {}, []
    for s in frozen:
        k = key[s["id"]]
        r = by_run[k["run"]]
        rec = {**s, "run": k["run"], "task": k["task"], "budget": k["budget"], "seed": k["seed"], "kind": r["kind"]}
        scores[(k["budget"], k["task"], r["kind"])] = rec
        out.append(rec)
    out.sort(key=lambda x: (x["budget"], x["task"], x["kind"]))
    with (HERE / "scores.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    res = {b: gate(b, rows, scores) for b in (512, 1024)}
    labels = [res[b]["decision"] for b in (512, 1024)]
    overall = ("VALIDATED FOR LOCAL/PERSONAL USE" if "VALIDATED FOR LOCAL/PERSONAL USE" in labels
               else "EXPERIMENTAL" if "EXPERIMENTAL" in labels else "REJECTED")
    summary = {"per_budget": res, "overall": overall}
    (HERE / "results-summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
