"""Image tasks and the explicit task -> runtime routing table.

PHOTO-GEN is model-selective: each task type is served by one deliberately chosen runtime, and the choice is
explicit and deterministic (no automatic model selection). The router only maps a task name to the runtime
registered for it; validation stays in each runtime's normalize().

  text-to-image -> MFluxZImageRuntime          (Z-Image-Turbo; production)
  image-edit    -> MFluxQwenImageEditRuntime    (Qwen-Image-2.1; RESEARCH / EXPERIMENTAL)
"""
from __future__ import annotations

from .errors import UnsupportedParameterError

TEXT_TO_IMAGE = "text-to-image"
IMAGE_EDIT = "image-edit"


class TaskRouter:
    def __init__(self, routes: dict):
        if TEXT_TO_IMAGE not in routes:
            raise ValueError("a text-to-image runtime is required")
        self.routes = dict(routes)

    @property
    def default(self):
        return self.routes[TEXT_TO_IMAGE]

    @staticmethod
    def task_of(params: dict) -> str:
        """The task a request asks for; requests and stored jobs without one are text-to-image."""
        return params.get("task") or TEXT_TO_IMAGE

    def runtime_for(self, task: str):
        rt = self.routes.get(task)
        if rt is None:
            raise UnsupportedParameterError(f"task '{task}' is not supported; available: {', '.join(self.routes)}",
                                            parameter="task")
        return rt
