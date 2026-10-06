"""Test helpers. FakeRuntime is a test double used only by tests: it reuses the real validation logic
(MFluxZImageRuntime.normalize) but renders a synthetic PNG instead of running MLX."""
from __future__ import annotations

import dataclasses
import tempfile
import threading
import time
from pathlib import Path

from PIL import Image

from photogen.config import AppConfig
from photogen.errors import GenerationError, JobCancelledError
from photogen.imaging import check_output, inspect_image
from photogen.models import GenerationResult
from photogen.runtimes.base import RuntimeHealth
from photogen.runtimes.mflux_zimage import MFluxZImageRuntime


def temp_config(**overrides) -> AppConfig:
    tmp = Path(tempfile.mkdtemp(prefix="photogen-test-"))
    cfg = dataclasses.replace(AppConfig.load(), data_dir=tmp / "data", **overrides)
    cfg.ensure_dirs()
    return cfg


class FakeRuntime(MFluxZImageRuntime):
    def __init__(self, cfg, delay: float = 0.0, fail: bool = False, blank: bool = False):
        super().__init__(cfg)
        self.delay, self.fail, self.blank = delay, fail, blank
        self.active = 0
        self.max_active = 0
        self._lock = threading.Lock()

    def health(self, full_verify: bool = False) -> RuntimeHealth:
        return RuntimeHealth(ok=True, checks={"fake": {"ok": True, "detail": "test double"}})

    def generate(self, job_id, request, output_path, work_dir, cancel):
        with self._lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        try:
            end = time.monotonic() + self.delay
            while time.monotonic() < end:
                if cancel.cancelled:
                    raise JobCancelledError("cancelled while running")
                time.sleep(0.01)
            if self.fail:
                raise GenerationError("synthetic failure")
            img = Image.new("RGB", (request.width, request.height), (128, 64, 32))
            if not self.blank:
                for x in range(0, request.width, 8):  # deterministic pattern keyed on seed
                    img.putpixel((x, x % request.height), ((request.seed + x) % 256, 10, 200))
                band = Image.new("RGB", (request.width // 4, request.height // 4), ((request.seed * 7) % 256, 220, 30))
                img.paste(band, (0, 0))  # large enough that the blank-image check passes at any size
            img.save(output_path)
            ident = inspect_image(Path(output_path))
            check_output(ident, request.width, request.height)
            return GenerationResult(output_path=output_path, width=ident.width, height=ident.height,
                                    pixel_sha256=ident.pixel_sha256, file_sha256=ident.file_sha256,
                                    generation_seconds=self.delay, step_seconds=[0.1] * request.steps,
                                    effective_parameters={"guidance": 0.0, "scheduler": "fake", "low_ram": True})
        finally:
            with self._lock:
                self.active -= 1


def wait_for(pred, timeout=10.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if pred():
            return True
        time.sleep(0.02)
    return False


# ---------------- image-edit (Phase 4) ----------------
import hashlib  # noqa: E402
import json  # noqa: E402

from photogen.runtimes.mflux_qwen_edit import MFluxQwenImageEditRuntime  # noqa: E402


def edit_manifest(root: Path) -> Path:
    """A minimal, valid edit-backend manifest whose single 'model file' is a tiny temp file."""
    model = root / "fake-qwen-export"
    model.mkdir(parents=True, exist_ok=True)
    (model / "w.bin").write_bytes(b"qwen" * 10)
    digest = hashlib.sha256((model / "w.bin").read_bytes()).hexdigest()
    path = root / "backend-qwen21-edit-test.json"
    path.write_text(json.dumps({
        "backend_id": "test-qwen-edit", "status": "experimental",
        "runtime": {"name": "mflux", "interpreter": "nonexistent/python3.12", "python": "3.12.14",
                    "packages": {"mflux": "0.21.0", "mlx": "0.32.2"}, "entry_point": "x:main"},
        "model": {"name": "Qwen-Image-2.1", "repo": "Qwen/Qwen-Image-2.1", "revision": "d26bb61" + "0" * 33,
                  "license": "Qwen Research License (non-commercial)", "local_path": str(model),
                  "quantization": "test", "files": [{"path": "w.bin", "algo": "sha256", "digest": digest, "size": 40}]},
        "defaults": {"steps": 40, "guidance": 1.0, "output_resolution": 1024, "base_model": "qwen-image-2.1",
                     "scheduler": "linear (test)"},
        "limits": {"min_output_resolution": 384, "max_output_resolution": 1024, "min_steps": 2, "max_steps": 60},
    }))
    return path


class FakeEditRuntime(MFluxQwenImageEditRuntime):
    """Test double: the real edit normalization/staging/sidecar, a synthetic edit instead of MLX."""

    def __init__(self, cfg, delay: float = 0.0, healthy: bool = True, counter=None):
        super().__init__(cfg, manifest_path=edit_manifest(Path(tempfile.mkdtemp(prefix="photogen-edit-"))))
        self.delay, self.healthy = delay, healthy
        self.counter = counter  # optional shared FakeRuntime to count concurrency across tasks

    def health(self, full_verify: bool = False) -> RuntimeHealth:
        return RuntimeHealth(ok=self.healthy, checks={"fake": {"ok": self.healthy, "detail": "test double"}})

    def generate(self, job_id, request, output_path, work_dir, cancel):
        c = self.counter
        if c is not None:
            with c._lock:
                c.active += 1
                c.max_active = max(c.max_active, c.active)
        try:
            end = time.monotonic() + self.delay
            while time.monotonic() < end:
                if cancel.cancelled:
                    raise JobCancelledError("cancelled while running")
                time.sleep(0.01)
            with Image.open(request.input_image["staged_path"]) as src:
                img = src.convert("RGBA").resize((request.width, request.height))
            img.paste((request.seed % 256, 0, 255, 255), (0, 0, request.width // 3, request.height // 3))
            img.save(output_path)  # RGBA, like mflux's Qwen-Image-2.1 output
            ident = inspect_image(Path(output_path))
            check_output(ident, request.width, request.height)
            from photogen.runtimes.mflux_qwen_edit import _alpha_identity
            return GenerationResult(output_path=output_path, width=ident.width, height=ident.height,
                                    pixel_sha256=ident.pixel_sha256, file_sha256=ident.file_sha256,
                                    generation_seconds=self.delay, step_seconds=[0.1] * request.steps,
                                    runtime_info={"output_alpha": _alpha_identity(Path(output_path))},
                                    effective_parameters={"guidance": 1.0, "scheduler": "fake"})
        finally:
            if c is not None:
                with c._lock:
                    c.active -= 1


def make_image(path: Path, size=(256, 256), mode="RGB", fmt=None, **save_kw) -> Path:
    """A deterministic, non-uniform test image."""
    img = Image.new("RGB", size, (40, 90, 160))
    for x in range(0, size[0], 4):
        img.putpixel((x, (x * 7) % size[1]), (250, (x * 3) % 256, 20))
    img.paste((200, 200, 30), (size[0] // 4, size[1] // 4, size[0] // 2, size[1] // 2))
    if mode != "RGB":
        img = img.convert(mode)
    img.save(path, format=fmt, **save_kw)
    return path
