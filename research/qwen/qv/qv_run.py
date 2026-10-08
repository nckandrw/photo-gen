"""Phase 7 Q-V launcher: run research/qwen/qv/qv_roundtrip.py in the edit venv with EXACTLY the production edit
worker's environment (photogen.runtimes.mflux_qwen_edit._worker_env: MLX_*/HF_*/PYTHON* stripped, offline HF), like
research/qwen/qq/qq_run.py. Run with the production interpreter.

Usage: mflux/.venv/bin/python3.12 research/qwen/qv/qv_run.py <out_dir> <roundtrip|gate> [<staged.png> <budget>]"""
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "app"))
from photogen.config import AppConfig  # noqa: E402
from photogen.runtimes.mflux_qwen_edit import QwenEditManifest, _worker_env  # noqa: E402

out, mode, *rest = sys.argv[1:]
out = Path(out).resolve()
cfg = AppConfig.load()
m = QwenEditManifest.load(ROOT / "config" / "backend-qwen21-edit-mflux.json", ROOT)
cmd = [str(m.interpreter), str(ROOT / "research/qwen/qv/qv_roundtrip.py"), mode]
cmd += [rest[0], rest[1], str(out)] if mode == "roundtrip" else [str(out)]
out.parent.mkdir(parents=True, exist_ok=True)
t0 = time.perf_counter()
log = out.parent / "qv.log"
with log.open("wb") as lf:
    rc = subprocess.run(cmd, stdout=lf, stderr=subprocess.STDOUT, env=_worker_env(cfg), cwd=str(ROOT)).returncode
rec_path = out / ("identity.json" if mode == "roundtrip" else "gate.json")
rec = json.loads(rec_path.read_text()) if rec_path.exists() else {}
summary = {"rc": rc, "process_wall_seconds": round(time.perf_counter() - t0, 3), "mode": mode, "record": str(rec_path),
           "pass": rec.get("checks", {}).get("pass") if mode == "gate" else None,
           "roundtrip_pixel_sha256": rec.get("roundtrip", {}).get("pixel_sha256"),
           "peak_footprint_gb": rec.get("peak_footprint_gb"), "mlx_peak_gb": rec.get("mlx_peak_gb"),
           "seconds": rec.get("seconds")}
print(json.dumps(summary))
sys.exit(rc)
