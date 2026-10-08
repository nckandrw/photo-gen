"""Phase 8 Q-VR: a verbatim NumPy port of mflux 0.21.0's tiled VAE decode and image conversion, so the CPU reference
(A2) can decode with exactly the production arithmetic around its own per-tile decoder. PROTOCOL.md section 4.2.

Sources (mflux 0.21.0, edit venv): models/common/vae/vae_tiler.py VAETiler.decode_image_tiled and _cos_ramp;
models/common/vae/vae_util.py VAEUtil.decode (overlap_px = vae_decode_overlap * spatial_scale); TilingConfig() defaults
(tile 512 px, overlap 8 latents); utils/image_util.py ImageUtil.to_pil (_denormalize: clip(x / 2 + 0.5, 0, 1);
_numpy_to_pil: (x * 255).round().astype(uint8)). Only NumPy is imported; the transcription is gated bit for bit
against mflux itself (PROTOCOL.md section 5.1 gate 6)."""
from typing import Callable

import numpy as np

TILE_SIZE = 512      # TilingConfig().vae_decode_tile_size
OVERLAP_LATENTS = 8  # TilingConfig().vae_decode_overlap
SPATIAL_SCALE = 16   # QwenImage21VAE.spatial_scale


def _cos_ramp(n: int) -> np.ndarray:
    if n <= 0:
        return np.zeros((0,), dtype=np.float32)
    t = np.linspace(0.0, 1.0, num=n, dtype=np.float32)
    return 0.5 - 0.5 * np.cos(t * np.pi)


def decode_image_tiled(latent: np.ndarray, decode_fn: Callable[[np.ndarray], np.ndarray],
                       tile_size: int = TILE_SIZE, overlap_latents: int = OVERLAP_LATENTS,
                       spatial_scale: int = SPATIAL_SCALE) -> np.ndarray:
    """latent: (1, C, 1, H_lat, W_lat) float32. decode_fn: (1, C, 1, h, w) -> (1, 4, 1, h*s, w*s) or (1, 4, h*s, w*s),
    returned as a NumPy array. Returns (1, 4, H, W) float32, as VAETiler.decode_image_tiled."""
    B, _, T, H_lat, W_lat = latent.shape
    overlap_h = overlap_w = int(overlap_latents) * spatial_scale
    tile_h = tile_w = int(tile_size)
    if B != 1 or T != 1:
        d = decode_fn(latent)
        return d[:, :, 0] if d.ndim == 5 and d.shape[2] == 1 else d
    scale = int(spatial_scale)
    H_out, W_out = H_lat * scale, W_lat * scale
    latent_tile_h, latent_tile_w = max(1, tile_h // scale), max(1, tile_w // scale)
    if H_lat <= latent_tile_h and W_lat <= latent_tile_w:
        d = decode_fn(latent)
        return d[:, :, 0] if d.ndim == 5 and d.shape[2] == 1 else d
    latent_overlap_h = max(0, min(overlap_h // scale, latent_tile_h - 1))
    latent_overlap_w = max(0, min(overlap_w // scale, latent_tile_w - 1))
    stride_h, stride_w = max(1, latent_tile_h - latent_overlap_h), max(1, latent_tile_w - latent_overlap_w)
    ramp_h, ramp_w = _cos_ramp(overlap_h), _cos_ramp(overlap_w)
    out_np = count_np = None
    for y_lat in range(0, H_lat, stride_h):
        y_lat_end = min(y_lat + latent_tile_h, H_lat)
        for x_lat in range(0, W_lat, stride_w):
            x_lat_end = min(x_lat + latent_tile_w, W_lat)
            if (y_lat > 0 and (y_lat_end - y_lat) <= latent_overlap_h) or (
                    x_lat > 0 and (x_lat_end - x_lat) <= latent_overlap_w):
                continue
            decoded_tile = np.asarray(decode_fn(latent[:, :, :, y_lat:y_lat_end, x_lat:x_lat_end]))
            if decoded_tile.ndim == 5 and decoded_tile.shape[2] == 1:
                decoded_tile = decoded_tile[:, :, 0, :, :]
            tile_np = decoded_tile.astype(np.float32)[0].transpose(1, 2, 0)
            y_out, x_out = y_lat * scale, x_lat * scale
            h_out, w_out = y_lat_end * scale - y_out, x_lat_end * scale - x_out
            eff_h = min(h_out, tile_np.shape[0], H_out - y_out)
            eff_w = min(w_out, tile_np.shape[1], W_out - x_out)
            tile_np = tile_np[:eff_h, :eff_w, :]
            if out_np is None:
                out_np = np.zeros((H_out, W_out, tile_np.shape[2]), dtype=np.float32)
                count_np = np.zeros((H_out, W_out, 1), dtype=np.float32)
            ov_h_out, ov_w_out = max(0, min(overlap_h, eff_h - 1)), max(0, min(overlap_w, eff_w - 1))
            wh, ww = np.ones((eff_h,), dtype=np.float32), np.ones((eff_w,), dtype=np.float32)
            if ov_h_out > 0:
                if y_lat > 0:
                    wh[:ov_h_out] = ramp_h[:ov_h_out]
                if y_lat_end < H_lat:
                    wh[-ov_h_out:] = 1.0 - ramp_h[:ov_h_out]
            if ov_w_out > 0:
                if x_lat > 0:
                    ww[:ov_w_out] = ramp_w[:ov_w_out]
                if x_lat_end < W_lat:
                    ww[-ov_w_out:] = 1.0 - ramp_w[:ov_w_out]
            w2d = wh[:, None] * ww[None, :]
            out_np[y_out:y_out + eff_h, x_out:x_out + eff_w, :] += tile_np * w2d[:, :, None]
            count_np[y_out:y_out + eff_h, x_out:x_out + eff_w, :] += w2d[:, :, None]
    out_np = out_np / np.clip(count_np, 1e-6, None)
    return out_np.transpose(2, 0, 1)[None, ...]


def to_uint8(decoded: np.ndarray) -> np.ndarray:
    """(1, 4, H, W) float in [-1, 1] -> (H, W, 4) uint8, ImageUtil.to_pil's arithmetic in NumPy."""
    x = np.asarray(decoded, dtype=np.float32)
    if x.ndim == 5:
        x = x[:, :, 0]
    x = np.clip(x / 2 + 0.5, 0, 1).transpose(0, 2, 3, 1).astype(np.float32)
    return (x * 255).round().astype("uint8")[0]
