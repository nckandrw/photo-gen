"""Phase 5: explicit backend identity on job rows (SQLite migration), authoritative model identity stamped from the
trusted local manifest (never from the client), and the edit configuration identity (configuration_id / edit_id)
that makes an edit reproducible from its metadata. No GPU and no Qwen venv needed (test doubles)."""
import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from helpers import FakeEditRuntime, FakeRuntime, edit_manifest, make_image, temp_config
from photogen.api import public_job
from photogen.errors import IdentityMismatchError, UnsupportedParameterError
from photogen.jobs import JobManager
from photogen.runtimes.base import check_worker_versions
from photogen.runtimes.mflux_qwen_edit import canonical_sha256
from photogen.store import LEGACY_BACKEND_IDS, JobStore
from photogen.tasks import IMAGE_EDIT, TEXT_TO_IMAGE, TaskRouter

ROOT = Path(__file__).resolve().parents[2]
DEFAULTS = {"width": 1024, "height": 1024, "steps": 9, "seed": "random"}

# The jobs table exactly as photo-gen <= v3 created it (store.py at tag photo-gen-m5-16gb-v3).
V3_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY, source TEXT NOT NULL, owner_pid INTEGER, status TEXT NOT NULL, created_at TEXT NOT NULL,
    started_at TEXT, finished_at TEXT, runtime TEXT NOT NULL, prompt TEXT NOT NULL, width INTEGER NOT NULL,
    height INTEGER NOT NULL, steps INTEGER NOT NULL, seed INTEGER NOT NULL, request_json TEXT NOT NULL,
    result_json TEXT, error_json TEXT, output_path TEXT, metadata_path TEXT, pixel_sha256 TEXT,
    generation_seconds REAL
);
CREATE INDEX IF NOT EXISTS jobs_status ON jobs(status, created_at);
CREATE INDEX IF NOT EXISTS jobs_pixel ON jobs(pixel_sha256);
"""


def tmpdir() -> Path:
    return Path(tempfile.mkdtemp(prefix="photogen-identity-test-"))


def v3_insert(db: Path, job_id: str, request: dict, status="completed", pixel=None):
    c = sqlite3.connect(db)
    c.execute("INSERT INTO jobs (id, source, owner_pid, status, created_at, runtime, prompt, width, height, steps, seed,"
              " request_json, pixel_sha256) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
              (job_id, "cli", 1, status, "2026-10-01T00:00:00.000+00:00", "mflux", request["prompt"],
               request["width"], request["height"], request["steps"], request["seed"], json.dumps(request), pixel))
    c.commit()
    c.close()


class BackendIdMigrationTests(unittest.TestCase):
    def legacy_db(self) -> Path:
        db = tmpdir() / "photogen.sqlite3"
        c = sqlite3.connect(db)
        c.executescript(V3_SCHEMA)
        c.close()
        t2i = {"prompt": "apple", "width": 512, "height": 512, "steps": 9, "seed": 1}
        v3_insert(db, "a-pre-task", dict(t2i), pixel="aa")                     # a row from before tasks existed
        v3_insert(db, "b-t2i", {**t2i, "task": TEXT_TO_IMAGE}, pixel="bb")
        edit = {"prompt": "x", "width": 512, "height": 512, "steps": 40, "seed": 2, "task": IMAGE_EDIT}
        v3_insert(db, "c-edit-pre-aa6d8aa", dict(edit), pixel="cc")            # edit row without backend_id
        v3_insert(db, "d-edit", {**edit, "backend_id": "mflux-qwen-image-2.1-edit-q4"}, status="cancelled")
        return db

    def snapshot(self, db: Path) -> list:
        c = sqlite3.connect(db)
        c.row_factory = sqlite3.Row
        rows = [dict(r) for r in c.execute("SELECT * FROM jobs ORDER BY id")]
        c.close()
        return rows

    def test_existing_rows_preserved_and_backfilled(self):
        db = self.legacy_db()
        before = self.snapshot(db)
        store = JobStore(db)
        after = self.snapshot(db)
        self.assertEqual([{k: v for k, v in r.items() if k != "backend_id"} for r in after], before)  # nothing else
        self.assertEqual({r["id"]: r["backend_id"] for r in after}, {
            "a-pre-task": "mflux-zimage-turbo-q4", "b-t2i": "mflux-zimage-turbo-q4",
            "c-edit-pre-aa6d8aa": "mflux-qwen-image-2.1-edit-q4", "d-edit": "mflux-qwen-image-2.1-edit-q4"})
        self.assertEqual(store.get("a-pre-task")["pixel_sha256"], "aa")
        c = sqlite3.connect(db)
        name, detail = c.execute("SELECT name, detail FROM schema_migrations").fetchone()
        c.close()
        self.assertEqual((name, json.loads(detail)["backfilled_rows"]), ("jobs.backend_id", 4))

    def test_migration_idempotent(self):
        db = self.legacy_db()
        JobStore(db)
        first = self.snapshot(db)
        JobStore(db)
        self.assertEqual(self.snapshot(db), first)
        c = sqlite3.connect(db)
        self.assertEqual(c.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0], 1)
        c.close()

    def test_row_written_later_by_old_code_reads_with_derived_backend(self):
        db = self.legacy_db()
        store = JobStore(db)
        # pre-Phase-5 code still running against the migrated DB: its INSERT names no backend_id column
        v3_insert(db, "e-old-writer", {"prompt": "p", "width": 512, "height": 512, "steps": 9, "seed": 3,
                                       "task": IMAGE_EDIT})
        self.assertEqual(store.get("e-old-writer")["backend_id"], LEGACY_BACKEND_IDS[IMAGE_EDIT])

    def test_real_database_copy_migrates_without_loss(self):
        """The project's own job database (if present): every row survives and names a backend."""
        real = ROOT / "data" / "photogen.sqlite3"
        if not real.exists():
            self.skipTest("no local job database")
        db = tmpdir() / "copy.sqlite3"
        src = sqlite3.connect(real)
        dst = sqlite3.connect(db)
        src.backup(dst)
        src.close()
        dst.close()
        before = self.snapshot(db)
        JobStore(db)
        after = self.snapshot(db)
        self.assertEqual(len(after), len(before))
        self.assertEqual([{k: v for k, v in r.items() if k != "backend_id"} for r in after],
                         [{k: v for k, v in r.items() if k != "backend_id"} for r in before])
        self.assertTrue(all(r["backend_id"] in LEGACY_BACKEND_IDS.values() for r in after))

    def test_new_jobs_record_their_backend(self):
        cfg = temp_config()
        t2i, edit = FakeRuntime(cfg), FakeEditRuntime(cfg)
        jm = JobManager(cfg, TaskRouter({TEXT_TO_IMAGE: t2i, IMAGE_EDIT: edit}))
        a = jm.submit({"prompt": "p", "width": 512, "height": 512, "seed": 1}, "cli")
        b = jm.submit({"task": IMAGE_EDIT, "prompt": "x", "image": str(make_image(tmpdir() / "s.png")),
                       "output_resolution": 512, "allow_experimental": True}, "cli")
        self.assertEqual((a["backend_id"], b["backend_id"]), ("mflux-zimage-turbo-q4", "test-qwen-edit"))
        self.assertEqual((a["runtime"], b["runtime"]), ("mflux", "mflux"))  # legacy column unchanged
        self.assertEqual(public_job(jm.store.get(b["id"]))["backend_id"], "test-qwen-edit")


class AuthoritativeIdentityTests(unittest.TestCase):
    def make(self):
        cfg = temp_config()
        t2i, edit = FakeRuntime(cfg), FakeEditRuntime(cfg)
        return cfg, t2i, edit, JobManager(cfg, TaskRouter({TEXT_TO_IMAGE: t2i, IMAGE_EDIT: edit}))

    def edit_params(self, **kw):
        return {"task": IMAGE_EDIT, "prompt": "turn the square red", "image": str(make_image(tmpdir() / "s.png")),
                "seed": 5, "output_resolution": 512, "allow_experimental": True, **kw}

    def test_client_cannot_choose_identity(self):
        cfg, t2i, edit, jm = self.make()
        for k, v in (("model", "Qwen/Other"), ("model_revision", "deadbeef"), ("backend_id", "evil"),
                     ("manifest_sha256", "0" * 64)):
            with self.assertRaises(UnsupportedParameterError, msg=k):
                jm.submit(self.edit_params(**{k: v}), "cli")
        for k, v in (("model", "other"), ("backend_id", "evil"), ("model_revision", "x")):
            with self.assertRaises(UnsupportedParameterError, msg=k):
                jm.submit({"prompt": "p", "width": 512, "height": 512, k: v}, "cli")

    def test_submission_stamps_manifest_identity(self):
        cfg, t2i, edit, jm = self.make()
        job = jm.submit(self.edit_params(), "cli")
        m = edit.m
        self.assertEqual({k: job["request"][k] for k in ("backend_id", "model", "model_revision", "manifest_sha256")},
                         {"backend_id": m.backend_id, "model": m.model_name, "model_revision": m.model_revision,
                          "manifest_sha256": hashlib.sha256(edit.manifest_path.read_bytes()).hexdigest()})

    def tamper(self, jm, job_id, **request_changes):
        req = {**jm.store.get(job_id)["request"], **request_changes}
        c = sqlite3.connect(jm.store.db_path)
        c.execute("UPDATE jobs SET request_json=? WHERE id=?", (json.dumps(req), job_id))
        c.commit()
        c.close()

    def test_tampered_queued_row_fails_and_runs_nothing(self):
        for field, value in (("manifest_sha256", "0" * 64), ("model_revision", "deadbeef" * 5),
                             ("model", "Qwen-Image-Edit-2511"), ("backend_id", "some-other-backend")):
            cfg, t2i, edit, jm = self.make()
            calls = []
            orig = edit.generate
            edit.generate = lambda *a, **k: calls.append(1) or orig(*a, **k)
            job = jm.submit(self.edit_params(), "cli")
            self.tamper(jm, job["id"], **{field: value})
            done = jm.run_sync(job["id"])
            self.assertEqual(done["status"], "failed", field)
            self.assertEqual(done["error"]["error"], "backend_identity_mismatch", field)
            self.assertIn(field, done["error"]["details"]["drift"], field)
            self.assertEqual((calls, done["output_path"]), ([], None), field)

    def test_row_backend_column_must_match_router(self):
        cfg, t2i, edit, jm = self.make()
        job = jm.submit({"prompt": "p", "width": 512, "height": 512, "seed": 1}, "cli")
        c = sqlite3.connect(jm.store.db_path)
        c.execute("UPDATE jobs SET backend_id='another-t2i-backend' WHERE id=?", (job["id"],))
        c.commit()
        c.close()
        done = jm.run_sync(job["id"])
        self.assertEqual((done["status"], done["error"]["error"]), ("failed", "backend_identity_mismatch"))

    def test_legacy_edit_row_without_identity_fields_still_runs(self):
        cfg, t2i, edit, jm = self.make()
        job = jm.submit(self.edit_params(), "cli")
        req = jm.store.get(job["id"])["request"]
        for k in ("backend_id", "model", "model_revision", "manifest_sha256"):
            req.pop(k)                                   # an edit row written before aa6d8aa
        c = sqlite3.connect(jm.store.db_path)
        c.execute("UPDATE jobs SET request_json=? WHERE id=?", (json.dumps(req), job["id"]))
        c.commit()
        c.close()
        self.assertEqual(jm.run_sync(job["id"])["status"], "completed")

    def test_sidecar_identity_comes_from_manifest(self):
        cfg, t2i, edit, jm = self.make()
        done = jm.run_sync(jm.submit(self.edit_params(), "cli")["id"])
        meta = json.loads(Path(done["metadata_path"]).read_text())
        m = edit.m
        self.assertEqual((meta["backend_id"], meta["model"], meta["model_repo"], meta["model_revision"],
                          meta["model_license"], meta["quantization"]),
                         (m.backend_id, m.model_name, m.model_repo, m.model_revision, m.model_license, m.quantization))
        self.assertEqual(meta["configuration"]["model_manifest_sha256"], meta["model_manifest"]["sha256"])
        self.assertEqual(done["backend_id"], m.backend_id)

    def test_worker_version_drift_is_an_error(self):
        pinned = {"mflux": "0.21.0", "mlx": "0.32.2"}
        check_worker_versions({"mflux": "0.21.0", "mlx": "0.32.2", "torch": "2.13.0"}, pinned, "b")
        for reported in ({"mflux": "0.21.1", "mlx": "0.32.2"}, {"mflux": "0.21.0"}, None):
            with self.assertRaises(IdentityMismatchError):
                check_worker_versions(reported, pinned, "b")

    def test_zimage_result_carries_manifest_identity(self):
        """Z-Image: the row names the backend; the photogen.generation/1 sidecar stays byte-compatible (golden)."""
        cfg = temp_config()
        self.assertEqual(cfg.backend.sha256,
                         hashlib.sha256((ROOT / "config/backend-zimage-mflux.json").read_bytes()).hexdigest())
        self.assertEqual(cfg.backend.backend_id, "mflux-zimage-turbo-q4")


class ConfigurationIdentityTests(unittest.TestCase):
    def setUp(self):
        self.cfg = temp_config()
        self.edit = FakeEditRuntime(self.cfg)
        self.img = make_image(tmpdir() / "src.png", size=(640, 427))

    def norm(self, **kw):
        p = {"task": IMAGE_EDIT, "prompt": "turn the square red", "image": str(self.img), "seed": 5,
             "output_resolution": 512, "allow_experimental": True, **kw}
        return self.edit.normalize(p, DEFAULTS)

    def ids(self, req, rt=None):
        rt = rt or self.edit
        return canonical_sha256(rt.configuration(req)), canonical_sha256(rt.edit_identity(req))

    def test_ids_are_deterministic(self):
        self.assertEqual(self.ids(self.norm()), self.ids(self.norm()))

    def test_what_changes_which_id(self):
        base_cfg, base_edit = self.ids(self.norm())
        for kw in ({"steps": 20}, {"output_resolution": 1024}):
            c, e = self.ids(self.norm(**kw))
            self.assertNotEqual(c, base_cfg, kw)
            self.assertNotEqual(e, base_edit, kw)
        other = make_image(tmpdir() / "o.png", size=(640, 427), mode="L")
        for kw in ({"seed": 6}, {"prompt": "turn the square blue"}, {"image": str(other)}):
            c, e = self.ids(self.norm(**kw))
            self.assertEqual(c, base_cfg, kw)            # same configuration ...
            self.assertNotEqual(e, base_edit, kw)        # ... different edit

    def test_manifest_change_changes_configuration(self):
        root = tmpdir()
        path = edit_manifest(root)
        raw = json.loads(path.read_text())
        raw["runtime"]["packages"]["mflux"] = "0.21.1"
        path.write_text(json.dumps(raw))
        from photogen.runtimes.mflux_qwen_edit import MFluxQwenImageEditRuntime
        other = MFluxQwenImageEditRuntime(self.cfg, manifest_path=path)
        req = self.norm()
        self.assertNotEqual(self.ids(req)[0], self.ids(req, other)[0])

    def test_edit_id_depends_on_input_pixels_not_file_bytes(self):
        from PIL import Image
        a, b = tmpdir() / "a.png", tmpdir() / "b.png"
        make_image(a)
        Image.open(a).save(b, compress_level=0)  # same pixels, different file bytes
        self.assertNotEqual(hashlib.sha256(a.read_bytes()).digest(), hashlib.sha256(b.read_bytes()).digest())
        ra, rb = self.norm(image=str(a)), self.norm(image=str(b))
        self.assertNotEqual(ra.input_image["source_file_sha256"], rb.input_image["source_file_sha256"])
        self.assertEqual(self.ids(ra), self.ids(rb))

    def test_edit_is_reproducible_from_its_metadata(self):
        jm = JobManager(self.cfg, TaskRouter({TEXT_TO_IMAGE: FakeRuntime(self.cfg), IMAGE_EDIT: self.edit}))
        done = jm.run_sync(jm.submit({"task": IMAGE_EDIT, "prompt": "turn the square red", "image": str(self.img),
                                      "seed": 5, "output_resolution": 512, "allow_experimental": True}, "cli")["id"])
        meta = json.loads(Path(done["metadata_path"]).read_text())
        for k in ("configuration", "configuration_id", "edit_identity", "edit_id", "execution"):
            self.assertIn(k, meta)
        self.assertEqual(meta["configuration_id"], canonical_sha256(meta["configuration"]))
        self.assertEqual(meta["edit_id"], canonical_sha256(meta["edit_identity"]))
        c = meta["configuration"]
        self.assertEqual((c["steps"], c["output_resolution"], c["adapters"], c["use_kv_cache"], c["low_ram"]),
                         (40, 512, [], True, True))
        self.assertEqual(meta["edit_identity"]["input_pixel_sha256"], meta["input_image"]["pixel_sha256"])
        # rebuild the request from the sidecar alone (staged input + instruction + seed + steps + budget)
        again = jm.run_sync(jm.submit({"task": IMAGE_EDIT, "prompt": meta["prompt"],
                                       "image": meta["input_image"]["staged_path"], "seed": meta["seed"],
                                       "steps": c["steps"], "output_resolution": c["output_resolution"],
                                       "allow_experimental": True}, "cli")["id"])
        meta2 = json.loads(Path(again["metadata_path"]).read_text())
        self.assertEqual((meta2["configuration_id"], meta2["edit_id"], meta2["pixel_sha256"]),
                         (meta["configuration_id"], meta["edit_id"], meta["pixel_sha256"]))


if __name__ == "__main__":
    unittest.main()
