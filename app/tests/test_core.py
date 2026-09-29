import hashlib
import json
import os
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path

from PIL import Image, PngImagePlugin

from helpers import FakeRuntime, temp_config, wait_for
from photogen.config import AppConfig, BackendManifest
from photogen.errors import (ConfigError, ConflictError, OutputCorruptedError, UnsupportedParameterError,
                             ValidationError)
from photogen.imaging import check_output, inspect_image
from photogen.integrity import file_digest, verify_model_files
from photogen.jobs import JobManager
from photogen.models import JobStatus
from photogen.store import JobStore

DEFAULTS = {"width": 1024, "height": 1024, "steps": 9, "seed": "random"}


class ConfigTests(unittest.TestCase):
    def test_manifest_matches_validated_backend(self):
        m = BackendManifest.load()
        self.assertEqual(m.model_revision, "d2d30500c4bc0d19770bd952951df3e7c635ae9e")
        self.assertEqual(m.packages, {"mflux": "0.20.0", "mlx": "0.32.2", "mlx-metal": "0.32.2"})
        self.assertTrue(m.low_ram)
        self.assertEqual(m.validated_steps, 9)
        self.assertEqual(len(m.model_files), 11)

    def test_user_config_defaults_localhost(self):
        cfg = AppConfig.load()
        self.assertEqual(cfg.host, "127.0.0.1")
        self.assertTrue(cfg.host_is_loopback)

    def test_bad_seed_rejected(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write('[defaults]\nseed = "sometimes"\n')
        with self.assertRaises(ConfigError):
            AppConfig.load(f.name)


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.rt = FakeRuntime(temp_config())

    def n(self, **p):
        return self.rt.normalize({"prompt": "x", **p}, DEFAULTS)

    def test_validated_defaults(self):
        r = self.n(seed=42)
        self.assertEqual((r.width, r.height, r.steps, r.seed, r.seed_source), (1024, 1024, 9, 42, "explicit"))
        self.assertTrue(r.validated)

    def test_random_seed_recorded(self):
        r = self.n()
        self.assertEqual(r.seed_source, "random")
        self.assertTrue(0 <= r.seed <= 2**32 - 1)

    def test_rejects_unsupported_backend_parameters(self):
        for k, v in (("negative_prompt", "blurry"), ("guidance", 3.5), ("scheduler", "euler"),
                     ("low_ram", False), ("model", "other"), ("lora", "x"), ("image", "a.png")):
            with self.assertRaises(UnsupportedParameterError, msg=k):
                self.n(**{k: v})
        self.assertTrue(self.n(low_ram=True).validated)  # explicit True is the enforced value

    def test_precision_default_fp32_and_bf16_opt_in(self):
        self.assertEqual(self.n().precision, "fp32")
        r = self.n(precision="bf16")
        self.assertEqual(r.precision, "bf16")
        self.assertTrue(r.validated)
        for bad in ("fp16", "BF16", "", None, 16):
            with self.assertRaises(ValidationError, msg=repr(bad)):
                self.n(precision=bad)
        self.assertEqual(self.rt.capabilities().precisions, ("fp32", "bf16"))

    def test_text_encoder_default_stock_and_unregistered_rejected(self):
        self.assertEqual(self.n().text_encoder, "stock")
        self.assertEqual(self.n(text_encoder="stock").text_encoder, "stock")
        for bad in ("heretic-v2", "nope", "../x", 3):  # heretic-v2 is registered but disabled
            with self.assertRaises(ValidationError, msg=repr(bad)):
                self.n(text_encoder=bad)
        self.assertEqual(self.rt.capabilities().text_encoders[0], "stock")

    def test_text_encoder_registry_and_verification(self):
        from photogen.config import ModelFile
        from photogen.errors import RuntimeUnavailableError
        from photogen.integrity import file_digest
        from photogen.text_encoders import TextEncoderEntry, verify_entry
        tmp = Path(tempfile.mkdtemp())
        stock = tmp / "stock"
        for c in ("transformer", "vae", "tokenizer", "text_encoder"):
            (stock / c).mkdir(parents=True)
        te = tmp / "te"; te.mkdir(); (te / "0.safetensors").write_bytes(b"weights")
        comp = tmp / "comp"; comp.mkdir()
        for c in ("transformer", "vae", "tokenizer"):
            (comp / c).symlink_to(stock / c)
        (comp / "text_encoder").symlink_to(te)
        mf = ModelFile("0.safetensors", "sha256", file_digest(te / "0.safetensors", "sha256"), 7)
        entry = TextEncoderEntry("t", True, te.resolve(), comp, (mf,), {})
        self.assertIn("0.safetensors", verify_entry(entry, stock, tmp / "cache.json")["files"])
        (te / "0.safetensors").write_bytes(b"WEIGHTS")  # same size, different content
        with self.assertRaises(RuntimeUnavailableError):
            verify_entry(entry, stock, tmp / "cache2.json")
        (te / "0.safetensors").write_bytes(b"weights")
        (comp / "vae").unlink(); (comp / "vae").symlink_to(te)  # composite must share the stock vae
        with self.assertRaises(RuntimeUnavailableError):
            verify_entry(entry, stock, tmp / "cache3.json")

    def test_profiles(self):
        r = self.n(profile="reference")
        self.assertEqual((r.precision, r.steps, r.validated, r.profile), ("fp32", 9, True, "reference"))
        f = self.n(profile="fast")
        self.assertEqual((f.precision, f.steps, f.validated, f.profile), ("bf16", 8, True, "fast"))
        d = self.n()  # no profile: unchanged reference behaviour
        self.assertEqual((d.precision, d.steps, d.profile), ("fp32", 9, None))
        with self.assertRaises(ValidationError):
            self.n(profile="fast", steps=9)          # conflicting explicit parameter
        with self.assertRaises(ValidationError):
            self.n(profile="turbo")
        for w in (512, 768):                         # fast is gated at 512², 768² and 1024² (direct gates)
            g = self.n(profile="fast", width=w, height=w)
            self.assertEqual((g.precision, g.steps, g.validated, g.warnings), ("bf16", 8, True, ()))
        with self.assertRaises(ValidationError):     # other sizes stay experimental and need the flag
            self.n(profile="fast", width=640, height=640)
        e = self.n(profile="fast", width=640, height=640, allow_experimental=True)
        self.assertFalse(e.validated)
        with self.assertRaises(ValidationError):     # fp32 + 8 was never gated
            self.n(steps=8)
        self.assertTrue(self.n(precision="bf16", steps=8).validated)  # explicit equivalent of fast @1024
        self.assertIn("fast", self.rt.capabilities().profiles)

    def test_validated_matrix_is_exact(self):
        """Regression guard: validity applies to the exact (precision, steps, resolution) combination.
        A configuration never becomes valid because a nearby one was gated (research/experiments/STATUS.md)."""
        from photogen.runtimes.mflux_zimage import VALIDATED_COMBINATIONS
        three = ((512, 512), (768, 768), (1024, 1024))
        self.assertEqual(VALIDATED_COMBINATIONS, {("fp32", 9): three, ("bf16", 8): three, ("bf16", 9): ((1024, 1024),),
                                                  ("bf16", 4): ((512, 512),), ("bf16", 5): ((1024, 1024),)})
        for prec, steps in (("fp32", 9), ("bf16", 8)):
            for w in (512, 768, 1024):
                self.assertTrue(self.n(precision=prec, steps=steps, width=w, height=w).validated, (prec, steps, w))
        self.assertTrue(self.n(precision="bf16", steps=9).validated)          # gated vs fp32/9 at 1024² only
        for w in (512, 768):                                                  # bf16/9 was never gated here
            with self.assertRaises(ValidationError):
                self.n(precision="bf16", steps=9, width=w, height=w)
            r = self.n(precision="bf16", steps=9, width=w, height=w, allow_experimental=True)
            self.assertFalse(r.validated)
            self.assertTrue(any("validated only at 1024x1024" in x for x in r.warnings))
        for prec, steps in (("fp32", 8), ("fp32", 4), ("bf16", 7), ("bf16", 6)):  # never gated anywhere
            with self.assertRaises(ValidationError):
                self.n(precision=prec, steps=steps)
            self.assertFalse(self.n(precision=prec, steps=steps, allow_experimental=True).validated)

    def test_ultra_profile_gated_at_512_only(self):
        u = self.n(profile="ultra", width=512, height=512)
        self.assertEqual((u.precision, u.steps, u.validated, u.profile, u.warnings), ("bf16", 4, True, "ultra", ()))
        for w in (768, 1024):                               # REJECTED by the Stage A gate at these sizes
            with self.assertRaises(ValidationError):
                self.n(profile="ultra", width=w, height=w)
            e = self.n(profile="ultra", width=w, height=w, allow_experimental=True)
            self.assertFalse(e.validated)
            self.assertTrue(any("validated only at 512x512" in x for x in e.warnings))
        with self.assertRaises(ValidationError):
            self.n(profile="ultra")                         # default 1024x1024
        with self.assertRaises(ValidationError):
            self.n(profile="ultra", steps=5, width=512, height=512)  # a profile fixes its steps
        self.assertIn("ultra", self.rt.capabilities().profiles)

    def test_balanced_profile_gated_at_1024_only(self):
        b = self.n(profile="balanced")                      # default 1024x1024
        self.assertEqual((b.precision, b.steps, b.validated, b.profile, b.warnings), ("bf16", 5, True, "balanced", ()))
        self.assertTrue(self.n(precision="bf16", steps=5).validated)  # same exact combination without the profile name
        for w in (512, 768):                                # 768: not confirmed; 512: dominated by ULTRA
            with self.assertRaises(ValidationError):
                self.n(profile="balanced", width=w, height=w)
            e = self.n(profile="balanced", width=w, height=w, allow_experimental=True)
            self.assertFalse(e.validated)
            self.assertTrue(any("validated only at 1024x1024" in x for x in e.warnings))
        with self.assertRaises(ValidationError):
            self.n(profile="balanced", steps=8)             # a profile fixes its steps
        self.assertIn("balanced", self.rt.capabilities().profiles)

    def test_request_without_precision_loads_as_fp32(self):  # rows stored before the field existed
        from photogen.models import GenerationRequest
        d = self.n(seed=1).to_dict()
        del d["precision"]
        self.assertEqual(GenerationRequest.from_dict(d).precision, "fp32")

    def test_rejects_unknown_parameter(self):
        with self.assertRaises(UnsupportedParameterError):
            self.n(temperature=1)

    def test_prompt_required(self):
        with self.assertRaises(ValidationError):
            self.rt.normalize({"prompt": "  "}, DEFAULTS)

    def test_unvalidated_resolution_needs_flag_and_is_bounded(self):
        with self.assertRaises(ValidationError):
            self.n(width=640, height=640)
        r = self.n(width=640, height=640, allow_experimental=True)
        self.assertFalse(r.validated)
        self.assertTrue(r.warnings)
        with self.assertRaises(ValidationError):  # above the largest validated pixel count
            self.n(width=1536, height=1024, allow_experimental=True)
        with self.assertRaises(ValidationError):
            self.n(width=2048, height=2048, allow_experimental=True)
        with self.assertRaises(ValidationError):  # not a multiple of 16
            self.n(width=1000, height=1000, allow_experimental=True)

    def test_steps_other_than_validated_need_flag(self):
        with self.assertRaises(ValidationError):
            self.n(steps=4)
        self.assertFalse(self.n(steps=4, allow_experimental=True).validated)
        with self.assertRaises(ValidationError):
            self.n(steps=500, allow_experimental=True)

    def test_output_format_and_name(self):
        with self.assertRaises(UnsupportedParameterError):
            self.n(output_format="jpg")
        for bad in ("../x", "a/b", ".hidden"):
            with self.assertRaises(ValidationError):
                self.n(output_name=bad)
        self.assertEqual(self.n(output_name="apple").output_name, "apple")

    def test_type_errors(self):
        for bad in ({"width": "wide"}, {"seed": True}, {"seed": -1}, {"steps": 9.5}):
            with self.assertRaises(ValidationError, msg=bad):
                self.n(**bad)


class ImagingTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())

    def _img(self, name, color=(10, 20, 30), pattern=True, meta=None):
        im = Image.new("RGB", (64, 32), color)
        if pattern:
            for x in range(64):
                im.putpixel((x, x % 32), (x * 3, 200, 7))
        info = PngImagePlugin.PngInfo()
        for k, v in (meta or {}).items():
            info.add_text(k, v)
        p = self.dir / name
        im.save(p, pnginfo=info)
        return p, im

    def test_pixel_hash_is_raw_rgb_sha256(self):
        p, im = self._img("a.png")
        self.assertEqual(inspect_image(p).pixel_sha256, hashlib.sha256(im.tobytes()).hexdigest())

    def test_metadata_changes_file_hash_not_pixel_hash(self):
        a, _ = self._img("a.png", meta={"generation_time": "1.0"})
        b, _ = self._img("b.png", meta={"generation_time": "2.0"})
        ia, ib = inspect_image(a), inspect_image(b)
        self.assertEqual(ia.pixel_sha256, ib.pixel_sha256)
        self.assertNotEqual(ia.file_sha256, ib.file_sha256)

    def test_blank_and_wrong_size_and_corrupt_rejected(self):
        p, _ = self._img("blank.png", color=(255, 255, 255), pattern=False)
        with self.assertRaises(OutputCorruptedError):
            check_output(inspect_image(p), 64, 32)
        p, _ = self._img("ok.png")
        with self.assertRaises(OutputCorruptedError):
            check_output(inspect_image(p), 32, 32)
        bad = self.dir / "bad.png"
        bad.write_bytes(b"\x89PNG\r\n\x1a\nnot really")
        with self.assertRaises(OutputCorruptedError):
            inspect_image(bad)
        with self.assertRaises(OutputCorruptedError):
            inspect_image(self.dir / "missing.png")


class IntegrityTests(unittest.TestCase):
    def test_git_sha1_matches_git(self):
        p = Path(tempfile.mkdtemp()) / "f.json"
        p.write_text('{"a": 1}\n')
        git = subprocess.run(["git", "hash-object", str(p)], capture_output=True, text=True).stdout.strip()
        self.assertEqual(file_digest(p, "git-sha1"), git)

    def test_cache_detects_modification(self):
        root = Path(tempfile.mkdtemp())
        (root / "m").mkdir()
        f = root / "m" / "w.bin"
        f.write_bytes(b"abc" * 1000)
        digest = hashlib.sha256(f.read_bytes()).hexdigest()
        import dataclasses
        from photogen.config import ModelFile
        m = dataclasses.replace(BackendManifest.load(), model_path=root / "m",
                                model_files=(ModelFile("w.bin", "sha256", digest, f.stat().st_size),))
        cache = root / "cache.json"
        self.assertTrue(verify_model_files(m, cache)[0].hashed)
        self.assertFalse(verify_model_files(m, cache)[0].hashed)  # trusted from cache
        f.write_bytes(b"abd" * 1000)  # same size, different content, new mtime
        res = verify_model_files(m, cache)[0]
        self.assertFalse(res.ok)
        self.assertTrue(res.hashed)
        f.unlink()
        self.assertEqual(verify_model_files(m, cache)[0].detail, "missing")


class JobTests(unittest.TestCase):
    def make(self, **rt_kw):
        cfg = temp_config()
        rt = FakeRuntime(cfg, **rt_kw)
        return cfg, rt, JobManager(cfg, rt)

    def test_happy_path_and_metadata(self):
        cfg, rt, jm = self.make()
        job = jm.submit({"prompt": "apple", "width": 512, "height": 512, "seed": 7}, source="cli")
        self.assertEqual(job["status"], "queued")
        done = jm.run_sync(job["id"])
        self.assertEqual(done["status"], "completed")
        self.assertTrue(Path(done["output_path"]).is_file())
        meta = json.loads(Path(done["metadata_path"]).read_text())
        for k in ("timestamp", "job_id", "runtime", "runtime_version", "model", "model_revision", "prompt",
                  "negative_prompt", "width", "height", "steps", "guidance", "scheduler", "seed",
                  "generation_time_seconds", "status", "output_path", "pixel_sha256", "file_sha256"):
            self.assertIn(k, meta)
        self.assertEqual(meta["seed"], 7)
        self.assertEqual(meta["pixel_sha256"], done["pixel_sha256"])
        self.assertIn("--seed 7", meta["reproduce"]["cli"])
        self.assertEqual(meta["precision"], "fp32")
        self.assertEqual(meta["text_encoder"]["name"], "stock")
        self.assertNotIn("--precision", meta["reproduce"]["cli"])

    def test_bf16_recorded_in_metadata_and_repro(self):
        cfg, rt, jm = self.make()
        # bf16 + 9 at 512² is ungated: it runs only as an experimental request, and is recorded as such
        job = jm.submit({"prompt": "apple", "width": 512, "height": 512, "seed": 7, "precision": "bf16",
                         "allow_experimental": True}, source="cli")
        done = jm.run_sync(job["id"])
        meta = json.loads(Path(done["metadata_path"]).read_text())
        self.assertEqual(meta["precision"], "bf16")
        self.assertFalse(meta["validated_configuration"])
        self.assertIn("--precision bf16", meta["reproduce"]["cli"])
        self.assertIn("--allow-experimental", meta["reproduce"]["cli"])

    def test_fast_profile_metadata(self):
        cfg, rt, jm = self.make()
        job = jm.submit({"prompt": "apple", "seed": 7, "profile": "fast"}, source="cli")
        done = jm.run_sync(job["id"])
        meta = json.loads(Path(done["metadata_path"]).read_text())
        self.assertEqual((meta["profile"], meta["precision"], meta["steps"], meta["validated_configuration"]),
                         ("fast", "bf16", 8, True))
        self.assertIn("--profile fast", meta["reproduce"]["cli"])
        for k in ("runtime", "model", "scheduler", "width", "height", "seed"):
            self.assertIn(k, meta)

    def test_same_seed_same_pixels(self):
        cfg, rt, jm = self.make()
        a = jm.run_sync(jm.submit({"prompt": "p", "width": 512, "height": 512, "seed": 3}, "cli")["id"])
        b = jm.run_sync(jm.submit({"prompt": "p", "width": 512, "height": 512, "seed": 3}, "cli")["id"])
        self.assertEqual(a["pixel_sha256"], b["pixel_sha256"])

    def test_failure_and_blank_output_become_failed(self):
        for kw in ({"fail": True}, {"blank": True}):
            cfg, rt, jm = self.make(**kw)
            j = jm.run_sync(jm.submit({"prompt": "p", "width": 512, "height": 512}, "cli")["id"])
            self.assertEqual(j["status"], "failed", kw)
            self.assertIsNotNone(j["error"])

    def test_queue_one_at_a_time_and_cancel(self):
        cfg, rt, jm = self.make(delay=0.5)
        jm.start()
        ids = [jm.submit({"prompt": f"p{i}", "width": 512, "height": 512})["id"] for i in range(3)]
        self.assertTrue(wait_for(lambda: jm.store.get(ids[0])["status"] == "running"))
        jm.cancel(ids[2])  # queued -> cancelled
        self.assertEqual(jm.store.get(ids[2])["status"], "cancelled")
        self.assertTrue(wait_for(lambda: jm.store.get(ids[1])["status"] == "running"))
        jm.cancel(ids[1])  # running -> cancelled
        self.assertTrue(wait_for(lambda: jm.store.get(ids[1])["status"] == "cancelled"))
        self.assertEqual(jm.store.get(ids[0])["status"], "completed")
        self.assertEqual(rt.max_active, 1)
        with self.assertRaises(ConflictError):
            jm.cancel(ids[0])  # already terminal
        jm.stop()

    def test_illegal_transition(self):
        cfg, rt, jm = self.make()
        j = jm.submit({"prompt": "p", "width": 512, "height": 512}, "cli")
        jm.run_sync(j["id"])
        with self.assertRaises(ConflictError):
            jm.store.transition(j["id"], JobStatus.RUNNING)

    def test_recovery_marks_orphaned_running_job_failed(self):
        cfg, rt, jm = self.make()
        j = jm.submit({"prompt": "p", "width": 512, "height": 512}, "cli")
        jm.store.transition(j["id"], JobStatus.RUNNING, owner_pid=999999)  # a pid that is not alive
        jm2 = JobManager(cfg, rt)
        jm2._recover()
        self.assertEqual(jm2.store.get(j["id"])["status"], "failed")

    def test_gpu_lock_serializes_across_managers(self):
        cfg = temp_config()
        rt = FakeRuntime(cfg, delay=0.4)
        a, b = JobManager(cfg, rt), JobManager(cfg, rt)  # two "processes" sharing the lock file and DB
        ja = a.submit({"prompt": "a", "width": 512, "height": 512}, "cli")
        jb = b.submit({"prompt": "b", "width": 512, "height": 512}, "cli")
        t = threading.Thread(target=a.run_sync, args=(ja["id"],))
        t.start()
        time.sleep(0.05)
        b.run_sync(jb["id"])
        t.join()
        self.assertEqual(rt.max_active, 1)
        self.assertEqual({a.store.get(ja["id"])["status"], b.store.get(jb["id"])["status"]}, {"completed"})

    def test_queue_limit(self):
        cfg = temp_config(max_pending=2)
        jm = JobManager(cfg, FakeRuntime(cfg))
        jm.submit({"prompt": "a"})
        jm.submit({"prompt": "b"})
        from photogen.errors import QueueFullError
        with self.assertRaises(QueueFullError):
            jm.submit({"prompt": "c"})


if __name__ == "__main__":
    unittest.main()
