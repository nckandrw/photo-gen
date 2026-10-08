"""Phase 8 Q-VR directive section 13: per-element table (calls of the Phase 8 rater for D0 / A1 / A2 / TF / ID, plus the
frozen Phase 7 calls for D0 and A1), with the pre-registered approximate glyph heights (glyph-heights.json, measured on
the sources before any Phase 8 output) and the loss-by-bin summary. Descriptive only; nothing is re-scored.

Run: mflux/.venv/bin/python3.12 research/qwen/qv-reference/strata.py  -> glyph-strata.{json,md}"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEG = {"PRESERVED", "DEGRADED"}
AB = {"PRESERVED": "P", "DEGRADED": "D", "GARBLED": "G", "REMOVED": "R", "NA": "NA", None: "–"}


def main() -> None:
    calls = json.loads((HERE / "qvr-summary.json").read_text())["review"]["calls"]
    gh = json.loads((HERE / "glyph-heights.json").read_text())["elements"]
    p7 = {f"{r['task']}-{r['budget']}-{r['element']}": r for r in json.loads((HERE / "phase7-transitions.json").read_text())["table"]}
    rows, summ = [], {}
    for b in (512, 1024):
        for t in ("R02", "R12", "R15"):
            for e in ("t1", "t2", "t3", "t4", "t5"):
                k = f"{t}-{b}-{e}"
                if k not in calls:
                    continue
                g = gh[f"{t}-{e}"]
                c = calls[k]
                row = {"element": k, "main_px": g[f"out_px_main_{b}"], "smallest_px": g[f"out_px_smallest_{b}"],
                       "bin": g[f"bin_{b}"], **{a: c.get(a) for a in ("D0", "A1", "A2", "TF", "ID")},
                       "p7_D0": p7[k]["after_resize"], "p7_A1": p7[k]["after_vae"]}
                rows.append(row)
                s = summ.setdefault(f"{b} {row['bin']}", {"n": 0, "D0_legible": 0, "A1_legible": 0, "A2_legible": 0,
                                                          "TF_legible": 0, "vae_lost_of_D0_legible": 0})
                s["n"] += 1
                for a in ("D0", "A1", "A2", "TF"):
                    s[f"{a}_legible"] += c.get(a) in LEG
                s["vae_lost_of_D0_legible"] += c.get("D0") in LEG and c.get("A1") not in LEG
    (HERE / "glyph-strata.json").write_text(json.dumps({"rows": rows, "by_budget_bin": summ}, indent=1) + "\n")
    md = ["# Q-VR per-element table with glyph-height strata (directive §13; descriptive)", "",
          "Calls: the Phase 8 rater (frozen `review/SCORES-FROZEN.csv`); P7 = the frozen Phase 7 rater on the same D0/A1 "
          "pixels. Heights: approximate output-pixel heights of the main line / smallest material line "
          "(`glyph-heights.json`, measured on the sources, ±20 %). P/D/G = PRESERVED/DEGRADED/GARBLED.", "",
          "| element | main / smallest px | bin | D0 | A1 | A2 | TF | ID | P7 D0 | P7 A1 |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['element']} | {r['main_px']} / {r['smallest_px']} | {r['bin']} | " + " | ".join(
            AB[r[a]] for a in ("D0", "A1", "A2", "TF", "ID", "p7_D0", "p7_A1")) + " |")
    md += ["", "**By budget and main-line bin (Phase 8 rater):**", "",
           "| budget, bin | n | D0 legible | A1 legible | A2 legible | TF legible | lost by the round trip (of D0-legible) |",
           "|---|---:|---:|---:|---:|---:|---:|"]
    for k, s in summ.items():
        md.append(f"| {k} px | {s['n']} | {s['D0_legible']} | {s['A1_legible']} | {s['A2_legible']} | {s['TF_legible']} | "
                  f"{s['vae_lost_of_D0_legible']} |")
    (HERE / "glyph-strata.md").write_text("\n".join(md) + "\n")
    print("\n".join(md[-(len(summ) + 3):]))


if __name__ == "__main__":
    main()
