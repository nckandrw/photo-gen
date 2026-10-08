"""Provenance-blind review tool for Phase 9 CMPF (PROTOCOL.md §7). A sibling of research/qwen/qv-reference/qvr_blind.py
(same stages and guarantees), with the Phase 9 rubric, an append-only draft with a `revision` column (check/freeze use
the latest revision per id; the whole history is preserved), and a full-resolution ORIGINAL for judging the
source-resolution versions.

  prepare <sheets.json> <review_dir> <seed>
      sheets.json: [{"task": "R12", "staged": <full-res staged source>, "instruction": "...",
                     "panels": {"C0": png, "C1": png, "C2": png, "C3": png, "D0": png}}]
      The key is sealed read-only before any panel is written; then blind/<SHEET>-ORIGINAL.png (long side <= 2048),
      blind/<SHEET>-ORIGINAL-FULL.png (full resolution), blind/<SHEET>-<L>.png (RGB, native size), ITEMS.md,
      RATER-INSTRUCTIONS.md, scores-template.csv, MANIFEST.json.
  check <review_dir> [scores.csv]   format-only checks on the latest revision per id
  freeze <review_dir> <scores.csv>  SCORES-DRAFT-HISTORY.csv (the whole draft) + SCORES-FROZEN.csv (latest per id)
  unblind <review_dir>

Run: mflux/.venv/bin/python3.12 research/editing/compositing/cmp_blind.py ..."""
import csv
import hashlib
import json
import os
import random
import re
import shutil
import stat
import sys
import time
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research/qwen/qq"))
from qq_blind import ELEMENTS  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
NSLOT = 5
TEXT_CAT = {"PRESERVED", "DEGRADED", "GARBLED", "REMOVED", "NA"}
ADH = {"PASS", "PARTIAL", "FAIL"}
LEVEL = {"NONE", "MINOR", "MAJOR"}
QUAL = {"PASS", "MINOR", "MAJOR"}
DEFECTS = {"none", "leftover-of-target", "truncated-edit", "orphan-shadow-or-reflection", "seam-or-tone-step",
           "ghosting", "resolution-mismatch", "collateral-change", "text-damage"}
COLUMNS = (["id", "revision", "adherence", "seam", "realism", "unintended", "geometry", "primary_defect"]
           + [f"t{i}" for i in range(1, NSLOT + 1)] + ["notes"])
KEYNAME = "KEY-DO-NOT-OPEN-BEFORE-FREEZE.json"
RUBRIC = """# Rater instructions (provenance-blind)

Each sheet is one photograph and one editing INSTRUCTION (quoted in `ITEMS.md`). The files of a sheet:
- `<SHEET>-ORIGINAL.png`: the unedited photograph, reduced to a long side of at most 2048 px;
- `<SHEET>-ORIGINAL-FULL.png`: the same unedited photograph at full resolution (use it when a version is larger than
  2048 px, and for reading small lettering);
- `<SHEET>-A.png`, `<SHEET>-B.png`, …: versions of the photograph, each at its own native size. You are not told how
  they were produced, and you must not try to find out. Versions differ in size; some may look nearly identical;
  one or more may not carry out the instruction at all. Score each version on its own merits against ORIGINAL and the
  instruction.

Read ONLY the files in this directory. Inspect at native resolution: crop the same region from ORIGINAL (or
ORIGINAL-FULL) and from each version, e.g. `sips -c <h> <w> --cropOffset <y> <x> in.png --out <file>`, writing crops
and any helper files ONLY to the scratch directory named in your prompt. Do not enlarge crops with smoothing
(nearest-neighbour enlargement is allowed). Score sheets in the order listed in `ITEMS.md`, one row per version
(`<SHEET>-A`, `<SHEET>-B`, …).

## Per version
- **`adherence`**: `PASS` = the instruction is fully carried out; `PARTIAL` = partly (e.g. remnants of the object, only
  part of the change); `FAIL` = not carried out.
- **`seam`**: visible boundaries, edges, halos, tone steps or discontinuities: `NONE`, `MINOR` (visible on
  inspection), `MAJOR` (obvious at normal viewing).
- **`realism`** of the whole image as a photograph: `PASS`, `MINOR` (small implausibilities), `MAJOR` (clearly
  implausible: wrong or orphan shadows/reflections, floating or cut objects, broken geometry, impossible content).
- **`unintended`**: changes OUTSIDE what the instruction asks for, compared with ORIGINAL, semantic or geometric:
  `NONE`, `MINOR`, `MAJOR`.
- **`geometry`**: does the edited region fit the unchanged scene (perspective, scale, contact with surfaces,
  continuity of edges and lines)? `PASS`, `MINOR`, `MAJOR`.
- **`primary_defect`**: the single most serious defect, or `none`: `leftover-of-target` (part of something that should
  have changed or gone is still there), `truncated-edit` (the edited content is cut off), `orphan-shadow-or-reflection`
  (a shadow/reflection with no cause, or a missing one), `seam-or-tone-step`, `ghosting` (semi-transparent mix of old
  and new content), `resolution-mismatch` (a region visibly blurrier or sharper than its surroundings),
  `collateral-change` (something not asked for was changed), `text-damage`, or `other:<one word>`.
- **`t1`..`t5`** (the sheet's TEXT ELEMENTS, all outside what the instruction asks to change; `-` for numbers the sheet
  does not have): `PRESERVED` (same wording readable, lettering like the original's allowing for size), `DEGRADED`
  (same wording still correctly readable but visibly softened/deformed), `GARBLED` (no longer readable as the
  original's: wrong letters or unreadable blur; say which in the note), `REMOVED` (gone or replaced), `NA` (unreadable
  in ORIGINAL too; then NA for every version of the sheet).
- **`notes`**: one or two short sentences: what you saw, where.

## Output and revisions
Copy `scores-template.csv` to `scores-draft.csv` in this directory and APPEND rows as you finish each sheet. The draft
is **append-only**: to change an earlier row, append a new row with the same `id` and `revision` + 1 (the first row of
an id has `revision` 1). Never edit or delete earlier rows. The latest revision of each id counts; all are kept.
"""


def sha256(p) -> str:
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        while b := f.read(1 << 24):
            h.update(b)
    return h.hexdigest()


def readonly(p: Path) -> None:
    os.chmod(p, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)


def prepare(sheets_path: str, review_dir: str, seed: str) -> None:
    d = Path(review_dir)
    sheets = json.loads(Path(sheets_path).read_text())
    hashes = {p: sha256(p) for s in sheets for p in [s["staged"], *s["panels"].values()]}
    if d.exists():
        sys.exit(f"refusing: {d} exists")
    (d / "key").mkdir(parents=True)
    (d / "blind").mkdir()
    rng = random.Random(int(seed))
    order = list(range(len(sheets)))
    rng.shuffle(order)
    key = {}
    for n, i in enumerate(order):
        s = sheets[i]
        arms = list(s["panels"])
        rng.shuffle(arms)
        labels = [chr(ord("A") + j) for j in range(len(arms))]
        key[f"S{n + 1:02d}"] = {"task": s["task"], "staged": s["staged"], "instruction": s["instruction"],
                                "counted": s.get("counted", True), "panels": dict(zip(labels, arms)),
                                "paths": {lab: s["panels"][arm] for lab, arm in zip(labels, arms)}}
    kp = d / "key" / KEYNAME
    kp.write_text(json.dumps(key, indent=1))
    readonly(kp)
    rendered, lines = {}, ["# CMPF sheets (provenance-blind)", ""]
    for sid in sorted(key):
        k = key[sid]
        full = Image.open(k["staged"]).convert("RGB")
        o = full
        if max(o.size) > 2048:
            s_ = 2048 / max(o.size)
            o = o.resize((round(o.width * s_), round(o.height * s_)), Image.Resampling.LANCZOS)
        for name, im in (("ORIGINAL", o), ("ORIGINAL-FULL", full)):
            p = d / "blind" / f"{sid}-{name}.png"
            im.save(p)
            rendered[p.name] = sha256(p)
        sizes = []
        for lab, src in k["paths"].items():
            im = Image.open(src).convert("RGB")
            p = d / "blind" / f"{sid}-{lab}.png"
            im.save(p)
            rendered[p.name] = sha256(p)
            sizes.append(f"{lab} {im.width}x{im.height}")
        els = ELEMENTS.get(k["task"], [])
        lines += [f"## {sid}  (ORIGINAL {o.width}x{o.height}; ORIGINAL-FULL {full.width}x{full.height}; versions: {', '.join(sizes)})",
                  f"- **INSTRUCTION:** \"{k['instruction']}\"",
                  "- **TEXT ELEMENTS:** " + ("; ".join(f"t{i + 1} = {e}" for i, e in enumerate(els)) if els else "none"), ""]
    (d / "blind" / "ITEMS.md").write_text("\n".join(lines))
    (d / "blind" / "RATER-INSTRUCTIONS.md").write_text(RUBRIC)
    with (d / "blind" / "scores-template.csv").open("w", newline="") as f:
        csv.writer(f).writerow(COLUMNS)
    man = {"tool": "research/editing/compositing/cmp_blind.py", "prepared": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
           "seed": int(seed), "sheets": len(sheets), "input_sha256": hashes, "key_sha256": sha256(kp),
           "rendered_sha256": rendered, "items_md_sha256": sha256(d / "blind" / "ITEMS.md"), "frozen_scores_sha256": None}
    (d / "MANIFEST.json").write_text(json.dumps(man, indent=1))
    print(f"prepared {len(sheets)} sheets in {d}/blind (key sealed: {man['key_sha256'][:16]}…)")


def latest(rows):
    by = {}
    for r in rows:
        try:
            rev = int(r["revision"])
        except (TypeError, ValueError):
            rev = -1
        if r["id"] not in by or rev > int(by[r["id"]]["revision"] or -1):
            by[r["id"]] = r
    return by


def problems(d: Path, scores: Path) -> list[str]:
    sheets, cur = {}, None
    for line in (d / "blind" / "ITEMS.md").read_text().splitlines():
        m = re.match(r"## (S\d+)\s+\(.*versions: (.*)\)$", line)
        if m:
            cur = m.group(1)
            sheets[cur] = {"labels": [v.split()[0] for v in m.group(2).split(", ")], "n": 0}
        if line.startswith("- **TEXT ELEMENTS:**") and cur:
            sheets[cur]["n"] = len(re.findall(r"\bt\d+ = ", line))
    out = []
    if scores.read_text().splitlines()[0].strip() != ",".join(COLUMNS):
        out.append("scores header differs from the template")
    rows = list(csv.DictReader(scores.open()))
    seen = {}
    for r in rows:
        try:
            rev = int(r["revision"])
        except (TypeError, ValueError):
            out.append(f"{r.get('id')}: revision must be an integer")
            continue
        if rev != seen.get(r["id"], 0) + 1:
            out.append(f"{r['id']}: revision {rev} out of order (expected {seen.get(r['id'], 0) + 1})")
        seen[r["id"]] = rev
    by = latest(rows)
    want = [f"{s}-{lab}" for s, v in sheets.items() for lab in v["labels"]]
    if sorted(by) != sorted(want):
        out.append(f"ids: missing {sorted(set(want) - set(by))}, extra {sorted(set(by) - set(want))}")
    for i, r in by.items():
        if None in r or any(v is None for v in r.values()):
            out.append(f"{i}: wrong column count")
            continue
        sid = i.split("-")[0]
        if sid not in sheets:
            continue
        for c, allowed in (("adherence", ADH), ("seam", LEVEL), ("realism", QUAL), ("unintended", LEVEL), ("geometry", QUAL)):
            if r[c] not in allowed:
                out.append(f"{i}: {c} not in {sorted(allowed)}")
        if not (r["primary_defect"] in DEFECTS or r["primary_defect"].startswith("other:")):
            out.append(f"{i}: primary_defect not in the list")
        n = sheets[sid]["n"]
        for k in range(1, NSLOT + 1):
            v = r[f"t{k}"]
            if k <= n and v not in TEXT_CAT:
                out.append(f"{i}: t{k} not in {sorted(TEXT_CAT)}")
            if k > n and v != "-":
                out.append(f"{i}: t{k} must be '-' (this sheet has {n} text elements)")
    for s, v in sheets.items():
        rs = [by.get(f"{s}-{lab}") for lab in v["labels"]]
        if all(rs):
            for k in range(1, NSLOT + 1):
                if len({x[f"t{k}"] == "NA" for x in rs}) > 1:
                    out.append(f"{s}: t{k} is NA for some versions only")
    return out


def check(review_dir: str, scores: str | None = None) -> None:
    d = Path(review_dir)
    probs = problems(d, Path(scores) if scores else d / "blind" / "scores-draft.csv")
    print("\n".join(probs) if probs else "no format violations")


def freeze(review_dir: str, scores: str) -> None:
    d = Path(review_dir)
    man = json.loads((d / "MANIFEST.json").read_text())
    if man.get("frozen_scores_sha256"):
        sys.exit("refusing: already frozen")
    probs = problems(d, Path(scores))
    if probs:
        sys.exit("invalid sheets:\n  " + "\n  ".join(probs))
    hist = d / "SCORES-DRAFT-HISTORY.csv"
    shutil.copyfile(scores, hist)
    readonly(hist)
    rows = list(csv.DictReader(Path(scores).open()))
    by = latest(rows)
    dst = d / "SCORES-FROZEN.csv"
    with dst.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for i in sorted(by):
            w.writerow(by[i])
    readonly(dst)
    man["frozen_scores_sha256"] = sha256(dst)
    man["draft_history_sha256"] = sha256(hist)
    man["revised_ids"] = sorted({r["id"] for r in rows if int(r["revision"]) > 1})
    man["frozen_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    (d / "MANIFEST.json").write_text(json.dumps(man, indent=1))
    readonly(d / "MANIFEST.json")
    print(f"frozen: scores {man['frozen_scores_sha256']}; revised ids: {man['revised_ids']}")


def unblind(review_dir: str) -> None:
    d = Path(review_dir)
    man = json.loads((d / "MANIFEST.json").read_text())
    kp = d / "key" / KEYNAME
    if not man.get("frozen_scores_sha256") or sha256(d / "SCORES-FROZEN.csv") != man["frozen_scores_sha256"]:
        sys.exit("refusing: SCORES-FROZEN.csv is not frozen or no longer matches its recorded hash")
    if sha256(kp) != man["key_sha256"]:
        sys.exit("refusing: key does not match its recorded hash")
    key = json.loads(kp.read_text())
    (d / "key-unblinded.json").write_text(json.dumps(key, indent=1))
    print(json.dumps({s: {"task": k["task"], "panels": k["panels"]} for s, k in key.items()}, indent=1))


if __name__ == "__main__":
    cmd, *args = sys.argv[1:]
    {"prepare": prepare, "check": check, "freeze": freeze, "unblind": unblind}[cmd](*args)
