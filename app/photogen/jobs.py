"""Job queue: at most one generation at a time on this machine (fanless 16 GB M5; concurrency is not validated).

One queue serves every task. A job's task (request["task"]; stored rows without one are text-to-image) selects its
runtime through the explicit TaskRouter (tasks.py); generations and edits share the queue, the GPU lock, the
store, the output layout and the cancellation path.

- API jobs are queued and executed by a single background worker thread.
- CLI jobs execute synchronously in the CLI process.
- A cross-process advisory lock (flock on data/gpu.lock) serializes generations between the API server
  and any CLI process, so "one active generation" holds machine-wide, not just per process.
"""
from __future__ import annotations

import fcntl
import json
import logging
import os
import queue
import re
import statistics
import threading
import time
from contextlib import contextmanager
from pathlib import Path

from . import system
from .config import AppConfig
from .errors import (ConflictError, GenerationError, JobCancelledError, PhotoGenError, QueueFullError)
from .models import JobStatus, new_job_id, utcnow
from .runtimes.base import CancelToken, ImageRuntime
from .store import JobStore
from .tasks import TaskRouter

log = logging.getLogger(__name__)


class JobManager:
    def __init__(self, config: AppConfig, runtime: ImageRuntime | TaskRouter, store: JobStore | None = None):
        self.cfg = config
        self.router = runtime if isinstance(runtime, TaskRouter) else TaskRouter({runtime.task: runtime})
        self.runtime = self.router.default  # the text-to-image runtime
        self.store = store or JobStore(config.db_path)
        self._queue: "queue.Queue[str | None]" = queue.Queue()
        self._tokens: dict[str, CancelToken] = {}
        self._tokens_lock = threading.Lock()
        self._worker: threading.Thread | None = None
        self._active_job: str | None = None

    # ---------- submission ----------
    def submit(self, params: dict, source: str = "api") -> dict:
        defaults = {"width": self.cfg.default_width, "height": self.cfg.default_height,
                    "steps": self.cfg.default_steps, "seed": self.cfg.default_seed}
        runtime = self.router.runtime_for(TaskRouter.task_of(params))
        req = runtime.normalize(params, defaults)
        if source == "api" and self.store.count_active() >= self.cfg.max_pending:
            raise QueueFullError(f"{self.cfg.max_pending} jobs already queued or running; try again later")
        for w in req.warnings:
            log.warning("request: %s", w)
        job_id = new_job_id()
        job = self.store.create(job_id, source, os.getpid(), runtime.capabilities().runtime, req.to_dict())
        log.info("job %s queued (%s, %s, %dx%d, steps=%d, seed=%d/%s)", job_id, source, req.task, req.width,
                 req.height, req.steps, req.seed, req.seed_source)
        if source == "api":
            self._queue.put(job_id)
        return job

    def run_sync(self, job_id: str) -> dict:
        """Execute one job in the calling thread (used by the CLI)."""
        self._execute(job_id)
        return self.store.get(job_id)

    # ---------- background worker (API server) ----------
    def start(self) -> None:
        self._recover()
        self._worker = threading.Thread(target=self._loop, name="photogen-worker", daemon=True)
        self._worker.start()

    def stop(self) -> None:
        self._queue.put(None)
        if self._active_job:
            self.cancel(self._active_job)

    def _loop(self) -> None:
        while True:
            job_id = self._queue.get()
            if job_id is None:
                return
            try:
                self._execute(job_id)
            except Exception:  # noqa: BLE001 — the worker thread must survive any single job
                log.exception("unexpected error while executing job %s", job_id)

    def _recover(self) -> None:
        """Mark jobs orphaned by a previous process as failed; re-queue this server's pending API jobs."""
        for job in self.store.running():
            if not _pid_alive(job["owner_pid"]):
                self.store.transition(job["id"], JobStatus.FAILED,
                                      error_json={"error": "interrupted", "message": "owning process exited"})
                log.warning("job %s marked failed: owning process %s is gone", job["id"], job["owner_pid"])
        for job in self.store.queued_for_source("api"):
            if job["owner_pid"] != os.getpid() and _pid_alive(job["owner_pid"]):
                continue  # another live server owns it
            log.info("re-queueing job %s from a previous session", job["id"])
            self._queue.put(job["id"])

    # ---------- execution ----------
    def _execute(self, job_id: str) -> None:
        job = self.store.get(job_id)
        if job["status"] != JobStatus.QUEUED.value:
            return  # cancelled while queued
        runtime = self.router.runtime_for(TaskRouter.task_of(job["request"]))
        req = runtime.request_from_dict(job["request"])
        token = CancelToken()
        with self._tokens_lock:
            self._tokens[job_id] = token
        try:
            with self._gpu_lock(job_id, token):
                if token.cancelled:
                    raise JobCancelledError("cancelled before start")
                try:
                    self.store.transition(job_id, JobStatus.RUNNING, owner_pid=os.getpid())
                except ConflictError:
                    return  # cancelled (or otherwise finalized) between dequeue and start
                self._active_job = job_id
                before = {"memory": system.memory_telemetry(), "thermal": system.thermal_telemetry(),
                          "power": system.power_source()}
                log.info("job %s running", job_id)
                out_path, meta_path = self._output_paths(job_id, req)
                result = runtime.generate(job_id, req, str(out_path), str(self.cfg.jobs_dir / job_id), token)
                after = {"memory": system.memory_telemetry(), "thermal": system.thermal_telemetry()}
                meta = runtime.sidecar(job_id, req, result, before, after)
                meta_path.write_text(json.dumps(meta, indent=2))
                self.store.transition(job_id, JobStatus.COMPLETED, result_json=result.to_dict(),
                                      output_path=str(out_path), metadata_path=str(meta_path),
                                      pixel_sha256=result.pixel_sha256,
                                      generation_seconds=result.generation_seconds)
                log.info("job %s completed in %.1fs (pixel_sha256 %s…)", job_id, result.generation_seconds,
                         result.pixel_sha256[:12])
        except JobCancelledError as e:
            self._finish(job_id, JobStatus.CANCELLED, e)
            log.info("job %s cancelled", job_id)
        except PhotoGenError as e:
            self._finish(job_id, JobStatus.FAILED, e)
            log.error("job %s failed: %s %s", job_id, e.message, e.details or "")
        except Exception as e:  # noqa: BLE001
            self._finish(job_id, JobStatus.FAILED, GenerationError(f"unexpected error: {e!r}"))
            log.exception("job %s failed unexpectedly", job_id)
        finally:
            self._active_job = None
            with self._tokens_lock:
                self._tokens.pop(job_id, None)

    def _finish(self, job_id: str, status: JobStatus, err: PhotoGenError) -> None:
        try:
            self.store.transition(job_id, status, error_json=err.to_dict())
        except ConflictError:
            pass  # already terminal

    @contextmanager
    def _gpu_lock(self, job_id: str, token: CancelToken):
        self.cfg.gpu_lock_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cfg.gpu_lock_path, "a+") as f:
            waited = False
            while True:
                try:
                    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if not waited:
                        log.info("job %s waiting: another process is generating (GPU lock held)", job_id)
                        waited = True
                    if token.cancelled:
                        raise JobCancelledError("cancelled while waiting for the GPU lock")
                    time.sleep(0.5)
            try:
                f.seek(0)
                f.truncate()
                f.write(f"{os.getpid()} {job_id} {utcnow()}\n")
                f.flush()
                yield
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

    def _output_paths(self, job_id: str, req) -> tuple[Path, Path]:
        day = self.cfg.outputs_dir / job_id[:4] / job_id[4:6] / job_id[6:8]
        day.mkdir(parents=True, exist_ok=True)
        stem = job_id if not req.output_name else f"{job_id}-{_safe_name(req.output_name)}"
        return day / f"{stem}.png", day / f"{stem}.json"

    # ---------- cancel / status ----------
    def cancel(self, job_id: str) -> dict:
        job = self.store.get(job_id)
        status = JobStatus(job["status"])
        if status is JobStatus.QUEUED:
            try:
                return self.store.transition(job_id, JobStatus.CANCELLED,
                                             error_json={"error": "cancelled", "message": "cancelled while queued"})
            except ConflictError:
                job = self.store.get(job_id)
                status = JobStatus(job["status"])
        if status is JobStatus.RUNNING:
            with self._tokens_lock:
                token = self._tokens.get(job_id)
            if token is None:
                raise ConflictError(f"job {job_id} is running in another process (pid {job['owner_pid']})")
            token.cancel()
            for _ in range(60):  # wait briefly for the worker to exit and the job to become terminal
                job = self.store.get(job_id)
                if JobStatus(job["status"]).terminal:
                    break
                time.sleep(0.25)
            return job
        if status.terminal:
            raise ConflictError(f"job {job_id} is already {status.value}", status=status.value)
        return job

    def status(self) -> dict:
        recent = self.store.recent_completed(self.cfg.recent_window)
        durations = [j["generation_seconds"] for j in recent if j["generation_seconds"] is not None]
        per_step = []
        for j in recent:
            steps = (j.get("result") or {}).get("step_seconds") or []
            if steps:
                per_step.append({"job_id": j["id"], "resolution": f"{j['width']}x{j['height']}",
                                 "mean_step_seconds": round(statistics.fmean(steps), 2),
                                 "last_step_seconds": steps[-1]})
        active = self.store.running()
        return {
            "active_jobs": [{"job_id": j["id"], "started_at": j["started_at"], "owner_pid": j["owner_pid"],
                             "source": j["source"]} for j in active],
            "queue_length": len(self.store.list(status=JobStatus.QUEUED.value, limit=1000)),
            "last_generation_seconds": durations[0] if durations else None,
            "recent_generation_seconds": durations,
            "recent_step_timing": per_step,
            "note": "Durations reflect thermal state: on this fanless M5, 1024² runs ≈85 s cold and ≈134 s "
                    "once throttled (measured). Step timing is observed performance, not a temperature.",
        }


def _pid_alive(pid) -> bool:
    if not pid:
        return False
    try:
        os.kill(int(pid), 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name)[:80].rstrip(".") or "image"
