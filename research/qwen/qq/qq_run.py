"""Phase 6 Q-Q: run the PRODUCTION edit worker (photogen.runtimes.mflux_qwen_edit_worker) directly with the production
environment, arguments and adopted memory policy P2, changing ONLY the model export it loads (research/qwen/qq/PROTOCOL.md
§2). Like research/qwen/memory/mem_run.py (Phase 5), which reproduced the production path's pixels exactly.
Run with the production interpreter (it only launches the edit venv).

Usage: mflux/.venv/bin/python3.12 research/qwen/qq/qq_run.py <out_dir> <staged_image> <res> <seed> <prompt> <q4|q8> [steps]
  q4 = the canonical, manifest-pinned export (config/backend-qwen21-edit-mflux.json)
  q8 = the Phase 6 research export models/research/qwen-image-2.1-edit-mflux-q8 (identity: qq/export/merge-q8.json)
Writes <out_dir>/{worker-request.json, worker-result.json, worker.log, out.png, identity.json}."""
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "app"))
from photogen.config import AppConfig  # noqa: E402
from photogen.imaging import inspect_image  # noqa: E402
from photogen.runtimes.mflux_qwen_edit import (WORKER_MODULE, WORKER_PATH, QwenEditManifest,  # noqa: E402
                                               _alpha_identity, _worker_env)

P2 = {"defer_transformer_load": True, "release_text_encoder_after_encode": True, "release_vae_during_denoise": True}
Q8 = ROOT / "models/research/qwen-image-2.1-edit-mflux-q8"
Q8_RECORD = ROOT / "research/qwen/qq/export/merge-q8.json"

out, image, res, seed, prompt, arm = sys.argv[1:7]
steps = int(sys.argv[7]) if len(sys.argv) > 7 else 40
out = Path(out).resolve()  # the worker runs with cwd=out, so every path it receives must be absolute
out.mkdir(parents=True, exist_ok=True)
cfg = AppConfig.load()
m = QwenEditManifest.load(ROOT / "config" / "backend-qwen21-edit-mflux.json", ROOT)
model_path = {"q4": m.model_path, "q8": Q8}[arm]
req = {"model_path": str(model_path), "base_model": m.defaults["base_model"], "prompt": prompt, "image_path": image,
       "seed": int(seed), "steps": steps, "output_resolution": int(res), "output_path": str(out / "out.png"), **P2}
(out / "worker-request.json").write_text(json.dumps(req, indent=1))
t0 = time.perf_counter()
with (out / "worker.log").open("wb") as lf:
    rc = subprocess.run([str(m.interpreter), "-m", WORKER_MODULE, str(out / "worker-request.json"),
                         str(out / "worker-result.json")], stdout=lf, stderr=subprocess.STDOUT, env=_worker_env(cfg),
                        cwd=str(out)).returncode
wall = round(time.perf_counter() - t0, 3)
ident = inspect_image(out / "out.png") if (out / "out.png").exists() else None
r = json.loads((out / "worker-result.json").read_text()) if (out / "worker-result.json").exists() else {}
identity = {"rc": rc, "wall_seconds": wall, "arm": arm, "model_path": str(model_path.relative_to(ROOT)),
            "model_identity": ({"manifest": "config/backend-qwen21-edit-mflux.json",
                                "manifest_sha256": hashlib.sha256((ROOT / "config/backend-qwen21-edit-mflux.json")
                                                                  .read_bytes()).hexdigest()} if arm == "q4" else
                               {"record": str(Q8_RECORD.relative_to(ROOT)),
                                "record_sha256": hashlib.sha256(Q8_RECORD.read_bytes()).hexdigest()
                                if Q8_RECORD.exists() else None}),
            "policy_flags": P2, "worker_sha256": hashlib.sha256(WORKER_PATH.read_bytes()).hexdigest(),
            "pixel_sha256": ident.pixel_sha256 if ident else None, "size": [ident.width, ident.height] if ident else None,
            "output_alpha": _alpha_identity(out / "out.png") if ident else None,
            "peak_footprint_gb": r.get("peak_footprint_gb"), "mlx_peak_gb": r.get("mlx_peak_gb"),
            "denoise_mlx_peak_gb": r.get("denoise_mlx_peak_gb"), "denoise_active_gb_max": r.get("denoise_active_gb_max"),
            "active_gb": r.get("active_gb"), "footprint_gb": r.get("footprint_gb"), "phases": r.get("phases"),
            "step_seconds": r.get("step_seconds"), "memory_policy": r.get("memory_policy"),
            "deferred": r.get("defer_transformer_load"), "error": r.get("error")}
(out / "identity.json").write_text(json.dumps(identity, indent=1))
print(json.dumps({k: identity[k] for k in ("rc", "wall_seconds", "arm", "pixel_sha256", "peak_footprint_gb",
                                           "mlx_peak_gb")}))
sys.exit(rc)
