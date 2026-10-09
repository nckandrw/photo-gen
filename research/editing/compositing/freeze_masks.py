"""Phase 9 CMPF: freeze the annotator's masks (PROTOCOL.md §3) before any composite exists. Validates the draft (every
case present; polygons of >= 3 points in [0, 1]), copies it to masks/masks-frozen.json (read-only), rasterises each
mask at the D0 and source canvases (masks/<case>-{d0,src}.png, gitignored), and writes MASK-MANIFEST.json with the
polygon, raster, source and view hashes, the descriptive mask geometry, and text-box intersections (a mask property).

Run: mflux/.venv/bin/python3.12 research/editing/compositing/freeze_masks.py <audit.json>"""
import hashlib
import json
import math
import os
import shutil
import stat
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
from cmp_run import feather_width, rasterise  # noqa: E402


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main(audit_json: str) -> None:
    ann = HERE / "annotation"
    draft = ann / "masks-draft.json"
    cfg = json.loads((HERE / "config.json").read_text())["cases"]
    masks = json.loads(draft.read_text())
    probs = []
    for c in cfg:
        if c not in masks or not masks[c].get("polygons"):
            probs.append(f"{c}: no polygons")
            continue
        for i, poly in enumerate(masks[c]["polygons"]):
            if len(poly) < 3 or not all(len(p) == 2 and 0 <= p[0] <= 1 and 0 <= p[1] <= 1 for p in poly):
                probs.append(f"{c}: polygon {i} invalid")
        if masks[c].get("difficulty") not in ("STRAIGHTFORWARD", "AMBIGUOUS"):
            probs.append(f"{c}: difficulty missing")
    if probs:
        sys.exit("invalid draft:\n  " + "\n  ".join(probs))
    out = HERE / "masks"
    out.mkdir(exist_ok=False)
    frozen = out / "masks-frozen.json"
    shutil.copyfile(draft, frozen)
    os.chmod(frozen, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    boxes = json.loads((ROOT / "research/qwen/qv/text-boxes.json").read_text())
    man = {"tool": "research/editing/compositing/freeze_masks.py", "frozen_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
           "draft_sha256": sha(draft), "frozen_json_sha256": sha(frozen),
           "annotator_audit": json.loads(Path(audit_json).read_text()) if Path(audit_json).exists() else None,
           "views_sha256_file": sha(ann / "views.sha256"), "cases": {}}
    for c, v in cfg.items():
        polys = masks[c]["polygons"]
        w, h = v["size"]
        with Image.open(v["staged"]) as im:
            ws, hs = im.size
        r = {"polygons": len(polys), "points": sum(len(p) for p in polys),
             "polygons_sha256": hashlib.sha256(json.dumps(polys, sort_keys=True).encode()).hexdigest(),
             "components": masks[c].get("components"), "difficulty": masks[c].get("difficulty"),
             "rationale": masks[c].get("rationale"), "staged_pixel_sha256": v["staged_pixel_sha256"],
             "counted": c in json.loads((HERE / "config.json").read_text())["primary_cases"]}
        for name, (cw, ch) in (("d0", (w, h)), ("src", (ws, hs))):
            m = rasterise(polys, cw, ch)
            p = out / f"{c}-{name}.png"
            Image.fromarray((m * 255).astype(np.uint8)).save(p)
            r[f"raster_{name}"] = {"size": [cw, ch], "file_sha256": sha(p),
                                   "pixel_sha256": hashlib.sha256(np.ascontiguousarray(m).tobytes()).hexdigest(),
                                   "area_fraction": round(float(m.mean()), 5), "feather_px": feather_width(max(cw, ch))}
            if name == "d0":
                r["text_boxes_intersecting_mask"] = {
                    el: bool(m[int(y0 * ch):max(int(y0 * ch) + 1, math.ceil(y1 * ch)),
                               int(x0 * cw):max(int(x0 * cw) + 1, math.ceil(x1 * cw))].any())
                    for el, (x0, y0, x1, y1) in boxes.get(c, {}).items()}
        man["cases"][c] = r
    (HERE / "MASK-MANIFEST.json").write_text(json.dumps(man, indent=1) + "\n")
    print(json.dumps({c: {"polygons": r["polygons"], "area_d0": r["raster_d0"]["area_fraction"], "difficulty": r["difficulty"],
                          "text_hit": r.get("text_boxes_intersecting_mask")} for c, r in man["cases"].items()}, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:])
