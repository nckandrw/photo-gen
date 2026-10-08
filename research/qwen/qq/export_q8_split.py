"""Phase 6 Q-Q: per-component export of the Qwen-Image-2.1 edit checkpoint from the retained source, plus two checks.

Why per component: mflux 0.21.0's documented export, QwenImage21Edit(quantize=N, model_path=src).save_model(dst), loads
and materializes all three components before writing. At q8 that is ~18.4 GB (DiT 7.66 + text encoder 9.44 + VAE 1.35,
from the q4 export's tensor headers), more than this 16 GB machine holds. Narrowing
QwenImage21WeightDefinition.get_components to a subset in-process makes the SAME code (QwenImage21Initializer ->
Qwen21Initializer.load_components -> ModelSaver.save_model) load, quantize and write only those components.
Quantization is per tensor (MLX affine, group 64), so each component's files are the ones a monolithic export would
write; `check` proves this on the canonical q4 export without writing any q4 file.

Modes (run ONLY in the edit venv: mflux-qwen/.venv/bin/python3.12 research/qwen/qq/export_q8_split.py ...):
  export <src> <dst_part> <bits> <comp[,comp]> <record.json>
      Load <comp> from <src> at <bits>, set the other components to None (their lazily initialized random weights are
      never evaluated or written), save_model(<dst_part>). Refuses an existing <dst_part>.
  check <src> <canonical_export> <bits> <comp[,comp]> <record.json>
      Load <comp> from <src> at <bits> exactly as `export` does, then compare every in-memory parameter with the
      canonical export's tensors (dtype, shape, mx.array_equal), shard by shard. Writes nothing but the record.
  qerr <src> <comp> <every_nth> <record.json>
      Quantization error vs the dense bf16 source for every n-th quantizable 2-D weight of <comp>: mx.quantize at 4
      and 8 bits (affine, group 64, what mflux uses), dequantize, relative RMS error. Shows how different q8 is from q4.
"""
import json
import os
import sys
import time

import mlx.core as mx
from mlx.utils import tree_flatten


def versions() -> dict:
    import importlib.metadata as md
    return {p: md.version(p) for p in ("mflux", "mlx", "mlx-metal", "transformers", "torch")}


def load_subset(src: str, bits: int, comps: list[str]):
    from mflux.models.qwen21.weights.qwen_image21_weight_definition import QwenImage21WeightDefinition as WD
    full = WD.get_components
    names = [c.name for c in full()]
    if not comps or not set(comps) <= set(names):
        sys.exit(f"components must be a subset of {names}")
    WD.get_components = staticmethod(lambda: [c for c in full() if c.name in comps])
    from mflux.models.qwen21.variants.edit.qwen_image_21_edit import QwenImage21Edit
    t0 = time.perf_counter()
    model = QwenImage21Edit(quantize=bits, model_path=src)
    for n in names:
        if n not in comps:
            setattr(model, n, None)
    return model, round(time.perf_counter() - t0, 1)


def main() -> None:
    mode = sys.argv[1]
    rec = {"mode": mode, "argv": sys.argv[1:], "versions": versions(), "started": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    if mode == "export":
        src, dst, bits, comps, out = sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5].split(","), sys.argv[6]
        if os.path.exists(dst):
            sys.exit(f"refusing to overwrite {dst}")
        model, t_load = load_subset(src, bits, comps)
        rec.update(load_quantize_seconds=t_load, mlx_active_gb_after_load=round(mx.get_active_memory() / 1e9, 3),
                   mlx_peak_gb_after_load=round(mx.get_peak_memory() / 1e9, 3), bits=model.bits, components=comps)
        t = time.perf_counter()
        model.save_model(dst)
        rec.update(save_seconds=round(time.perf_counter() - t, 1), mlx_peak_gb_total=round(mx.get_peak_memory() / 1e9, 3),
                   api="QwenImage21Edit(quantize=bits, model_path=src).save_model(dst), get_components narrowed")
    elif mode == "check":
        src, canon, bits, comps, out = sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5].split(","), sys.argv[6]
        model, t_load = load_subset(src, bits, comps)
        rec.update(load_quantize_seconds=t_load, bits=model.bits, components=comps, canonical=canon, result={})
        for comp in comps:
            mem = dict(tree_flatten(getattr(model, comp).parameters()))
            seen, bad = set(), []
            shards = sorted(f for f in os.listdir(os.path.join(canon, comp)) if f.endswith(".safetensors"))
            for sh in shards:
                ref = mx.load(os.path.join(canon, comp, sh))
                for k, v in ref.items():
                    seen.add(k)
                    m = mem.get(k)
                    if m is None:
                        bad.append([k, "missing in memory"])
                    elif m.dtype != v.dtype or m.shape != v.shape:
                        bad.append([k, f"{m.dtype}{m.shape} vs {v.dtype}{v.shape}"])
                    elif not mx.array_equal(m, v).item():
                        bad.append([k, "values differ"])
                del ref
                mx.clear_cache()
            only_mem = sorted(set(mem) - seen)
            rec["result"][comp] = {"tensors_in_canonical": len(seen), "tensors_in_memory": len(mem), "mismatched": bad[:20],
                                   "mismatched_count": len(bad), "only_in_memory": only_mem[:20],
                                   "equal": not bad and not only_mem}
        rec["mlx_peak_gb_total"] = round(mx.get_peak_memory() / 1e9, 3)
    elif mode == "qerr":
        src, comp, nth, out = sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5]
        d = os.path.join(src, comp)
        rows = []
        idx = 0
        for sh in sorted(f for f in os.listdir(d) if f.endswith(".safetensors")):
            w = mx.load(os.path.join(d, sh))
            for k in sorted(w):
                v = w[k]
                if not (k.endswith(".weight") and v.ndim == 2 and v.shape[-1] % 64 == 0 and min(v.shape) >= 64):
                    continue
                idx += 1
                if idx % nth:
                    continue
                x = v.astype(mx.float32)
                r = {"key": k, "shape": list(v.shape)}
                for b in (4, 8):
                    q, s, z = mx.quantize(v, group_size=64, bits=b)
                    y = mx.dequantize(q, s, z, group_size=64, bits=b).astype(mx.float32)
                    r[f"rel_rms_q{b}"] = (mx.sqrt(mx.mean((y - x) ** 2)) / mx.sqrt(mx.mean(x ** 2))).item()
                rows.append(r)
            del w
            mx.clear_cache()
        q4 = sorted(r["rel_rms_q4"] for r in rows)
        q8 = sorted(r["rel_rms_q8"] for r in rows)
        rec.update(component=comp, sampled=len(rows), every_nth=nth, layers=rows,
                   median_rel_rms_q4=q4[len(q4) // 2] if q4 else None, median_rel_rms_q8=q8[len(q8) // 2] if q8 else None)
    else:
        sys.exit(f"unknown mode {mode}")
    rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    with open(out, "w") as f:
        json.dump(rec, f, indent=1)
    print(json.dumps({k: v for k, v in rec.items() if k not in ("layers",)}, indent=1)[:4000])


if __name__ == "__main__":
    main()
