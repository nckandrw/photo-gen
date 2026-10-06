"""One-time q4 export of the complete, vision-capable Qwen-Image-2.1 edit checkpoint (Phase 4).

Runs ONLY in the edit backend venv: mflux-qwen/.venv/bin/python3.12 research/qwen/export_q4.py <src> <dst>
Uses mflux 0.21.0's documented path (reference/README.md "Quantized checkpoints and reproducibility"):
QwenImage21Edit(quantize=4, model_path=src).save_model(dst). Each component is loaded and quantized in turn with
chunked materialization (Qwen21Initializer.load_components), so the dense bf16 checkpoint is never resident at once.
Writes <dst>/../<name>.export.json with timings, peak memory and the quantization result."""
import json
import os
import sys
import time

import mlx.core as mx

src, dst = sys.argv[1], sys.argv[2]
if os.path.exists(dst):
    sys.exit(f"refusing to overwrite existing export {dst}")
t0 = time.perf_counter()
from mflux.models.qwen21.variants.edit.qwen_image_21_edit import QwenImage21Edit  # noqa: E402

model = QwenImage21Edit(quantize=4, model_path=src)
t_load = time.perf_counter() - t0
peak_load = mx.get_peak_memory()
active_load = mx.get_active_memory()
model.save_model(dst)
t_total = time.perf_counter() - t0
import importlib.metadata as md  # noqa: E402

info = {"source": src, "export": dst, "quantize": 4, "bits": model.bits,
        "load_quantize_seconds": round(t_load, 1), "total_seconds": round(t_total, 1),
        "mlx_peak_gb_after_load": round(peak_load / 1e9, 3), "mlx_active_gb_after_load": round(active_load / 1e9, 3),
        "mlx_peak_gb_total": round(mx.get_peak_memory() / 1e9, 3),
        "versions": {p: md.version(p) for p in ("mflux", "mlx", "mlx-metal", "transformers", "torch")},
        "api": "mflux.models.qwen21.variants.edit.qwen_image_21_edit.QwenImage21Edit(quantize=4).save_model"}
with open(dst.rstrip("/") + ".export.json", "w") as f:
    json.dump(info, f, indent=1)
print(json.dumps(info, indent=1))
