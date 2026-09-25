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
