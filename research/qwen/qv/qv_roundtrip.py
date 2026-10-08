"""Phase 7 Q-V: Qwen-Image-2.1 VAE round trip of a staged photograph at an edit output budget, with no DiT and no text
encoder (research/qwen/qv/PROTOCOL.md). Runs ONLY in the edit venv, with the production worker's environment.

Every step calls mflux 0.21.0's own code, in the order QwenImage21Edit.generate_image uses it for the reference image
(variants/edit/qwen_image_21_edit.py):
  open_oriented(path).convert("RGBA")
  -> resize to QwenImage21LatentCreator.dimensions(budget, w / h) with LANCZOS (the output size)
  -> pixels = float32 / 127.5 - 1, NCHW                        (the edit's reference preprocessing)
  -> vae.encode(pixels)  (untiled; returns the latent MEAN, so no sampling)
  -> pack_latents(...).astype(latent dtype)                   (what the DiT receives; bf16 per the equivalence gate)
  -> unpack_latents(..., h, w).astype(float32)                (what the edit does to the DiT's output latents)
  -> VAEUtil.decode(vae, latents, tiling_config)              (tiled: --low-ram's MemorySaver sets TilingConfig())
  -> ImageUtil.to_pil(decoded)                                 (RGBA, as the edit's output)
So the PRIMARY output is what a DiT that copied the reference latents perfectly would produce: a ceiling of the output
path, not an imitation of an edit. Two variants are computed for pixel differences only (never rated): fp32 latents
(no cast) and untiled decode.

The VAE is loaded alone from the canonical q4 export through mflux's own Qwen21Initializer.load_components with a
vae-only weight definition, as the production worker's P2 policy reloads the decode VAE for every edit.

Modes:
  roundtrip <staged.png> <budget> <out_dir>    -> out_dir/{input.png, roundtrip.png, variant-*.png, identity.json}
  gate <out_dir>   pipeline-equivalence gate (PROTOCOL.md section 4): runs one real 3-step edit of the G0 source E05
                   at 512 through the production worker (q4 export, policy P2) with read-only capture hooks, then checks
                   that this harness reproduces the captured encode input/output and decode output bit for bit.
"""
import hashlib
import json
import sys
import time
import types
from pathlib import Path

import mlx.core as mx
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "app"))
EXPORT = ROOT / "models/qwen/qwen-image-2.1-edit-mflux-q4"


def sha_file(p: Path) -> str:
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        while b := f.read(1 << 24):
            h.update(b)
    return h.hexdigest()


def versions() -> dict:
    import importlib.metadata as md
    return {p: md.version(p) for p in ("mflux", "mlx", "mlx-metal", "pillow", "numpy")}


def load_vae(export: Path = EXPORT):
    from mflux.models.qwen21.model.qwen21_vae.vae import QwenImage21VAE
    from mflux.models.qwen21.qwen21_initializer import Qwen21Initializer
    from mflux.models.qwen21.weights.qwen_image21_weight_definition import QwenImage21WeightDefinition as WD
    vae = QwenImage21VAE(json.loads((export / "vae" / "config.json").read_text()))
    vae_only = type("VaeOnly", (WD,), {"get_components": staticmethod(
        lambda: [c for c in WD.get_components() if c.name == "vae"])})
    Qwen21Initializer.load_components(types.SimpleNamespace(vae=vae, bits=None), export, vae_only, None, validate=True)
    return vae


def preprocess(staged: str, budget: int):
    from mflux.models.qwen21.latent_creator.qwen_image21_latent_creator import QwenImage21LatentCreator as LC
    from mflux.utils.exif_orientation import open_oriented
    image = open_oriented(staged).convert("RGBA")
    w, h = LC.dimensions(budget, image.width / image.height)
    image = image.resize((w, h), Image.Resampling.LANCZOS)
    pixels = mx.array(np.asarray(image).astype(np.float32) / 127.5 - 1).transpose(2, 0, 1)[None]
    return image, pixels, w, h


def tiling_for(vae, tiled: bool):
    from mflux.models.common.vae.tiling_config import TilingConfig
    model = types.SimpleNamespace(vae=vae)
    return TilingConfig() if tiled and TilingConfig.may_tile_implicitly(model) else None


def decode(vae, unpacked, tiling, vae_util_decode=None):
    from mflux.models.common.vae.vae_util import VAEUtil
    out = (vae_util_decode or VAEUtil.decode)(vae, unpacked, tiling)
    mx.eval(out)
    return out


def pack_unpack(enc, w: int, h: int, dtype):
    from mflux.models.qwen21.latent_creator.qwen_image21_latent_creator import QwenImage21LatentCreator as LC
    packed = LC.pack_latents(enc).astype(dtype)
    return LC.unpack_latents(packed, h, w).astype(mx.float32)


def to_pil(decoded) -> Image.Image:
    from mflux.utils.image_util import ImageUtil
    return ImageUtil.to_pil(decoded)


def identity(path: Path) -> dict:
    from photogen.imaging import inspect_image
    from photogen.runtimes.mflux_qwen_edit import _alpha_identity
    i = inspect_image(path)
    return {"pixel_sha256": i.pixel_sha256, "size": [i.width, i.height], "alpha": _alpha_identity(path),
            "file_sha256": sha_file(path)}


def footprint() -> dict:
    from photogen.runtimes.mflux_qwen_edit_worker import _lifetime_max_footprint_bytes
    b = _lifetime_max_footprint_bytes()
    return {"peak_footprint_gb": round(b / 1e9, 3) if b else None, "mlx_peak_gb": round(mx.get_peak_memory() / 1e9, 3)}


def roundtrip(staged: str, budget: str, out_dir: str) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=False)
    budget = int(budget)
    mx.set_cache_limit(1000 ** 3)  # as --low-ram's MemorySaver does in the edit (memory only; numerics unchanged)
    t0 = time.perf_counter()
    vae = load_vae()
    t_load = time.perf_counter() - t0
    image, pixels, w, h = preprocess(staged, budget)
    image.convert("RGB").save(out / "input.png")  # the scaled conditioning image (alpha is 255 everywhere)
    t = time.perf_counter()
    enc = vae.encode(pixels)
    mx.eval(enc)
    t_encode = time.perf_counter() - t
    tiling = tiling_for(vae, True)
    t = time.perf_counter()
    decoded = decode(vae, pack_unpack(enc, w, h, mx.bfloat16), tiling)
    t_decode = time.perf_counter() - t
    to_pil(decoded).save(out / "roundtrip.png")
    mem_primary = footprint()  # peak after load + preprocess + the primary round trip only
    t_primary = time.perf_counter() - t0
    variants = {}
    for name, dtype, tiled in (("fp32-latents", mx.float32, True), ("untiled-decode", mx.bfloat16, False)):
        v = decode(vae, pack_unpack(enc, w, h, dtype), tiling_for(vae, tiled))
        to_pil(v).save(out / f"variant-{name}.png")
        a = np.asarray(Image.open(out / "roundtrip.png").convert("RGBA")).astype(np.int16)
        b = np.asarray(Image.open(out / f"variant-{name}.png").convert("RGBA")).astype(np.int16)
        d = np.abs(a - b)
        variants[name] = {"identity": identity(out / f"variant-{name}.png"), "max_abs_diff": int(d.max()),
                          "mean_abs_diff": round(float(d.mean()), 5), "pixels_differing": round(float((d.max(-1) > 0).mean()), 6)}
    rec = {"tool": "research/qwen/qv/qv_roundtrip.py roundtrip", "staged": staged, "budget": budget, "size": [w, h],
           "staged_identity": identity(Path(staged)), "input": identity(out / "input.png"),
           "roundtrip": identity(out / "roundtrip.png"), "variants": variants,
           "latent_shape": list(enc.shape), "latent_dtype_to_dit": "bfloat16", "tiling": repr(tiling),
           "vae_file_sha256": sha_file(EXPORT / "vae" / "0.safetensors"),
           "vae_config_sha256": sha_file(EXPORT / "vae" / "config.json"),
           "seconds": {"load": round(t_load, 3), "encode": round(t_encode, 3), "decode": round(t_decode, 3),
                       "primary_total": round(t_primary, 3), "total_with_variants": round(time.perf_counter() - t0, 3)},
           "memory_primary": mem_primary, **footprint(), "mlx_cache_limit_bytes": 1000 ** 3, "versions": versions()}
    (out / "identity.json").write_text(json.dumps(rec, indent=1))
    return rec


def gate(out_dir: str) -> dict:
    from mflux.models.common.vae.vae_util import VAEUtil
    from mflux.models.qwen21.latent_creator.qwen_image21_latent_creator import QwenImage21LatentCreator as LC
    from mflux.models.qwen21.model.qwen21_vae.vae import QwenImage21VAE
    import photogen.runtimes.mflux_qwen_edit_worker as W
    from photogen.runtimes.mflux_qwen_edit import QwenEditManifest

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=False)
    cap: dict = {}
    orig_encode, orig_decode, orig_unpack = QwenImage21VAE.encode, VAEUtil.decode, LC.unpack_latents

    def encode(self, image):  # read-only capture
        r = orig_encode(self, image)
        mx.eval(r)
        cap.setdefault("enc_in", np.array(image))
        cap.setdefault("enc_out", np.array(r))
        return r

    def unpack(latents, height, width):
        cap.setdefault("unpack_in_dtype", str(latents.dtype))
        return orig_unpack(latents, height, width)

    def dec(vae, latent, tiling_config=None):
        r = orig_decode(vae, latent, tiling_config)
        mx.eval(r)
        cap.setdefault("dec_in", np.array(latent))
        cap.setdefault("dec_tiling", repr(tiling_config))
        cap.setdefault("dec_out", np.array(r))
        return r

    QwenImage21VAE.encode, VAEUtil.decode, LC.unpack_latents = encode, staticmethod(dec), staticmethod(unpack)
    inputs = json.loads((ROOT / "research/qwen/memory/inputs.json").read_text())
    staged = inputs["E05"]["staged_path"]
    m = QwenEditManifest.load(ROOT / "config" / "backend-qwen21-edit-mflux.json", ROOT)
    req = {"model_path": str(m.model_path), "base_model": m.defaults["base_model"],
           "prompt": "Change the background to a sunset beach", "image_path": staged, "seed": 42, "steps": 3,
           "output_resolution": 512, "output_path": str((out / "edit.png").resolve()),
           "defer_transformer_load": True, "release_text_encoder_after_encode": True, "release_vae_during_denoise": True}
    (out / "worker-request.json").write_text(json.dumps(req, indent=1))
    rc = W.main(str(out / "worker-request.json"), str(out / "worker-result.json"))
    QwenImage21VAE.encode, VAEUtil.decode, LC.unpack_latents = orig_encode, staticmethod(orig_decode), staticmethod(orig_unpack)

    vae = load_vae()
    _, pixels, w, h = preprocess(staged, 512)
    enc = vae.encode(pixels)
    mx.eval(enc)
    tiling = tiling_for(vae, True)
    dec_h = decode(vae, mx.array(cap["dec_in"]), tiling)
    checks = {
        "edit_rc": rc,
        "captured": sorted(cap),
        "encode_input_identical": bool(np.array_equal(np.array(pixels), cap["enc_in"])),
        "encode_output_identical": bool(np.array_equal(np.array(enc), cap["enc_out"])),
        "latent_dtype_into_unpack": cap.get("unpack_in_dtype"),
        "tiling_pipeline": cap.get("dec_tiling"), "tiling_harness": repr(tiling),
        "tiling_identical": cap.get("dec_tiling") == repr(tiling),
        "decode_output_identical": bool(np.array_equal(np.array(dec_h), cap["dec_out"])),
        "shapes": {k: list(v.shape) for k, v in cap.items() if isinstance(v, np.ndarray)},
    }
    checks["pass"] = all([rc == 0, checks["encode_input_identical"], checks["encode_output_identical"],
                          checks["latent_dtype_into_unpack"] == "mlx.core.bfloat16", checks["tiling_identical"],
                          checks["decode_output_identical"]])
    rec = {"tool": "research/qwen/qv/qv_roundtrip.py gate", "source": "G0 E05 (not a G2 item)", "staged": staged,
           "request": req, "checks": checks, "vae_file_sha256": sha_file(EXPORT / "vae" / "0.safetensors"),
           **footprint(), "versions": versions()}
    (out / "gate.json").write_text(json.dumps(rec, indent=1))
    return rec


if __name__ == "__main__":
    mode, *args = sys.argv[1:]
    r = {"roundtrip": roundtrip, "gate": gate}[mode](*args)
    print(json.dumps({k: v for k, v in r.items() if k in ("checks", "size", "roundtrip", "seconds", "peak_footprint_gb",
                                                          "mlx_peak_gb")}, indent=1))
    sys.exit(0 if mode != "gate" or r["checks"]["pass"] else 1)
