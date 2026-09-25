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
from .runtimes.mflux_zimage import MFluxZImageRuntime

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
    def __init__(self, cfg: AppConfig, runtime: ImageRuntime | None = None):
        self.cfg = cfg
        cfg.ensure_dirs()
        self.runtime = runtime or MFluxZImageRuntime(cfg)
        self.jobs = JobManager(cfg, self.runtime)
        self.last_health: RuntimeHealth | None = None

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

    def health(self) -> dict:
        h = self.last_health
        m = self.cfg.backend
        return {
            "service": "ok" if h and h.ok else "degraded",
            "version": __version__,
            "runtime": self.runtime.capabilities().runtime,
            "runtime_version": m.packages.get("mflux"),
            "model": m.model_name,
            "model_revision": m.model_revision,
            "low_ram": m.low_ram,
            "checks": h.to_dict()["checks"] if h else None,
        }

    def status(self) -> dict:
        return {
            **self.health(),
            **self.jobs.status(),
            "memory": system.memory_telemetry(),
            "thermal": system.thermal_telemetry(),
            "power_source": system.power_source(),
            "capabilities": self.runtime.capabilities().to_dict(),
        }
