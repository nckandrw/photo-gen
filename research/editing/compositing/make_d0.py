"""Phase 9 CMPF: recompute D0 (the scaled conditioning input of each G2-1024 edit) with Phase 7's own preprocessing
function (research/qwen/qv/qv_roundtrip.py preprocess: EXIF-oriented, RGBA, LANCZOS to dimensions(1024, w/h)), saved
as RGB. Gates (PROTOCOL.md §5): staged source pixel sha256 = G2 sidecar; D0 size = G2 output size; D0 bit-identical
to Phase 7's input.png for R02, R12 and R15. No model is loaded. Runs in the edit venv (mflux 0.21.0's helpers).

Run: mflux-qwen/.venv/bin/python3.12 research/editing/compositing/make_d0.py <out_dir> <case> [<case> ...]"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "research/qwen/qv"))
sys.path.insert(0, str(ROOT / "app"))
import qv_roundtrip as QV  # noqa: E402  (Phase 7 harness, unchanged)
from photogen.imaging import inspect_image  # noqa: E402


def main(out_dir: str, *cases: str) -> None:
    out = Path(out_dir).resolve()
    out.mkdir(parents=True, exist_ok=False)
    rec = {"tool": "research/editing/compositing/make_d0.py", "budget": 1024, "cases": {}}
    for c in cases:
        side = json.loads((ROOT / f"research/qwen/runs/G2-1024-{c}/sidecar.json").read_text())
        staged = side["input_image"]["staged_path"]
        src_px = inspect_image(Path(staged)).pixel_sha256
        image, _, w, h = QV.preprocess(staged, 1024)
        p = out / f"{c}.png"
        image.convert("RGB").save(p)
        d0 = inspect_image(p)
        r = {"staged": staged, "staged_pixel_sha256": src_px,
             "gate_source_equals_sidecar": src_px == side["input_image"]["pixel_sha256"],
             "d0_size": [w, h], "gate_size_equals_g2_output": [w, h] == [side["width"], side["height"]],
             "d0_pixel_sha256": d0.pixel_sha256, "d0_file_sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
        p7 = ROOT / f"research/qwen/runs/QV-1024-{c}-a/worker/input.png"
        if p7.exists():
            a = np.asarray(Image.open(p).convert("RGB"))
            b = np.asarray(Image.open(p7).convert("RGB"))
            r["gate_equals_phase7_input"] = bool(a.shape == b.shape and np.array_equal(a, b))
        rec["cases"][c] = r
    rec["all_gates_pass"] = all(v["gate_source_equals_sidecar"] and v["gate_size_equals_g2_output"]
                                and v.get("gate_equals_phase7_input", True) for v in rec["cases"].values())
    (out / "record.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({c: {k: v[k] for k in v if k.startswith("gate")} for c, v in rec["cases"].items()}, indent=1))
    print("all_gates_pass", rec["all_gates_pass"])
    sys.exit(0 if rec["all_gates_pass"] else 1)


if __name__ == "__main__":
    main(*sys.argv[1:])
