"""Mask-annotation helper (source-only). Draws the polygons of one case from a masks JSON onto that case's source view
and writes a PNG, so the annotator can check coverage. It reads only files in this annotation directory and writes
only to the output path given.

Run: /Users/nckandrw/Dev/photo-gen/mflux/.venv/bin/python3.12 overlay.py <masks.json> <case> <out.png>"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent


def main(masks_path: str, case: str, out: str) -> None:
    meta = json.loads((HERE / "cases.json").read_text())[case]
    im = Image.open(HERE / meta["view"]["file"]).convert("RGB")
    w, h = im.size
    polys = json.loads(Path(masks_path).read_text())[case]["polygons"]
    shade = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(shade)
    for poly in polys:
        d.polygon([(x * w, y * h) for x, y in poly], fill=255)
    red = Image.new("RGB", (w, h), (255, 0, 0))
    over = Image.composite(Image.blend(im, red, 0.45), im, shade)
    d2 = ImageDraw.Draw(over)
    for poly in polys:
        d2.line([(x * w, y * h) for x, y in poly + poly[:1]], fill=(255, 255, 0), width=2)
    over.save(out)
    print(f"{case}: {len(polys)} polygon(s), mask covers {sum(shade.point(lambda v: v > 0 and 255).histogram()[255:]) / (w * h):.3%} of the view")


if __name__ == "__main__":
    main(*sys.argv[1:])
