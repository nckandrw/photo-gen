"""Phase 8 Q-VR, MLX side (arms A1 / A1T and the MLX primitive probes; PROTOCOL.md sections 4.1, 5.1, 5.2). Runs ONLY
in the edit venv (mflux 0.21.0 / MLX 0.32.2), launched by mlx_run.py with the production worker's environment. It
imports Phase 7's research/qwen/qv/qv_roundtrip.py unchanged and calls the same functions in the same order; the only
additions are read-only captures of the intermediate tensors.

Modes:
  capture <staged.png|synthetic:WxH> <budget> <out_dir> [--tiler-gate] [--foreign <z_dec_in.npy>]
      -> out_dir/{x_in,moments,z_norm,z_dec_in,dec}.npy, input.png, roundtrip.png, record.json
         --tiler-gate: also decode with tiler_port + MLX per-tile decode and compare with VAETiler bit for bit
         --foreign: also decode a foreign decoder input (X21) -> dec_foreign.npy
  probe <out_dir>   hooks every mx.pad call during an encode and a tiled decode of synthetic images at the four G2
                    sizes, then replays each distinct call on the GPU (fp32, bf16) against np.pad, and the full
                    Qwen21AvgDown at each temporal call site against a NumPy transcription of Diffusers' AvgDown3D."""
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import mlx.core as mx
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "research/qwen/qv"))
sys.path.insert(0, str(HERE))
import qv_roundtrip as QV  # noqa: E402  (Phase 7 harness, unchanged)
import tiler_port  # noqa: E402

G2_SIZES = [(576, 448), (448, 576), (1184, 896), (896, 1184)]


def sha(a: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def save(out: Path, name: str, a: np.ndarray) -> dict:
    a = np.ascontiguousarray(a)
    np.save(out / f"{name}.npy", a)
    return {"shape": list(a.shape), "dtype": str(a.dtype), "sha256": sha(a)}


def synthetic(w: int, h: int) -> Path:
    """A deterministic synthetic RGB test card (no G2 content), for smoke tests and shape probes only."""
    p = Path(os.environ.get("TMPDIR", "/tmp")) / f"qvr-synthetic-{w}x{h}.png"
    if not p.exists():
        y, x = np.mgrid[0:h, 0:w]
        img = np.stack([(x * 255 // max(1, w - 1)), (y * 255 // max(1, h - 1)), ((x // 16 + y // 16) % 2) * 255], -1)
        Image.fromarray(img.astype(np.uint8), "RGB").save(p)
    return p


def staged_path(arg: str, budget: int) -> str:
    if arg.startswith("synthetic:"):
        w, h = (int(v) for v in arg.split(":", 1)[1].split("x"))
        return str(synthetic(w, h))
    return arg


def param_check(vae) -> dict:
    from mlx.utils import tree_flatten
    from safetensors.numpy import load_file
    p = dict(tree_flatten(vae.parameters()))
    f = load_file(str(QV.EXPORT / "vae" / "0.safetensors"))
    bad = [k for k in sorted(set(p) & set(f))
           if not (tuple(p[k].shape) == f[k].shape and np.array_equal(np.array(p[k]).view(np.uint8), f[k].view(np.uint8)))]
    return {"mlx_params": len(p), "file_tensors": len(f), "only_mlx": sorted(set(p) - set(f)),
            "only_file": sorted(set(f) - set(p)), "mismatched": bad,
            "pass": len(p) == len(f) == 238 and not bad and set(p) == set(f)}


def capture(staged_arg: str, budget: str, out_dir: str, *flags: str) -> dict:
    from mflux.models.common.vae.vae_tiler import VAETiler  # noqa: F401  (imported so the record names the source)
    budget = int(budget)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=False)
    staged = staged_path(staged_arg, budget)
    mx.set_cache_limit(1000 ** 3)  # as Phase 7 / --low-ram
    t0 = time.perf_counter()
    vae = QV.load_vae()
    rec: dict = {"tool": "research/qwen/qv-reference/mlx_side.py capture", "staged": staged, "budget": budget,
                 "MLX_ENABLE_TF32": os.environ.get("MLX_ENABLE_TF32"), "default_device": str(mx.default_device()),
                 "param_check": param_check(vae), "seconds": {"load": round(time.perf_counter() - t0, 3)}}
    image, pixels, w, h = QV.preprocess(staged, budget)
    image.convert("RGB").save(out / "input.png")
    arrays = {"x_in": save(out, "x_in", np.array(pixels))}
    t = time.perf_counter()
    moments = vae.quant_conv(vae.encoder(vae._to_nhwc(pixels)))  # read-only capture: what encode() takes the mean of
    mx.eval(moments)
    arrays["moments"] = save(out, "moments", np.array(moments).transpose(0, 3, 1, 2)[:, :, None])
    enc = vae.encode(pixels)  # the production call
    mx.eval(enc)
    rec["seconds"]["encode"] = round((time.perf_counter() - t) / 2, 3)  # two encoder passes above; per pass
    arrays["z_norm"] = save(out, "z_norm", np.array(enc))
    z_dec_in = QV.pack_unpack(enc, w, h, mx.bfloat16)
    mx.eval(z_dec_in)
    arrays["z_dec_in"] = save(out, "z_dec_in", np.array(z_dec_in))
    elementwise = enc.astype(mx.bfloat16).astype(mx.float32)
    rec["cast_commutes_with_pack"] = bool(np.array_equal(np.array(elementwise), np.array(z_dec_in)))
    tiling = QV.tiling_for(vae, True)
    t = time.perf_counter()
    dec = QV.decode(vae, z_dec_in, tiling)
    rec["seconds"]["decode_tiled"] = round(time.perf_counter() - t, 3)
    dec_np = np.array(dec)
    arrays["dec"] = save(out, "dec", dec_np)
    QV.to_pil(dec).save(out / "roundtrip.png")
    rec["tiling"] = repr(tiling)
    rec["identity"] = {"input": QV.identity(out / "input.png"), "roundtrip": QV.identity(out / "roundtrip.png")}
    rgba = np.asarray(Image.open(out / "roundtrip.png").convert("RGBA"))
    port_u8 = tiler_port.to_uint8(dec_np)
    rec["to_uint8_port_vs_to_pil"] = {"differing_values": int((port_u8 != rgba).sum()), "pass": bool(np.array_equal(port_u8, rgba))}
    rec["memory_after_primary"] = QV.footprint()
    if "--tiler-gate" in flags:
        def mlx_decode(tile):
            r = vae.decode(mx.array(tile))
            mx.eval(r)
            return np.array(r)
        t = time.perf_counter()
        port = tiler_port.decode_image_tiled(np.array(z_dec_in), mlx_decode)
        rec["tiler_gate"] = {"pass": bool(np.array_equal(port, dec_np)), "max_abs": float(np.abs(port - dec_np).max()),
                             "seconds": round(time.perf_counter() - t, 3)}
    if "--foreign" in flags:
        f = np.load(flags[flags.index("--foreign") + 1])
        d = QV.decode(vae, mx.array(f), tiling)
        arrays["dec_foreign"] = save(out, "dec_foreign", np.array(d))
        rec["foreign_source"] = flags[flags.index("--foreign") + 1]
    rec["arrays"] = arrays
    rec["seconds"]["total"] = round(time.perf_counter() - t0, 3)
    rec.update(QV.footprint())
    rec["versions"] = QV.versions()
    (out / "record.json").write_text(json.dumps(rec, indent=1))
    return rec


def avgdown3d_numpy(x5: np.ndarray, out_channels: int, factor_t: int, factor_s: int) -> np.ndarray:
    """Diffusers QwenImage21AvgDown3D.forward transcribed to NumPy (front temporal zero pad, view/permute/mean)."""
    pad_t = (factor_t - x5.shape[2] % factor_t) % factor_t
    x = np.pad(x5, [(0, 0), (0, 0), (pad_t, 0), (0, 0), (0, 0)])
    B, C, T, H, W = x.shape
    factor = factor_t * factor_s * factor_s
    x = x.reshape(B, C, T // factor_t, factor_t, H // factor_s, factor_s, W // factor_s, factor_s)
    x = x.transpose(0, 1, 3, 5, 7, 2, 4, 6).reshape(B, C * factor, T // factor_t, H // factor_s, W // factor_s)
    x = x.reshape(B, out_channels, C * factor // out_channels, T // factor_t, H // factor_s, W // factor_s)
    return x.mean(axis=2)


def probe(out_dir: str) -> dict:
    from mflux.models.qwen21.model.qwen21_vae.qwen21_avg_down import Qwen21AvgDown
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=False)
    mx.set_cache_limit(1000 ** 3)
    vae = QV.load_vae()
    calls: dict = {}
    avg_sites: dict = {}
    orig_pad, orig_avg = mx.pad, Qwen21AvgDown.__call__

    def pad(a, pad_width, *args, **kw):
        key = (tuple(a.shape), json.dumps([list(map(int, p)) for p in pad_width]), str(a.dtype))
        calls.setdefault(key, 0)
        calls[key] += 1
        return orig_pad(a, pad_width, *args, **kw)

    def avg(self, x):
        if self.factor_t == 2:
            avg_sites.setdefault((tuple(x.shape), self.out_channels, self.factor_t, self.factor_s), 0)
            avg_sites[(tuple(x.shape), self.out_channels, self.factor_t, self.factor_s)] += 1
        return orig_avg(self, x)

    mx.pad, Qwen21AvgDown.__call__ = pad, avg
    try:
        for w, h in G2_SIZES:
            _, pixels, ww, hh = QV.preprocess(str(synthetic(w, h)), 512 if max(w, h) < 1000 else 1024)
            assert (ww, hh) == (w, h), (ww, hh, w, h)
            enc = vae.encode(pixels)
            mx.eval(enc)
            dec = QV.decode(vae, QV.pack_unpack(enc, w, h, mx.bfloat16), QV.tiling_for(vae, True))
            mx.eval(dec)
    finally:
        mx.pad, Qwen21AvgDown.__call__ = orig_pad, orig_avg
    rng = np.random.default_rng(20261009)
    results = []
    for (shape, pw, dtype), n in sorted(calls.items()):
        pad_width = [tuple(p) for p in json.loads(pw)]
        x = rng.standard_normal(shape).astype(np.float32)
        for dt in (mx.float32, mx.bfloat16):
            xa = mx.array(x).astype(dt)
            got = np.array(mx.pad(xa, pad_width).astype(mx.float32))
            want = np.pad(np.array(xa.astype(mx.float32)), pad_width)
            results.append({"op": "mx.pad", "shape": list(shape), "pad_width": pad_width, "seen_dtype": dtype,
                            "calls_seen": n, "dtype": str(dt), "inner_elements": int(np.prod(shape[2:])),
                            "bit_exact": bool(np.array_equal(got, want)),
                            "elements_differing": int((got != want).sum()), "max_abs": float(np.abs(got - want).max())})
    for (shape, oc, ft, fs), n in sorted(avg_sites.items()):
        b, c, hh, ww = shape
        x = rng.standard_normal(shape).astype(np.float32)
        layer = Qwen21AvgDown(c, oc, ft, fs)
        got = np.array(layer(mx.array(x)))
        want = avgdown3d_numpy(x[:, :, None], oc, ft, fs)[:, :, 0]
        d = np.abs(got - want)
        results.append({"op": "Qwen21AvgDown vs NumPy AvgDown3D", "shape": list(shape), "out_channels": oc,
                        "factor_t": ft, "factor_s": fs, "calls_seen": n, "dtype": "float32",
                        "max_abs": float(d.max()), "pass": bool(d.max() <= 1e-6)})
    rec = {"tool": "research/qwen/qv-reference/mlx_side.py probe", "default_device": str(mx.default_device()),
           "MLX_ENABLE_TF32": os.environ.get("MLX_ENABLE_TF32"), "sizes": G2_SIZES,
           "distinct_pad_calls": len(calls), "temporal_avgdown_sites": len(avg_sites), "results": results,
           "pass": all(r.get("bit_exact", r.get("pass")) for r in results), "versions": QV.versions()}
    (out / "probe.json").write_text(json.dumps(rec, indent=1))
    return rec


if __name__ == "__main__":
    mode, *args = sys.argv[1:]
    r = {"capture": capture, "probe": probe}[mode](*args)
    keep = ("param_check", "cast_commutes_with_pack", "to_uint8_port_vs_to_pil", "tiler_gate", "seconds",
            "peak_footprint_gb", "mlx_peak_gb", "pass", "distinct_pad_calls", "temporal_avgdown_sites")
    print(json.dumps({k: (v if k != "param_check" else {"pass": v["pass"]}) for k, v in r.items() if k in keep}, indent=1))
