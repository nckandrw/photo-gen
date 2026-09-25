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
"""

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

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path, timeout=30, isolation_level=None)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def create(self, job_id: str, source: str, owner_pid: int, runtime: str, request: dict) -> dict:
        with self._lock, self._conn() as c:
            c.execute("INSERT INTO jobs (id, source, owner_pid, status, created_at, runtime, prompt, width, height,"
                      " steps, seed, request_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                      (job_id, source, owner_pid, JobStatus.QUEUED.value, utcnow(), runtime, request["prompt"],
                       request["width"], request["height"], request["steps"], request["seed"], json.dumps(request)))
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


def _row(r: sqlite3.Row) -> dict:
    d = dict(r)
    for k in ("request_json", "result_json", "error_json"):
        v = d.pop(k)
        d[k[:-5]] = json.loads(v) if v else None
    return d
