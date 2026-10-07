"""Provenance-blind review tool for G2 (single configuration, so there are no A/B pairs). A single-image sibling of
research/experiments/blind_stage.py that follows research/experiments/BLIND-PROTOCOL.md: separate stages, no stage
can silently redo another, failures become incident records, nothing is deleted.

  prepare <items.json> <g2_dir> <seed>
      items.json: [{"run": run_id, "task": "R01", "budget": 512, "seed": int, "source": staged.png, "output": out.png}]
      Hashes every input first (a missing file aborts before anything is created); refuses an existing <g2_dir>.
      Writes the key  <g2_dir>/key/KEY-DO-NOT-OPEN-BEFORE-FREEZE.json  atomically and read-only BEFORE any
      composite exists, then renders <g2_dir>/blind/<ID>.png (re-rendered pixels, no metadata; both panels scaled to a
      long side of 1024 px; landscape -> source on top, output below; portrait -> source left, output right), plus
      <g2_dir>/blind/ITEMS.md (per ID: instruction, MUST CHANGE, MUST NOT CHANGE, whether text is scored),
      RATER-INSTRUCTIONS.md, scores-template.csv and <g2_dir>/MANIFEST.json (hashes of inputs, key, composites).
  freeze <g2_dir> <scores.csv>
      Validates the sheet (every ID exactly once, fixed vocabulary), copies it to <g2_dir>/SCORES-FROZEN.csv, records
      its sha256 in the manifest, makes both read-only. Freezing twice is refused.
  unblind <g2_dir>
      Refuses unless the frozen scores and the key still match their recorded hashes; then writes
      <g2_dir>/key-unblinded.json (ID -> run/task/budget/seed) and prints it.

Run with the production interpreter: mflux/.venv/bin/python3.12 research/editing/real-world/g2_blind.py ..."""
import csv
import hashlib
import json
import os
import random
import shutil
import stat
import sys
import time
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
TASKS = {t["id"]: t for t in json.loads((HERE / "task-manifest.json").read_text())["tasks"]}
VOCAB = {"adherence": {"PASS", "PARTIAL", "FAIL"}, "preservation": {"PASS", "PARTIAL", "FAIL"},
         "composition": {"PASS", "FAIL"}, "quality": {"PASS", "MINOR", "MAJOR"},
         "text": {"PASS", "PARTIAL", "FAIL", "NA"}}
FAMILIES = {"seam/halo", "grain/grid", "malformed-object", "texture-smear", "lighting-mismatch", "colour-cast",
            "detail-loss/blur", "ghosting/duplication", "oversharpening"}
COLUMNS = ["id", "adherence", "preservation", "composition", "quality", "quality_family", "text", "notes"]
RUBRIC = """# G2 rater instructions (provenance-blind)

You are scoring image edits. Each item is ONE composite image `<ID>.png`:
- landscape images: **top = the original photograph**, **bottom = the edited result**;
- portrait images: **left = the original photograph**, **right = the edited result**.
`ITEMS.md` gives, per ID, the edit instruction, what MUST CHANGE and what MUST NOT CHANGE.

Read ONLY the files in this directory (`ITEMS.md`, this file, the `<ID>.png` composites, `scores-template.csv`).
Do not open any other file in the repository. You are not told which model, settings or run produced an item, and
you must not try to find out. Score every item on its own merits, in the order listed in ITEMS.md.

Score in this order (the first dimension that fails matters most):

| dimension | PASS | PARTIAL / MINOR | FAIL / MAJOR |
|---|---|---|---|
| adherence | the MUST CHANGE is fully present and recognizable | present but incomplete or wrong in an attribute (shade, partial removal/recolour, wrong object type, leftovers) | absent, or a different change |
| preservation | every MUST NOT CHANGE element is recognizably unchanged (small global tone/sharpness shifts are allowed) | exactly ONE listed element materially altered, OR one unrequested object added or removed | scene regenerated, identity of a person/object lost, or >= 2 listed elements materially altered |
| composition | layout, viewpoint and framing unchanged | - | layout, viewpoint, crop or zoom changed |
| quality | natural, no visible artifact | MINOR: visible but not distracting | MAJOR: distracting or unrealistic (seams/halos, grain/grid, malformed objects, smeared texture, implausible lighting, heavy over-sharpening) |
| text (only where ITEMS.md says "text: scored") | exact wording, no duplication/dropped letters/ghosting, legible | legible but a minor glyph/style deviation | wrong or misspelled word, garbled, duplicated or ghosted letters, illegible, or text changed where it had to stay |

For quality MINOR or MAJOR, name the artifact family in `quality_family`, one of: seam/halo, grain/grid,
malformed-object, texture-smear, lighting-mismatch, colour-cast, detail-loss/blur, ghosting/duplication,
oversharpening, other:<one word>. Leave it empty for PASS. Use `text = NA` where text is not scored.
Write one short factual note per item (what you saw that decided the scores).

Output: a CSV with exactly the header of `scores-template.csv`
(id,adherence,preservation,composition,quality,quality_family,text,notes), one row per ID, values exactly as above.
"""


def sha256(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def readonly(p: Path) -> None:
    os.chmod(p, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)


def incident(g2: Path, stage: str, err: BaseException) -> None:
    g2.mkdir(parents=True, exist_ok=True)
    rec = {"time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "stage": stage, "error": repr(err)}
    (g2 / f"INCIDENT-{time.strftime('%Y%m%dT%H%M%S')}.json").write_text(json.dumps(rec, indent=1))


def panel_pair(src: Path, out: Path) -> Image.Image:
    o = Image.open(out).convert("RGB")
    s = Image.open(src).convert("RGB").resize(o.size, Image.Resampling.LANCZOS)  # what the model was conditioned on
    scale = 1024 / max(o.size)
    size = (round(o.width * scale), round(o.height * scale))
    s, o = s.resize(size, Image.Resampling.LANCZOS), o.resize(size, Image.Resampling.LANCZOS)
    gap = 16
    if size[0] >= size[1]:
        sheet = Image.new("RGB", (size[0], 2 * size[1] + gap), "white")
        sheet.paste(s, (0, 0))
        sheet.paste(o, (0, size[1] + gap))
    else:
        sheet = Image.new("RGB", (2 * size[0] + gap, size[1]), "white")
        sheet.paste(s, (0, 0))
        sheet.paste(o, (size[0] + gap, 0))
    return sheet


def prepare(items_path: str, g2_dir: str, seed: str) -> None:
    g2 = Path(g2_dir)
    items = json.loads(Path(items_path).read_text())
    hashes = {}
    for it in items:  # every input is hashed first; a missing file aborts before anything is created
        for k in ("source", "output"):
            hashes[it[k]] = sha256(Path(it[k]))
    if g2.exists():
        sys.exit(f"refusing: {g2} exists")
    (g2 / "key").mkdir(parents=True)
    (g2 / "blind").mkdir()
    try:
        order = list(range(len(items)))
        random.Random(int(seed)).shuffle(order)
        ids = {i: f"Q{n + 1:02d}" for n, i in enumerate(order)}
        key = {ids[i]: {k: items[i][k] for k in ("run", "task", "budget", "seed", "source", "output")}
               for i in range(len(items))}
        key = dict(sorted(key.items()))
        kp = g2 / "key" / "KEY-DO-NOT-OPEN-BEFORE-FREEZE.json"
        tmp = kp.with_suffix(".tmp")
        tmp.write_text(json.dumps(key, indent=1))
        os.replace(tmp, kp)
        readonly(kp)
        comp = {}
        lines = ["# G2 items (provenance-blind)", ""]
        for cid in sorted(key):
            it = key[cid]
            t = TASKS[it["task"]]
            img = panel_pair(Path(it["source"]), Path(it["output"]))
            p = g2 / "blind" / f"{cid}.png"
            img.save(p)  # PIL writes no text chunks unless given: pixels only
            comp[cid] = sha256(p)
            layout = "top = original, bottom = edited" if img.width < img.height else \
                "left = original, right = edited"
            lines += [f"## {cid}  (`{cid}.png`; {layout})",
                      f"- **Instruction:** {t['instruction']}",
                      f"- **MUST CHANGE:** {t['must_change']}",
                      "- **MUST NOT CHANGE:** " + "; ".join(t["must_not_change"]),
                      f"- **text:** {'scored (' + t['text'] + ')' if t['text'] else 'NA'}", ""]
        (g2 / "blind" / "ITEMS.md").write_text("\n".join(lines))
        (g2 / "blind" / "RATER-INSTRUCTIONS.md").write_text(RUBRIC)
        with (g2 / "blind" / "scores-template.csv").open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(COLUMNS)
            for cid in sorted(key):
                w.writerow([cid] + [""] * (len(COLUMNS) - 1))
        manifest = {"tool": "research/editing/real-world/g2_blind.py", "prepared": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    "seed": int(seed), "items": len(items), "input_sha256": hashes, "key_sha256": sha256(kp),
                    "composite_sha256": comp, "items_md_sha256": sha256(g2 / "blind" / "ITEMS.md"),
                    "frozen_scores_sha256": None}
        (g2 / "MANIFEST.json").write_text(json.dumps(manifest, indent=1))
        print(f"prepared {len(items)} items in {g2}/blind (key sealed: {manifest['key_sha256'][:16]}…)")
    except BaseException as e:
        incident(g2, "prepare", e)
        raise


def freeze(g2_dir: str, scores: str) -> None:
    g2 = Path(g2_dir)
    man = json.loads((g2 / "MANIFEST.json").read_text())
    if man.get("frozen_scores_sha256"):
        sys.exit("refusing: already frozen")
    rows = list(csv.DictReader(Path(scores).open()))
    ids = sorted(man["composite_sha256"])
    problems = []
    if [r["id"] for r in sorted(rows, key=lambda r: r["id"])] != ids:
        problems.append("ids do not match the prepared items exactly once each")
    for r in rows:
        for k, allowed in VOCAB.items():
            if r.get(k) not in allowed:
                problems.append(f"{r.get('id')}: {k}={r.get(k)!r}")
        fam = (r.get("quality_family") or "").strip()
        if r.get("quality") in ("MINOR", "MAJOR") and not (fam in FAMILIES or fam.startswith("other:")):
            problems.append(f"{r['id']}: quality_family={fam!r}")
    if problems:
        sys.exit("invalid score sheet:\n  " + "\n  ".join(problems))
    dst = g2 / "SCORES-FROZEN.csv"
    shutil.copyfile(scores, dst)
    readonly(dst)
    man["frozen_scores_sha256"] = sha256(dst)
    man["frozen_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    os.chmod(g2 / "MANIFEST.json", stat.S_IRUSR | stat.S_IWUSR)
    (g2 / "MANIFEST.json").write_text(json.dumps(man, indent=1))
    readonly(g2 / "MANIFEST.json")
    print(f"frozen: {man['frozen_scores_sha256']}")


def unblind(g2_dir: str) -> None:
    g2 = Path(g2_dir)
    man = json.loads((g2 / "MANIFEST.json").read_text())
    kp = g2 / "key" / "KEY-DO-NOT-OPEN-BEFORE-FREEZE.json"
    if not man.get("frozen_scores_sha256") or sha256(g2 / "SCORES-FROZEN.csv") != man["frozen_scores_sha256"]:
        sys.exit("refusing: scores are not frozen or no longer match their recorded hash")
    if sha256(kp) != man["key_sha256"]:
        sys.exit("refusing: key does not match its recorded hash")
    key = json.loads(kp.read_text())
    out = g2 / "key-unblinded.json"
    out.write_text(json.dumps(key, indent=1))
    print(json.dumps(key, indent=1))


if __name__ == "__main__":
    cmd, *args = sys.argv[1:]
    {"prepare": prepare, "freeze": freeze, "unblind": unblind}[cmd](*args)
