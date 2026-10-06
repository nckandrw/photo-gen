"""Input-image staging for tasks that take a source image (image-edit).

An input file is never used in place. At submit time it is validated, decoded, EXIF-oriented, reduced to 8-bit RGB
and written as a metadata-free PNG under data/inputs/, named by the SHA-256 of its decoded RGB pixels (the same
identity definition as outputs: imaging.inspect_image). The job records both identities (the original file's
sha256 and the canonical pixel sha256); the worker reads only the staged copy, and the runtime re-verifies the
staged pixels before every launch, so a job is reproducible even if the original file later changes.

Colour handling: no colour management. Pixel values are used as decoded (treated as sRGB); an embedded ICC
profile is recorded and reported as a warning, never applied. Transparency is not supported in this phase:
inputs whose alpha channel is not fully opaque are rejected; a fully opaque alpha channel is dropped.
"""
from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image, ImageOps

from .errors import GenerationError, ValidationError

ACCEPTED_FORMATS = ("PNG", "JPEG", "WEBP")
ACCEPTED_MODES = ("1", "L", "LA", "P", "RGB", "RGBA")
MAX_INPUT_BYTES = 50 * 1024 * 1024
MIN_SIDE, MAX_SIDE = 64, 8192
MAX_PIXELS = 40_000_000  # checked from the header, before any pixel is decoded


@dataclass(frozen=True)
class InputImage:
    source_path: str          # the resolved path that was read at submit time
    source_file_sha256: str   # identity of the original file bytes
    source_format: str
    source_mode: str
    staged_path: str          # canonical RGB PNG actually given to the runtime
    pixel_sha256: str         # sha256 of the staged image's raw RGB bytes (= its canonical identity)
    width: int                # after EXIF orientation
    height: int
    exif_orientation: int | None
    alpha_dropped: bool       # a fully opaque alpha channel was removed
    icc_profile: bool         # an embedded ICC profile was present (and ignored)

    def to_dict(self) -> dict:
        return asdict(self)


def stage_input_image(path, inputs_dir: Path) -> tuple[InputImage, list[str]]:
    """Validate and stage one input image. Returns (identity, warnings). Raises ValidationError."""
    if not isinstance(path, str) or not path.strip():
        raise ValidationError("'image' must be a path to an image file")
    if not os.path.isabs(path):
        raise ValidationError("'image' must be an absolute path (the CLI resolves relative paths for you)")
    real = Path(os.path.realpath(path))
    if not real.is_file():
        raise ValidationError(f"input image is not a regular file: {path}")
    size = real.stat().st_size
    if size == 0 or size > MAX_INPUT_BYTES:
        raise ValidationError(f"input image must be 1 byte..{MAX_INPUT_BYTES // (1024 * 1024)} MB (got {size} bytes)")
    data = real.read_bytes()
    warnings: list[str] = []
    try:
        with Image.open(real) as im:
            fmt, mode, (w, h) = im.format, im.mode, im.size
            if fmt not in ACCEPTED_FORMATS:
                raise ValidationError(f"input format {fmt} is not accepted ({', '.join(ACCEPTED_FORMATS)})")
            if getattr(im, "is_animated", False):
                raise ValidationError("animated images are not accepted")
            if w * h > MAX_PIXELS:
                raise ValidationError(f"input is {w}x{h}; at most {MAX_PIXELS} pixels are accepted")
            if mode not in ACCEPTED_MODES:
                raise ValidationError(f"input mode {mode} is not accepted ({', '.join(ACCEPTED_MODES)})")
            im.verify()
        with Image.open(real) as im:
            im.load()
            orientation = im.getexif().get(0x0112)
            icc = bool(im.info.get("icc_profile"))
            oriented = ImageOps.exif_transpose(im)
            has_alpha = oriented.mode in ("LA", "RGBA") or (oriented.mode == "P" and "transparency" in oriented.info)
            alpha_dropped = False
            if has_alpha:
                lo, _ = oriented.convert("RGBA").getchannel("A").getextrema()
                if lo < 255:
                    raise ValidationError("input has transparent pixels; transparency is not supported for editing yet")
                alpha_dropped = True
            rgb = oriented.convert("RGB")
    except ValidationError:
        raise
    except Exception as e:  # PIL raises a variety of types for broken or hostile files
        raise ValidationError(f"input is not a readable image: {e}") from None
    w, h = rgb.size
    if not (MIN_SIDE <= w <= MAX_SIDE and MIN_SIDE <= h <= MAX_SIDE):
        raise ValidationError(f"input is {w}x{h}; each side must be within {MIN_SIDE}..{MAX_SIDE}")
    if icc:
        warnings.append("input has an embedded ICC profile; it is ignored (pixel values are used as-is, as sRGB)")
    pixel_sha = hashlib.sha256(rgb.tobytes()).hexdigest()
    staged = Path(inputs_dir) / f"{pixel_sha}.png"
    if not staged.exists():
        staged.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=staged.parent, suffix=".png.tmp")
        os.close(fd)
        try:
            rgb.save(tmp, format="PNG")  # no metadata chunks: pixels only
            os.replace(tmp, staged)
        finally:
            Path(tmp).unlink(missing_ok=True)
    verify_staged(str(staged), pixel_sha)
    return InputImage(source_path=str(real), source_file_sha256=hashlib.sha256(data).hexdigest(), source_format=fmt,
                      source_mode=mode, staged_path=str(staged), pixel_sha256=pixel_sha, width=w, height=h,
                      exif_orientation=orientation, alpha_dropped=alpha_dropped, icc_profile=icc), warnings


def verify_staged(staged_path: str, pixel_sha256: str) -> None:
    """Re-decode a staged input and check its pixel identity. Raises GenerationError on any mismatch."""
    try:
        with Image.open(staged_path) as im:
            im.load()
            if im.mode != "RGB":
                raise GenerationError(f"staged input {staged_path} is {im.mode}, expected RGB")
            got = hashlib.sha256(im.tobytes()).hexdigest()
    except GenerationError:
        raise
    except Exception as e:  # noqa: BLE001
        raise GenerationError(f"staged input {staged_path} is unreadable: {e}") from None
    if got != pixel_sha256:
        raise GenerationError("staged input failed its integrity check", path=staged_path, expected=pixel_sha256,
                              found=got)
