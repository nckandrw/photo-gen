"""Provenance-blind review tool for Phase 8 Q-VR (PROTOCOL.md section 10). A sibling of research/qwen/qv/qv_blind.py
(same stages and guarantees: research/experiments/BLIND-PROTOCOL.md), generalised to N panels per sheet and shipped as
separate panel files (no composites), so a rater can crop each at native resolution.

  prepare <sheets.json> <review_dir> <seed>
      sheets.json: [{"kind": "item", "task": "R12", "budget": 512, "staged": <full-res staged source>,
                     "panels": {"D0": png, "A1": png, "A2": png, ...}},
                    {"kind": "composite", "task": "R02", "budget": 1024, "staged": ..., "instruction": "...",
                     "panels": {"G2": png, "HARD": png, "FEATHER": png}}]
      Hashes every input; refuses an existing <review_dir>. random.Random(seed) shuffles the sheet order and, per sheet,
      the panel labels A, B, C, ...; the key is written read-only BEFORE any panel file exists. Then writes
      blind/<SHEET>-ORIGINAL.png (the staged source, long side <= 2048, never upscaled) and blind/<SHEET>-<L>.png (each
      panel as RGB at its native size, pixels only), ITEMS.md, RATER-INSTRUCTIONS.md, scores-template.csv, MANIFEST.json.
  check <review_dir> [scores.csv]      format-only checks (violations only, never content)
  freeze <review_dir> <scores.csv>     checks, then SCORES-FROZEN.csv, read-only
  unblind <review_dir>                 refuses unless the frozen sheet and the key match; writes key-unblinded.json

Run with the production interpreter: mflux/.venv/bin/python3.12 research/qwen/qv-reference/qvr_blind.py ..."""
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

NSLOT = 5
TEXT_CAT = {"PRESERVED", "DEGRADED", "GARBLED", "REMOVED", "NA"}
FIDELITY = {"PASS", "MINOR", "MAJOR"}
ADHERENCE = {"PASS", "PARTIAL", "FAIL"}
LEVEL = {"NONE", "MINOR", "MAJOR"}
FAMILIES = {"seam/halo", "grain/grid", "malformed-object", "texture-smear", "lighting-mismatch", "colour-cast",
            "detail-loss/blur", "ghosting/duplication", "oversharpening"}
COLUMNS = (["id", "fidelity", "fidelity_family", "adherence", "seam", "realism", "unintended"]
           + [f"t{i}" for i in range(1, NSLOT + 1)] + ["notes"])
KEYNAME = "KEY-DO-NOT-OPEN-BEFORE-FREEZE.json"
RUBRIC = """# Rater instructions (provenance-blind)

Each sheet is a set of image files of ONE photograph:
- `<SHEET>-ORIGINAL.png`: the photograph, reduced in size. It is the ground truth for what the lettering says.
- `<SHEET>-A.png`, `<SHEET>-B.png`, `<SHEET>-C.png`, ...: processed versions of the same photograph, each at its own
  native pixel size. You are not told how they were produced, and you must not try to find out. Some versions may look
  identical or nearly identical to each other; score each one on its own merits anyway.

There are two kinds of sheet; `ITEMS.md` gives each sheet's kind, its panel labels, its sizes and its numbered TEXT
ELEMENTS (lettering in the photograph, by location only; read their wording off ORIGINAL).

Read ONLY the files in this directory (`ITEMS.md`, this file, the sheet images, `scores-template.csv`). Do not open any
other file in the repository. Inspect lettering at native resolution: crop the same region from ORIGINAL and from each
version (for example `sips -c <h> <w> --cropOffset <y> <x> in.png --out <file>`), writing crops ONLY to a scratch
directory outside the repository. Do not enlarge crops with smoothing: judge what the pixels show. Score the sheets in
the order listed in ITEMS.md; within a sheet, one row per version (`<SHEET>-A`, `<SHEET>-B`, ...).

## Text elements `t1`..`t5` (both kinds; `-` for numbers the sheet does not have)
- `PRESERVED`: the same wording as in ORIGINAL is readable and the lettering looks like the original's (allowing the
  softening that a smaller size causes);
- `DEGRADED`: the same wording is still correctly readable, but glyphs are visibly softened, deformed or partly missing;
- `GARBLED`: the wording can no longer be read as the original's: wrong, invented or duplicated letters, gibberish, or
  unreadable where ORIGINAL is readable (say in the note whether it is wrong letters or blur);
- `REMOVED`: the element or its lettering is gone or replaced by something else;
- `NA`: the element's lettering cannot be read in ORIGINAL either (then give NA for every version of that sheet). If
  ORIGINAL is readable but you are unsure about a version because the text is tiny, choose the category you can defend
  and say so in the note; do not use NA for that.

## Kind "item": nothing was supposed to change
Judge how faithfully each version keeps ORIGINAL, above all its lettering. Fill `fidelity`, `fidelity_family`, `t1..t5`,
`notes`; put `-` in `adherence`, `seam`, `realism`, `unintended`.
- **`fidelity`** (everything apart from the lettering): `PASS` = matches ORIGINAL apart from the softening a smaller size
  causes; `MINOR` = visible deviation (colour, texture, small artifacts) that is not distracting; `MAJOR` = distracting
  deviation or changed content/structure. For MINOR or MAJOR name the family in `fidelity_family`: seam/halo,
  grain/grid, malformed-object, texture-smear, lighting-mismatch, colour-cast, detail-loss/blur, ghosting/duplication,
  oversharpening, other:<one word>. Leave it empty for PASS.

## Kind "edit": an instruction was applied (ITEMS.md quotes it)
Judge each version as a complete edited photograph. Fill `adherence`, `seam`, `realism`, `unintended`, `t1..t5`,
`notes`; put `-` in `fidelity` and `fidelity_family`.
- **`adherence`**: `PASS` = the instruction is fully carried out; `PARTIAL` = partly (e.g. remnants of the object);
  `FAIL` = not carried out.
- **`seam`**: visible boundaries, edges, halos or discontinuities: `NONE`, `MINOR` (visible on inspection), `MAJOR`
  (obvious).
- **`realism`** of the whole image as a photograph: `PASS`, `MINOR` (small implausibilities), `MAJOR` (clearly
  implausible: wrong shadows/reflections, broken geometry, impossible content).
- **`unintended`** changes OUTSIDE what the instruction asks for, compared with ORIGINAL: `NONE`, `MINOR`, `MAJOR`.
- Text elements as above (they are all outside what the instruction asks to change).

## Output
Copy `scores-template.csv` to `scores-draft.csv` in this directory and append one row per version as you go. Notes: one
short sentence per text element you call anything but PRESERVED, naming what you see. When done, stop; the session
assistant runs a format check and may return format-only corrections.
"""


def sha256(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def readonly(p: Path) -> None:
    os.chmod(p, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)


def incident(d: Path, stage: str, err: BaseException) -> None:
    d.mkdir(parents=True, exist_ok=True)
    (d / f"INCIDENT-{time.strftime('%Y%m%dT%H%M%S')}.json").write_text(
        json.dumps({"time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "stage": stage, "error": repr(err)}, indent=1))


def prepare(sheets_path: str, review_dir: str, seed: str) -> None:
    d = Path(review_dir)
    sheets = json.loads(Path(sheets_path).read_text())
    hashes = {}
    for s in sheets:
        for p in [s["staged"], *s["panels"].values()]:
            hashes[p] = sha256(p)
    if d.exists():
        sys.exit(f"refusing: {d} exists")
    (d / "key").mkdir(parents=True)
    (d / "blind").mkdir()
    try:
        rng = random.Random(int(seed))
        order = list(range(len(sheets)))
        rng.shuffle(order)
        key = {}
        for n, i in enumerate(order):
            s = sheets[i]
            arms = list(s["panels"])
            rng.shuffle(arms)
            labels = [chr(ord("A") + j) for j in range(len(arms))]
            key[f"S{n + 1:02d}"] = {"kind": s["kind"], "task": s["task"], "budget": s["budget"], "staged": s["staged"],
                                    "instruction": s.get("instruction"), "panels": dict(zip(labels, arms)),
                                    "paths": {lab: s["panels"][arm] for lab, arm in zip(labels, arms)}}
        kp = d / "key" / KEYNAME
        tmp = kp.with_suffix(".tmp")
        tmp.write_text(json.dumps(key, indent=1))
        os.replace(tmp, kp)
        readonly(kp)
        rendered, lines = {}, ["# Q-VR sheets (provenance-blind)", ""]
        for sid in sorted(key):
            k = key[sid]
            o = Image.open(k["staged"]).convert("RGB")
            if max(o.size) > 2048:
                s_ = 2048 / max(o.size)
                o = o.resize((round(o.width * s_), round(o.height * s_)), Image.Resampling.LANCZOS)
            p = d / "blind" / f"{sid}-ORIGINAL.png"
            o.save(p)
            rendered[p.name] = sha256(p)
            sizes = []
            for lab, src in k["paths"].items():
                im = Image.open(src).convert("RGB")
                p = d / "blind" / f"{sid}-{lab}.png"
                im.save(p)
                rendered[p.name] = sha256(p)
                sizes.append(f"{lab} {im.width}x{im.height}")
            kind = "item" if k["kind"] == "item" else "edit"
            lines += [f"## {sid}  (kind **{kind}**; ORIGINAL {o.width}x{o.height}; versions: {', '.join(sizes)})"]
            if kind == "edit":
                lines.append(f"- **INSTRUCTION:** \"{k['instruction']}\"")
            lines += ["- **TEXT ELEMENTS:** " + "; ".join(f"t{i + 1} = {e}" for i, e in enumerate(ELEMENTS[k["task"]])), ""]
        (d / "blind" / "ITEMS.md").write_text("\n".join(lines))
        (d / "blind" / "RATER-INSTRUCTIONS.md").write_text(RUBRIC)
        with (d / "blind" / "scores-template.csv").open("w", newline="") as f:
            csv.writer(f).writerow(COLUMNS)
        manifest = {"tool": "research/qwen/qv-reference/qvr_blind.py", "prepared": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    "seed": int(seed), "sheets": len(sheets), "input_sha256": hashes, "key_sha256": sha256(kp),
                    "rendered_sha256": rendered, "items_md_sha256": sha256(d / "blind" / "ITEMS.md"),
                    "frozen_scores_sha256": None}
        (d / "MANIFEST.json").write_text(json.dumps(manifest, indent=1))
        print(f"prepared {len(sheets)} sheets in {d}/blind (key sealed: {manifest['key_sha256'][:16]}…)")
    except BaseException as e:
        incident(d, "prepare", e)
        raise


def problems(d: Path, scores: Path) -> list[str]:
    sheets, cur = {}, None
    for line in (d / "blind" / "ITEMS.md").read_text().splitlines():
        m = re.match(r"## (S\d+)\s+\(kind \*\*(\w+)\*\*.*versions: (.*)\)$", line)
        if m:
            cur = m.group(1)
            sheets[cur] = {"kind": m.group(2), "labels": [v.split()[0] for v in m.group(3).split(", ")], "n": 0}
        if line.startswith("- **TEXT ELEMENTS:**") and cur:
            sheets[cur]["n"] = len(re.findall(r"\bt\d+ = ", line))
    out = []
    if scores.read_text().splitlines()[0] != ",".join(COLUMNS):
        out.append("scores header differs from the template")
    rows = list(csv.DictReader(scores.open()))
    want = [f"{s}-{lab}" for s, v in sheets.items() for lab in v["labels"]]
    ids = [r["id"] for r in rows]
    if sorted(ids) != sorted(want):
        out.append(f"score ids: missing {sorted(set(want) - set(ids))}, extra {sorted(set(ids) - set(want))}, "
                   f"duplicates {sorted({i for i in ids if ids.count(i) > 1})}")
    by = {r["id"]: r for r in rows}
    for r in rows:
        if None in r or any(v is None for v in r.values()):
            out.append(f"{r.get('id')}: wrong column count")
            continue
        sid = r["id"].split("-")[0]
        if sid not in sheets:
            continue
        kind, n = sheets[sid]["kind"], sheets[sid]["n"]
        if kind == "item":
            if r["fidelity"] not in FIDELITY:
                out.append(f"{r['id']}: fidelity not in {sorted(FIDELITY)}")
            fam = (r["fidelity_family"] or "").strip()
            if r["fidelity"] == "PASS" and fam:
                out.append(f"{r['id']}: fidelity_family must be empty when fidelity is PASS")
            if r["fidelity"] in ("MINOR", "MAJOR") and not (fam in FAMILIES or fam.startswith("other:")):
                out.append(f"{r['id']}: fidelity_family not in the list")
            for c in ("adherence", "seam", "realism", "unintended"):
                if r[c] != "-":
                    out.append(f"{r['id']}: {c} must be '-' on an item sheet")
        else:
            for c, allowed in (("adherence", ADHERENCE), ("seam", LEVEL), ("realism", FIDELITY), ("unintended", LEVEL)):
                if r[c] not in allowed:
                    out.append(f"{r['id']}: {c} not in {sorted(allowed)}")
            for c in ("fidelity", "fidelity_family"):
                if r[c] not in ("-", ""):
                    out.append(f"{r['id']}: {c} must be '-' on an edit sheet")
        for i in range(1, NSLOT + 1):
            v = r[f"t{i}"]
            if i <= n and v not in TEXT_CAT:
                out.append(f"{r['id']}: t{i} not in {sorted(TEXT_CAT)}")
            if i > n and v != "-":
                out.append(f"{r['id']}: t{i} must be '-' (this sheet has {n} text elements)")
    for s, v in sheets.items():
        rs = [by.get(f"{s}-{lab}") for lab in v["labels"]]
        if all(rs):
            for i in range(1, NSLOT + 1):
                na = {x[f"t{i}"] == "NA" for x in rs}
                if len(na) > 1:
                    out.append(f"{s}: t{i} is NA for some versions only (NA means unreadable in ORIGINAL)")
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
    dst = d / "SCORES-FROZEN.csv"
    shutil.copyfile(scores, dst)
    readonly(dst)
    man["frozen_scores_sha256"] = sha256(dst)
    man["frozen_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    (d / "MANIFEST.json").write_text(json.dumps(man, indent=1))
    readonly(d / "MANIFEST.json")
    print(f"frozen: scores {man['frozen_scores_sha256']}")


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
    print(json.dumps({s: {"kind": k["kind"], "task": k["task"], "budget": k["budget"], "panels": k["panels"]}
                      for s, k in key.items()}, indent=1))


if __name__ == "__main__":
    cmd, *args = sys.argv[1:]
    {"prepare": prepare, "check": check, "freeze": freeze, "unblind": unblind}[cmd](*args)
