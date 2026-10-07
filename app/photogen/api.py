"""Local HTTP API (stdlib only). JSON in/out; designed for scripts and local LLM agents.

Endpoints
  GET  /health                     service + startup verification summary
  GET  /status                     queue, active job, recent durations/step timing, memory/thermal telemetry
  GET  /capabilities               what the text-to-image runtime supports, plus "tasks" (every task's backend)
  POST /generate                   submit a text-to-image job (Z-Image) -> 202 {job}
  POST /edit                       submit an image-edit job (Qwen-Image-2.1, EXPERIMENTAL) -> 202 {job};
                                   body {"image": "<absolute path>", "prompt": "<instruction>", "allow_experimental": true,
                                   "seed"?, "steps"?, "output_resolution"?, "output_name"?}
  GET  /jobs?status=&limit=&pixel_sha256=
  GET  /jobs/{id}[?wait=seconds]   job record; `wait` long-polls until the job is terminal (max 900 s)
  POST /jobs/{id}/cancel
  GET  /outputs/{id}               PNG bytes of a completed job
"""
from __future__ import annotations

import json
import logging
import re
import signal
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .errors import NotFoundError, PhotoGenError, UnsupportedParameterError, ValidationError
from .models import JobStatus
from .service import PhotoGenService
from .tasks import IMAGE_EDIT, TEXT_TO_IMAGE

log = logging.getLogger(__name__)
MAX_BODY = 64 * 1024
LOCAL_HOSTNAMES = {"127.0.0.1", "localhost", "::1"}
_JOB = re.compile(r"^/jobs/([A-Za-z0-9_-]+)$")
_CANCEL = re.compile(r"^/jobs/([A-Za-z0-9_-]+)/cancel$")
_OUTPUT = re.compile(r"^/outputs/([A-Za-z0-9_-]+)$")


def public_job(job: dict) -> dict:
    """Stable machine-readable job view."""
    res = job.get("result") or {}
    req = job.get("request") or {}
    return {
        "job_id": job["id"],
        "task": req.get("task") or TEXT_TO_IMAGE,
        "backend_id": job.get("backend_id"),
        "status": job["status"],
        "source": job["source"],
        "created_at": job["created_at"],
        "started_at": job["started_at"],
        "finished_at": job["finished_at"],
        "request": req,
        "seed": job["seed"],
        "output_path": job["output_path"],
        "metadata_path": job["metadata_path"],
        "pixel_sha256": job["pixel_sha256"],
        "file_sha256": res.get("file_sha256"),
        "generation_seconds": job["generation_seconds"],
        "phases": res.get("phases"),
        "step_seconds": res.get("step_seconds"),
        "memory": res.get("memory"),
        "runtime": res.get("runtime_info"),
        "effective_parameters": res.get("effective_parameters"),
        "error": job.get("error"),
    }


def make_handler(svc: PhotoGenService):
    class Handler(BaseHTTPRequestHandler):
        server_version = "photo-gen"
        sys_version = ""

        def log_message(self, fmt, *args):  # route http.server access logs to DEBUG
            log.debug("%s %s", self.address_string(), fmt % args)

        # ---- helpers ----
        def _send(self, status: int, payload=None, body: bytes | None = None, ctype="application/json"):
            if body is None:
                body = json.dumps(payload, indent=1, default=str).encode()
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _error(self, e: PhotoGenError):
            self._send(e.http_status, e.to_dict())

        def _local_only(self, post: bool) -> bool:
            host = urlparse("//" + (self.headers.get("Host") or "")).hostname
            if host not in LOCAL_HOSTNAMES:
                self._send(403, {"error": "forbidden", "message": "non-local Host header rejected"})
                return False
            if post:
                origin = self.headers.get("Origin")
                if origin and urlparse(origin).hostname not in {"127.0.0.1", "localhost", "::1"}:
                    self._send(403, {"error": "forbidden", "message": "cross-origin request rejected"})
                    return False
                if (self.headers.get("Content-Type") or "").split(";")[0].strip() != "application/json":
                    self._send(415, {"error": "unsupported_media_type",
                                     "message": "POST bodies must be Content-Type: application/json"})
                    return False
            return True

        def _json_body(self) -> dict:
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_BODY:
                raise ValidationError("request body too large")
            raw = self.rfile.read(n) if n else b"{}"
            try:
                body = json.loads(raw or b"{}")
            except ValueError:
                raise ValidationError("body is not valid JSON") from None
            if not isinstance(body, dict):
                raise ValidationError("body must be a JSON object")
            return body

        # ---- routes ----
        def do_GET(self):
            if not self._local_only(post=False):
                return
            u = urlparse(self.path)
            qs = {k: v[-1] for k, v in parse_qs(u.query).items()}
            try:
                if u.path == "/health":
                    h = svc.health()
                    return self._send(200 if h["service"] == "ok" else 503, h)
                if u.path == "/status":
                    return self._send(200, svc.status())
                if u.path == "/capabilities":
                    return self._send(200, svc.capabilities())
                if u.path == "/jobs":
                    jobs = svc.jobs.store.list(status=qs.get("status"), limit=int(qs.get("limit", 50)),
                                               pixel_sha256=qs.get("pixel_sha256"))
                    return self._send(200, {"jobs": [public_job(j) for j in jobs]})
                m = _JOB.match(u.path)
                if m:
                    wait = min(max(float(qs.get("wait", 0) or 0), 0.0), 900.0)
                    deadline = time.monotonic() + wait
                    job = svc.jobs.store.get(m.group(1))
                    while wait and not JobStatus(job["status"]).terminal and time.monotonic() < deadline:
                        time.sleep(0.5)
                        job = svc.jobs.store.get(m.group(1))
                    return self._send(200, public_job(job))
                m = _OUTPUT.match(u.path)
                if m:
                    job = svc.jobs.store.get(m.group(1))
                    if job["status"] != JobStatus.COMPLETED.value or not job["output_path"]:
                        raise NotFoundError(f"job {job['id']} has no output (status {job['status']})")
                    p = Path(job["output_path"])
                    if not p.is_file():
                        raise NotFoundError(f"output file for job {job['id']} is missing")
                    return self._send(200, body=p.read_bytes(), ctype="image/png")
                raise NotFoundError(f"no route for GET {u.path}")
            except PhotoGenError as e:
                self._error(e)
            except ValueError as e:
                self._error(ValidationError(str(e)))

        def do_POST(self):
            if not self._local_only(post=True):
                return
            u = urlparse(self.path)
            try:
                if u.path == "/generate":
                    body = self._json_body()
                    if body.get("task") not in (None, "", TEXT_TO_IMAGE):
                        raise UnsupportedParameterError("POST /generate is text-to-image only; use POST /edit for "
                                                        "image-edit", parameter="task")
                    job = svc.jobs.submit(body, source="api")
                    return self._send(202, public_job(job))
                if u.path == "/edit":
                    body = self._json_body()
                    if body.get("task") not in (None, "", IMAGE_EDIT):
                        raise UnsupportedParameterError("POST /edit only accepts task 'image-edit'", parameter="task")
                    svc.require_edit_healthy(cached=True)
                    job = svc.jobs.submit({**body, "task": IMAGE_EDIT}, source="api")
                    return self._send(202, public_job(job))
                m = _CANCEL.match(u.path)
                if m:
                    return self._send(200, public_job(svc.jobs.cancel(m.group(1))))
                raise NotFoundError(f"no route for POST {u.path}")
            except PhotoGenError as e:
                self._error(e)

    return Handler


def serve(svc: PhotoGenService) -> None:
    cfg = svc.cfg
    httpd = ThreadingHTTPServer((cfg.host, cfg.port), make_handler(svc))
    httpd.daemon_threads = True

    def _graceful(signum, _frame):  # SIGTERM (process managers) and SIGINT (Ctrl-C) shut down the same way
        log.info("received signal %d; shutting down", signum)
        threading.Thread(target=httpd.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, _graceful)
    signal.signal(signal.SIGINT, _graceful)
    svc.verify_edit()  # informational: an unavailable edit backend only disables POST /edit (503)
    svc.jobs.start()
    log.info("photo-gen API listening on http://%s:%d (runtime %s, model %s@%s)", cfg.host, cfg.port,
             svc.runtime.capabilities().runtime, cfg.backend.model_name, cfg.backend.model_revision[:7])
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        log.info("shutting down")
    finally:
        svc.jobs.stop()
        httpd.server_close()
