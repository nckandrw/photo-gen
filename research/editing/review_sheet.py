"""Render G0 review sheets: for each test, the source (Lanczos-resized to the output size) | the edit output, with the
test's instruction, expected change and expected preserved elements printed above. Model-independent.

Usage: python research/editing/review_sheet.py <runs_prefix e.g. research/qwen/runs/G0-512-> <out_dir>
Reads research/editing/{suite-v1,sources}.json; the output path of each run comes from its result.json (app mode)."""
import json
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
prefix, out_dir = sys.argv[1], Path(sys.argv[2])
out_dir.mkdir(parents=True, exist_ok=True)
suite = json.loads((ROOT / "research/editing/suite-v1.json").read_text())
sources = json.loads((ROOT / "research/editing/sources.json").read_text())["accepted"]
for t in suite["tests"]:
    run = Path(prefix + t["id"])
    res = json.loads((run / "result.json").read_text())
    out = Image.open(res["output_path"]).convert("RGB")
    src = Image.open(sources[t["id"]]["output_path"]).convert("RGB").resize(out.size, Image.Resampling.LANCZOS)
    w, h = out.size
    head = [f"{t['id']}  [{t['category']}]  {run.name}  {w}x{h}",
            *textwrap.wrap("INSTRUCTION: " + t["instruction"], 150),
            *textwrap.wrap("EXPECTED CHANGE: " + t["expected_change"], 150),
            *textwrap.wrap("PRESERVE: " + "; ".join(t["expected_preserved"]), 150),
            "LEFT = source (resized to output size)   RIGHT = edit output"]
    top = 16 * len(head) + 12
    sheet = Image.new("RGB", (2 * w + 16, h + top), "white")
    d = ImageDraw.Draw(sheet)
    for i, line in enumerate(head):
        d.text((8, 6 + 16 * i), line, fill="black")
    sheet.paste(src, (0, top))
    sheet.paste(out, (w + 16, top))
    sheet.save(out_dir / f"{t['id']}.png")
print(f"wrote {len(suite['tests'])} sheets to {out_dir}")
