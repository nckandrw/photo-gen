"""Application assembly and startup verification shared by the API server and the CLI."""
from __future__ import annotations

import logging
import logging.handlers
import sys

from . import __version__, system
from .config import AppConfig
from .errors import RuntimeUnavailableError
from .jobs import JobManager
from .runtimes.base import ImageRuntime, RuntimeHealth
from .runtimes.mflux_qwen_edit import MFluxQwenImageEditRuntime
from .runtimes.mflux_zimage import MFluxZImageRuntime
from .tasks import IMAGE_EDIT, TEXT_TO_IMAGE, TaskRouter

log = logging.getLogger("photogen")


def setup_logging(cfg: AppConfig, verbose: bool = False) -> None:
    cfg.ensure_dirs()
    level = logging.DEBUG if verbose else getattr(logging, cfg.log_level, logging.INFO)
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(level)
    console.setFormatter(fmt)
    fileh = logging.handlers.RotatingFileHandler(cfg.logs_dir / "photogen.log", maxBytes=5_000_000, backupCount=3)
    fileh.setLevel(logging.DEBUG if verbose else level)
    fileh.setFormatter(fmt)
    root.addHandler(console)
    root.addHandler(fileh)
    for noisy in ("PIL", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


class PhotoGenService:
    """One application, one job system, one API; one explicitly selected runtime per task (tasks.py).

    Health is per backend: the text-to-image backend (Z-Image) decides the service status exactly as before; the
    image-edit backend (Qwen, experimental) is checked separately and its absence or failure only disables editing."""

    def __init__(self, cfg: AppConfig, runtime: ImageRuntime | None = None, edit_runtime: ImageRuntime | None = None):
        self.cfg = cfg
        cfg.ensure_dirs()
        self.runtime = runtime or MFluxZImageRuntime(cfg)
        self.edit_runtime = edit_runtime or MFluxQwenImageEditRuntime(cfg)
        self.router = TaskRouter({TEXT_TO_IMAGE: self.runtime, IMAGE_EDIT: self.edit_runtime})
        self.jobs = JobManager(cfg, self.router)
        self.last_health: RuntimeHealth | None = None
        self.last_edit_health: RuntimeHealth | None = None

    def verify(self, full: bool = False) -> RuntimeHealth:
        h = self.runtime.health(full_verify=full)
        self.last_health = h
        for name, c in h.checks.items():
            (log.info if c["ok"] else log.error)("startup check %-11s %s", name, "ok" if c["ok"] else c["detail"])
        return h

    def require_healthy(self, full: bool = False) -> RuntimeHealth:
        h = self.verify(full)
        if not h.ok:
            failed = {k: v["detail"] for k, v in h.checks.items() if not v["ok"]}
            raise RuntimeUnavailableError("runtime verification failed; nothing was repaired or downloaded",
                                          failed=failed)
        return h

    def verify_edit(self, full: bool = False) -> RuntimeHealth:
        h = self.edit_runtime.health(full_verify=full)
        self.last_edit_health = h
        for name, c in h.checks.items():
            (log.info if c["ok"] else log.warning)("image-edit check %-11s %s", name, "ok" if c["ok"] else c["detail"])
        return h

    def require_edit_healthy(self, full: bool = False, cached: bool = False) -> RuntimeHealth:
        """Raise 503 unless the image-edit backend verifies. cached=True reuses the last check (API requests)."""
        h = self.last_edit_health if cached and self.last_edit_health is not None else self.verify_edit(full)
        if not h.ok:
            failed = {k: v["detail"] for k, v in h.checks.items() if not v["ok"]}
            raise RuntimeUnavailableError("image-edit backend is unavailable; nothing was repaired or downloaded",
                                          failed=failed)
        return h

    def tasks(self) -> dict:
        """Task -> backend summary (additive to /capabilities and /status)."""
        eh = self.last_edit_health
        edit_caps = self.edit_runtime.capabilities().to_dict()
        return {
            TEXT_TO_IMAGE: {"endpoint": "POST /generate", "cli": "photo-gen generate", "runtime": self.runtime.name,
                            "status": "production", "models": list(self.runtime.capabilities().supported_models)},
            IMAGE_EDIT: {"endpoint": "POST /edit", "cli": "photo-gen edit", "runtime": self.edit_runtime.name,
                         "status": edit_caps.get("memory_profile", {}).get("status", "unavailable"),
                         "available": None if eh is None else eh.ok, "models": edit_caps["supported_models"],
                         "capabilities": edit_caps},
        }

    def capabilities(self) -> dict:
        return {**self.runtime.capabilities().to_dict(), "tasks": self.tasks()}

    def health(self) -> dict:
        h = self.last_health
        m = self.cfg.backend
        eh = self.last_edit_health
        return {
            "service": "ok" if h and h.ok else "degraded",
            "version": __version__,
            "runtime": self.runtime.capabilities().runtime,
            "runtime_version": m.packages.get("mflux"),
            "model": m.model_name,
            "model_revision": m.model_revision,
            "low_ram": m.low_ram,
            "checks": h.to_dict()["checks"] if h else None,
            "backends": {IMAGE_EDIT: {"runtime": self.edit_runtime.name, "ok": None if eh is None else eh.ok,
                                      "checks": eh.to_dict()["checks"] if eh else None}},
        }

    def status(self) -> dict:
        return {
            **self.health(),
            **self.jobs.status(),
            "memory": system.memory_telemetry(),
            "thermal": system.thermal_telemetry(),
            "power_source": system.power_source(),
            "capabilities": self.runtime.capabilities().to_dict(),
            "tasks": self.tasks(),
        }
