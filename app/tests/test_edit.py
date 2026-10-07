"""Phase 4: the image-task layer (router), input staging, the Qwen image-edit backend's request contract, and
regression guards that Z-Image text-to-image behaviour is unchanged. No GPU and no Qwen venv needed (test doubles);
the one cross-check against mflux 0.21.0 itself is skipped when the edit venv is absent."""
import http.client
import json
import os
import shutil
import subprocess
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

from PIL import Image

from helpers import FakeEditRuntime, FakeRuntime, make_image, temp_config, wait_for
from photogen.api import make_handler, public_job
from photogen.cli import build_parser
from photogen.errors import (GenerationError, RuntimeUnavailableError, UnsupportedParameterError, ValidationError)
from photogen.inputs import stage_input_image, verify_staged
from photogen.jobs import JobManager
from photogen.runtimes.mflux_qwen_edit import MFluxQwenImageEditRuntime, output_dimensions
from photogen.service import PhotoGenService
from photogen.tasks import IMAGE_EDIT, TEXT_TO_IMAGE, TaskRouter

ROOT = Path(__file__).resolve().parents[2]
DEFAULTS = {"width": 1024, "height": 1024, "steps": 9, "seed": "random"}


def tmpdir() -> Path:
    return Path(tempfile.mkdtemp(prefix="photogen-edit-test-"))


class ZImageRegressionTests(unittest.TestCase):
    """The text-to-image sidecar, stored request and job row are byte-for-byte what the pre-Phase-4 code wrote."""

    def test_sidecars_match_pre_phase4_golden(self):
        golden = json.loads((Path(__file__).parent / "data" / "zimage-sidecar-golden.json").read_text())
        cases = {
            "default": {"prompt": "apple's \"core\"", "width": 512, "height": 512, "seed": 7},
            "fast": {"prompt": "apple", "seed": 7, "profile": "fast"},
            "bf16exp": {"prompt": "apple", "width": 512, "height": 512, "seed": 7, "precision": "bf16",
                        "allow_experimental": True},
            "named": {"prompt": "x", "width": 768, "height": 768, "seed": 1, "output_name": "my apple",
                      "profile": "reference"},
        }
        for name, params in cases.items():
            cfg = temp_config()
            jm = JobManager(cfg, FakeRuntime(cfg))
            done = jm.run_sync(jm.submit(params, source="cli")["id"])
            meta = json.loads(Path(done["metadata_path"]).read_text())
            g = golden["cases"][name]
            self.assertEqual(sorted(meta), g["sidecar_keys"], name)
            self.assertEqual({k: v for k, v in meta.items() if k not in golden["volatile"]}, g["sidecar"], name)
            self.assertEqual(done["request"], g["request"], name)
            # Phase 5 adds exactly one key to the job row: the backend_id column (the fixture is not regenerated)
            self.assertEqual(sorted(set(done) - {"backend_id"}), g["job_row_keys"], name)
            self.assertEqual(done["backend_id"], "mflux-zimage-turbo-q4", name)
            self.assertEqual(meta["schema"], "photogen.generation/1")

    def test_generate_still_rejects_image_parameters(self):
        rt = FakeRuntime(temp_config())
        for k in ("image", "images", "strength"):
            with self.assertRaises(UnsupportedParameterError, msg=k):
                rt.normalize({"prompt": "x", k: "a.png"}, DEFAULTS)
        with self.assertRaises(UnsupportedParameterError):
            rt.normalize({"prompt": "x", "task": IMAGE_EDIT}, DEFAULTS)


class RouterTests(unittest.TestCase):
    def test_explicit_routes(self):
        cfg = temp_config()
        t2i, edit = FakeRuntime(cfg), FakeEditRuntime(cfg)
        r = TaskRouter({TEXT_TO_IMAGE: t2i, IMAGE_EDIT: edit})
        self.assertIs(r.runtime_for(TEXT_TO_IMAGE), t2i)
        self.assertIs(r.runtime_for(IMAGE_EDIT), edit)
        self.assertIs(r.default, t2i)
        self.assertEqual(TaskRouter.task_of({}), TEXT_TO_IMAGE)          # old rows / requests without a task
        self.assertEqual(TaskRouter.task_of({"task": IMAGE_EDIT}), IMAGE_EDIT)
        with self.assertRaises(UnsupportedParameterError):
            r.runtime_for("image-to-image")                               # conceptual task, not implemented
        with self.assertRaises(ValueError):
            TaskRouter({IMAGE_EDIT: edit})                                # text-to-image is mandatory

    def test_bare_runtime_manager_has_no_edit_route(self):
        cfg = temp_config()
        jm = JobManager(cfg, FakeRuntime(cfg))
        with self.assertRaises(UnsupportedParameterError):
            jm.submit({"task": IMAGE_EDIT, "prompt": "x", "image": "/x.png", "allow_experimental": True}, "cli")

    def test_stored_row_without_task_runs_as_text_to_image(self):
        cfg = temp_config()
        t2i, edit = FakeRuntime(cfg), FakeEditRuntime(cfg)
        jm = JobManager(cfg, TaskRouter({TEXT_TO_IMAGE: t2i, IMAGE_EDIT: edit}))
        req = t2i.normalize({"prompt": "p", "width": 512, "height": 512, "seed": 3}, DEFAULTS).to_dict()
        del req["task"]                                                   # a row written before tasks existed
        jm.store.create("20260101T000000Z-aaaaaa", "cli", os.getpid(), "mflux", req, backend_id=t2i.backend_id)
        done = jm.run_sync("20260101T000000Z-aaaaaa")
        self.assertEqual(done["status"], "completed")
        self.assertEqual(public_job(done)["task"], TEXT_TO_IMAGE)


class InputStagingTests(unittest.TestCase):
    def setUp(self):
        self.src, self.inputs = tmpdir(), tmpdir() / "inputs"

    def stage(self, p):
        return stage_input_image(str(p), self.inputs)

    def test_png_jpeg_webp_staged_content_addressed(self):
        for fmt, ext in (("PNG", "png"), ("JPEG", "jpg"), ("WEBP", "webp")):
            p = make_image(self.src / f"a.{ext}", fmt=fmt, **({"quality": 95} if fmt != "PNG" else {}))
            inp, warn = self.stage(p)
            self.assertEqual((inp.source_format, inp.width, inp.height), (fmt, 256, 256))
            self.assertTrue(inp.staged_path.endswith(f"{inp.pixel_sha256}.png"))
            with Image.open(inp.staged_path) as im:
                self.assertEqual((im.mode, im.format), ("RGB", "PNG"))
                self.assertFalse({k for k in im.info if k not in ("dpi",)})  # no metadata chunks
            verify_staged(inp.staged_path, inp.pixel_sha256)
            self.assertEqual(warn, [])

    def test_same_pixels_same_identity_different_file_bytes(self):
        a = make_image(self.src / "a.png")
        b = make_image(self.src / "b.png", pnginfo=None, compress_level=1)  # different bytes, same pixels
        ia, ib = self.stage(a)[0], self.stage(b)[0]
        self.assertEqual(ia.pixel_sha256, ib.pixel_sha256)
        self.assertEqual(ia.staged_path, ib.staged_path)
        self.assertNotEqual(ia.source_file_sha256, ib.source_file_sha256)

    def test_exif_orientation_applied(self):
        img = Image.open(make_image(self.src / "w.png", size=(320, 200)))
        exif = Image.Exif()
        exif[0x0112] = 6  # rotate 90° CW on display
        img.save(self.src / "rot.jpg", format="JPEG", exif=exif.tobytes(), quality=95)
        inp, _ = self.stage(self.src / "rot.jpg")
        self.assertEqual((inp.width, inp.height, inp.exif_orientation), (200, 320, 6))

    def test_alpha_policy(self):
        opaque = make_image(self.src / "o.png", mode="RGBA")
        inp, _ = self.stage(opaque)
        self.assertTrue(inp.alpha_dropped)
        self.assertEqual(inp.pixel_sha256, self.stage(make_image(self.src / "o2.png"))[0].pixel_sha256)
        img = Image.open(opaque).copy()
        img.putpixel((0, 0), (1, 2, 3, 0))
        img.save(self.src / "t.png")
        with self.assertRaises(ValidationError):
            self.stage(self.src / "t.png")

    def test_rejections(self):
        make_image(self.src / "ok.png")
        cases = {
            "relative": "ok.png",
            "missing": str(self.src / "nope.png"),
            "directory": str(self.src),
            "not an image": str(self._write(self.src / "x.png", b"\x89PNG\r\n\x1a\nnot really")),
            "empty": str(self._write(self.src / "e.png", b"")),
            "gif": str(make_image(self.src / "g.gif", fmt="GIF")),
            "too small": str(make_image(self.src / "s.png", size=(32, 32))),
            "16-bit": str(self._sixteen_bit()),
        }
        for why, p in cases.items():
            with self.assertRaises(ValidationError, msg=why):
                stage_input_image(p, self.inputs)
        with self.assertRaises(ValidationError):
            stage_input_image(None, self.inputs)

    def test_symlink_resolved_and_icc_warned(self):
        target = make_image(self.src / "real.png", icc_profile=b"fake-icc-profile")
        link = self.src / "link.png"
        link.symlink_to(target)
        inp, warn = self.stage(link)
        self.assertEqual(inp.source_path, str(target.resolve()))
        self.assertTrue(inp.icc_profile)
        self.assertTrue(any("ICC" in w for w in warn))

    def test_tampered_staged_input_detected(self):
        inp, _ = self.stage(make_image(self.src / "a.png"))
        Image.new("RGB", (256, 256), (1, 1, 1)).save(inp.staged_path)
        with self.assertRaises(GenerationError):
            verify_staged(inp.staged_path, inp.pixel_sha256)

    def _write(self, p: Path, data: bytes) -> Path:
        p.write_bytes(data)
        return p

    def _sixteen_bit(self) -> Path:
        p = self.src / "i16.png"
        Image.new("I;16", (128, 128), 1000).save(p)
        return p


class EditRequestTests(unittest.TestCase):
    def setUp(self):
        self.cfg = temp_config()
        self.rt = FakeEditRuntime(self.cfg)
        self.img = str(make_image(tmpdir() / "src.png", size=(512, 512)))

    def n(self, **p):
        return self.rt.normalize({"task": IMAGE_EDIT, "prompt": "make it blue", "image": self.img,
                                  "allow_experimental": True, **p}, DEFAULTS)

    def test_upstream_defaults_and_experimental(self):
        r = self.n(seed=42)
        self.assertEqual((r.task, r.width, r.height, r.steps, r.output_resolution, r.seed, r.seed_source),
                         (IMAGE_EDIT, 1024, 1024, 40, 1024, 42, "explicit"))
        self.assertFalse(r.validated)
        self.assertTrue(any("EXPERIMENTAL" in w for w in r.warnings))
        self.assertEqual(r.input_image["width"], 512)
        self.assertEqual((r.backend_id, r.model), ("test-qwen-edit", "Qwen-Image-2.1"))  # known while queued
        with self.assertRaises(ValidationError):  # every edit needs the explicit opt-in
            self.rt.normalize({"task": IMAGE_EDIT, "prompt": "x", "image": self.img}, DEFAULTS)

    def test_worker_request_carries_adopted_memory_policy(self):
        """Phase 5 gate (research/qwen/QWEN-MEMORY-LIFETIME.md): all three lifetime patches are production defaults,
        and nothing else in the worker request changed (the configuration identity does not include them)."""
        r = self.n(seed=42, output_resolution=512)
        req = self.rt._worker_request(r, "/tmp/out.png")
        self.assertEqual({k: req[k] for k in ("defer_transformer_load", "release_text_encoder_after_encode",
                                              "release_vae_during_denoise")},
                         {"defer_transformer_load": True, "release_text_encoder_after_encode": True,
                          "release_vae_during_denoise": True})
        self.assertEqual(sorted(req), sorted(["model_path", "base_model", "prompt", "image_path", "seed", "steps",
                                              "output_resolution", "output_path", "defer_transformer_load",
                                              "release_text_encoder_after_encode", "release_vae_during_denoise",
                                              "expected_size"]))
        self.assertEqual((req["seed"], req["steps"], req["output_resolution"], req["expected_size"]),
                         (42, 40, 512, [512, 512]))
        self.assertNotIn("memory", json.dumps(self.rt.configuration(r)))

    def test_output_size_follows_input_aspect(self):
        img = str(make_image(tmpdir() / "wide.png", size=(600, 400)))
        r = self.n(image=img, output_resolution=1024)
        self.assertEqual((r.width, r.height), output_dimensions(1024, 1.5))
        self.assertEqual((r.width % 32, r.height % 32), (0, 0))
        square = self.n(output_resolution=512)
        self.assertEqual((square.width, square.height), (512, 512))

    def test_output_dimensions_formula(self):
        self.assertEqual(output_dimensions(1024, 1.0), (1024, 1024))
        self.assertEqual(output_dimensions(1024, 1.5), (1248, 832))
        self.assertEqual(output_dimensions(512, 0.75), (448, 576))
        self.assertEqual(output_dimensions(384, 1.0), (384, 384))

    def test_rejected_parameters_are_explicit(self):
        for k, v in (("negative_prompt", "blurry"), ("guidance", 2.5), ("true_cfg_scale", 4.0), ("scheduler", "x"),
                     ("width", 512), ("height", 512), ("mask_image", "/m.png"), ("auto_mask", "shirt"),
                     ("strength", 0.6), ("enhance_prompt", True), ("verify", True), ("use_step_cache", True),
                     ("use_kv_cache", False), ("images", ["/a", "/b"]), ("lora", "x"), ("profile", "fast"),
                     ("precision", "bf16"), ("model", "qwen-edit-2511"), ("low_ram", False)):
            with self.assertRaises(UnsupportedParameterError, msg=k):
                self.n(**{k: v})
        with self.assertRaises(UnsupportedParameterError):
            self.n(temperature=1)
        self.assertFalse(self.n(low_ram=True).validated)  # the enforced value is accepted

    def test_bounds(self):
        for k, v in (("output_resolution", 1056), ("output_resolution", 352), ("output_resolution", 1000),
                     ("steps", 1), ("steps", 61), ("seed", -1), ("prompt", "  "), ("output_name", "../x"),
                     ("output_format", "jpg")):
            with self.assertRaises((ValidationError, UnsupportedParameterError), msg=(k, v)):
                self.n(**{k: v})
        with self.assertRaises(ValidationError):
            self.rt.normalize({"task": IMAGE_EDIT, "prompt": "x", "allow_experimental": True}, DEFAULTS)  # no image

    def test_missing_backend_is_503_not_a_crash(self):
        rt = MFluxQwenImageEditRuntime(self.cfg, manifest_path=tmpdir() / "absent.json")
        self.assertFalse(rt.health().ok)
        self.assertEqual(rt.capabilities().supported_tasks, (IMAGE_EDIT,))
        with self.assertRaises(RuntimeUnavailableError):
            rt.normalize({"task": IMAGE_EDIT, "prompt": "x", "image": self.img, "allow_experimental": True}, DEFAULTS)

    def test_dimensions_match_mflux_021(self):
        """Cross-check output_dimensions against mflux 0.21.0 itself (skipped without the edit venv)."""
        py = ROOT / "mflux-qwen" / ".venv" / "bin" / "python3.12"
        if not py.is_file():
            self.skipTest("edit venv not installed")
        grid = [(r, w, h) for r in (384, 512, 768, 1024) for (w, h) in
                ((1, 1), (3, 2), (2, 3), (4, 3), (16, 9), (9, 16), (1000, 999), (640, 427), (7, 5))]
        code = ("import json,sys;from mflux.models.qwen21.latent_creator.qwen_image21_latent_creator import "
                "QwenImage21LatentCreator as L;g=json.loads(sys.argv[1]);"
                "print(json.dumps([list(L.dimensions(r,w/h)) for r,w,h in g]))")
        out = subprocess.run([str(py), "-c", code, json.dumps(grid)], capture_output=True, text=True, timeout=120,
                             env={"PATH": "/usr/bin:/bin", "HF_HUB_OFFLINE": "1"})
        self.assertEqual(out.returncode, 0, out.stderr[-2000:])
        self.assertEqual(json.loads(out.stdout), [list(output_dimensions(r, w / h)) for r, w, h in grid])


class EditJobTests(unittest.TestCase):
    def make(self, **kw):
        cfg = temp_config()
        t2i = FakeRuntime(cfg, delay=kw.pop("t2i_delay", 0.0))
        edit = FakeEditRuntime(cfg, counter=t2i, **kw)
        return cfg, t2i, edit, JobManager(cfg, TaskRouter({TEXT_TO_IMAGE: t2i, IMAGE_EDIT: edit}))

    def test_edit_job_metadata_and_identity(self):
        cfg, t2i, edit, jm = self.make()
        img = make_image(tmpdir() / "src.png", size=(640, 427))
        job = jm.submit({"task": IMAGE_EDIT, "prompt": "turn the square red", "image": str(img), "seed": 5,
                         "output_resolution": 512, "allow_experimental": True}, source="cli")
        self.assertEqual(job["runtime"], "mflux")
        done = jm.run_sync(job["id"])
        self.assertEqual(done["status"], "completed", done["error"])
        meta = json.loads(Path(done["metadata_path"]).read_text())
        self.assertEqual(meta["schema"], "photogen.edit/1")
        for k in ("task", "model", "model_revision", "model_license", "runtime", "runtime_version", "backend_id",
                  "backend_status", "input_image", "prompt", "seed", "output_resolution", "width", "height", "steps",
                  "scheduler", "guidance", "use_kv_cache", "adapters", "pixel_sha256", "file_sha256", "output_alpha",
                  "determinism", "validated_configuration", "reproduce", "system_before", "system_after"):
            self.assertIn(k, meta)
        self.assertEqual((meta["task"], meta["seed"], meta["validated_configuration"]), (IMAGE_EDIT, 5, False))
        self.assertEqual(meta["input_image"]["source_file_sha256"], __import__("hashlib").sha256(
            img.read_bytes()).hexdigest())
        self.assertEqual((meta["width"], meta["height"]), output_dimensions(512, 640 / 427))
        self.assertEqual(meta["output_alpha"]["mode"], "RGBA")
        self.assertEqual(meta["model_manifest"]["sha256"],
                         __import__("hashlib").sha256(edit.manifest_path.read_bytes()).hexdigest())
        self.assertEqual(done["request"]["backend_id"], "test-qwen-edit")
        self.assertTrue(meta["output_alpha"]["opaque"])
        self.assertIn("bin/photo-gen edit --image", meta["reproduce"]["cli"])
        self.assertIn("--allow-experimental", meta["reproduce"]["cli"])
        pj = public_job(done)
        self.assertEqual((pj["task"], pj["request"]["input_image"]["pixel_sha256"]),
                         (IMAGE_EDIT, meta["input_image"]["pixel_sha256"]))

    def test_generation_and_editing_share_one_queue(self):
        cfg, t2i, edit, jm = self.make(delay=0.3, t2i_delay=0.3)
        img = str(make_image(tmpdir() / "src.png"))
        jm.start()
        ids = [jm.submit({"prompt": "a", "width": 512, "height": 512})["id"],
               jm.submit({"task": IMAGE_EDIT, "prompt": "b", "image": img, "allow_experimental": True,
                          "output_resolution": 512})["id"],
               jm.submit({"prompt": "c", "width": 512, "height": 512})["id"],
               jm.submit({"task": IMAGE_EDIT, "prompt": "d", "image": img, "allow_experimental": True,
                          "output_resolution": 512})["id"]]
        self.assertTrue(wait_for(lambda: all(jm.store.get(i)["status"] == "completed" for i in ids), 20))
        self.assertEqual(t2i.max_active, 1)  # never a generation and an edit at the same time
        jm.stop()

    def test_cancel_queued_and_running_edit(self):
        cfg, t2i, edit, jm = self.make(delay=1.0)
        img = str(make_image(tmpdir() / "src.png"))
        jm.start()
        p = {"task": IMAGE_EDIT, "prompt": "x", "image": img, "allow_experimental": True, "output_resolution": 512}
        a, b = jm.submit(dict(p))["id"], jm.submit(dict(p))["id"]
        jm.cancel(b)
        self.assertEqual(jm.store.get(b)["status"], "cancelled")
        self.assertTrue(wait_for(lambda: jm.store.get(a)["status"] == "running"))
        jm.cancel(a)
        self.assertTrue(wait_for(lambda: jm.store.get(a)["status"] == "cancelled"))
        jm.stop()

    def test_staged_input_tamper_fails_job(self):
        cfg, t2i, edit, jm = self.make()
        img = make_image(tmpdir() / "src.png")
        job = jm.submit({"task": IMAGE_EDIT, "prompt": "x", "image": str(img), "allow_experimental": True,
                         "output_resolution": 512}, "cli")
        Image.new("RGB", (256, 256), (9, 9, 9)).save(job["request"]["input_image"]["staged_path"])

        real = edit.generate

        def checked(job_id, request, *a):
            verify_staged(request.input_image["staged_path"], request.input_image["pixel_sha256"])
            return real(job_id, request, *a)
        edit.generate = checked
        done = jm.run_sync(job["id"])
        self.assertEqual(done["status"], "failed")


class ServiceAndApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cfg = temp_config()
        cls.svc = PhotoGenService(cfg, runtime=FakeRuntime(cfg, delay=0.1), edit_runtime=FakeEditRuntime(cfg))
        cls.svc.require_healthy()
        cls.svc.verify_edit()
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(cls.svc))
        cls.port = cls.httpd.server_address[1]
        cls.svc.jobs.start()
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        cls.img = str(make_image(tmpdir() / "src.png", size=(320, 320)))

    @classmethod
    def tearDownClass(cls):
        cls.svc.jobs.stop()
        cls.httpd.shutdown()

    def req(self, method, path, body=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        c.request(method, path, json.dumps(body) if body is not None else None,
                  {"Content-Type": "application/json"} if body is not None else {})
        r = c.getresponse()
        data = r.read()
        c.close()
        return r.status, (json.loads(data) if r.getheader("Content-Type") == "application/json" else data)

    def test_post_edit_end_to_end(self):
        s, job = self.req("POST", "/edit", {"image": self.img, "prompt": "add a hat", "seed": 1,
                                            "output_resolution": 384, "allow_experimental": True})
        self.assertEqual(s, 202, job)
        self.assertEqual(job["task"], IMAGE_EDIT)
        s, done = self.req("GET", f"/jobs/{job['job_id']}?wait=30")
        self.assertEqual(done["status"], "completed", done)
        self.assertEqual(done["task"], IMAGE_EDIT)
        s, png = self.req("GET", f"/outputs/{job['job_id']}")
        self.assertTrue(png.startswith(b"\x89PNG"))

    def test_task_endpoints_are_explicit(self):
        s, e = self.req("POST", "/generate", {"prompt": "x", "task": IMAGE_EDIT, "image": self.img})
        self.assertEqual((s, e["error"]), (400, "unsupported_parameter"))
        s, e = self.req("POST", "/edit", {"prompt": "x", "task": TEXT_TO_IMAGE, "image": self.img})
        self.assertEqual((s, e["error"]), (400, "unsupported_parameter"))
        s, e = self.req("POST", "/edit", {"prompt": "x", "image": self.img})  # no allow_experimental
        self.assertEqual((s, e["error"]), (400, "invalid_request"))
        s, e = self.req("POST", "/edit", {"prompt": "x", "image": "relative.png", "allow_experimental": True})
        self.assertEqual(s, 400)
        s, e = self.req("POST", "/edit", {"prompt": "x", "image": self.img, "guidance": 4.0,
                                          "allow_experimental": True})
        self.assertEqual((s, e["error"]), (400, "unsupported_parameter"))
        s, job = self.req("POST", "/generate", {"prompt": "x", "width": 512, "height": 512})
        self.assertEqual((s, job["task"]), (202, TEXT_TO_IMAGE))

    def test_capabilities_and_health_are_additive(self):
        s, caps = self.req("GET", "/capabilities")
        for k in ("runtime", "supported_tasks", "validated_resolutions", "profiles", "precisions"):
            self.assertIn(k, caps)  # the original text-to-image capability document is unchanged
        self.assertEqual(caps["supported_tasks"], [TEXT_TO_IMAGE])
        self.assertEqual(set(caps["tasks"]), {TEXT_TO_IMAGE, IMAGE_EDIT})
        self.assertEqual(caps["tasks"][IMAGE_EDIT]["endpoint"], "POST /edit")
        self.assertEqual(caps["tasks"][IMAGE_EDIT]["status"], "experimental")
        s, h = self.req("GET", "/health")
        self.assertEqual((s, h["service"]), (200, "ok"))
        self.assertTrue(h["backends"][IMAGE_EDIT]["ok"])

    def test_unhealthy_edit_backend_never_degrades_generation(self):
        cfg = temp_config()
        svc = PhotoGenService(cfg, runtime=FakeRuntime(cfg), edit_runtime=FakeEditRuntime(cfg, healthy=False))
        svc.require_healthy()
        svc.verify_edit()
        self.assertEqual(svc.health()["service"], "ok")
        self.assertFalse(svc.health()["backends"][IMAGE_EDIT]["ok"])
        with self.assertRaises(RuntimeUnavailableError):
            svc.require_edit_healthy(cached=True)
        done = svc.jobs.run_sync(svc.jobs.submit({"prompt": "x", "width": 512, "height": 512}, "cli")["id"])
        self.assertEqual(done["status"], "completed")
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(svc))
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        c = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=10)
        c.request("POST", "/edit", json.dumps({"prompt": "x", "image": self.img, "allow_experimental": True}),
                  {"Content-Type": "application/json"})
        self.assertEqual(c.getresponse().status, 503)
        httpd.shutdown()


class CliTests(unittest.TestCase):
    def test_edit_command_contract(self):
        p = build_parser()
        a = p.parse_args(["edit", "--image", "in.png", "-p", "make it blue", "--seed", "3", "--allow-experimental"])
        self.assertEqual((a.cmd, a.image, a.prompt, a.seed, a.allow_experimental), ("edit", "in.png", "make it blue",
                                                                                   3, True))
        for missing in (["edit", "-p", "x"], ["edit", "--image", "a.png"]):
            with self.assertRaises(SystemExit):
                p.parse_args(missing)
        g = p.parse_args(["generate", "-p", "x", "--profile", "balanced"])  # unchanged
        self.assertEqual((g.cmd, g.profile), ("generate", "balanced"))


class ProductionManifestTests(unittest.TestCase):
    def test_edit_manifest_pins(self):
        path = ROOT / "config" / "backend-qwen21-edit-mflux.json"
        if not path.exists():
            self.skipTest("edit backend manifest not created yet")
        m = json.loads(path.read_text())
        self.assertEqual(m["status"], "experimental")
        self.assertEqual(m["runtime"]["packages"]["mflux"], "0.21.0")
        self.assertEqual(m["runtime"]["packages"]["mlx"], "0.32.2")
        self.assertEqual(m["runtime"]["interpreter"], "mflux-qwen/.venv/bin/python3.12")
        self.assertEqual(m["model"]["revision"], "d26bb61231c349cf6b7896fa83353113880e1ba3")
        self.assertIn("Qwen Research License", m["model"]["license"])
        self.assertEqual((m["defaults"]["steps"], m["defaults"]["guidance"]), (40, 1.0))
        self.assertTrue(m["model"]["files"])
        self.assertEqual(m["validated"]["combinations"], [])  # nothing is gated yet

    def test_production_venv_untouched(self):
        """The Z-Image interpreter must stay on mflux 0.20.0 (0.21.0 changes the REFERENCE hashes)."""
        import importlib.metadata as md
        self.assertEqual(md.version("mflux"), "0.20.0")
        self.assertEqual(md.version("mlx"), "0.32.2")


if __name__ == "__main__":
    unittest.main()
