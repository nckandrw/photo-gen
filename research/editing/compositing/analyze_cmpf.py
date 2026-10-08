"""Phase 9 CMPF analysis (PROTOCOL.md §8–§10), applied mechanically to the frozen review and the run records.

Run: mflux/.venv/bin/python3.12 research/editing/compositing/analyze_cmpf.py <review_dir> <out.json>"""
import csv
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEG = {"PRESERVED", "DEGRADED"}
MASK_DEFECTS = {"leftover-of-target", "truncated-edit", "orphan-shadow-or-reflection"}
COMP_DEFECTS = {"seam-or-tone-step", "ghosting", "resolution-mismatch"}


def viability(r: dict, canvas_legible: dict) -> dict:
    text_ok = all(r[e] in LEG for e, leg in canvas_legible.items() if leg)
    crit = {"adherence_pass": r["adherence"] == "PASS", "unintended_ok": r["unintended"] in ("NONE", "MINOR"),
            "text_kept": text_ok, "seam_ok": r["seam"] in ("NONE", "MINOR"), "realism_ok": r["realism"] in ("PASS", "MINOR"),
            "geometry_ok": r["geometry"] != "MAJOR"}
    return {"viable": all(crit.values()), "criteria": crit}


def failure_class(r: dict, c0: dict, aligned: bool) -> str:
    if not aligned:
        return "alignment"
    if r["primary_defect"] in MASK_DEFECTS or (r["adherence"] != "PASS" and c0["adherence"] == "PASS"):
        return "mask"
    if r["primary_defect"] in COMP_DEFECTS or r["seam"] == "MAJOR":
        return "compositing"
    return f"other ({r['primary_defect']})"


def classify(n: int, v: int, unevaluable: int) -> str:
    if n < 4 or unevaluable > 1:
        return "INCONCLUSIVE"
    if v >= math.ceil(0.75 * n):
        return "SUPPORTED FOR FURTHER DEVELOPMENT"
    if v < n / 2:
        return "NOT SUPPORTED"
    return "MIXED"


def main(review_dir: str, out_json: str) -> None:
    rv = Path(review_dir)
    key = json.loads((rv / "key-unblinded.json").read_text())
    rows = {r["id"]: r for r in csv.DictReader((rv / "SCORES-FROZEN.csv").open())}
    cfg = json.loads((HERE / "config.json").read_text())
    cases, per_arm = {}, {a: {"n": 0, "viable": 0} for a in ("C0", "C1", "C2", "C3")}
    unevaluable = 0
    for sid, k in key.items():
        t = k["task"]
        arm = {a: rows[f"{sid}-{lab}"] for lab, a in k["panels"].items()}
        runs = [json.loads(p.read_text()) for p in sorted((HERE / "runs").glob(f"{t}-*/record.json"))]
        rec = runs[0] if runs else {}
        evaluable = bool(rec) and all(rec.get("gates", {}).values()) and all(rec.get("invariants", {}).values())
        deterministic = len(runs) >= 2 and all(r["outputs"] == runs[0]["outputs"] for r in runs)
        evaluable = evaluable and deterministic
        aligned = rec.get("alignment", {}).get("aligned", False)
        n_el = len([c for c in ("t1", "t2", "t3", "t4", "t5") if arm["D0"][c] != "-"])
        els = [f"t{i}" for i in range(1, n_el + 1)]
        d0_leg = {e: arm["D0"][e] in LEG for e in els}
        orig_leg = {e: arm["D0"][e] != "NA" for e in els}
        res = {"counted": t in cfg["primary_cases"], "evaluable": evaluable, "deterministic": deterministic,
               "aligned": aligned, "attention_check_D0_adherence_FAIL": arm["D0"]["adherence"] == "FAIL",
               "editor_failure": arm["C0"]["adherence"] != "PASS", "arms": {}}
        for a in ("C0", "C1", "C2", "C3"):
            canvas = orig_leg if a == "C3" else d0_leg
            v = viability(arm[a], canvas)
            v["scores"] = {c: arm[a][c] for c in ("adherence", "seam", "realism", "unintended", "geometry", "primary_defect", *els)}
            v["notes"] = arm[a]["notes"]
            if not v["viable"] and a != "C0":
                v["failure_class"] = failure_class(arm[a], arm["C0"], aligned)
            res["arms"][a] = v
        res["text_canvas_legible"] = {"D0": d0_leg, "ORIGINAL": orig_leg}
        res["metrics"] = {k_: rec.get(k_) for k_ in ("mask", "alignment", "c0_vs_d0", "inside_mask_psnr_vs_canvas", "text_boxes",
                                                      "feather_px", "sizes", "seconds", "peak_footprint_gb")}
        cases[t] = res
        if res["counted"]:
            if not evaluable:
                unevaluable += 1
            elif not res["editor_failure"]:
                for a in per_arm:
                    per_arm[a]["n"] += 1
                    per_arm[a]["viable"] += res["arms"][a]["viable"]
    for a, s in per_arm.items():
        s["classification_by_rule"] = classify(s["n"], s["viable"], unevaluable)
    all_cases = {a: sum(c["arms"][a]["viable"] and not c["editor_failure"] for c in cases.values() if c["counted"])
                 for a in per_arm}
    out = {"tool": "research/editing/compositing/analyze_cmpf.py",
           "primary_classification_C2": per_arm["C2"]["classification_by_rule"],
           "per_arm": per_arm, "all_primary_cases_viable_counting_editor_failures_as_failed": all_cases,
           "editor_failures": [t for t, c in cases.items() if c["counted"] and c["editor_failure"]],
           "unevaluable_primary": unevaluable, "cases": cases}
    Path(out_json).write_text(json.dumps(out, indent=1) + "\n")
    print("C2 (primary):", out["primary_classification_C2"], per_arm["C2"])
    for a in ("C0", "C1", "C3"):
        print(a, per_arm[a])
    for t, c in cases.items():
        print(t, "counted" if c["counted"] else "demo", "editor_failure" if c["editor_failure"] else "",
              {a: ("V" if c["arms"][a]["viable"] else "x:" + c["arms"][a].get("failure_class", "-")) for a in ("C0", "C1", "C2", "C3")})


if __name__ == "__main__":
    main(*sys.argv[1:])
