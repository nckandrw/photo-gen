"""Provenance-blind review tool for the Phase 7 Q-V diagnostic (research/qwen/qv/PROTOCOL.md section 6-7). A sibling of
research/qwen/qq/qq_blind.py (same stages and guarantees; research/experiments/BLIND-PROTOCOL.md). NOT an A/B model
comparison: the two processed panels are the scaled conditioning input and the VAE round trip of the same budget, shown
in randomised order.

  prepare <items.json> <qv_dir> <seed>
      items.json: [{"item": "R12-1024", "task": "R12", "budget": 1024, "staged": full-res staged source,
                    "input": scaled input PNG, "roundtrip": round-trip PNG, "run": run id}]
      Hashes every input first; refuses an existing <qv_dir>. Shuffles the sheets and the A/B order of the two processed
      panels with random.Random(seed); writes the key read-only BEFORE any composite exists; then renders
      <qv_dir>/blind/<ID>.png: ORIGINAL (the staged source downscaled to a long side of at most 2048 px, never
      upscaled) | A | B (both at their NATIVE pixel size, no resampling). Portrait -> side by side, landscape -> stacked.
      Also ITEMS.md, RATER-INSTRUCTIONS.md, scores-template.csv, preference-template.csv, MANIFEST.json.
  check <qv_dir> [scores.csv] [preference.csv]   format-only checks (violations only, never content)
  freeze <qv_dir> <scores.csv> <preference.csv>  checks, then SCORES-FROZEN.csv / PREFERENCE-FROZEN.csv, read-only
  unblind <qv_dir>                               refuses unless frozen sheets and key match; writes key-unblinded.json

Run with the production interpreter: mflux/.venv/bin/python3.12 research/qwen/qv/qv_blind.py ..."""
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
from qq_blind import ELEMENTS  # noqa: E402  (the Q-Q text elements, verbatim)

TASKS = {t["id"]: t for t in json.loads((ROOT / "research/editing/real-world/task-manifest.json").read_text())["tasks"]}
NSLOT = 5
TEXT_CAT = {"PRESERVED", "DEGRADED", "GARBLED", "REMOVED", "NA"}
FIDELITY = {"PASS", "MINOR", "MAJOR"}
FAMILIES = {"seam/halo", "grain/grid", "malformed-object", "texture-smear", "lighting-mismatch", "colour-cast",
            "detail-loss/blur", "ghosting/duplication", "oversharpening"}
COLUMNS = ["id", "fidelity", "fidelity_family"] + [f"t{i}" for i in range(1, NSLOT + 1)] + ["notes"]
PREF_COLUMNS = ["sheet", "text_preference", "notes"]
RUBRIC = """# Rater instructions (provenance-blind)

Each sheet is ONE composite image `<SHEET>.png` with three panels of the same photograph:
- **ORIGINAL**: the photograph, reduced in size (the largest panel);
- **A** and **B**: two processed versions of the same photograph, each shown at its own native pixel size.
For portrait photographs the panels are side by side (ORIGINAL left, then A, then B); for landscape photographs they are
stacked (ORIGINAL top, then A, then B). ITEMS.md states the layout of each sheet.

You are not told how A and B were produced, and you must not try to find out. They are NOT edits: nothing was supposed
to change. Judge how faithfully each one keeps the original, above all its lettering. `ITEMS.md` lists, per sheet,
numbered TEXT ELEMENTS (lettering in the photograph, by location only); read their wording off the ORIGINAL panel.

Read ONLY the files in this directory (`ITEMS.md`, this file, the `<SHEET>.png` composites, the two templates).
Do not open any other file in the repository. Inspect lettering at native resolution: crop the same region of ORIGINAL,
A and B (for example `sips -c <h> <w> --cropOffset <y> <x> in.png --out <file>`), writing crops ONLY to a scratch
directory outside the repository. Do not enlarge crops with smoothing: judge what the pixels show. Score the sheets in
the order listed in ITEMS.md, A and B each on their own merits (rows `<SHEET>-A` and `<SHEET>-B`), then compare them.

## 1. Per processed version (scores-draft.csv; one row per version)
**Text elements `t1`..`t5`** (the sheet's numbered TEXT ELEMENTS; `-` for numbers the sheet does not have):
- `PRESERVED`: the same wording as in ORIGINAL is readable and the lettering looks like the original's (allowing the
  softening that a smaller size causes);
- `DEGRADED`: the same wording is still correctly readable, but glyphs are visibly softened, deformed or partly missing;
- `GARBLED`: the wording can no longer be read as the original's: wrong, invented or duplicated letters, gibberish, or
  unreadable where ORIGINAL is readable (say in the note whether it is wrong letters or blur);
- `REMOVED`: the element or its lettering is gone or replaced by something else;
- `NA`: the element's lettering cannot be read in ORIGINAL either (give the same NA for A and B). If ORIGINAL is
  readable but you are unsure about A or B because the text is tiny, choose the category you can defend and say so in
  the note; do not use NA for that.

**`fidelity`** (everything apart from the lettering): `PASS` = matches ORIGINAL apart from the softening a smaller size
causes; `MINOR` = visible deviation (colour, texture, small artifacts) that is not distracting; `MAJOR` = distracting
deviation or changed content/structure. For MINOR or MAJOR name the family in `fidelity_family`: seam/halo, grain/grid,
malformed-object, texture-smear, lighting-mismatch, colour-cast, detail-loss/blur, ghosting/duplication, oversharpening,
other:<one word>. Leave it empty for PASS.

Write one short factual note per version (what decided the scores, naming the elements).

## 2. Per sheet (preference-draft.csv; one row per sheet)
`text_preference`: which version keeps the TEXT ELEMENTS better: `A`, `B`, or `SAME` (no material difference). Judge
only the listed text elements; one short note.

## Output
Append each row to `scores-draft.csv` / `preference-draft.csv` (headers exactly as in the templates) as soon as it is
scored, in ITEMS.md order, so that a partial sheet survives an interruption. Values exactly as above.
"""


def sha256(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def readonly(p: Path) -> None:
    os.chmod(p, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)


def incident(d: Path, stage: str, err: BaseException) -> None:
    d.mkdir(parents=True, exist_ok=True)
    (d / f"INCIDENT-{time.strftime('%Y%m%dT%H%M%S')}.json").write_text(
        json.dumps({"time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "stage": stage, "error": repr(err)}, indent=1))


def sheet(staged: Path, a: Path, b: Path) -> tuple[Image.Image, str]:
    ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    if ia.size != ib.size:
        raise ValueError(f"A and B differ in size: {ia.size} vs {ib.size}")
    o = Image.open(staged).convert("RGB")
    scale = min(1.0, 2048 / max(o.size))  # downscale only, never upscale
    if scale < 1:
        o = o.resize((round(o.width * scale), round(o.height * scale)), Image.Resampling.LANCZOS)
    gap = 24
    if o.width >= o.height:  # landscape: stacked
        w = max(o.width, ia.width)
        canvas = Image.new("RGB", (w, o.height + 2 * ia.height + 2 * gap), "white")
        canvas.paste(o, (0, 0))
        canvas.paste(ia, (0, o.height + gap))
        canvas.paste(ib, (0, o.height + ia.height + 2 * gap))
        return canvas, "stacked: ORIGINAL top, then A, then B (A and B at native size, left-aligned)"
    h = max(o.height, ia.height)
    canvas = Image.new("RGB", (o.width + 2 * ia.width + 2 * gap, h), "white")
    canvas.paste(o, (0, 0))
    canvas.paste(ia, (o.width + gap, 0))
    canvas.paste(ib, (o.width + ia.width + 2 * gap, 0))
    return canvas, "side by side: ORIGINAL left, then A, then B (A and B at native size, top-aligned)"


def prepare(items_path: str, qv_dir: str, seed: str) -> None:
    d = Path(qv_dir)
    items = json.loads(Path(items_path).read_text())
    hashes = {}
    for it in items:
        for k in ("staged", "input", "roundtrip"):
            hashes[it[k]] = sha256(it[k])
    if d.exists():
        sys.exit(f"refusing: {d} exists")
    (d / "key").mkdir(parents=True)
    (d / "blind").mkdir()
    try:
        rng = random.Random(int(seed))
        order = list(range(len(items)))
        rng.shuffle(order)
        key = {}
        for n, i in enumerate(order):
            it = items[i]
            sides = ["input", "roundtrip"]
            rng.shuffle(sides)
            key[f"V{n + 1:02d}"] = {**{k: it[k] for k in ("item", "task", "budget", "run", "staged")},
                                    "A": sides[0], "B": sides[1], "A_path": it[sides[0]], "B_path": it[sides[1]]}
        kp = d / "key" / "KEY-DO-NOT-OPEN-BEFORE-FREEZE.json"
        tmp = kp.with_suffix(".tmp")
        tmp.write_text(json.dumps(key, indent=1))
        os.replace(tmp, kp)
        readonly(kp)
        comp, lines = {}, ["# Q-V sheets (provenance-blind)", ""]
        for sid in sorted(key):
            k = key[sid]
            img, layout = sheet(Path(k["staged"]), Path(k["A_path"]), Path(k["B_path"]))
            p = d / "blind" / f"{sid}.png"
            img.save(p)  # pixels only, no metadata
            comp[sid] = sha256(p)
            lines += [f"## {sid}  (`{sid}.png`; {layout}; A and B are {Image.open(k['A_path']).size[0]}x"
                      f"{Image.open(k['A_path']).size[1]} px)",
                      "- **TEXT ELEMENTS:** " + "; ".join(f"t{i + 1} = {e}" for i, e in enumerate(ELEMENTS[k["task"]])),
                      ""]
        (d / "blind" / "ITEMS.md").write_text("\n".join(lines))
        (d / "blind" / "RATER-INSTRUCTIONS.md").write_text(RUBRIC)
        with (d / "blind" / "scores-template.csv").open("w", newline="") as f:
            csv.writer(f).writerow(COLUMNS)
        with (d / "blind" / "preference-template.csv").open("w", newline="") as f:
            csv.writer(f).writerow(PREF_COLUMNS)
        manifest = {"tool": "research/qwen/qv/qv_blind.py", "prepared": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    "seed": int(seed), "sheets": len(items), "input_sha256": hashes, "key_sha256": sha256(kp),
                    "composite_sha256": comp, "items_md_sha256": sha256(d / "blind" / "ITEMS.md"),
                    "frozen_scores_sha256": None, "frozen_preference_sha256": None}
        (d / "MANIFEST.json").write_text(json.dumps(manifest, indent=1))
        print(f"prepared {len(items)} sheets in {d}/blind (key sealed: {manifest['key_sha256'][:16]}…)")
    except BaseException as e:
        incident(d, "prepare", e)
        raise


def problems(d: Path, scores: Path, pref: Path) -> list[str]:
    man = json.loads((d / "MANIFEST.json").read_text())
    sheets = sorted(man["composite_sha256"])
    n_el, cur = {}, None
    for line in (d / "blind" / "ITEMS.md").read_text().splitlines():
        if line.startswith("## V"):
            cur = line.split()[1]
        if line.startswith("- **TEXT ELEMENTS:**"):
            n_el[cur] = len(re.findall(r"\bt\d+ = ", line))
    out = []
    if scores.read_text().splitlines()[0] != ",".join(COLUMNS):
        out.append("scores header differs from the template")
    rows = list(csv.DictReader(scores.open()))
    want = [f"{s}-{x}" for s in sheets for x in "AB"]
    ids = [r["id"] for r in rows]
    if sorted(ids) != sorted(want):
        out.append(f"score ids: missing {sorted(set(want) - set(ids))}, extra {sorted(set(ids) - set(want))}, "
                   f"duplicates {sorted({i for i in ids if ids.count(i) > 1})}")
    by = {r["id"]: r for r in rows}
    for r in rows:
        if None in r or any(v is None for v in r.values()):
            out.append(f"{r.get('id')}: wrong column count")
            continue
        if r["fidelity"] not in FIDELITY:
            out.append(f"{r['id']}: fidelity not in {sorted(FIDELITY)}")
        fam = (r["fidelity_family"] or "").strip()
        if r["fidelity"] == "PASS" and fam:
            out.append(f"{r['id']}: fidelity_family must be empty when fidelity is PASS")
        if r["fidelity"] in ("MINOR", "MAJOR") and not (fam in FAMILIES or fam.startswith("other:")):
            out.append(f"{r['id']}: fidelity_family not in the list")
        n = n_el.get(r["id"].split("-")[0], 0)
        for i in range(1, NSLOT + 1):
            v = r[f"t{i}"]
            if i <= n and v not in TEXT_CAT:
                out.append(f"{r['id']}: t{i} not in {sorted(TEXT_CAT)}")
            if i > n and v != "-":
                out.append(f"{r['id']}: t{i} must be '-' (this sheet has {n} text elements)")
    for s in sheets:
        a, b = by.get(f"{s}-A"), by.get(f"{s}-B")
        if a and b:
            for i in range(1, NSLOT + 1):
                if (a[f"t{i}"] == "NA") != (b[f"t{i}"] == "NA"):
                    out.append(f"{s}: t{i} is NA for one version only (NA means unreadable in ORIGINAL)")
    if pref.read_text().splitlines()[0] != ",".join(PREF_COLUMNS):
        out.append("preference header differs from the template")
    prows = list(csv.DictReader(pref.open()))
    pids = [r["sheet"] for r in prows]
    if sorted(pids) != sheets:
        out.append(f"preference sheets: missing {sorted(set(sheets) - set(pids))}, extra {sorted(set(pids) - set(sheets))}, "
                   f"duplicates {sorted({i for i in pids if pids.count(i) > 1})}")
    for r in prows:
        if r.get("text_preference") not in ("A", "B", "SAME"):
            out.append(f"{r.get('sheet')}: text_preference must be A, B or SAME")
    return out


def check(qv_dir: str, scores: str | None = None, pref: str | None = None) -> None:
    d = Path(qv_dir)
    probs = problems(d, Path(scores) if scores else d / "blind" / "scores-draft.csv",
                     Path(pref) if pref else d / "blind" / "preference-draft.csv")
    print("\n".join(probs) if probs else "no format violations")


def freeze(qv_dir: str, scores: str, pref: str) -> None:
    d = Path(qv_dir)
    man = json.loads((d / "MANIFEST.json").read_text())
    if man.get("frozen_scores_sha256"):
        sys.exit("refusing: already frozen")
    probs = problems(d, Path(scores), Path(pref))
    if probs:
        sys.exit("invalid sheets:\n  " + "\n  ".join(probs))
    for src, name, field in ((scores, "SCORES-FROZEN.csv", "frozen_scores_sha256"),
                             (pref, "PREFERENCE-FROZEN.csv", "frozen_preference_sha256")):
        dst = d / name
        shutil.copyfile(src, dst)
        readonly(dst)
        man[field] = sha256(dst)
    man["frozen_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    (d / "MANIFEST.json").write_text(json.dumps(man, indent=1))
    readonly(d / "MANIFEST.json")
    print(f"frozen: scores {man['frozen_scores_sha256']}  preference {man['frozen_preference_sha256']}")


def unblind(qv_dir: str) -> None:
    d = Path(qv_dir)
    man = json.loads((d / "MANIFEST.json").read_text())
    kp = d / "key" / "KEY-DO-NOT-OPEN-BEFORE-FREEZE.json"
    for name, field in (("SCORES-FROZEN.csv", "frozen_scores_sha256"), ("PREFERENCE-FROZEN.csv", "frozen_preference_sha256")):
        if not man.get(field) or sha256(d / name) != man[field]:
            sys.exit(f"refusing: {name} is not frozen or no longer matches its recorded hash")
    if sha256(kp) != man["key_sha256"]:
        sys.exit("refusing: key does not match its recorded hash")
    key = json.loads(kp.read_text())
    (d / "key-unblinded.json").write_text(json.dumps(key, indent=1))
    print(json.dumps(key, indent=1))


if __name__ == "__main__":
    cmd, *args = sys.argv[1:]
    {"prepare": prepare, "check": check, "freeze": freeze, "unblind": unblind}[cmd](*args)
