"""Mechanical tally of the Phase 7 Q-V diagnostic (research/qwen/qv/PROTOCOL.md sections 5, 8, 9). Written and
committed before any Q-V output existed; it only reads the frozen sheets, the unblinded key and the run records.
Metrics (section 10) are descriptive and computed here, after the freeze.

Usage: mflux/.venv/bin/python3.12 research/qwen/qv/analyze_qv.py <qv_review_dir> <summary.json>"""
import csv
import json
import math
import statistics
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research/editing"))
from edit_metrics import _gray, _load, ssim_map  # noqa: E402

RUNS = ROOT / "research/qwen/runs"
LEGIBLE = {"PRESERVED", "DEGRADED"}
LOST = {"GARBLED", "REMOVED"}
BOXES = json.loads((ROOT / "research/qwen/qv/text-boxes.json").read_text())


def js(p: Path) -> dict:
    return json.loads(p.read_text()) if p.exists() else {}


def monitor(rid: str) -> dict:
    p = RUNS / rid / "monitor.csv"
    rows = list(csv.DictReader(p.open())) if p.exists() else []
    sw = [float(r["swap_used_mb"]) for r in rows if r.get("swap_used_mb")]
    pl = [int(r["pressure_level"]) for r in rows if r.get("pressure_level")]
    return {"swap_growth_gb": round((max(sw) - sw[0]) / 1024, 3) if sw else None, "warn_samples": pl.count(2),
            "critical_samples": pl.count(4), "samples": len(pl)}


def gates() -> dict:
    g = {}
    gate = js(RUNS / "QVGATE-512-E05/worker/gate.json")
    g["equivalence"] = {"pass": bool(gate.get("checks", {}).get("pass")), "checks": gate.get("checks")}
    manifest = js(ROOT / "config/backend-qwen21-edit-mflux.json")
    pins = {f["path"]: f["digest"] for f in manifest.get("model", {}).get("files", [])}
    vae_pin = pins.get("vae/0.safetensors")
    runs = {}
    for budget in (512, 1024):
        for task in ("R02", "R12", "R15"):
            sc = js(RUNS / f"G2-{budget}-{task}/sidecar.json")
            ids = {rep: js(RUNS / f"QV-{budget}-{task}-{rep}/worker/identity.json") for rep in ("a", "b")}
            a, b = ids["a"], ids["b"]
            runs[f"{task}-{budget}"] = {
                "source_pixels_equal_g2": a.get("staged_identity", {}).get("pixel_sha256") == sc["input_image"]["pixel_sha256"],
                "size_equals_g2_output": a.get("size") == [sc["width"], sc["height"]],
                "vae_sha256": a.get("vae_file_sha256"),
                "deterministic": bool(a) and all(
                    a[k]["pixel_sha256"] == b[k]["pixel_sha256"] and a[k]["alpha"] == b[k]["alpha"] for k in ("input", "roundtrip"))
                and all(a["variants"][v]["identity"]["pixel_sha256"] == b["variants"][v]["identity"]["pixel_sha256"]
                        for v in a["variants"]),
            }
    g["runs"] = runs
    g["vae_pin"] = vae_pin
    g["vae_identity"] = bool(vae_pin) and all(r["vae_sha256"] == vae_pin for r in runs.values())
    g["source"] = all(r["source_pixels_equal_g2"] for r in runs.values())
    g["geometry"] = all(r["size_equals_g2_output"] for r in runs.values())
    g["determinism"] = all(r["deterministic"] for r in runs.values())
    g["all_pass"] = all([g["equivalence"]["pass"], g["vae_identity"], g["source"], g["geometry"], g["determinism"]])
    return g


def main(review: str, out: str) -> None:
    rv = Path(review)
    key = js(rv / "key-unblinded.json")
    scores = {r["id"]: r for r in csv.DictReader((rv / "SCORES-FROZEN.csv").open())}
    prefs = {r["sheet"]: r for r in csv.DictReader((rv / "PREFERENCE-FROZEN.csv").open())}
    units, sheets = [], []
    for sid, k in sorted(key.items()):
        row = {k["A"]: scores[f"{sid}-A"], k["B"]: scores[f"{sid}-B"]}
        p = prefs[sid]["text_preference"]
        sheets.append({"sheet": sid, "task": k["task"], "budget": k["budget"], "run": k["run"],
                       "preference": "SAME" if p == "SAME" else k[p],
                       "fidelity": {arm: (row[arm]["fidelity"], row[arm]["fidelity_family"]) for arm in row}})
        for i in range(1, 6):
            vi, vr = row["input"][f"t{i}"], row["roundtrip"][f"t{i}"]
            if vi == "-":
                continue
            units.append({"task": k["task"], "budget": k["budget"], "element": f"t{i}", "input": vi, "roundtrip": vr})
    per = {}
    for b in (512, 1024):
        u = [x for x in units if x["budget"] == b]
        N = [x for x in u if x["input"] != "NA"]
        K = [x for x in N if x["input"] in LEGIBLE]
        L = [x for x in K if x["roundtrip"] in LOST]
        S = [x for x in N if x["input"] in LOST]
        per[b] = {"units": len(u), "N_original_legible": len(N), "K_input_legible": len(K), "L_vae_lost": len(L),
                  "S_scaling_lost": len(S), "vae_softened_P_to_D": sum(1 for x in K if x["input"] == "PRESERVED"
                                                                       and x["roundtrip"] == "DEGRADED"),
                  "roundtrip_legible": sum(1 for x in N if x["roundtrip"] in LEGIBLE),
                  "L_by_task": {t: sum(1 for x in L if x["task"] == t) for t in ("R02", "R12", "R15")},
                  "lost_units": [f"{x['task']}-{x['element']}" for x in L],
                  "scaling_lost_units": [f"{x['task']}-{x['element']}" for x in S]}
    g = gates()
    p5, p10 = per[512], per[1024]
    half = lambda n: math.ceil(n / 2)  # noqa: E731
    if not g["all_pass"] or p10["K_input_legible"] < 3:
        verdict = "INCONCLUSIVE"
    elif p10["L_vae_lost"] >= max(2, half(p10["K_input_legible"])):
        verdict = "VAE-IMPLICATED"
    elif p10["L_vae_lost"] <= 1 and p5["N_original_legible"] >= 1 and \
            p5["S_scaling_lost"] + p5["L_vae_lost"] >= half(p5["N_original_legible"]):
        verdict = "BUDGET-LIMITED"
    elif p10["L_vae_lost"] <= 1 and p5["L_vae_lost"] <= 1:
        verdict = "VAE-CLEARED"
    else:
        verdict = "MIXED"
    # secondary, cross-rater: the core units the q4 EDIT garbled in Q-Q (frozen), followed through Q-V
    qq = js(ROOT / "research/qwen/qq/qq-summary.json")
    E = [u for u in qq.get("units", []) if u["kind"] == "primary" and u["q4"] in LOST]
    look = {(x["task"], x["budget"], x["element"]): x for x in units}
    part = {"na_in_qv": [], "scaling": [], "vae": [], "regeneration": []}
    for u in E:
        x = look.get((u["task"], u["budget"], u["element"]))
        name = f"{u['task']}-{u['budget']}-{u['element']}"
        if x is None or x["input"] == "NA":
            part["na_in_qv"].append(name)
        elif x["input"] in LOST:
            part["scaling"].append(name)
        elif x["roundtrip"] in LOST:
            part["vae"].append(name)
        else:
            part["regeneration"].append(name)
    secondary = {"E_edit_garbled_units": len(E), **{k: len(v) for k, v in part.items()}, "units": part,
                 "by_budget": {b: {k: sum(1 for n in v if f"-{b}-" in n) for k, v in part.items()} for b in (512, 1024)}}
    # descriptive metrics (after the freeze): input vs round trip, whole image and per text box
    metrics = {}
    for s in sheets:
        d = RUNS / s["run"] / "worker"
        a, b = _load(d / "input.png"), _load(d / "roundtrip.png")
        ga, gb = _gray(a), _gray(b)
        sm = ssim_map(ga, gb)
        mse = float(((a - b) ** 2).mean())
        h, w = ga.shape
        reg = {}
        for el, (x0, y0, x1, y1) in BOXES[s["task"]].items():
            ys, xs = slice(int(y0 * h), max(int(y0 * h) + 1, math.ceil(y1 * h))), slice(int(x0 * w), max(int(x0 * w) + 1, math.ceil(x1 * w)))
            u = look.get((s["task"], s["budget"], el), {})
            reg[el] = {"ssim": round(float(sm[ys, xs].mean()), 4), "mae": round(float(np.abs(a[ys, xs] - b[ys, xs]).mean()), 3),
                       "box_px": [xs.stop - xs.start, ys.stop - ys.start], "input": u.get("input"), "roundtrip": u.get("roundtrip")}
        metrics[f"{s['task']}-{s['budget']}"] = {"ssim": round(float(sm.mean()), 4), "mae": round(float(np.abs(a - b).mean()), 3),
                                                 "psnr": round(10 * math.log10(255 ** 2 / mse), 2) if mse > 0 else None,
                                                 "regions": reg}
    def rssim(pred):
        v = [r["ssim"] for m in metrics.values() for r in m["regions"].values() if pred(r)]
        return {"n": len(v), "median_ssim": round(statistics.median(v), 4) if v else None}
    tracking = {"roundtrip_legible": rssim(lambda r: r["roundtrip"] in LEGIBLE),
                "roundtrip_lost": rssim(lambda r: r["roundtrip"] in LOST),
                "input_legible_roundtrip_lost": rssim(lambda r: r["input"] in LEGIBLE and r["roundtrip"] in LOST)}
    perf = {}
    for rid in sorted(p.name for p in RUNS.glob("QV-*")) + ["QVGATE-512-E05"]:
        i = js(RUNS / rid / "worker/identity.json") or js(RUNS / rid / "worker/gate.json")
        r = js(RUNS / rid / "result.json")
        perf[rid] = {"seconds": i.get("seconds"), "process_wall_seconds": r.get("process_wall_seconds"),
                     "peak_footprint_gb": i.get("peak_footprint_gb"), "mlx_peak_gb": i.get("mlx_peak_gb"), **monitor(rid)}
    variants = {f"{t}-{b}": js(RUNS / f"QV-{b}-{t}-a/worker/identity.json").get("variants")
                for b in (512, 1024) for t in ("R02", "R12", "R15")}
    summary = {"tool": "research/qwen/qv/analyze_qv.py", "verdict": verdict, "per_budget": per, "gates": g,
               "secondary_cross_rater": secondary, "preference": [{k: s[k] for k in ("sheet", "task", "budget", "preference")}
                                                                    for s in sheets],
               "fidelity": {f"{s['task']}-{s['budget']}": s["fidelity"] for s in sheets}, "units": units,
               "metrics": metrics, "metric_tracking": tracking, "variants": variants, "performance": perf}
    Path(out).write_text(json.dumps(summary, indent=1))
    print(f"verdict {verdict}")
    for b in (512, 1024):
        print(b, {k: v for k, v in per[b].items() if k not in ("lost_units", "scaling_lost_units")})
    print("secondary:", {k: v for k, v in secondary.items() if k != "units"})
    print("gates:", {k: g[k] for k in ("vae_identity", "source", "geometry", "determinism", "all_pass")}, "equivalence", g["equivalence"]["pass"])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
