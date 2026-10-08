"""Phase 8 Q-VR gate 1 (PROTOCOL.md section 5.1): are the canonical q4 export's VAE tensors (what A1/MLX loads) the dense
source checkpoint's VAE tensors (what A2/Diffusers loads), bit for bit, after a layout transform?

For each of the tensors the transform is DERIVED from the two shapes and recorded; only three are allowed:
  identical      same shape, compared directly;
  conv4d_to_mlx  4-D torch (O, I, kh, kw) -> MLX (O, kh, kw, I), i.e. transpose(0, 2, 3, 1);
  squeeze        a reshape that only removes size-1 axes (e.g. RMSNorm gamma (C, 1, 1[, 1]) -> (C,)).
Anything else, a missing tensor, or any differing bit fails the gate. Reads only; NumPy + safetensors.

Run: torch-ref/.venv/bin/python3.12 -I research/qwen/qv-reference/weight_identity.py <out.json>"""
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from safetensors.numpy import load_file

ROOT = Path(__file__).resolve().parents[3]
DENSE = ROOT / "models/research/qwen-image-2.1/vae/diffusion_pytorch_model.safetensors"
EXPORT = ROOT / "models/qwen/qwen-image-2.1-edit-mflux-q4/vae/0.safetensors"


def sha_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        while b := f.read(1 << 24):
            h.update(b)
    return h.hexdigest()


def transform(d: np.ndarray, e: np.ndarray) -> tuple[str, np.ndarray | None]:
    if d.shape == e.shape:
        return "identical", d
    if d.ndim == 4 and e.ndim == 4 and d.transpose(0, 2, 3, 1).shape == e.shape:
        return "conv4d_to_mlx", d.transpose(0, 2, 3, 1)
    if tuple(s for s in d.shape if s != 1) == tuple(s for s in e.shape if s != 1) and d.size == e.size:
        return "squeeze", d.reshape(e.shape)
    return "unmapped", None


def main(out_json: str) -> int:
    dense, export = load_file(str(DENSE)), load_file(str(EXPORT))
    rows, kinds = {}, Counter()
    for k in sorted(set(dense) | set(export)):
        if k not in dense or k not in export:
            rows[k] = {"status": "missing", "in_dense": k in dense, "in_export": k in export}
            kinds["missing"] += 1
            continue
        d, e = dense[k], export[k]
        kind, t = transform(d, e)
        kinds[kind] += 1
        ok = t is not None and t.dtype == e.dtype and np.array_equal(np.ascontiguousarray(t).view(np.uint8),
                                                                     np.ascontiguousarray(e).view(np.uint8))
        rows[k] = {"dense_shape": list(d.shape), "export_shape": list(e.shape), "dtype": str(d.dtype),
                   "transform": kind, "bit_identical": bool(ok),
                   "max_abs": None if t is None else float(np.abs(t.astype(np.float64) - e.astype(np.float64)).max())}
    passed = all(r.get("bit_identical") for r in rows.values()) and len(rows) == 238 and not kinds["unmapped"]
    rec = {"tool": "research/qwen/qv-reference/weight_identity.py",
           "dense": {"path": str(DENSE.relative_to(ROOT)), "sha256": sha_file(DENSE), "tensors": len(dense)},
           "export": {"path": str(EXPORT.relative_to(ROOT)), "sha256": sha_file(EXPORT), "tensors": len(export)},
           "transforms": dict(kinds), "bit_identical": sum(bool(r.get("bit_identical")) for r in rows.values()),
           "pass": passed, "tensors": rows}
    Path(out_json).parent.mkdir(parents=True, exist_ok=False)
    Path(out_json).write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: rec[k] for k in ("transforms", "bit_identical", "pass")}))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
