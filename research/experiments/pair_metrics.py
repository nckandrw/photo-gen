"""PSNR + SSIM (luminance, 11x11 Gaussian sigma=1.5, K1=.01 K2=.03 — Wang et al. 2004 constants) between image pairs,
and blinded side-by-side composites. numpy + Pillow only (both already in the validated venv).
Usage:
  pair_metrics.py metrics <dir> <pairs.json> <out.json>     pairs: [[name, pathA, pathB], ...]
  pair_metrics.py blind   <dir> <pairs.json> <outdir> <keyfile> [seed]
"""
import json, random, sys
import numpy as np
from PIL import Image, ImageDraw

def lum(p):
    return np.asarray(Image.open(p).convert("RGB")).astype(np.float64) @ np.array([0.299, 0.587, 0.114])

def gauss(n=11, s=1.5):
    x = np.arange(n) - n // 2; g = np.exp(-(x ** 2) / (2 * s * s)); return g / g.sum()

def filt(img, g):  # separable 'valid' convolution
    k = len(g)
    a = np.stack([img[:, i:i + img.shape[1] - k + 1] for i in range(k)], 0)
    a = np.tensordot(g, a, axes=(0, 0))
    b = np.stack([a[i:i + a.shape[0] - k + 1, :] for i in range(k)], 0)
    return np.tensordot(g, b, axes=(0, 0))

def ssim(x, y):
    g = gauss(); C1, C2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    mx, my = filt(x, g), filt(y, g)
    sxx, syy, sxy = filt(x * x, g) - mx * mx, filt(y * y, g) - my * my, filt(x * y, g) - mx * my
    m = ((2 * mx * my + C1) * (2 * sxy + C2)) / ((mx * mx + my * my + C1) * (sxx + syy + C2))
    return float(m.mean())

def psnr(a, b):
    a = np.asarray(Image.open(a).convert("RGB")).astype(np.float64); b = np.asarray(Image.open(b).convert("RGB")).astype(np.float64)
    mse = ((a - b) ** 2).mean(); return float("inf") if mse == 0 else float(10 * np.log10(255 ** 2 / mse)), float(np.abs(a - b).mean())

if __name__ == "__main__":
    mode, d = sys.argv[1], sys.argv[2]
    pairs = json.load(open(sys.argv[3]))
    if mode == "metrics":
        out = []
        for name, a, b in pairs:
            p, mad = psnr(f"{d}/{a}", f"{d}/{b}")
            out.append({"pair": name, "psnr_db": round(p, 2), "mean_abs": round(mad, 2), "ssim": round(ssim(lum(f"{d}/{a}"), lum(f"{d}/{b}")), 4)})
            print(out[-1], flush=True)
        json.dump(out, open(sys.argv[4], "w"), indent=1)
    elif mode == "blind":
        outdir, keyfile = sys.argv[4], sys.argv[5]
        rng = random.Random(int(sys.argv[6]) if len(sys.argv) > 6 else 1234)
        key = {}
        for i, (name, a, b) in enumerate(pairs):
            L, R = (a, b) if rng.random() < 0.5 else (b, a)
            key[f"C{i + 1:02d}"] = {"pair": name, "left": L, "right": R}
            im = [Image.open(f"{d}/{x}").convert("RGB") for x in (L, R)]
            w, h = im[0].size
            c = Image.new("RGB", (2 * w + 16, h + 40), (255, 255, 255)); c.paste(im[0], (0, 40)); c.paste(im[1], (w + 16, 40))
            ImageDraw.Draw(c).text((10, 10), f"C{i + 1:02d}   LEFT", fill=(0, 0, 0)); ImageDraw.Draw(c).text((w + 26, 10), "RIGHT", fill=(0, 0, 0))
            c.save(f"{outdir}/C{i + 1:02d}.png")
        json.dump(key, open(keyfile, "w"), indent=1)
        print(f"{len(pairs)} blinded composites written; key in {keyfile} (do not open before scoring)")
