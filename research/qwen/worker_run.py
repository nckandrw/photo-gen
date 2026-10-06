"""Run the PRODUCTION edit worker (photogen.runtimes.mflux_qwen_edit_worker) directly, with the production
environment and arguments, toggling only `defer_transformer_load` (Phase 4 parity A/B). Like prod_runner.py for
Z-Image: no job system, same worker. Run with the production interpreter (it only launches the edit venv).

Usage: mflux/.venv/bin/python3.12 research/qwen/worker_run.py <out_dir> <staged_image> <res> <seed> <prompt> <defer 0|1> [steps]
Writes <out_dir>/{worker-request.json, worker-result.json, worker.log, out.png, identity.json}."""
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "app"))
from photogen.config import AppConfig  # noqa: E402
from photogen.imaging import inspect_image  # noqa: E402
from photogen.runtimes.mflux_qwen_edit import (WORKER_MODULE, QwenEditManifest, _alpha_identity,  # noqa: E402
                                               _worker_env)

out, image, res, seed, prompt, defer = sys.argv[1:7]
steps = int(sys.argv[7]) if len(sys.argv) > 7 else 40
out = Path(out).resolve()  # the worker runs with cwd=out, so every path it receives must be absolute
out.mkdir(parents=True, exist_ok=True)
cfg = AppConfig.load()
m = QwenEditManifest.load(ROOT / "config" / "backend-qwen21-edit-mflux.json", ROOT)
req = {"model_path": str(m.model_path), "base_model": m.defaults["base_model"], "prompt": prompt, "image_path": image,
       "seed": int(seed), "steps": steps, "output_resolution": int(res), "output_path": str(out / "out.png"),
       "defer_transformer_load": defer == "1"}
(out / "worker-request.json").write_text(json.dumps(req, indent=1))
t0 = time.perf_counter()
with (out / "worker.log").open("wb") as lf:
    rc = subprocess.run([str(m.interpreter), "-m", WORKER_MODULE, str(out / "worker-request.json"),
                         str(out / "worker-result.json")], stdout=lf, stderr=subprocess.STDOUT, env=_worker_env(cfg),
                        cwd=str(out)).returncode
wall = round(time.perf_counter() - t0, 3)
ident = inspect_image(out / "out.png") if (out / "out.png").exists() else None
res_json = json.loads((out / "worker-result.json").read_text()) if (out / "worker-result.json").exists() else {}
identity = {"rc": rc, "wall_seconds": wall, "defer_transformer_load": defer == "1",
            "pixel_sha256": ident.pixel_sha256 if ident else None, "size": [ident.width, ident.height] if ident else None,
            "output_alpha": _alpha_identity(out / "out.png") if ident else None,
            "peak_footprint_gb": res_json.get("peak_footprint_gb"), "mlx_peak_gb": res_json.get("mlx_peak_gb"),
            "denoise_mlx_peak_gb": res_json.get("denoise_mlx_peak_gb"), "active_gb": res_json.get("active_gb"),
            "phases": res_json.get("phases"), "deferred": res_json.get("defer_transformer_load")}
(out / "identity.json").write_text(json.dumps(identity, indent=1))
print(json.dumps({k: identity[k] for k in ("rc", "wall_seconds", "pixel_sha256", "peak_footprint_gb", "mlx_peak_gb")}))
sys.exit(rc)
