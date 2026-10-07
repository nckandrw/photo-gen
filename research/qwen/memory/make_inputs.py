"""Inputs for the Phase 5 memory-lifetime A/B (deterministic; recorded in inputs.json).

- E05: the G0 benchmark source E05 (Z-Image REFERENCE 1024², seed 1505), already staged by the app.
- E08c: a 3:2 landscape crop of the G0 source E08 (rows 171..853 of the 1024² image, i.e. 1024x683, centred) so the
  A/B also covers a non-square input (non-square output size and VAE decode tiling). Staged through the production
  staging code (photogen.inputs.stage_input_image), exactly as the app would.
Neither is a G2 (real-photograph) source: no G2 source is edited before G2 is pre-registered.

Usage: mflux/.venv/bin/python3.12 research/qwen/memory/make_inputs.py"""
import hashlib
import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "app"))
from photogen.config import AppConfig  # noqa: E402
from photogen.inputs import stage_input_image  # noqa: E402

cfg = AppConfig.load()
src = json.loads((ROOT / "research/editing/sources.json").read_text())["accepted"]
out = {}
e05, _ = stage_input_image(src["E05"]["output_path"], cfg.inputs_dir)
out["E05"] = {"from": "research/editing/sources.json E05", "transform": None, **e05.to_dict()}

work = ROOT / "data" / "research-inputs"
work.mkdir(parents=True, exist_ok=True)
with Image.open(src["E08"]["output_path"]) as im:
    assert im.size == (1024, 1024), im.size
    top = (1024 - 683) // 2
    crop = im.convert("RGB").crop((0, top, 1024, top + 683))
crop_path = work / "memory-ab-E08-crop-3x2.png"
crop.save(crop_path)
e08c, _ = stage_input_image(str(crop_path), cfg.inputs_dir)
out["E08c"] = {"from": "research/editing/sources.json E08", "transform": f"crop box (0, {top}, 1024, {top + 683})",
               "source_pixel_sha256": src["E08"]["pixel_sha256"], **e08c.to_dict()}
(Path(__file__).parent / "inputs.json").write_text(json.dumps(out, indent=1))
for k, v in out.items():
    print(k, v["staged_path"], v["width"], v["height"], v["pixel_sha256"][:16])
