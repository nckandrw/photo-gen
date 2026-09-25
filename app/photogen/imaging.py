"""Output validation and identity. The decoded-pixel SHA-256 is the canonical image identity:
PNG bytes can differ between identical generations because mflux embeds run metadata (e.g. timing)."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageStat

from .errors import OutputCorruptedError

# Per-channel standard deviation below this means a (near-)uniform image — the signature of the
# blank-output failures seen in research (sd.cpp #1990 produced all-255 PNGs with exit code 0).
UNIFORM_STD_THRESHOLD = 2.0


@dataclass(frozen=True)
class ImageIdentity:
    width: int
    height: int
    mode: str
    pixel_sha256: str  # sha256 of raw decoded RGB bytes (row-major, 8-bit) — same definition as research pixcmp
    file_sha256: str
    channel_std: tuple[float, ...]


def inspect_image(path: Path) -> ImageIdentity:
    path = Path(path)
    if not path.is_file() or path.stat().st_size == 0:
        raise OutputCorruptedError("output file missing or empty", path=str(path))
    try:
        with Image.open(path) as im:
            im.verify()
        with Image.open(path) as im:
            im.load()
            rgb = im if im.mode == "RGB" else im.convert("RGB")
            pixel_sha = hashlib.sha256(rgb.tobytes()).hexdigest()
            std = tuple(round(s, 2) for s in ImageStat.Stat(rgb).stddev)
            ident = ImageIdentity(im.width, im.height, im.mode, pixel_sha, _file_sha256(path), std)
    except OutputCorruptedError:
        raise
    except Exception as e:  # PIL raises a variety of types for broken files
        raise OutputCorruptedError(f"output is not a readable image: {e}", path=str(path)) from e
    return ident


def check_output(ident: ImageIdentity, width: int, height: int) -> None:
    if (ident.width, ident.height) != (width, height):
        raise OutputCorruptedError(f"output is {ident.width}x{ident.height}, requested {width}x{height}")
    if all(s < UNIFORM_STD_THRESHOLD for s in ident.channel_std):
        raise OutputCorruptedError("output is a uniform (blank) image", channel_std=list(ident.channel_std))


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
