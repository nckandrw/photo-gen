"""Configuration: immutable backend manifest (JSON) + user/application settings (TOML)."""
from __future__ import annotations

import hashlib
import ipaddress
import json
import logging
import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .errors import ConfigError

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(os.environ.get("PHOTOGEN_ROOT", Path(__file__).resolve().parents[2]))
DEFAULT_USER_CONFIG = PROJECT_ROOT / "config" / "photogen.toml"
DEFAULT_BACKEND_MANIFEST = PROJECT_ROOT / "config" / "backend-zimage-mflux.json"


@dataclass(frozen=True)
class ModelFile:
    path: str
    algo: str  # "sha256" or "git-sha1"
    digest: str
    size: int


@dataclass(frozen=True)
class BackendManifest:
    """Research-validated identity of the production backend. Read-only by design."""
    backend_id: str
    python_version: str
    packages: dict[str, str]
    entry_point: str
    model_name: str
    model_repo: str
    model_revision: str
    model_path: Path
    base_model: str
    quantization: str
    model_files: tuple[ModelFile, ...]
    validated_resolutions: tuple[tuple[int, int], ...]
    validated_steps: int
    guidance: float
    low_ram: bool
    scheduler: str
    reference_pixel_sha256: dict[str, str]
    max_pixels: int
    dimension_multiple: int
    min_dimension: int
    max_dimension: int
    source_path: Path | None = None  # the manifest file this identity was read from
    sha256: str | None = None        # sha256 of that file's bytes (stamped into job metadata)

    @classmethod
    def load(cls, path: Path = DEFAULT_BACKEND_MANIFEST, root: Path = PROJECT_ROOT) -> "BackendManifest":
        try:
            data = Path(path).read_bytes()
            raw = json.loads(data)
            rt, m, v, lim = raw["runtime"], raw["model"], raw["validated"], raw["limits"]
            return cls(
                backend_id=raw["backend_id"],
                python_version=rt["python"],
                packages=dict(rt["packages"]),
                entry_point=rt["entry_point"],
                model_name=m["name"],
                model_repo=m["repo"],
                model_revision=m["revision"],
                model_path=(root / m["local_path"]).resolve(),
                base_model=m["base_model"],
                quantization=m["quantization"],
                model_files=tuple(ModelFile(**f) for f in m["files"]),
                validated_resolutions=tuple(tuple(r) for r in v["resolutions"]),
                validated_steps=int(v["steps"]),
                guidance=float(v["guidance"]),
                low_ram=bool(v["low_ram"]),
                scheduler=v["scheduler"],
                reference_pixel_sha256=dict(v.get("reference_pixel_sha256", {})),
                max_pixels=int(lim["max_pixels"]),
                dimension_multiple=int(lim["dimension_multiple"]),
                min_dimension=int(lim["min_dimension"]),
                max_dimension=int(lim["max_dimension"]),
                source_path=Path(path),
                sha256=hashlib.sha256(data).hexdigest(),
            )
        except (OSError, KeyError, TypeError, ValueError) as e:
            raise ConfigError(f"cannot load backend manifest {path}: {e}") from e


@dataclass(frozen=True)
class AppConfig:
    host: str = "127.0.0.1"
    port: int = 8765
    data_dir: Path = PROJECT_ROOT / "data"
    default_width: int = 1024
    default_height: int = 1024
    default_steps: int = 9
    default_seed: str | int = "random"
    max_pending: int = 20
    recent_window: int = 10
    log_level: str = "INFO"
    root: Path = PROJECT_ROOT
    backend: BackendManifest = field(default=None)  # type: ignore[assignment]

    @property
    def outputs_dir(self) -> Path:
        return self.data_dir / "outputs"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "photogen.sqlite3"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def jobs_dir(self) -> Path:
        return self.data_dir / "jobs"

    @property
    def inputs_dir(self) -> Path:
        """Staged, content-addressed input images (inputs.py)."""
        return self.data_dir / "inputs"

    @property
    def gpu_lock_path(self) -> Path:
        return self.data_dir / "gpu.lock"

    @property
    def integrity_cache_path(self) -> Path:
        return self.data_dir / "integrity-cache.json"

    @classmethod
    def load(cls, path: Path | None = None, manifest_path: Path | None = None, root: Path = PROJECT_ROOT) -> "AppConfig":
        path = Path(path or os.environ.get("PHOTOGEN_CONFIG", DEFAULT_USER_CONFIG))
        try:
            raw = tomllib.loads(path.read_text()) if path.exists() else {}
        except (OSError, tomllib.TOMLDecodeError) as e:
            raise ConfigError(f"cannot parse config {path}: {e}") from e
        s, p, d, q, lg = (raw.get(k, {}) for k in ("server", "paths", "defaults", "queue", "logging"))
        data_dir = Path(p.get("data_dir", "data"))
        seed = d.get("seed", "random")
        if not (seed == "random" or (isinstance(seed, int) and seed >= 0)):
            raise ConfigError(f"defaults.seed must be 'random' or a non-negative integer, got {seed!r}")
        cfg = cls(
            host=str(s.get("host", "127.0.0.1")),
            port=int(s.get("port", 8765)),
            data_dir=(data_dir if data_dir.is_absolute() else root / data_dir).resolve(),
            default_width=int(d.get("width", 1024)),
            default_height=int(d.get("height", 1024)),
            default_steps=int(d.get("steps", 9)),
            default_seed=seed,
            max_pending=int(q.get("max_pending", 20)),
            recent_window=int(q.get("recent_window", 10)),
            log_level=str(lg.get("level", "INFO")).upper(),
            root=root,
            backend=BackendManifest.load(Path(manifest_path) if manifest_path else DEFAULT_BACKEND_MANIFEST, root),
        )
        if not cfg.host_is_loopback:
            log.warning("server.host=%s is NOT a loopback address; the API will be reachable from the network", cfg.host)
        return cfg

    @property
    def host_is_loopback(self) -> bool:
        if self.host == "localhost":
            return True
        try:
            return ipaddress.ip_address(self.host).is_loopback
        except ValueError:
            return False

    def ensure_dirs(self) -> None:
        for d in (self.data_dir, self.outputs_dir, self.logs_dir, self.jobs_dir, self.inputs_dir):
            d.mkdir(parents=True, exist_ok=True)
