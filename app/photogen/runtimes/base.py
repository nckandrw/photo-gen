"""Runtime abstraction. A runtime serves exactly one task (tasks.py) and owns: what it can do (capabilities),
whether it is usable (health), how raw parameters map onto what it will actually run (normalize), running one job
(generate), and the model-specific metadata sidecar written next to each output (sidecar)."""
from __future__ import annotations

import abc
import threading
from dataclasses import asdict, dataclass, field

from ..models import GenerationRequest, GenerationResult
from ..tasks import TEXT_TO_IMAGE


@dataclass(frozen=True)
class Capabilities:
    runtime: str
    runtime_version: str
    supported_models: tuple[str, ...]
    supported_tasks: tuple[str, ...]
    validated_resolutions: tuple[tuple[int, int], ...]
    supports_seed: bool
    supports_negative_prompt: bool
    supports_guidance: bool
    supports_editing: bool
    supports_lora: bool
    output_formats: tuple[str, ...]
    memory_profile: dict = field(default_factory=dict)
    precisions: tuple[str, ...] = ("fp32",)  # first entry is the default
    text_encoders: tuple[str, ...] = ("stock",)  # first entry is the default
    profiles: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["validated_resolutions"] = [list(r) for r in self.validated_resolutions]
        return d


@dataclass
class RuntimeHealth:
    ok: bool
    checks: dict  # name -> {"ok": bool, "detail": str}

    def to_dict(self) -> dict:
        return {"ok": self.ok, "checks": self.checks}


class CancelToken:
    """Set by the queue when a running job is cancelled; runtimes must honor it promptly."""

    def __init__(self) -> None:
        self._event = threading.Event()
        self._callbacks: list = []
        self._lock = threading.Lock()

    def cancel(self) -> None:
        with self._lock:
            self._event.set()
            callbacks = list(self._callbacks)
        for cb in callbacks:
            cb()

    def on_cancel(self, cb) -> None:
        with self._lock:
            if self._event.is_set():
                fire = True
            else:
                self._callbacks.append(cb)
                fire = False
        if fire:
            cb()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()


class ImageRuntime(abc.ABC):
    task: str = TEXT_TO_IMAGE
    name: str = "runtime"

    @abc.abstractmethod
    def capabilities(self) -> Capabilities: ...

    @abc.abstractmethod
    def health(self, full_verify: bool = False) -> RuntimeHealth: ...

    @abc.abstractmethod
    def normalize(self, params: dict, defaults: dict):
        """Validate raw parameters; reject unsupported ones; return exactly what will run."""

    def request_from_dict(self, d: dict):
        """Rebuild a stored (normalized) request of this runtime's task."""
        return GenerationRequest.from_dict(d)

    @abc.abstractmethod
    def generate(self, job_id: str, request, output_path: str, work_dir: str,
                 cancel: CancelToken) -> GenerationResult: ...

    @abc.abstractmethod
    def sidecar(self, job_id: str, request, result: GenerationResult, before: dict, after: dict) -> dict:
        """The JSON metadata written next to a completed job's output (schema + model identity + timings)."""
