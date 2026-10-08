"""Arm-blind paired review tool for the Phase 6 Q-Q diagnostic (research/qwen/qq/PROTOCOL.md §6-§7). A paired sibling
of research/editing/real-world/g2_blind.py (same stages and guarantees; BLIND-PROTOCOL.md).

  prepare <pairs.json> <qq_dir> <seed>
      pairs.json: [{"pair": "R12-512", "task": "R12", "budget": 512, "seed": int, "kind": "primary|second_seed",
                    "source": staged.png, "q4": out.png, "q8": out.png, "q4_run": id, "q8_run": id}]
      Hashes every input first; refuses an existing <qq_dir>. Shuffles the sheets and assigns the A/B sides per sheet
      with random.Random(seed); writes the key read-only BEFORE any composite exists; then renders <qq_dir>/blind/<ID>.png
      (source | A | B; the source resized to the output size, i.e. what the model was conditioned on, then all three
      panels scaled to a long side of 1024 px; portrait -> side by side, landscape -> stacked), ITEMS.md,
      RATER-INSTRUCTIONS.md, scores-template.csv, preference-template.csv and MANIFEST.json.
  check <qq_dir> [scores.csv] [preference.csv]
      Format-only checks of the rater's drafts (prints violations only, never score content).
  freeze <qq_dir> <scores.csv> <preference.csv>
      Same checks, then copies both to SCORES-FROZEN.csv / PREFERENCE-FROZEN.csv, records their sha256, read-only.
  unblind <qq_dir>
      Refuses unless both frozen sheets and the key match their recorded hashes; writes key-unblinded.json.

Run with the production interpreter: mflux/.venv/bin/python3.12 research/qwen/qq/qq_blind.py ..."""
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
TASKS = {t["id"]: t for t in json.loads((ROOT / "research/editing/real-world/task-manifest.json").read_text())["tasks"]}
# Text elements per task, defined from the SOURCE photographs' lettering before any q8 output existed (PROTOCOL.md §7).
# Descriptions give the location only, never the wording: the rater reads the wording off the original panel.
ELEMENTS = {
    "R02": ["the blue street-name sign on the wall above the van (white lettering, three lines)",
            "the small white plate under the red no-entry sign (one word above two bicycle pictograms)"],
    "R12": ["the banner hung across the street (two lines of lettering, round logos at both ends)",
            "the pink half-disc hanging sign at the upper left (two words)",
            "the small green sign on the brick wall (two lines)",
            "the purple shopfront fascia lettering at the left edge, and the pink round sign with a letter below it",
            "the signs at the right edge (the tall vertical sign; the red fascia above the lit window)"],
    "R15": ["the large shop sign above the windows (the main word and the small word beside it)",
            "the white banner at the top of the right-hand window (two lines)",
            "the number in the speech-bubble decal at the top of the door glass",
            "the poster on the lower door panel (several lines)",
            "the small round red sticker on the door glass"],
}
NSLOT = 5
TEXT_CAT = {"PRESERVED", "DEGRADED", "GARBLED", "REMOVED", "NA"}
VOCAB = {"adherence": {"PASS", "PARTIAL", "FAIL"}, "preservation": {"PASS", "PARTIAL", "FAIL"},
         "composition": {"PASS", "FAIL"}, "quality": {"PASS", "MINOR", "MAJOR"}, "text": {"PASS", "PARTIAL", "FAIL"}}
FAMILIES = {"seam/halo", "grain/grid", "malformed-object", "texture-smear", "lighting-mismatch", "colour-cast",
            "detail-loss/blur", "ghosting/duplication", "oversharpening"}
COLUMNS = ["id", "adherence", "preservation", "composition", "quality", "quality_family", "text"] + \
          [f"t{i}" for i in range(1, NSLOT + 1)] + ["notes"]
PREF_COLUMNS = ["sheet", "text_preference", "notes"]
RUBRIC = """# Rater instructions (arm-blind paired review)

Each sheet is ONE composite image `<SHEET>.png` with three panels of the same scene:
- portrait scenes: **left = the original photograph**, **middle = result A**, **right = result B**;
- landscape scenes: **top = the original photograph**, **middle = result A**, **bottom = result B**.
A and B are two edited results of the same original and the same instruction, produced by two configurations of an
image-editing system. You are not told how the configurations differ or which is which, and you must not try to find
out. `ITEMS.md` gives, per sheet, the instruction, what MUST CHANGE, what MUST NOT CHANGE, and a numbered list of
TEXT ELEMENTS (lettering in the original that must stay unchanged).

Read ONLY the files in this directory (`ITEMS.md`, this file, the `<SHEET>.png` composites, the two templates).
Do not open any other file in the repository. You may crop any region of a composite at its native resolution
(for example `sips -c <h> <w> --cropOffset <y> <x> in.png --out <file>`), writing crops ONLY to a scratch directory
outside the repository; crops are views of the same composite. Score every sheet in the order listed in ITEMS.md.
Score A and B each on their own merits (one row each, ids `<SHEET>-A` and `<SHEET>-B`), then compare them.

## 1. Per result (scores-draft.csv; one row per result; score in this order)
| dimension | PASS | PARTIAL / MINOR | FAIL / MAJOR |
|---|---|---|---|
| adherence | the MUST CHANGE is fully present and recognizable | present but incomplete or wrong in an attribute (shade, partial removal/recolour, wrong object type, leftovers) | absent, or a different change |
| preservation | every MUST NOT CHANGE element is recognizably unchanged (small global tone/sharpness shifts are allowed) | exactly ONE listed element materially altered, OR one unrequested object added or removed | scene regenerated, identity of a person/object lost, or >= 2 listed elements materially altered |
| composition | layout, viewpoint and framing unchanged | - | layout, viewpoint, crop or zoom changed |
| quality | natural, no visible artifact | MINOR: visible but not distracting | MAJOR: distracting or unrealistic (seams/halos, grain/grid, malformed objects, smeared texture, implausible lighting, heavy over-sharpening) |
| text | exact wording, no duplication/dropped letters/ghosting, legible | legible but a minor glyph/style deviation | wrong or misspelled word, garbled, duplicated or ghosted letters, illegible, or text changed where it had to stay |

For quality MINOR or MAJOR name the artifact family in `quality_family`: seam/halo, grain/grid, malformed-object,
texture-smear, lighting-mismatch, colour-cast, detail-loss/blur, ghosting/duplication, oversharpening, other:<one word>.
Leave it empty for PASS.

**Text elements `t1`..`t5`** (the numbered TEXT ELEMENTS of the sheet; `-` for numbers the sheet does not have):
- `PRESERVED`: the same wording as in the original is readable, and the lettering looks like the original's
  (allowing the softening any resize causes);
- `DEGRADED`: the same wording is still correctly readable, but the glyphs are visibly deformed, smeared or partly missing;
- `GARBLED`: the wording can no longer be read as the original's: wrong, invented or duplicated letters, gibberish, or
  unreadable where the original panel is readable (say in the note whether it is wrong letters or blur);
- `REMOVED`: the element or its lettering is gone or replaced by something else;
- `NA`: the element's lettering cannot be read in the ORIGINAL panel either (give the same NA for A and B).

Write one short factual note per result (what decided the scores, naming the elements).

## 2. Per sheet (preference-draft.csv; one row per sheet)
`text_preference`: which result preserves the TEXT ELEMENTS better: `A`, `B`, or `SAME` (no material difference).
Judge only the listed text elements; one short note.

## Output
Append each row to `scores-draft.csv` / `preference-draft.csv` (headers exactly as in the templates) as soon as it is
scored, in ITEMS.md order, so that a partial sheet survives an interruption. Values exactly as above.
"""


def sha256(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def readonly(p: Path) -> None:
    os.chmod(p, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)


def incident(d: Path, stage: str, err: BaseException) -> None:
    d.mkdir(parents=True, exist_ok=True)
    rec = {"time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "stage": stage, "error": repr(err)}
    (d / f"INCIDENT-{time.strftime('%Y%m%dT%H%M%S')}.json").write_text(json.dumps(rec, indent=1))


def triptych(src: Path, a: Path, b: Path) -> tuple[Image.Image, str]:
    ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    if ia.size != ib.size:
        raise ValueError(f"A and B differ in size: {ia.size} vs {ib.size}")
    s = Image.open(src).convert("RGB").resize(ia.size, Image.Resampling.LANCZOS)  # what the model was conditioned on
    scale = 1024 / max(ia.size)
    size = (round(ia.width * scale), round(ia.height * scale))
    panels = [x.resize(size, Image.Resampling.LANCZOS) for x in (s, ia, ib)]
    gap = 16
    if size[0] >= size[1]:
        sheet = Image.new("RGB", (size[0], 3 * size[1] + 2 * gap), "white")
        for i, p in enumerate(panels):
            sheet.paste(p, (0, i * (size[1] + gap)))
        return sheet, "top = original, middle = A, bottom = B"
    sheet = Image.new("RGB", (3 * size[0] + 2 * gap, size[1]), "white")
    for i, p in enumerate(panels):
        sheet.paste(p, (i * (size[0] + gap), 0))
    return sheet, "left = original, middle = A, right = B"


def prepare(pairs_path: str, qq_dir: str, seed: str) -> None:
    d = Path(qq_dir)
    pairs = json.loads(Path(pairs_path).read_text())
    hashes = {}
    for p in pairs:
        for k in ("source", "q4", "q8"):
            hashes[p[k]] = sha256(Path(p[k]))
    if d.exists():
        sys.exit(f"refusing: {d} exists")
    (d / "key").mkdir(parents=True)
    (d / "blind").mkdir()
    try:
        rng = random.Random(int(seed))
        order = list(range(len(pairs)))
        rng.shuffle(order)
        key = {}
        for n, i in enumerate(order):
            p = pairs[i]
            sides = ["q4", "q8"]
            rng.shuffle(sides)
            key[f"P{n + 1:02d}"] = {**{k: p[k] for k in ("pair", "task", "budget", "seed", "kind", "source")},
                                    "A": sides[0], "B": sides[1], "A_run": p[f"{sides[0]}_run"], "B_run": p[f"{sides[1]}_run"],
                                    "A_output": p[sides[0]], "B_output": p[sides[1]]}
        kp = d / "key" / "KEY-DO-NOT-OPEN-BEFORE-FREEZE.json"
        tmp = kp.with_suffix(".tmp")
        tmp.write_text(json.dumps(key, indent=1))
        os.replace(tmp, kp)
        readonly(kp)
        comp, lines = {}, ["# Q-Q sheets (arm-blind paired review)", ""]
        for sid in sorted(key):
            k = key[sid]
            t = TASKS[k["task"]]
            img, layout = triptych(Path(k["source"]), Path(k["A_output"]), Path(k["B_output"]))
            p = d / "blind" / f"{sid}.png"
            img.save(p)  # pixels only, no metadata
            comp[sid] = sha256(p)
            lines += [f"## {sid}  (`{sid}.png`; {layout})",
                      f"- **Instruction:** {t['instruction']}",
                      f"- **MUST CHANGE:** {t['must_change']}",
                      "- **MUST NOT CHANGE:** " + "; ".join(t["must_not_change"]),
                      "- **TEXT ELEMENTS:** " + "; ".join(f"t{i + 1} = {e}" for i, e in enumerate(ELEMENTS[k["task"]])),
                      ""]
        (d / "blind" / "ITEMS.md").write_text("\n".join(lines))
        (d / "blind" / "RATER-INSTRUCTIONS.md").write_text(RUBRIC)
        with (d / "blind" / "scores-template.csv").open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(COLUMNS)
        with (d / "blind" / "preference-template.csv").open("w", newline="") as f:
            csv.writer(f).writerow(PREF_COLUMNS)
        manifest = {"tool": "research/qwen/qq/qq_blind.py", "prepared": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    "seed": int(seed), "sheets": len(pairs), "input_sha256": hashes, "key_sha256": sha256(kp),
                    "composite_sha256": comp, "items_md_sha256": sha256(d / "blind" / "ITEMS.md"),
                    "frozen_scores_sha256": None, "frozen_preference_sha256": None}
        (d / "MANIFEST.json").write_text(json.dumps(manifest, indent=1))
        print(f"prepared {len(pairs)} sheets in {d}/blind (key sealed: {manifest['key_sha256'][:16]}…)")
    except BaseException as e:
        incident(d, "prepare", e)
        raise


def problems(d: Path, scores: Path, pref: Path) -> list[str]:
    man = json.loads((d / "MANIFEST.json").read_text())
    sheets = sorted(man["composite_sha256"])
    tasks = {}
    for line in (d / "blind" / "ITEMS.md").read_text().splitlines():
        if line.startswith("## P"):
            cur = line.split()[1]
        if line.startswith("- **TEXT ELEMENTS:**"):
            tasks[cur] = len(re.findall(r"\bt\d+ = ", line))
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
        for k, allowed in VOCAB.items():
            if r[k] not in allowed:
                out.append(f"{r['id']}: {k} not in {sorted(allowed)}")
        fam = (r["quality_family"] or "").strip()
        if r["quality"] == "PASS" and fam:
            out.append(f"{r['id']}: quality_family must be empty when quality is PASS")
        if r["quality"] in ("MINOR", "MAJOR") and not (fam in FAMILIES or fam.startswith("other:")):
            out.append(f"{r['id']}: quality_family not in the list")
        n = tasks.get(r["id"].split("-")[0], 0)
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
                    out.append(f"{s}: t{i} is NA for one result only (NA means unreadable in the original panel)")
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


def check(qq_dir: str, scores: str | None = None, pref: str | None = None) -> None:
    d = Path(qq_dir)
    s = Path(scores) if scores else d / "blind" / "scores-draft.csv"
    p = Path(pref) if pref else d / "blind" / "preference-draft.csv"
    probs = problems(d, s, p)
    print("\n".join(probs) if probs else "no format violations")


def freeze(qq_dir: str, scores: str, pref: str) -> None:
    d = Path(qq_dir)
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


def unblind(qq_dir: str) -> None:
    d = Path(qq_dir)
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
