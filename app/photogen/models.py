"""Request/job data types shared by the API, CLI, queue and runtimes."""
from __future__ import annotations

import enum
import secrets
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def new_job_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + secrets.token_hex(3)


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def terminal(self) -> bool:
        return self in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED)


@dataclass(frozen=True)
class GenerationRequest:
    """A fully normalized, runtime-validated text-to-image request. Every field is what will actually run."""
    task: str
    prompt: str
    width: int
    height: int
    steps: int
    seed: int
    seed_source: str  # "explicit" | "random"
    output_format: str
    validated: bool  # True only if (resolution, steps) match the research-validated configuration
    warnings: tuple[str, ...] = ()
    output_name: str | None = None
    precision: str = "fp32"  # DiT hidden-stream dtype: "fp32" (production default/reference) | "bf16" (opt-in)
    profile: str | None = None  # "reference" | "fast" | None (explicit parameters)
    text_encoder: str = "stock"  # "stock" (validated pack) | a registered, enabled substitute (config/text-encoders.json)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["warnings"] = list(self.warnings)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "GenerationRequest":
        return cls(**{"task": "text-to-image", **d, "warnings": tuple(d.get("warnings", ()))})


@dataclass(frozen=True)
class EditRequest:
    """A fully normalized image-edit request (task 'image-edit'). Every field is what will actually run."""
    task: str
    prompt: str              # the edit instruction
    width: int               # output size, derived from output_resolution and the input's aspect ratio
    height: int
    steps: int
    seed: int
    seed_source: str
    output_format: str
    validated: bool          # False for every edit until an edit configuration passes a gate
    input_image: dict        # inputs.InputImage.to_dict(): staged path + both identities
    output_resolution: int   # pixel-area budget (side length) for the reference image and the output
    warnings: tuple[str, ...] = ()
    output_name: str | None = None
    profile: str | None = None  # no edit profiles exist yet
    backend_id: str | None = None      # identity known from submission on, so queued/failed jobs name their model
    model: str | None = None
    model_revision: str | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["warnings"] = list(self.warnings)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "EditRequest":
        return cls(**{**d, "warnings": tuple(d.get("warnings", ()))})


@dataclass
class GenerationResult:
    """What a runtime reports after a successful generation or edit."""
    output_path: str
    width: int
    height: int
    pixel_sha256: str
    file_sha256: str
    generation_seconds: float  # wall time of the worker process
    phases: dict = field(default_factory=dict)  # text_encode_s, denoise_s, vae_s, load_s, ...
    step_seconds: list[float] = field(default_factory=list)
    memory: dict = field(default_factory=dict)  # peak_footprint_gb, mlx_peak_gb, ...
    runtime_info: dict = field(default_factory=dict)  # runtime/model identity actually used
    effective_parameters: dict = field(default_factory=dict)  # guidance, scheduler, low_ram, ...

    def to_dict(self) -> dict:
        return asdict(self)
