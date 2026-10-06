"""Model-independent edit metrics (research/editing/README.md §3). Descriptive aids only: a visual verdict always wins.

Usage: python edit_metrics.py <source.png> <output.png> [regions_json_entry]
       python edit_metrics.py --batch <jobs.json>   (list of {"id", "source", "output", "regions"}) -> JSON to stdout

- The source is Lanczos-resized to the output size. That is what the edit model is conditioned on: mflux and
  Diffusers resize the reference to the output-resolution budget.
- Local edits: preservation outside the change region(s) dilated by 3% of the image side (MAE, PSNR, SSIM), plus
  the change magnitude inside the region (MAE).
- All edits: structure = Pearson correlation of Sobel gradient magnitudes (layout/composition proxy).
Only numpy + PIL are needed (no scipy)."""
import json
import math
import sys

import numpy as np
from PIL import Image


def _load(path, size=None):
    im = Image.open(path).convert("RGB")
    if size is not None and im.size != size:
        im = im.resize(size, Image.Resampling.LANCZOS)
    return np.asarray(im, dtype=np.float64)


def _gray(a):
    return a @ np.array([0.299, 0.587, 0.114])


def _box(x, r):
    """Mean filter with a (2r+1)^2 window via integral images (edge-replicated)."""
    p = np.pad(x, r + 1, mode="edge")
    c = p.cumsum(0).cumsum(1)
    k = 2 * r + 1
    s = c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]
    return s[: x.shape[0], : x.shape[1]] / (k * k)


def ssim_map(a, b, r=3):
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    mu_a, mu_b = _box(a, r), _box(b, r)
    va = _box(a * a, r) - mu_a ** 2
    vb = _box(b * b, r) - mu_b ** 2
    cov = _box(a * b, r) - mu_a * mu_b
    return ((2 * mu_a * mu_b + c1) * (2 * cov + c2)) / ((mu_a ** 2 + mu_b ** 2 + c1) * (va + vb + c2))


def sobel_mag(g):
    p = np.pad(g, 1, mode="edge")
    gx = (p[:-2, 2:] + 2 * p[1:-1, 2:] + p[2:, 2:]) - (p[:-2, :-2] + 2 * p[1:-1, :-2] + p[2:, :-2])
    gy = (p[2:, :-2] + 2 * p[2:, 1:-1] + p[2:, 2:]) - (p[:-2, :-2] + 2 * p[:-2, 1:-1] + p[:-2, 2:])
    return np.hypot(gx, gy)


def region_mask(shape, regions, dilate=0.0):
    h, w = shape
    m = np.zeros((h, w), dtype=bool)
    d = dilate * max(h, w)
    for x0, y0, x1, y1 in regions or []:
        m[max(0, int(y0 * h - d)):min(h, int(math.ceil(y1 * h + d))),
          max(0, int(x0 * w - d)):min(w, int(math.ceil(x1 * w + d)))] = True
    return m


def metrics(source, output, regions=None):
    out = _load(output)
    src = _load(source, size=(out.shape[1], out.shape[0]))
    gs, go = _gray(src), _gray(out)
    sm, om = sobel_mag(gs), sobel_mag(go)
    res = {"size": [out.shape[1], out.shape[0]],
           "global_mae": round(float(np.abs(src - out).mean()), 3),
           "structure_corr": round(float(np.corrcoef(sm.ravel(), om.ravel())[0, 1]), 4)}
    if regions:
        inside = region_mask(gs.shape, regions)
        outside = ~region_mask(gs.shape, regions, dilate=0.03)
        diff = np.abs(src - out).mean(axis=2)
        mse = float(((src - out) ** 2).mean(axis=2)[outside].mean())
        res.update({
            "outside_fraction": round(float(outside.mean()), 3),
            "outside_mae": round(float(diff[outside].mean()), 3),
            "outside_psnr": round(10 * math.log10(255 ** 2 / mse), 2) if mse > 0 else float("inf"),
            "outside_ssim": round(float(ssim_map(gs, go)[outside].mean()), 4),
            "inside_mae": round(float(diff[inside].mean()), 3),
        })
    return res


if __name__ == "__main__":
    if sys.argv[1] == "--batch":
        jobs = json.load(open(sys.argv[2]))
        print(json.dumps({j["id"]: metrics(j["source"], j["output"], j.get("regions")) for j in jobs}, indent=1))
    else:
        regs = json.loads(sys.argv[3]) if len(sys.argv) > 3 else None
        print(json.dumps(metrics(sys.argv[1], sys.argv[2], regs), indent=1))
