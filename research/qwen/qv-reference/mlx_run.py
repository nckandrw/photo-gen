"""Phase 8 Q-VR launcher for mlx_side.py: runs it in the edit venv with EXACTLY the production edit worker's environment
(photogen.runtimes.mflux_qwen_edit._worker_env: MLX_*/HF_*/PYTHON* stripped, HF offline), like Phase 7's qv_run.py.
With --tf32-off it adds MLX_ENABLE_TF32=0 to that environment (arm A1T only; production never sets it).

Usage: mflux/.venv/bin/python3.12 research/qwen/qv-reference/mlx_run.py [--tf32-off] <mode> <args...>"""
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "app"))
from photogen.config import AppConfig  # noqa: E402
from photogen.runtimes.mflux_qwen_edit import QwenEditManifest, _worker_env  # noqa: E402

args = sys.argv[1:]
tf32_off = "--tf32-off" in args
args = [a for a in args if a != "--tf32-off"]
env = _worker_env(AppConfig.load())
if tf32_off:
    env["MLX_ENABLE_TF32"] = "0"
m = QwenEditManifest.load(ROOT / "config" / "backend-qwen21-edit-mflux.json", ROOT)
cmd = [str(m.interpreter), str(ROOT / "research/qwen/qv-reference/mlx_side.py"), *args]
t0 = time.perf_counter()
rc = subprocess.run(cmd, env=env, cwd=str(ROOT)).returncode
print(json.dumps({"rc": rc, "process_wall_seconds": round(time.perf_counter() - t0, 3), "tf32_off": tf32_off,
                  "mlx_env": {k: v for k, v in env.items() if k.startswith("MLX_")}}))
sys.exit(rc)
