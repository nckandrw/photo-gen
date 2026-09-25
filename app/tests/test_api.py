import http.client
import json
import threading
import unittest
from http.server import ThreadingHTTPServer

from helpers import FakeRuntime, temp_config
from photogen.api import make_handler
from photogen.service import PhotoGenService


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cfg = temp_config()
        cls.svc = PhotoGenService(cfg, runtime=FakeRuntime(cfg, delay=0.2))
        cls.svc.require_healthy()
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(cls.svc))
        cls.port = cls.httpd.server_address[1]
        cls.svc.jobs.start()
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.svc.jobs.stop()
        cls.httpd.shutdown()

    def req(self, method, path, body=None, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        h = {"Content-Type": "application/json"} if body is not None else {}
        h.update(headers or {})
        c.request(method, path, json.dumps(body) if body is not None else None, h)
        r = c.getresponse()
        data = r.read()
        ctype = r.getheader("Content-Type")
        c.close()
        return r.status, (json.loads(data) if ctype == "application/json" else data), ctype

    def test_health_status_capabilities(self):
        s, h, _ = self.req("GET", "/health")
        self.assertEqual(s, 200)
        self.assertEqual(h["model_revision"], "d2d30500c4bc0d19770bd952951df3e7c635ae9e")
        self.assertTrue(h["low_ram"])
        s, st, _ = self.req("GET", "/status")
        self.assertEqual(s, 200)
        for k in ("active_jobs", "queue_length", "recent_generation_seconds", "memory", "thermal"):
            self.assertIn(k, st)
        s, caps, _ = self.req("GET", "/capabilities")
        self.assertFalse(caps["supports_negative_prompt"])

    def test_generate_wait_and_fetch_output(self):
        s, job, _ = self.req("POST", "/generate", {"prompt": "apple", "width": 512, "height": 512, "seed": 42})
        self.assertEqual(s, 202)
        self.assertEqual(job["seed"], 42)
        s, done, _ = self.req("GET", f"/jobs/{job['job_id']}?wait=30")
        self.assertEqual(done["status"], "completed")
        self.assertEqual(len(done["pixel_sha256"]), 64)
        s, png, ctype = self.req("GET", f"/outputs/{job['job_id']}")
        self.assertEqual((s, ctype), (200, "image/png"))
        self.assertTrue(png.startswith(b"\x89PNG"))
        s, lst, _ = self.req("GET", f"/jobs?pixel_sha256={done['pixel_sha256']}")
        self.assertIn(job["job_id"], [j["job_id"] for j in lst["jobs"]])

    def test_rejections(self):
        s, e, _ = self.req("POST", "/generate", {"prompt": "x", "negative_prompt": "blurry"})
        self.assertEqual((s, e["error"]), (400, "unsupported_parameter"))
        s, e, _ = self.req("POST", "/generate", {"prompt": "x", "width": 4096, "height": 4096,
                                                 "allow_experimental": True})
        self.assertEqual(s, 400)
        s, e, _ = self.req("GET", "/jobs/nope")
        self.assertEqual(s, 404)
        s, e, _ = self.req("GET", "/outputs/nope")
        self.assertEqual(s, 404)

    def test_localhost_protections(self):
        c = http.client.HTTPConnection("127.0.0.1", self.port)
        c.request("GET", "/health", headers={"Host": "evil.example:80"})
        self.assertEqual(c.getresponse().status, 403)
        c.close()
        s, _, _ = self.req("POST", "/generate", {"prompt": "x"}, headers={"Origin": "https://evil.example"})
        self.assertEqual(s, 403)
        c = http.client.HTTPConnection("127.0.0.1", self.port)
        c.request("POST", "/generate", "prompt=x", {"Content-Type": "application/x-www-form-urlencoded"})
        self.assertEqual(c.getresponse().status, 415)
        c.close()

    def test_cancel_queued(self):
        ids = [self.req("POST", "/generate", {"prompt": f"p{i}", "width": 512, "height": 512})[1]["job_id"]
               for i in range(3)]
        s, j, _ = self.req("POST", f"/jobs/{ids[2]}/cancel", {})
        self.assertEqual((s, j["status"]), (200, "cancelled"))
        for i in ids[:2]:
            self.req("GET", f"/jobs/{i}?wait=30")


if __name__ == "__main__":
    unittest.main()
