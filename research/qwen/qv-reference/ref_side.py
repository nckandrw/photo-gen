"""Phase 8 Q-VR, CPU reference side (arms A2 and X12, the Texture-Fix decoder arm, and the PyTorch-MPS positive
control; PROTOCOL.md sections 4.2, 5.1, 5.2, 8.1). Runs ONLY in torch-ref/.venv (torch 2.14.0, diffusers 0.41.0, no
MLX), launched with HF_HUB_OFFLINE=1. The VAE is the official Diffusers AutoencoderKLQwenImage21, built from the dense
checkpoint's vae/config.json and loaded with load_state_dict(strict=True) from its safetensors; nothing touches the hub.
Every parameter and input is asserted to be on the CPU, except in the mps-probe mode (a positive control, never a
reference).

Modes:
  run <a1_dir> <out_dir>                A2 (full CPU path from A1's exact x_in) + X12 (CPU decoder on A1's z_dec_in)
  texturefix <a2_dir> <tf_vae_dir> <out_dir>   TF decoder on A2's z_dec_in; TF-encoder equivalence on x_in
  weights-diff <tf_vae_dir> <out.json>  per-tensor diff of a VAE against the original (which tensors changed)
  mps-probe <mlx_probe.json> <out_dir>  F.pad temporal front pad on MPS vs CPU at the MLX probe's 5-D call-site shapes
  conv-gate <out_dir>                   amendment 1: banded vs unbanded convolution equivalence"""
import ctypes
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import tiler_port  # noqa: E402

DENSE_VAE = ROOT / "models/research/qwen-image-2.1/vae"
CONV_BAND_BYTES = 256 * 1024 ** 2  # PROTOCOL.md amendment 1: im2col budget per conv call


def install_banded_conv(limit_bytes: int = CONV_BAND_BYTES) -> dict:
    """PROTOCOL.md amendment 1. torch 2.14.0 on this Mac has no oneDNN, so a batch-1 CPU Conv2d runs im2col + GEMM with a
    (C_in * kh * kw) x (H_out * W_out) float32 buffer: about 5.4 GB for the decoder's 576-channel 3x3 conv on one
    512-px tile. This splits such a conv into bands of output rows. Each band is F.conv2d on the exact input rows it
    needs (after the layer's own zero padding), so every output element is the same kh*kw*C_in dot product with the same
    weights and bias; only the im2col buffer is smaller. Equivalence against the unbanded call is gated (conv-gate)."""
    import torch.nn.functional as F
    from torch import nn
    stats_ = {"banded_calls": 0, "plain_calls": 0}
    orig = nn.Conv2d._conv_forward

    def banded(self, x, weight, bias):
        kh, kw = self.kernel_size
        sh, sw = self.stride
        if (self.padding_mode != "zeros" or self.groups != 1 or self.dilation != (1, 1) or x.dim() != 4
                or x.shape[0] != 1 or isinstance(self.padding, str)):
            stats_["plain_calls"] += 1
            return orig(self, x, weight, bias)
        ph, pw = self.padding
        h_out = (x.shape[2] + 2 * ph - kh) // sh + 1
        w_out = (x.shape[3] + 2 * pw - kw) // sw + 1
        col_bytes = x.shape[1] * kh * kw * h_out * w_out * 4
        if col_bytes <= limit_bytes:
            stats_["plain_calls"] += 1
            return orig(self, x, weight, bias)
        stats_["banded_calls"] += 1
        xp = F.pad(x, (pw, pw, ph, ph)) if (ph or pw) else x
        rows = max(1, int(limit_bytes // (x.shape[1] * kh * kw * w_out * 4)))
        bands = [F.conv2d(xp[:, :, o0 * sh:(min(o0 + rows, h_out) - 1) * sh + kh, :], weight, bias, (sh, sw), 0)
                 for o0 in range(0, h_out, rows)]
        return torch.cat(bands, dim=2)

    nn.Conv2d._conv_forward = banded
    return stats_


def peak_footprint_gb() -> float | None:
    """ri_lifetime_max_phys_footprint (rusage_info_v4 field 28) via libproc, as the production worker records it."""
    try:
        libproc = ctypes.CDLL("/usr/lib/libproc.dylib")

        class RUsageInfoV4(ctypes.Structure):
            _fields_ = [("ri_uuid", ctypes.c_uint8 * 16)] + [(f"f{i}", ctypes.c_uint64) for i in range(40)]
        info = RUsageInfoV4()
        if libproc.proc_pid_rusage(os.getpid(), 4, ctypes.byref(info)) != 0:
            return None
        return round(getattr(info, "f28") / 1e9, 3)
    except OSError:
        return None


def sha_arr(a: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def sha_file(p: Path) -> str:
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        while b := f.read(1 << 24):
            h.update(b)
    return h.hexdigest()


def save(out: Path, name: str, a: np.ndarray) -> dict:
    a = np.ascontiguousarray(a)
    np.save(out / f"{name}.npy", a)
    return {"shape": list(a.shape), "dtype": str(a.dtype), "sha256": sha_arr(a)}


def versions() -> dict:
    import importlib.metadata as md
    return {p: md.version(p) for p in ("torch", "diffusers", "safetensors", "numpy", "pillow", "huggingface-hub")}


def load_vae(vae_dir: Path):
    from diffusers import AutoencoderKLQwenImage21
    from safetensors.torch import load_file
    cfg = json.loads((vae_dir / "config.json").read_text())
    vae = AutoencoderKLQwenImage21.from_config(cfg)
    files = sorted(vae_dir.glob("*.safetensors"))
    assert len(files) == 1, files
    sd = load_file(str(files[0]), device="cpu")
    res = vae.load_state_dict(sd, strict=True)
    vae = vae.to(dtype=torch.float32).eval()
    assert all(p.device.type == "cpu" and p.dtype == torch.float32 for p in vae.parameters())
    sd_now = vae.state_dict()
    identical = all(torch.equal(sd_now[k], sd[k]) for k in sd)
    info = {"vae_dir": str(vae_dir.relative_to(ROOT)), "file": files[0].name, "file_sha256": sha_file(files[0]),
            "config_sha256": sha_file(vae_dir / "config.json"), "tensors": len(sd),
            "missing": list(res.missing_keys), "unexpected": list(res.unexpected_keys),
            "loaded_equals_file": identical, "class": type(vae).__name__}
    lm = torch.tensor(vae.config.latents_mean, dtype=torch.float32).view(1, -1, 1, 1, 1)
    ls = torch.tensor(vae.config.latents_std, dtype=torch.float32).view(1, -1, 1, 1, 1)
    return vae, lm, ls, info


def preprocess_independent(staged: str, budget: int) -> tuple[np.ndarray, tuple[int, int], Image.Image]:
    """The A1 preprocessing recomputed here with this venv's own PIL calls (PROTOCOL.md section 4.2)."""
    import math
    image = ImageOps.exif_transpose(Image.open(staged)).convert("RGBA")
    ratio = image.width / image.height
    width = math.sqrt(budget * budget * ratio)
    w, h = max(32, round(width / 32) * 32), max(32, round(width / ratio / 32) * 32)
    image = image.resize((w, h), Image.Resampling.LANCZOS)
    x = (np.asarray(image).astype(np.float32) / 127.5 - 1).transpose(2, 0, 1)[None]
    return x, (w, h), image


def stats(a: np.ndarray) -> dict:
    a = a.astype(np.float64)
    fin = np.isfinite(a)
    return {"shape": list(a.shape), "min": float(a[fin].min()), "max": float(a[fin].max()), "mean": float(a[fin].mean()),
            "var": float(a[fin].var()), "finite": int(fin.sum()), "nonfinite": int((~fin).sum())}


def decode_fn_for(vae, lm, ls):
    def fn(tile: np.ndarray) -> np.ndarray:
        z = torch.from_numpy(np.ascontiguousarray(tile)).to(torch.float32)
        assert z.device.type == "cpu"
        return vae.decode(z * ls + lm).sample.numpy()  # Diffusers clamps to [-1, 1] inside _decode
    return fn


def run(a1_dir: str, out_dir: str) -> dict:
    a1, out = Path(a1_dir), Path(out_dir)
    out.mkdir(parents=True, exist_ok=False)
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    torch.set_grad_enabled(False)
    a1rec = json.loads((a1 / "record.json").read_text())
    rec: dict = {"tool": "research/qwen/qv-reference/ref_side.py run", "a1_dir": str(a1), "staged": a1rec["staged"],
                 "budget": a1rec["budget"], "device": "cpu", "torch_threads": torch.get_num_threads(),
                 "mps_built": torch.backends.mps.is_built(), "seconds": {}}
    t0 = time.perf_counter()
    vae, lm, ls, rec["vae"] = load_vae(DENSE_VAE)
    rec["seconds"]["load"] = round(time.perf_counter() - t0, 3)
    banding = install_banded_conv()
    x_in = np.load(a1 / "x_in.npy")
    # independent preprocessing check (gate 4) and the separately labelled Diffusers preprocessing variable
    x_own, (w, h), _ = preprocess_independent(a1rec["staged"], a1rec["budget"])
    rec["preprocessing_gate"] = {"pass": bool(x_own.shape == x_in.shape and np.array_equal(x_own, x_in)),
                                 "size": [w, h]}
    try:
        from diffusers.image_processor import VaeImageProcessor

        def calculate_dimensions(target_area, ratio):  # diffusers 0.41.0 pipeline_qwenimage21.py, verbatim (that
            import math                                # module imports transformers, which this venv lacks)
            width = math.sqrt(target_area * ratio)
            height = width / ratio
            return round(width / 32) * 32, round(height / 32) * 32, None
        vp = VaeImageProcessor(vae_scale_factor=16, vae_latent_channels=64)
        src = ImageOps.exif_transpose(Image.open(a1rec["staged"])).convert("RGBA")
        xd = vp.preprocess(src, width=w, height=h).numpy()
        d = np.abs(xd - x_in)
        cw, ch, _ = calculate_dimensions(a1rec["budget"] ** 2, src.width / src.height)
        rec["diffusers_preprocessing_variable"] = {"shape_equal": list(xd.shape) == list(x_in.shape),
                                                   "max_abs": float(d.max()), "elements_differing": int((d > 0).sum()),
                                                   "elements": int(d.size), "dims_equal_mflux": [cw, ch] == [w, h]}
    except Exception as e:  # reported, never fatal: it is a labelled variable, not an arm
        rec["diffusers_preprocessing_variable"] = {"error": repr(e)}
    x = torch.from_numpy(x_in)[:, :, None]
    assert x.device.type == "cpu"
    t = time.perf_counter()
    posterior = vae.encode(x).latent_dist
    rec["seconds"]["encode"] = round(time.perf_counter() - t, 3)
    moments = posterior.parameters
    mean = posterior.mode()
    z_norm = (mean - lm) / ls
    z_dec_in = z_norm.to(torch.bfloat16).to(torch.float32)
    arrays = {"moments": save(out, "moments", moments.numpy()), "z_norm": save(out, "z_norm", z_norm.numpy()),
              "z_dec_in": save(out, "z_dec_in", z_dec_in.numpy())}
    a1_zn, a1_zd = np.load(a1 / "z_norm.npy"), np.load(a1 / "z_dec_in.npy")
    cast = torch.from_numpy(a1_zn).to(torch.bfloat16).to(torch.float32).numpy()
    rec["cast_gate"] = {"pass": bool(np.array_equal(cast, a1_zd)), "elements_differing": int((cast != a1_zd).sum())}
    rec["after_encode_footprint_gb"] = peak_footprint_gb()
    fn = decode_fn_for(vae, lm, ls)
    t = time.perf_counter()
    dec = tiler_port.decode_image_tiled(z_dec_in.numpy(), fn)
    rec["seconds"]["decode_tiled"] = round(time.perf_counter() - t, 3)
    arrays["dec"] = save(out, "dec", dec)
    Image.fromarray(tiler_port.to_uint8(dec), "RGBA").save(out / "roundtrip.png")
    t = time.perf_counter()
    dec_x12 = tiler_port.decode_image_tiled(a1_zd, fn)  # stage isolation: CPU decoder on A1's exact decoder input
    rec["seconds"]["decode_tiled_x12"] = round(time.perf_counter() - t, 3)
    arrays["dec_x12"] = save(out, "dec_x12", dec_x12)
    Image.fromarray(tiler_port.to_uint8(dec_x12), "RGBA").save(out / "x12.png")
    rec["finite"] = {k: stats(np.load(out / f"{k}.npy"))["nonfinite"] == 0 for k in arrays}
    rec["banded_conv"] = {"limit_bytes": CONV_BAND_BYTES, **banding}
    rec["arrays"] = arrays
    rec["seconds"]["total"] = round(time.perf_counter() - t0, 3)
    rec["peak_footprint_gb"] = peak_footprint_gb()
    rec["versions"] = versions()
    (out / "record.json").write_text(json.dumps(rec, indent=1))
    return rec


def weights_diff(other_dir: str, out_json: str) -> dict:
    from safetensors.numpy import load_file
    a = load_file(str(DENSE_VAE / "diffusion_pytorch_model.safetensors"))
    other = Path(other_dir)
    b = load_file(str(sorted(other.glob("*.safetensors"))[0]))
    rows = {}
    for k in sorted(set(a) | set(b)):
        if k not in a or k not in b or a[k].shape != b[k].shape:
            rows[k] = {"status": "missing-or-shape", "a": list(a[k].shape) if k in a else None,
                       "b": list(b[k].shape) if k in b else None}
            continue
        x, y = a[k].astype(np.float64), b[k].astype(np.float64)
        if np.array_equal(a[k].view(np.uint8), b[k].view(np.uint8)):
            rows[k] = {"status": "identical"}
            continue
        nz = np.abs(x) > 0
        ratio = np.unique(np.round(y[nz] / x[nz], 9)) if nz.any() else np.array([])
        rows[k] = {"status": "differs", "max_abs": float(np.abs(x - y).max()),
                   "rel_l2": float(np.linalg.norm(x - y) / max(np.linalg.norm(x), 1e-30)),
                   "constant_ratio": float(ratio[0]) if ratio.size == 1 else None}
    summ = {}
    for k, r in rows.items():
        part = k.split(".")[0]
        s = summ.setdefault(part, {"identical": 0, "differs": 0, "constant_ratio": 0, "missing-or-shape": 0})
        s[r["status"]] += 1
        if r.get("constant_ratio") is not None:
            s["constant_ratio"] += 1
    rec = {"tool": "research/qwen/qv-reference/ref_side.py weights-diff", "a": str(DENSE_VAE.relative_to(ROOT)),
           "b": str(other), "summary": summ, "tensors": rows}
    Path(out_json).write_text(json.dumps(rec, indent=1))
    return {"summary": summ}


def texturefix(a2_dir: str, tf_dir: str, out_dir: str) -> dict:
    a2, out = Path(a2_dir), Path(out_dir)
    out.mkdir(parents=True, exist_ok=False)
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    torch.set_grad_enabled(False)
    a2rec = json.loads((a2 / "record.json").read_text())
    rec: dict = {"tool": "research/qwen/qv-reference/ref_side.py texturefix", "a2_dir": str(a2),
                 "budget": a2rec["budget"], "torch_threads": torch.get_num_threads(), "seconds": {}}
    t0 = time.perf_counter()
    vae, lm, ls, rec["vae"] = load_vae(Path(tf_dir))
    rec["banded_conv"] = install_banded_conv()
    a1_dir = Path(a2rec["a1_dir"])
    x = torch.from_numpy(np.load(a1_dir / "x_in.npy"))[:, :, None]
    t = time.perf_counter()
    z_tf = ((vae.encode(x).latent_dist.mode() - lm) / ls).numpy()
    rec["seconds"]["encode"] = round(time.perf_counter() - t, 3)
    z_orig = np.load(a2 / "z_norm.npy")
    d = z_tf.astype(np.float64) - z_orig
    rec["encoder_equivalence"] = {"max_abs": float(np.abs(d).max()),
                                  "rel_l2": float(np.linalg.norm(d) / np.linalg.norm(z_orig)),
                                  "bit_identical": bool(np.array_equal(z_tf, z_orig))}
    t = time.perf_counter()
    dec = tiler_port.decode_image_tiled(np.load(a2 / "z_dec_in.npy"), decode_fn_for(vae, lm, ls))
    rec["seconds"]["decode_tiled"] = round(time.perf_counter() - t, 3)
    rec["arrays"] = {"dec_tf": save(out, "dec_tf", dec)}
    Image.fromarray(tiler_port.to_uint8(dec), "RGBA").save(out / "roundtrip-tf.png")
    rec["nonfinite"] = int((~np.isfinite(dec)).sum())
    rec["seconds"]["total"] = round(time.perf_counter() - t0, 3)
    rec["peak_footprint_gb"] = peak_footprint_gb()
    rec["versions"] = versions()
    (out / "record.json").write_text(json.dumps(rec, indent=1))
    return rec


def mps_probe(mlx_probe_json: str, out_dir: str) -> dict:
    """Positive control (never a reference): the same 5-D temporal front-pad shapes through F.pad on MPS vs CPU."""
    import torch.nn.functional as F
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=False)
    probe = json.loads(Path(mlx_probe_json).read_text())
    shapes = sorted({tuple(r["shape"]) for r in probe["results"]
                     if r["op"] == "mx.pad" and len(r["shape"]) == 5 and r["pad_width"][2] != [0, 0]})
    rng = np.random.default_rng(20261009)
    rows = []
    for shape in shapes:
        x = torch.from_numpy(rng.standard_normal(shape).astype(np.float32))
        for dt in (torch.float32, torch.bfloat16):
            xc = x.to(dt)
            want = F.pad(xc, (0, 0, 0, 0, 1, 0)).float()
            got = F.pad(xc.to("mps"), (0, 0, 0, 0, 1, 0)).float().cpu()
            diff = (got - want).abs()
            rows.append({"shape": list(shape), "dtype": str(dt), "bit_exact": bool(torch.equal(got, want)),
                         "elements_differing": int((got != want).sum()), "fraction_differing": float((got != want).float().mean()),
                         "max_abs": float(torch.nan_to_num(diff, nan=float("inf")).max()),
                         "nonfinite": int((~torch.isfinite(got)).sum())})
    rec = {"tool": "research/qwen/qv-reference/ref_side.py mps-probe", "role": "positive control, not a reference",
           "torch": torch.__version__, "mps_available": torch.backends.mps.is_available(), "rows": rows,
           "defect_reproduced": any(not r["bit_exact"] for r in rows)}
    (out / "mps-probe.json").write_text(json.dumps(rec, indent=1))
    return rec


def conv_gate(out_dir: str) -> dict:
    """PROTOCOL.md amendment 1: banded vs unbanded convolution, (a) single convs at VAE-like shapes with random data and
    a tiny band budget (many bands), (b) a full 256-px encode and decode of a synthetic image with the real weights."""
    import torch.nn.functional as F  # noqa: F401
    from torch import nn
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=False)
    torch.set_grad_enabled(False)
    g = torch.Generator().manual_seed(20261009)
    orig = nn.Conv2d._conv_forward
    rows = []
    for cin, cout, k, s, p, h, w in [(576, 288, 3, 1, 1, 96, 80), (288, 144, 3, 1, 1, 130, 97), (96, 96, 3, 2, 0, 131, 99),
                                     (4, 96, 3, 1, 1, 160, 120), (1152, 1152, 3, 1, 1, 40, 36), (144, 4, 3, 1, 1, 128, 128)]:
        conv = nn.Conv2d(cin, cout, k, stride=s, padding=p)
        x = torch.randn(1, cin, h, w, generator=g)
        nn.Conv2d._conv_forward = orig
        want = conv(x)
        st = install_banded_conv(64 * 1024)
        got = conv(x)
        nn.Conv2d._conv_forward = orig
        rows.append({"conv": [cin, cout, k, s, p, h, w], "banded_calls": st["banded_calls"],
                     "bit_exact": bool(torch.equal(got, want)), "max_abs": float((got - want).abs().max())})
    vae, lm, ls, info = load_vae(DENSE_VAE)
    yy, xx = torch.meshgrid(torch.arange(256), torch.arange(256), indexing="ij")
    img = torch.stack([xx / 255.0, yy / 255.0, ((xx // 16 + yy // 16) % 2).float(), torch.ones_like(xx, dtype=torch.float32)])
    x = (img * 2 - 1)[None, :, None].float()
    nn.Conv2d._conv_forward = orig
    m_plain = vae.encode(x).latent_dist.parameters
    d_plain = vae.decode(m_plain[:, :64]).sample
    st = install_banded_conv(8 * 1024 ** 2)
    m_band = vae.encode(x).latent_dist.parameters
    d_band = vae.decode(m_plain[:, :64]).sample
    nn.Conv2d._conv_forward = orig
    full = {"banded_calls": st["banded_calls"], "encode_bit_exact": bool(torch.equal(m_band, m_plain)),
            "encode_max_abs": float((m_band - m_plain).abs().max()), "decode_bit_exact": bool(torch.equal(d_band, d_plain)),
            "decode_max_abs": float((d_band - d_plain).abs().max())}
    rec = {"tool": "research/qwen/qv-reference/ref_side.py conv-gate", "single_convs": rows, "full_vae_256": full,
           "pass": all(r["max_abs"] <= 1e-5 for r in rows) and full["decode_max_abs"] <= 1e-5 and full["encode_max_abs"] <= 1e-5,
           "all_bit_exact": all(r["bit_exact"] for r in rows) and full["encode_bit_exact"] and full["decode_bit_exact"],
           "torch_threads": torch.get_num_threads(), "versions": versions()}
    (out / "conv-gate.json").write_text(json.dumps(rec, indent=1))
    return rec


if __name__ == "__main__":
    mode, *args = sys.argv[1:]
    r = {"run": run, "texturefix": texturefix, "weights-diff": weights_diff, "mps-probe": mps_probe,
         "conv-gate": conv_gate}[mode](*args)
    keep = ("preprocessing_gate", "cast_gate", "diffusers_preprocessing_variable", "seconds", "peak_footprint_gb",
            "finite", "encoder_equivalence", "nonfinite", "defect_reproduced", "summary", "torch_threads",
            "banded_conv", "pass", "all_bit_exact", "full_vae_256", "single_convs")
    print(json.dumps({k: v for k, v in r.items() if k in keep}, indent=1))
