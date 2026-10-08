"""Phase 9 CMPF compositing (PROTOCOL.md §4–§6, §10). Deterministic, CPU-only (NumPy + PIL), no model.

For one case: rasterise the frozen polygons at the D0 canvas and at the source canvas; build
  C1 = hard composite on D0;  C2 = inner-feathered composite on D0 (primary);  C3 = inner-feathered composite on the
  staged source, with the G2 output resized to the source size (LANCZOS; the exact inverse of D0's full-frame resize);
verify the identity gates (staged source and G2 output pixel sha256 vs the sidecar, before and after) and the
construction invariants; run the integer-shift alignment check outside the dilated mask; write descriptive metrics.

Run: mflux/.venv/bin/python3.12 research/editing/compositing/cmp_run.py <case> <out_dir>"""
import ctypes
import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT / "research/editing"))
from edit_metrics import _gray, ssim_map  # noqa: E402
from photogen.imaging import inspect_image  # noqa: E402

F_REF, L_REF = 16, 1184
SHIFT = 4


def peak_footprint_gb():
    try:
        libproc = ctypes.CDLL("/usr/lib/libproc.dylib")

        class R(ctypes.Structure):
            _fields_ = [("u", ctypes.c_uint8 * 16)] + [(f"f{i}", ctypes.c_uint64) for i in range(40)]
        r = R()
        return round(r.f28 / 1e9, 3) if libproc.proc_pid_rusage(os.getpid(), 4, ctypes.byref(r)) == 0 else None
    except OSError:
        return None


def feather_width(long_side: int) -> int:
    return max(1, round(F_REF * long_side / L_REF))


def rasterise(polys, w: int, h: int) -> np.ndarray:
    im = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(im)
    for poly in polys:
        d.polygon([(x * w, y * h) for x, y in poly], fill=255)
    return np.asarray(im) > 0


def _morph(m: np.ndarray, flt) -> np.ndarray:
    """One 3x3 min/max filter step with edge-replicated borders (mask edges on the frame are not eroded)."""
    p = np.pad(m.astype(np.uint8) * 255, 1, mode="edge")
    return np.asarray(Image.fromarray(p).filter(flt))[1:-1, 1:-1] > 0


def feather_alpha(m: np.ndarray, f: int) -> np.ndarray:
    """alpha = sum_{k=0}^{f-1} erode^k(m) / f: a linear inner ramp in chessboard distance, 0 outside the mask."""
    acc = np.zeros(m.shape, np.float32)
    cur = m.copy()
    for _ in range(f):
        acc += cur
        if not cur.any():
            break
        cur = _morph(cur, ImageFilter.MinFilter(3))
    return acc / np.float32(f)


def dilate(m: np.ndarray, f: int) -> np.ndarray:
    cur = m.copy()
    for _ in range(f):
        cur = _morph(cur, ImageFilter.MaxFilter(3))
    return cur


def blend(canvas: np.ndarray, edit: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    a = alpha[..., None]
    out = (1.0 - a) * canvas.astype(np.float32) + a * edit.astype(np.float32)
    return np.clip(np.rint(out), 0, 255).astype(np.uint8)


def psnr(a, b):
    mse = float(((a.astype(np.float64) - b.astype(np.float64)) ** 2).mean()) if a.size else 0.0
    return round(10 * math.log10(255 ** 2 / mse), 3) if mse > 0 else None


def sha_px(a: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def alignment(c0: np.ndarray, d0: np.ndarray, outside: np.ndarray) -> dict:
    g0, gd = _gray(c0.astype(np.float64)), _gray(d0.astype(np.float64))
    h, w = gd.shape
    res = {}
    for dy in range(-SHIFT, SHIFT + 1):
        for dx in range(-SHIFT, SHIFT + 1):
            ys, xs = slice(SHIFT, h - SHIFT), slice(SHIFT, w - SHIFT)
            a = g0[SHIFT + dy:h - SHIFT + dy, SHIFT + dx:w - SHIFT + dx]
            sel = outside[ys, xs]
            res[(dy, dx)] = float(np.abs(a - gd[ys, xs])[sel].mean())
    best = min(res, key=res.get)
    return {"best_shift_dy_dx": list(best), "mae_at_best": round(res[best], 4), "mae_at_zero": round(res[(0, 0)], 4),
            "aligned": best == (0, 0), "region": f"outside the mask dilated by F; shifts in [-{SHIFT},{SHIFT}]^2"}


def main(case: str, out_dir: str) -> None:
    t0 = time.perf_counter()
    out = Path(out_dir).resolve()
    out.mkdir(parents=True, exist_ok=False)
    cfg = json.loads((HERE / "config.json").read_text())["cases"][case]
    polys = json.loads((HERE / "masks" / "masks-frozen.json").read_text())[case]["polygons"]
    side = json.loads((ROOT / cfg["g2_sidecar"]).read_text())
    gates = {"source_before": inspect_image(Path(cfg["staged"])).pixel_sha256 == cfg["staged_pixel_sha256"],
             "edit_before": inspect_image(Path(side["output_path"])).pixel_sha256 == cfg["g2_output_pixel_sha256"]}
    with Image.open(cfg["staged"]) as im:
        src = np.asarray(im.convert("RGB"))
    with Image.open(side["output_path"]) as im:
        c0_img = im.convert("RGB")
    c0 = np.asarray(c0_img)
    d0 = np.asarray(Image.open(ROOT / cfg["d0"]).convert("RGB"))
    h, w = d0.shape[:2]
    hs, ws = src.shape[:2]
    assert c0.shape == d0.shape, (c0.shape, d0.shape)
    t_load = time.perf_counter() - t0

    t = time.perf_counter()
    f_d0, f_src = feather_width(max(w, h)), feather_width(max(ws, hs))
    m = rasterise(polys, w, h)
    ms = rasterise(polys, ws, hs)
    a2 = feather_alpha(m, f_d0)
    a3 = feather_alpha(ms, f_src)
    c1 = np.where(m[..., None], c0, d0)
    c2 = blend(d0, c0, a2)
    edit_up = np.asarray(c0_img.resize((ws, hs), Image.Resampling.LANCZOS))
    c3 = blend(src, edit_up, a3)
    t_comp = time.perf_counter() - t

    for name, arr in (("C1", c1), ("C2", c2), ("C3", c3)):
        Image.fromarray(arr, "RGB").save(out / f"{name}.png")
    Image.fromarray((m * 255).astype(np.uint8)).save(out / "mask-d0.png")
    Image.fromarray((ms * 255).astype(np.uint8)).save(out / "mask-src.png")

    inv = {"C1_equals_D0_outside": bool(np.array_equal(c1[~m], d0[~m])),
           "C1_equals_C0_inside": bool(np.array_equal(c1[m], c0[m])),
           "C2_equals_D0_outside": bool(np.array_equal(c2[~m], d0[~m])),
           "C3_equals_source_outside": bool(np.array_equal(c3[~ms], src[~ms])),
           "C2_equals_C0_where_alpha_1": bool(np.array_equal(c2[a2 >= 1.0], c0[a2 >= 1.0]))}
    outside = ~dilate(m, f_d0)
    ring = dilate(m, f_d0) & ~m
    g0, gd = _gray(c0.astype(np.float64)), _gray(d0.astype(np.float64))
    diff = np.abs(c0.astype(np.int16) - d0.astype(np.int16)).max(-1)
    boxes = json.loads((ROOT / "research/qwen/qv/text-boxes.json").read_text()).get(case, {})
    text = {}
    for el, (x0, y0, x1, y1) in boxes.items():
        ys, xs = slice(int(y0 * h), max(int(y0 * h) + 1, math.ceil(y1 * h))), slice(int(x0 * w), max(int(x0 * w) + 1, math.ceil(x1 * w)))
        yss, xss = slice(int(y0 * hs), max(int(y0 * hs) + 1, math.ceil(y1 * hs))), slice(int(x0 * ws), max(int(x0 * ws) + 1, math.ceil(x1 * ws)))
        text[el] = {"intersects_mask_d0": bool(m[ys, xs].any()), "mask_fraction_d0": round(float(m[ys, xs].mean()), 4),
                    "intersects_mask_src": bool(ms[yss, xss].any()),
                    "psnr_vs_canvas": {"C0": psnr(c0[ys, xs], d0[ys, xs]), "C1": psnr(c1[ys, xs], d0[ys, xs]),
                                       "C2": psnr(c2[ys, xs], d0[ys, xs]), "C3": psnr(c3[yss, xss], src[yss, xss])}}
    sm0 = ssim_map(g0, gd)
    perim = int((m & ~_morph(m, ImageFilter.MinFilter(3))).sum())
    rec = {"tool": "research/editing/compositing/cmp_run.py", "case": case, "sizes": {"d0": [w, h], "source": [ws, hs]},
           "feather_px": {"d0": f_d0, "source": f_src},
           "mask": {"area_fraction_d0": round(float(m.mean()), 5), "area_fraction_src": round(float(ms.mean()), 5),
                    "perimeter_px_d0": perim, "feather_band_fraction_d0": round(float(((a2 > 0) & (a2 < 1)).mean()), 5),
                    "mask_d0_sha256": sha_px(m), "mask_src_sha256": sha_px(ms)},
           "invariants": inv, "alignment": alignment(c0, d0, outside),
           "c0_vs_d0": {"outside_mae": round(float(np.abs(g0 - gd)[outside].mean()), 4),
                        "outside_changed_gt8": round(float((diff > 8)[outside].mean()), 4),
                        "ring_mae": round(float(np.abs(g0 - gd)[ring].mean()), 4) if ring.any() else None,
                        "inside_mae": round(float(np.abs(g0 - gd)[m].mean()), 4) if m.any() else None,
                        "ssim_outside": round(float(sm0[outside].mean()), 4)},
           "inside_mask_psnr_vs_canvas": {"C0": psnr(c0[m], d0[m]), "C2": psnr(c2[m], d0[m]), "C3": psnr(c3[ms], src[ms])},
           "text_boxes": text,
           "outputs": {n: inspect_image(out / f"{n}.png").pixel_sha256 for n in ("C1", "C2", "C3")},
           "inputs": {"staged_pixel_sha256": cfg["staged_pixel_sha256"], "g2_output_pixel_sha256": cfg["g2_output_pixel_sha256"],
                      "d0_pixel_sha256": inspect_image(ROOT / cfg["d0"]).pixel_sha256,
                      "polygons_sha256": hashlib.sha256(json.dumps(polys, sort_keys=True).encode()).hexdigest()},
           "seconds": {"load": round(t_load, 3), "composite": round(t_comp, 3)}}
    gates["source_after"] = inspect_image(Path(cfg["staged"])).pixel_sha256 == cfg["staged_pixel_sha256"]
    gates["edit_after"] = inspect_image(Path(side["output_path"])).pixel_sha256 == cfg["g2_output_pixel_sha256"]
    gates["d0_matches_config"] = rec["inputs"]["d0_pixel_sha256"] == cfg["d0_pixel_sha256"]
    rec["gates"] = gates
    rec["seconds"]["total"] = round(time.perf_counter() - t0, 3)
    rec["peak_footprint_gb"] = peak_footprint_gb()
    import importlib.metadata as md
    rec["versions"] = {p: md.version(p) for p in ("numpy", "pillow")}
    (out / "record.json").write_text(json.dumps(rec, indent=1) + "\n")
    ok = all(gates.values()) and all(inv.values())
    print(json.dumps({"case": case, "gates_ok": all(gates.values()), "invariants_ok": all(inv.values()),
                      "aligned": rec["alignment"]["aligned"], "seconds": rec["seconds"], "peak_gb": rec["peak_footprint_gb"]}))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main(*sys.argv[1:])
