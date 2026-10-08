"""Mechanical tally of the Phase 6 Q-Q diagnostic (research/qwen/qq/PROTOCOL.md §5 and §8). Written and committed
before any Q-Q output existed; it only reads the frozen sheets, the unblinded key and the run records.

Usage: mflux/.venv/bin/python3.12 research/qwen/qq/analyze_qq.py <qq_review_dir> <summary.json>"""
import csv
import json
import math
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / "research/qwen/runs"
QQ = ROOT / "research/qwen/qq"
LEGIBLE = {"PRESERVED", "DEGRADED"}
NOT_LEGIBLE = {"GARBLED", "REMOVED"}


def js(p: Path) -> dict:
    return json.loads(p.read_text()) if p.exists() else {}


def run_record(rid: str) -> dict:
    d = RUNS / rid
    ident = js(d / "worker" / "identity.json")
    cond = (d / "conditions.txt").read_text() if (d / "conditions.txt").exists() else ""
    rows = list(csv.DictReader((d / "monitor.csv").open())) if (d / "monitor.csv").exists() else []
    swaps = [float(r["swap_used_mb"]) for r in rows if r.get("swap_used_mb")]
    levels = [int(r["pressure_level"]) for r in rows if r.get("pressure_level")]
    free = [int(r["free_pct"]) for r in rows if r.get("free_pct")]
    return {"run": rid, "rc": ident.get("rc"), "aborted": "ABORT" in cond, "pixel_sha256": ident.get("pixel_sha256"),
            "rgba_sha256": (ident.get("output_alpha") or {}).get("rgba_sha256"), "size": ident.get("size"),
            "wall_seconds": ident.get("wall_seconds"), "peak_footprint_gb": ident.get("peak_footprint_gb"),
            "mlx_peak_gb": ident.get("mlx_peak_gb"), "denoise_mlx_peak_gb": ident.get("denoise_mlx_peak_gb"),
            "phases": ident.get("phases"), "memory_policy": ident.get("memory_policy"), "model_path": ident.get("model_path"),
            "worker_sha256": ident.get("worker_sha256"),
            "swap_growth_gb": round((max(swaps) - swaps[0]) / 1024, 3) if swaps else None,
            "warn_samples": sum(1 for x in levels if x == 2), "critical_samples": sum(1 for x in levels if x == 4),
            "samples": len(levels), "min_free_pct": min(free) if free else None}


def g2_identity(budget: int, task: str, kind: str) -> dict:
    d = RUNS / f"G2-{budget}-{task}{'-s2' if kind == 'second_seed' else ''}"
    return {"pixel_sha256": js(d / "result.json").get("pixel_sha256"),
            "rgba_sha256": (js(d / "sidecar.json").get("output_alpha") or {}).get("rgba_sha256")}


def main(review: str, out: str) -> None:
    rv = Path(review)
    key = js(rv / "key-unblinded.json")
    scores = {r["id"]: r for r in csv.DictReader((rv / "SCORES-FROZEN.csv").open())}
    prefs = {r["sheet"]: r for r in csv.DictReader((rv / "PREFERENCE-FROZEN.csv").open())}
    sheets, units = [], []
    for sid, k in sorted(key.items()):
        arm_row = {k["A"]: scores[f"{sid}-A"], k["B"]: scores[f"{sid}-B"]}
        pref = prefs[sid]["text_preference"]
        winner = "SAME" if pref == "SAME" else k[pref]
        rec = {"sheet": sid, "pair": k["pair"], "task": k["task"], "budget": k["budget"], "kind": k["kind"],
               "seed": k["seed"], "q4_run": k[f"{'A' if k['A'] == 'q4' else 'B'}_run"],
               "q8_run": k[f"{'A' if k['A'] == 'q8' else 'B'}_run"], "text_preference_arm": winner,
               "q4": {c: arm_row["q4"][c] for c in ("adherence", "preservation", "composition", "quality", "quality_family", "text")},
               "q8": {c: arm_row["q8"][c] for c in ("adherence", "preservation", "composition", "quality", "quality_family", "text")},
               "elements": {}}
        for i in range(1, 6):
            a, b = arm_row["q4"][f"t{i}"], arm_row["q8"][f"t{i}"]
            if a == "-":
                continue
            rec["elements"][f"t{i}"] = {"q4": a, "q8": b}
            if a == "NA":
                continue
            units.append({"sheet": sid, "task": k["task"], "budget": k["budget"], "kind": k["kind"], "element": f"t{i}",
                          "q4": a, "q8": b, "rescued": a in NOT_LEGIBLE and b in LEGIBLE,
                          "worsened": a in LEGIBLE and b in NOT_LEGIBLE})
        sheets.append(rec)
    core = [s for s in sheets if s["kind"] == "primary"]
    cu = [u for u in units if u["kind"] == "primary"]
    n = len(core)
    g4 = sum(1 for u in cu if u["q4"] in NOT_LEGIBLE)
    r = sum(1 for u in cu if u["rescued"])
    w = sum(1 for u in cu if u["worsened"])
    rescue_tasks = sorted({u["task"] for u in cu if u["rescued"]})
    rescue_budgets = sorted({u["budget"] for u in cu if u["rescued"]})
    budgets = sorted({s["budget"] for s in core})
    q8_pref = sum(1 for s in core if s["text_preference_arm"] == "q8")
    q4_pref = sum(1 for s in core if s["text_preference_arm"] == "q4")
    q4_text_fail = sum(1 for s in core if s["q4"]["text"] == "FAIL")
    q8_text_fail = sum(1 for s in core if s["q8"]["text"] == "FAIL")
    strong = (r >= (3 if n >= 6 else 2) and 2 * r >= g4 and w <= 1 and len(rescue_tasks) >= 2
              and rescue_budgets == budgets and q8_pref >= math.ceil(2 * n / 3) and q4_pref <= n // 6)
    against = r <= 1 and q8_text_fail >= n - 1
    verdict = "STRONG" if strong else "AGAINST" if against else "INCONCLUSIVE"
    supp = [s for s in sheets if s["kind"] != "primary"]
    su = [u for u in units if u["kind"] != "primary"]

    def dims(arm, ss):
        return {c: {v: sum(1 for s in ss if s[arm][c] == v) for v in sorted({s[arm][c] for s in ss})}
                for c in ("adherence", "preservation", "composition", "quality", "text")}

    # gates (§5)
    runs = sorted(p.name for p in RUNS.glob("QQ-*"))
    rec = {rid: run_record(rid) for rid in runs}
    gate_q = []
    for rid, x in rec.items():
        parts = rid.split("-")  # QQ-<budget>-<task>[-s2]-<arm>[-rep]
        if parts[-1] == "q4":
            kind = "second_seed" if "s2" in parts else "primary"
            g = g2_identity(int(parts[1]), parts[2], kind)
            gate_q.append({"run": rid, "equal": x["pixel_sha256"] == g["pixel_sha256"] and x["rgba_sha256"] == g["rgba_sha256"],
                           "qq": [x["pixel_sha256"], x["rgba_sha256"]], "g2": [g["pixel_sha256"], g["rgba_sha256"]]})
    gate_d = []
    for rid, x in rec.items():
        if rid.endswith("-rep"):
            o = rec.get(rid.removesuffix("-rep"), {})
            gate_d.append({"run": rid, "equal": (x["pixel_sha256"], x["rgba_sha256"]) == (o.get("pixel_sha256"), o.get("rgba_sha256"))})
    merge = js(QQ / "export/merge-q8.json")
    checks = {p.stem: js(p).get("result") for p in (QQ / "export").glob("check-*.json")}
    perf = {}
    for rid, x in rec.items():
        parts = rid.split("-")
        arm = parts[-2] if parts[-1] == "rep" else parts[-1]
        perf.setdefault(f"{parts[1]}-{arm}", []).append(x)

    def med(xs, k):
        v = [x[k] for x in xs if x.get(k) is not None]
        return round(statistics.median(v), 3) if v else None
    perf_summary = {g: {"runs": len(xs), "wall_s_median": med(xs, "wall_seconds"),
                        "wall_s_range": [min(x["wall_seconds"] for x in xs if x["wall_seconds"]),
                                         max(x["wall_seconds"] for x in xs if x["wall_seconds"])] if any(x["wall_seconds"] for x in xs) else None,
                        "peak_footprint_gb_median": med(xs, "peak_footprint_gb"), "mlx_peak_gb_median": med(xs, "mlx_peak_gb"),
                        "denoise_mlx_peak_gb_median": med(xs, "denoise_mlx_peak_gb"),
                        "swap_growth_gb_median": med(xs, "swap_growth_gb"),
                        "swap_growth_gb_max": max((x["swap_growth_gb"] for x in xs if x["swap_growth_gb"] is not None), default=None),
                        "warn_samples_max": max((x["warn_samples"] for x in xs), default=None),
                        "critical_samples_total": sum(x["critical_samples"] for x in xs),
                        "aborted": sum(1 for x in xs if x["aborted"]), "rc_nonzero": sum(1 for x in xs if x["rc"] != 0)}
                    for g, xs in sorted(perf.items())}
    # inter-rater (descriptive): this rater's q4 text score vs the frozen G2 rater on the same pixels
    g2key = js(ROOT / "research/editing/real-world/g2/key-unblinded.json")
    g2s = {row["id"]: row for row in csv.DictReader((ROOT / "research/editing/real-world/g2/SCORES-FROZEN.csv").open())}
    g2_by_run = {v["run"]: g2s[q] for q, v in g2key.items() if q in g2s}
    inter = [{"sheet": s["sheet"], "g2_run": f"G2-{s['budget']}-{s['task']}{'-s2' if s['kind'] == 'second_seed' else ''}",
              "qq_q4_text": s["q4"]["text"], "qq_q4_preservation": s["q4"]["preservation"],
              "g2_text": g2_by_run.get(f"G2-{s['budget']}-{s['task']}{'-s2' if s['kind'] == 'second_seed' else ''}", {}).get("text"),
              "g2_preservation": g2_by_run.get(f"G2-{s['budget']}-{s['task']}{'-s2' if s['kind'] == 'second_seed' else ''}", {}).get("preservation")}
             for s in sheets]
    summary = {"tool": "research/qwen/qq/analyze_qq.py", "verdict": verdict,
               "core": {"sheets": n, "budgets": budgets, "units_assessable": len(cu), "G4_q4_not_legible": g4,
                        "R_rescued_by_q8": r, "W_worsened_by_q8": w, "rescue_tasks": rescue_tasks,
                        "rescue_budgets": rescue_budgets, "text_preference": {"q8": q8_pref, "q4": q4_pref,
                                                                              "SAME": n - q8_pref - q4_pref},
                        "text_FAIL": {"q4": q4_text_fail, "q8": q8_text_fail},
                        "strong_conditions": {"R>=min": r >= (3 if n >= 6 else 2), "2R>=G4": 2 * r >= g4, "W<=1": w <= 1,
                                              "rescue_tasks>=2": len(rescue_tasks) >= 2,
                                              "rescue_at_every_budget": rescue_budgets == budgets,
                                              "q8_preferred>=2n/3": q8_pref >= math.ceil(2 * n / 3),
                                              "q4_preferred<=n/6": q4_pref <= n // 6},
                        "against_conditions": {"R<=1": r <= 1, "q8_text_FAIL>=n-1": q8_text_fail >= n - 1},
                        "dims_q4": dims("q4", core), "dims_q8": dims("q8", core)},
               "supplementary": {"sheets": len(supp), "units_assessable": len(su),
                                 "rescued": sum(1 for u in su if u["rescued"]), "worsened": sum(1 for u in su if u["worsened"]),
                                 "q4_not_legible": sum(1 for u in su if u["q4"] in NOT_LEGIBLE),
                                 "text_preference": [s["text_preference_arm"] for s in supp]},
               "sheets": sheets, "units": units,
               "gates": {"Q_q4_identical_to_G2": gate_q, "Q_pass": all(g["equal"] for g in gate_q) and bool(gate_q),
                         "D_q8_repeats": gate_d, "D_pass": all(g["equal"] for g in gate_d) and bool(gate_d),
                         "V_vae_tensor_identical": (merge.get("vae_vs_canonical_q4") or {}).get("tensor_identical"),
                         "E_split_procedure_equals_canonical_q4": {k: {c: v.get("equal") for c, v in (res or {}).items()}
                                                                    for k, res in checks.items()}},
               "runs": rec, "performance": perf_summary, "inter_rater_q4_vs_g2": inter}
    Path(out).write_text(json.dumps(summary, indent=1))
    c = summary["core"]
    print(f"verdict {verdict}: core sheets {n} budgets {budgets}; units {c['units_assessable']}; G4 {g4} R {r} W {w}; "
          f"rescue tasks {rescue_tasks} budgets {rescue_budgets}; preference q8 {q8_pref} q4 {q4_pref}; "
          f"text FAIL q4 {q4_text_fail} q8 {q8_text_fail}")
    print("gates: Q", summary["gates"]["Q_pass"], "D", summary["gates"]["D_pass"], "V", summary["gates"]["V_vae_tensor_identical"])
    print(json.dumps(perf_summary, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
