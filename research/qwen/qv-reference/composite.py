"""Phase 8 Q-VR conditional arm CMP (PROTOCOL.md section 8.3): the simplest hard-preservation baseline on an EXISTING
G2 edit (no new edit). Canvas = D0 (the scaled conditioning input the edit saw); mask = G2's own regions.change box from
the task manifest (written before any G2 output existed). Alignment is checked first; if the integer phase-correlation
shift between the edit and D0 above the box is not (0, 0), no composite is made.

  output = (1 - M) * D0 + M * edit      hard: M = 1 inside the box; feathered: 16-px linear ramp on box edges that are
                                        not on the image border

Run: mflux/.venv/bin/python3.12 research/qwen/qv-reference/composite.py <out_dir> [task=R02] [budget=1024] [x0,y0,x1,y1]"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "app"))
FEATHER = 16


def gray(a: np.ndarray) -> np.ndarray:
    return a.astype(np.float64) @ np.array([0.299, 0.587, 0.114])


def phase_shift(a: np.ndarray, b: np.ndarray) -> tuple[int, int, float]:
    """Integer (dy, dx) that best aligns b to a, by phase correlation; also the peak height (1.0 = identical)."""
    fa, fb = np.fft.fft2(a - a.mean()), np.fft.fft2(b - b.mean())
    r = fa * np.conj(fb)
    r /= np.maximum(np.abs(r), 1e-12)
    c = np.real(np.fft.ifft2(r))
    dy, dx = np.unravel_index(np.argmax(c), c.shape)
    dy = dy - a.shape[0] if dy > a.shape[0] // 2 else dy
    dx = dx - a.shape[1] if dx > a.shape[1] // 2 else dx
    return int(dy), int(dx), float(c.max())


def main(out_dir: str, task: str = "R02", budget: str = "1024", box_px: str | None = None) -> None:
    from photogen.imaging import inspect_image
    budget = int(budget)
    out = Path(out_dir).resolve()
    out.mkdir(parents=True, exist_ok=False)
    d0_path = ROOT / f"research/qwen/runs/QV-{budget}-{task}-a/worker/input.png"
    side = json.loads((ROOT / f"research/qwen/runs/G2-{budget}-{task}/sidecar.json").read_text())
    edit_path = Path(side["output_path"])
    ident = inspect_image(edit_path)
    assert ident.pixel_sha256 == side["pixel_sha256"], "G2 output does not match its sidecar"
    tasks = {t["id"]: t for t in json.loads((ROOT / "research/editing/real-world/task-manifest.json").read_text())["tasks"]}
    (fx0, fy0, fx1, fy1), = tasks[task]["regions"]["change"]
    d0 = np.asarray(Image.open(d0_path).convert("RGB"))
    if box_px:  # PROTOCOL.md amendment 2: an explicit pixel box (drawn on D0 only) instead of G2's regions.change
        bx = [int(v) for v in box_px.split(",")]
        fx0, fy0, fx1, fy1 = bx[0] / d0.shape[1], bx[1] / d0.shape[0], bx[2] / d0.shape[1], bx[3] / d0.shape[0]
    ed = np.asarray(Image.open(edit_path).convert("RGB"))
    assert d0.shape == ed.shape, (d0.shape, ed.shape)
    h, w = d0.shape[:2]
    x0, y0, x1, y1 = round(fx0 * w), round(fy0 * h), round(fx1 * w), round(fy1 * h)
    dy, dx, peak = phase_shift(gray(d0[:y0]), gray(ed[:y0]))
    outside = np.ones((h, w), bool)
    outside[y0:y1, x0:x1] = False
    diff = np.abs(d0.astype(np.int16) - ed.astype(np.int16))
    rec = {"tool": "research/qwen/qv-reference/composite.py", "task": task, "budget": budget,
           "mask_source": "explicit pixel box (amendment 2)" if box_px else "G2 task-manifest regions.change",
           "instruction": tasks[task]["instruction"], "d0": str(d0_path.relative_to(ROOT)),
           "d0_sha256": hashlib.sha256(d0_path.read_bytes()).hexdigest(), "edit": str(edit_path),
           "edit_pixel_sha256": ident.pixel_sha256, "size": [w, h], "mask_fraction_box": [fx0, fy0, fx1, fy1],
           "mask_px_box": [x0, y0, x1, y1], "mask_area_fraction": round((x1 - x0) * (y1 - y0) / (w * h), 4),
           "alignment": {"region": f"rows 0..{y0} (above the box), full width", "shift_dy_dx": [dy, dx],
                         "phase_corr_peak": round(peak, 4), "aligned": dy == 0 and dx == 0},
           "edit_vs_d0_outside_mask": {"mae": round(float(diff[outside].mean()), 4),
                                       "pixels_changed_gt8": round(float((diff.max(-1) > 8)[outside].mean()), 4)},
           "edit_vs_d0_inside_mask_mae": round(float(diff[~outside].mean()), 4)}
    if rec["alignment"]["aligned"]:
        m_hard = np.zeros((h, w), np.float64)
        m_hard[y0:y1, x0:x1] = 1.0
        yy, xx = np.mgrid[0:h, 0:w]
        dist = np.full((h, w), np.inf)
        for edge, on_border, dd in ((y0, y0 == 0, yy - y0), (x0, x0 == 0, xx - x0), (x1, x1 == w, (x1 - 1) - xx),
                                    (y1, y1 == h, (y1 - 1) - yy)):
            if not on_border:
                dist = np.minimum(dist, dd.astype(np.float64))
        m_feather = np.where(m_hard > 0, np.clip((dist + 0.5) / FEATHER, 0, 1), 0.0)
        for name, m in (("hard", m_hard), ("feather", m_feather)):
            c = np.round((1 - m[..., None]) * d0 + m[..., None] * ed).astype(np.uint8)
            p = out / f"composite-{name}.png"
            Image.fromarray(c, "RGB").save(p)
            rec[f"composite_{name}"] = {"path": str(p.relative_to(ROOT)), "pixel_sha256": inspect_image(p).pixel_sha256,
                                        "identical_to_d0_outside_mask": bool(np.array_equal(c[outside], d0[outside]))}
    (out / "record.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: rec[k] for k in ("alignment", "edit_vs_d0_outside_mask", "mask_px_box")}, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:])
