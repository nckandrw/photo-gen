"""Format-only checks on a G2 score sheet (protocol amendment 2), printing violations only, never score content.

Usage: mflux/.venv/bin/python3.12 -I research/editing/real-world/check_scores_format.py <g2_dir>/blind [<sheet.csv>]
       (default sheet: <blind>/scores-draft.csv). Run on the draft before `g2_blind.py freeze`."""
import csv
import re
import sys
from pathlib import Path

blind = Path(sys.argv[1])
sheet = Path(sys.argv[2]) if len(sys.argv) > 2 else blind / "scores-draft.csv"
items = blind.joinpath("ITEMS.md").read_text()
scored = {}
for m in re.finditer(r"^## (Q\d\d) .*?^- \*\*text:\*\* (\S+)", items, re.M | re.S):
    scored[m.group(1)] = m.group(2) == "scored"
header = blind.joinpath("scores-template.csv").read_text().splitlines()[0]
probs = []
if sheet.read_text().splitlines()[0] != header:
    probs.append("header differs from scores-template.csv")
rows = list(csv.DictReader(sheet.open()))
ids = [r["id"] for r in rows]
missing = sorted(set(scored) - set(ids))
dup = sorted({i for i in ids if ids.count(i) > 1})
extra = sorted(set(ids) - set(scored))
for r in rows:
    i = r["id"]
    if i in scored:
        if scored[i] and r["text"] not in ("PASS", "PARTIAL", "FAIL"):
            probs.append(f"{i}: text must be PASS/PARTIAL/FAIL (text is scored for this item)")
        if not scored[i] and r["text"] != "NA":
            probs.append(f"{i}: text must be NA (text not scored for this item)")
    if r["quality"] == "PASS" and (r["quality_family"] or "").strip():
        probs.append(f"{i}: quality_family must be empty when quality is PASS")
    if None in r or any(v is None for v in r.values()):
        probs.append(f"{i}: wrong column count")
print(f"rows {len(rows)}; text-scored items {sum(scored.values())}; missing {missing}; duplicate {dup}; extra {extra}")
print("\n".join(probs) if probs else "no format violations")
