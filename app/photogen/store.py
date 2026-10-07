"""Persistent job history (SQLite, stdlib). Chosen over per-job JSON alone because the queue needs
atomic status transitions shared by the API server and CLI processes, plus history queries.
Per-generation metadata is additionally written as a JSON sidecar next to each image."""
from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

from .errors import ConflictError, NotFoundError
from .models import JobStatus, utcnow

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id            TEXT PRIMARY KEY,
    source        TEXT NOT NULL,              -- 'api' | 'cli'
    owner_pid     INTEGER,                    -- process that runs/ran the job
    status        TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    started_at    TEXT,
    finished_at   TEXT,
    runtime       TEXT NOT NULL,
    prompt        TEXT NOT NULL,
    width         INTEGER NOT NULL,
    height        INTEGER NOT NULL,
    steps         INTEGER NOT NULL,
    seed          INTEGER NOT NULL,
    request_json  TEXT NOT NULL,
    result_json   TEXT,
    error_json    TEXT,
    output_path   TEXT,
    metadata_path TEXT,
    pixel_sha256  TEXT,
    generation_seconds REAL
);
CREATE INDEX IF NOT EXISTS jobs_status ON jobs(status, created_at);
CREATE INDEX IF NOT EXISTS jobs_pixel ON jobs(pixel_sha256);
CREATE TABLE IF NOT EXISTS schema_migrations (
    name          TEXT PRIMARY KEY,
    applied_at    TEXT NOT NULL,
    detail        TEXT
);
"""

# Backend identity (Phase 5). `runtime` stays the generic runtime family ('mflux' for every task, as before); the
# `backend_id` column (added by migration so existing databases keep every row) names the exact backend, i.e. the
# `backend_id` of the immutable manifest that ran (or will run) the job. Rows written before the column existed
# (photo-gen <= v3) get theirs from their task: these were the only backends ever registered for each task, and the
# manifests' backend_id never changed (git log -S backend_id config/). Edit rows written after aa6d8aa already carry
# their backend_id in request_json and keep it.
LEGACY_BACKEND_IDS = {"text-to-image": "mflux-zimage-turbo-q4", "image-edit": "mflux-qwen-image-2.1-edit-q4"}

_ALLOWED = {
    JobStatus.QUEUED: {JobStatus.RUNNING, JobStatus.CANCELLED, JobStatus.FAILED},
    JobStatus.RUNNING: {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED},
}


class JobStore:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        with self._conn() as c:
            c.execute("PRAGMA journal_mode=WAL")
            c.executescript(SCHEMA)
            self._migrate(c)

    @staticmethod
    def _migrate(c: sqlite3.Connection) -> None:
        """Add and backfill the backend_id column. Idempotent and atomic (safe with the API server and a CLI process
        opening the same database); no existing column or row value is changed."""
        c.execute("BEGIN IMMEDIATE")
        try:
            if "backend_id" not in {r["name"] for r in c.execute("PRAGMA table_info(jobs)")}:
                c.execute("ALTER TABLE jobs ADD COLUMN backend_id TEXT")
            rows = c.execute("SELECT id, request_json FROM jobs WHERE backend_id IS NULL").fetchall()
            for r in rows:
                c.execute("UPDATE jobs SET backend_id=? WHERE id=?",
                          (legacy_backend_id(json.loads(r["request_json"])), r["id"]))
            c.execute("INSERT OR IGNORE INTO schema_migrations (name, applied_at, detail) VALUES (?,?,?)",
                      ("jobs.backend_id", utcnow(), json.dumps({"backfilled_rows": len(rows),
                                                                "rule": "request.backend_id, else by task",
                                                                "legacy_backend_ids": LEGACY_BACKEND_IDS})))
            c.execute("COMMIT")
        except BaseException:
            c.execute("ROLLBACK")
            raise

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path, timeout=30, isolation_level=None)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def create(self, job_id: str, source: str, owner_pid: int, runtime: str, request: dict, backend_id: str) -> dict:
        if not backend_id:
            raise ValueError("a job must name the backend that will run it")
        with self._lock, self._conn() as c:
            c.execute("INSERT INTO jobs (id, source, owner_pid, status, created_at, runtime, prompt, width, height,"
                      " steps, seed, request_json, backend_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (job_id, source, owner_pid, JobStatus.QUEUED.value, utcnow(), runtime, request["prompt"],
                       request["width"], request["height"], request["steps"], request["seed"], json.dumps(request),
                       backend_id))
        return self.get(job_id)

    def transition(self, job_id: str, new: JobStatus, **fields) -> dict:
        """Atomic compare-and-set status transition; raises ConflictError on an illegal transition."""
        with self._lock, self._conn() as c:
            c.execute("BEGIN IMMEDIATE")
            row = c.execute("SELECT status FROM jobs WHERE id=?", (job_id,)).fetchone()
            if row is None:
                c.execute("ROLLBACK")
                raise NotFoundError(f"job {job_id} not found")
            cur = JobStatus(row["status"])
            if new not in _ALLOWED.get(cur, set()):
                c.execute("ROLLBACK")
                raise ConflictError(f"job {job_id} is {cur.value}; cannot become {new.value}", status=cur.value)
            now = utcnow()
            cols = {"status": new.value, **fields}
            if new is JobStatus.RUNNING:
                cols["started_at"] = now
            if new.terminal:
                cols["finished_at"] = now
            for k in ("result_json", "error_json"):
                if k in cols and not isinstance(cols[k], str):
                    cols[k] = json.dumps(cols[k])
            sets = ", ".join(f"{k}=?" for k in cols)
            c.execute(f"UPDATE jobs SET {sets} WHERE id=?", (*cols.values(), job_id))
            c.execute("COMMIT")
        return self.get(job_id)

    def get(self, job_id: str) -> dict:
        with self._conn() as c:
            row = c.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"job {job_id} not found")
        return _row(row)

    def list(self, status: str | None = None, limit: int = 50, pixel_sha256: str | None = None) -> list[dict]:
        q, args = "SELECT * FROM jobs", []
        conds = []
        if status:
            conds.append("status=?")
            args.append(status)
        if pixel_sha256:
            conds.append("pixel_sha256=?")
            args.append(pixel_sha256)
        if conds:
            q += " WHERE " + " AND ".join(conds)
        q += " ORDER BY created_at DESC LIMIT ?"
        args.append(max(1, min(int(limit), 1000)))
        with self._conn() as c:
            return [_row(r) for r in c.execute(q, args).fetchall()]

    def count_active(self) -> int:
        with self._conn() as c:
            return c.execute("SELECT COUNT(*) FROM jobs WHERE status IN ('queued','running')").fetchone()[0]

    def queued_for_source(self, source: str) -> list[dict]:
        with self._conn() as c:
            rows = c.execute("SELECT * FROM jobs WHERE status='queued' AND source=? ORDER BY created_at",
                             (source,)).fetchall()
        return [_row(r) for r in rows]

    def running(self) -> list[dict]:
        return self.list(status=JobStatus.RUNNING.value, limit=100)

    def recent_completed(self, n: int) -> list[dict]:
        return self.list(status=JobStatus.COMPLETED.value, limit=n)


def legacy_backend_id(request: dict) -> str:
    """The backend of a row that predates the backend_id column (see LEGACY_BACKEND_IDS)."""
    return request.get("backend_id") or LEGACY_BACKEND_IDS[request.get("task") or "text-to-image"]


def _row(r: sqlite3.Row) -> dict:
    d = dict(r)
    for k in ("request_json", "result_json", "error_json"):
        v = d.pop(k)
        d[k[:-5]] = json.loads(v) if v else None
    if d.get("backend_id") is None:  # a row inserted later by pre-Phase-5 code (no backend_id column in its INSERT)
        d["backend_id"] = legacy_backend_id(d["request"] or {})
    return d
