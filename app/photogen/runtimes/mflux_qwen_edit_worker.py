"""Worker process for one Qwen-Image-2.1 edit via mflux 0.21.0. It runs in a fresh interpreter of the edit
backend's OWN venv (mflux-qwen/.venv), never the production Z-Image venv.

It invokes the unmodified mflux `mflux-generate-qwen-2.1-edit` CLI entry point with the pinned arguments (single
input image, 40 steps by default, guidance 1.0, prefix KV cache on, linear schedule, --low-ram), so mflux's
MemorySaver releases the text encoder before denoising and the transformer before decode, and implies tiled VAE
decode. Around it, it adds passive probes only: phase wall times and MLX allocator peaks (load, text+vision encode,
reference VAE encode, denoise, VAE decode), per-step times, resident MLX memory at the phase boundaries, and the
kernel's lifetime peak memory footprint. The probes do not alter computation (checked by pixel parity against the
plain CLI: research/qwen/QWEN-EDITING-BASELINE.md).

Usage: python -m photogen.runtimes.mflux_qwen_edit_worker <request.json> <result.json>
"""
from __future__ import annotations

import json
import os
import sys
import time
import traceback

_T0 = time.perf_counter()
_probe: dict = {"phases": {}, "step_timestamps": [], "active_gb": {}, "footprint_gb": {}, "model": None}


def _rusage_field(index: int) -> int | None:
    """One uint64 field of rusage_info_v4 via libproc: 7 = ri_phys_footprint (current), 28 =
    ri_lifetime_max_phys_footprint (the value `/usr/bin/time -l` reports)."""
    import ctypes
    try:
        libproc = ctypes.CDLL("/usr/lib/libproc.dylib")

        class RUsageInfoV4(ctypes.Structure):
            _fields_ = [("ri_uuid", ctypes.c_uint8 * 16)] + [(f"f{i}", ctypes.c_uint64) for i in range(40)]

        info = RUsageInfoV4()
        if libproc.proc_pid_rusage(os.getpid(), 4, ctypes.byref(info)) != 0:
            return None
        return int(getattr(info, f"f{index}"))
    except Exception:  # noqa: BLE001 — telemetry must never break an edit
        return None


def _lifetime_max_footprint_bytes() -> int | None:
    return _rusage_field(28)


def _footprint_now(label: str) -> None:
    """Passive probe: the process's current physical footprint at a stage boundary (Phase 5 lifetime profile)."""
    fp = _rusage_field(7)
    _probe["footprint_gb"][label] = round(fp / 1e9, 3) if fp else None


def _install_probes(mx) -> None:
    from mflux.callbacks.callback_manager import CallbackManager
    from mflux.models.common.vae.vae_util import VAEUtil
    from mflux.models.qwen21.model.qwen21_vae.vae import QwenImage21VAE
    from mflux.models.qwen21.variants.edit.qwen_image_21_edit import QwenImage21Edit

    def gb(x):
        return round(x / 1e9, 3)

    def phase(name, fn, accumulate=False):
        def wrapped(*a, **k):
            mx.synchronize()
            mx.reset_peak_memory()
            s = time.perf_counter()
            out = fn(*a, **k)
            arrays = [x for x in (out if isinstance(out, tuple) else (out,)) if isinstance(x, mx.array)]
            if arrays:
                mx.eval(arrays)
            mx.synchronize()
            rec = _probe["phases"].setdefault(name, {"seconds": 0.0, "mlx_peak_gb": 0.0, "calls": 0})
            rec["seconds"] = round(rec["seconds"] + time.perf_counter() - s, 3) if accumulate else \
                round(time.perf_counter() - s, 3)
            rec["mlx_peak_gb"] = max(rec["mlx_peak_gb"], gb(mx.get_peak_memory()))
            rec["calls"] += 1
            _probe["active_gb"][f"after_{name}"] = gb(mx.get_active_memory())
            _footprint_now(f"after_{name}")
            return out
        return wrapped

    orig_init = QwenImage21Edit.__init__

    def init(self, *a, **k):
        phase("load", orig_init)(self, *a, **k)
        _probe["model"] = self

    QwenImage21Edit.__init__ = init
    QwenImage21Edit._encode_prompt = phase("text_encode", QwenImage21Edit._encode_prompt, accumulate=True)
    QwenImage21VAE.encode = phase("vae_encode", QwenImage21VAE.encode, accumulate=True)
    VAEUtil.decode = staticmethod(phase("vae_decode", VAEUtil.decode))
    QwenImage21Edit.generate_image = phase("generate_total", QwenImage21Edit.generate_image)

    class StepTimer:
        def call_before_loop(self, *a, **k):  # after MemorySaver released the text encoder
            _probe["active_gb"]["before_loop"] = gb(mx.get_active_memory())
            _footprint_now("before_loop")
            mx.reset_peak_memory()
            _probe["step_timestamps"].append(time.perf_counter())

        def call_in_loop(self, *a, **k):
            _probe["step_timestamps"].append(time.perf_counter())
            active = gb(mx.get_active_memory())  # latents are evaluated: steady-state residency between steps
            _probe["denoise_active_gb_max"] = max(_probe.get("denoise_active_gb_max", 0.0), active)
            if len(_probe["step_timestamps"]) == 2:  # after step 0: DiT read (deferred) + prefix KV cache built
                _probe["active_gb"]["after_step0"] = active
                _footprint_now("after_step0")

        def call_after_loop(self, *a, **k):
            _probe["step_timestamps"].append(time.perf_counter())
            _probe["denoise_mlx_peak_gb"] = gb(mx.get_peak_memory())
            _footprint_now("after_loop")

    orig_register = CallbackManager.register_callbacks

    def register_callbacks(*a, **k):
        result = orig_register(*a, **k)
        model = k.get("model", a[1] if len(a) > 1 else None)
        model.callbacks.register(StepTimer())
        _probe["tiling"] = repr(getattr(model, "tiling_config", None))
        return result

    CallbackManager.register_callbacks = staticmethod(register_callbacks)


def _defer_transformer_load() -> dict:
    """Lifetime-only patch; production default (runtime DEFER_TRANSFORMER_LOAD) after its parity gate: pixel-identical
    to the stock lifecycle, peak footprint at 512 12.63 -> 8.85 GB (research/qwen/QWEN-EDITING-BASELINE.md).

    mflux 0.21.0's Qwen21Initializer.load_components materializes every component at load time, so the q4 DiT
    (~4.1 GB) is resident through text+vision encoding and the reference VAE encode, where it is never used; that
    pre-loop phase is the memory peak of an edit. This leaves the transformer's (pre-quantized) weights as lazy MLX
    loads: they are read from the export on first use, i.e. in denoising step 0, after MemorySaver has released the
    text encoder. Same weights, same graph, same kernels: only the time at which the bytes are read changes."""
    from mflux.models.qwen21.qwen21_initializer import Qwen21Initializer

    status = {"installed": True, "deferred": []}
    orig = Qwen21Initializer._materialize

    def _materialize(name, module, weight_definition):
        if name == "transformer":
            status["deferred"].append(name)
            return None
        return orig(name, module, weight_definition)

    Qwen21Initializer._materialize = staticmethod(_materialize)
    return status


def _install_lifetime_policy(req: dict) -> dict:
    """Phase 5 lifetime-only patches (opt-in per request; research/qwen/QWEN-MEMORY-LIFETIME.md). Neither changes a
    weight, the graph or a kernel: they only change WHEN a component is resident. The worker never passes guidance,
    a negative prompt, enhance/verify/auto-mask or multiple seeds (the runtime rejects them), so after the single
    _encode_prompt call nothing reads the text encoder again, and nothing reads the VAE between the reference encode
    and the final decode.

    release_text_encoder_after_encode: drop the Qwen3-VL text/vision encoder (q4, ~5.1 GB) as soon as the prompt
      embedding is evaluated, i.e. BEFORE the reference VAE encode (mflux's MemorySaver drops it only at
      before_loop, so it is resident through the VAE encode, the pre-denoise peak).
    release_vae_during_denoise: at before_loop (after the reference encode) replace the resident VAE (fp32, 1.35 GB:
      encoder 0.32 + decoder 1.04) by a fresh instance loaded through mflux's own Qwen21Initializer.load_components
      from the same export with the same arguments but left as lazy MLX loads (not materialized). The decoder's bytes
      are read again at the first decode tile; the encoder's are never read. Same weights, same graph."""
    import gc
    import types

    import mlx.core as mx
    from mflux.models.qwen21.qwen21_initializer import Qwen21Initializer
    from mflux.models.qwen21.variants.edit.qwen_image_21_edit import QwenImage21Edit

    status = {"release_text_encoder_after_encode": bool(req.get("release_text_encoder_after_encode")),
              "release_vae_during_denoise": bool(req.get("release_vae_during_denoise")),
              "text_encoder_released_after_encode": False, "vae_reloaded_lazily": False}

    if status["release_text_encoder_after_encode"]:
        orig_encode = QwenImage21Edit._encode_prompt

        def _encode_prompt(self, prompt, images):
            out = orig_encode(self, prompt, images)
            mx.eval([x for x in out if isinstance(x, mx.array)])
            if self.text_encoder is not None:
                self.text_encoder = None
                gc.collect()
                mx.clear_cache()
                status["text_encoder_released_after_encode"] = True
            return out

        QwenImage21Edit._encode_prompt = _encode_prompt

    if status["release_vae_during_denoise"]:
        from mflux.callbacks.callback_manager import CallbackManager
        from mflux.models.qwen21.model.qwen21_vae.vae import QwenImage21VAE

        load_args: dict = {}
        reloading = {"vae": False}
        orig_load = Qwen21Initializer.load_components
        orig_materialize = Qwen21Initializer._materialize

        def load_components(model, root, weight_definition, quantize, *, validate=False):
            if not reloading["vae"]:
                load_args.update(root=root, weight_definition=weight_definition, quantize=quantize, validate=validate)
            return orig_load(model, root, weight_definition, quantize, validate=validate)

        def _materialize(name, module, weight_definition):
            if reloading["vae"] and name == "vae":
                return None
            return orig_materialize(name, module, weight_definition)

        Qwen21Initializer.load_components = staticmethod(load_components)
        Qwen21Initializer._materialize = staticmethod(_materialize)

        class VaeLifetime:
            def __init__(self, model):
                self.model = model

            def call_before_loop(self, *a, **k):
                wd = load_args["weight_definition"]
                vae_only = type("VaeOnly", (wd,), {"get_components": staticmethod(
                    lambda: [c for c in wd.get_components() if c.name == "vae"])})
                fresh = QwenImage21VAE(self.model._component_configs["vae"])
                reloading["vae"] = True
                try:
                    Qwen21Initializer.load_components(types.SimpleNamespace(vae=fresh, bits=None), load_args["root"],
                                                      vae_only, load_args["quantize"], validate=load_args["validate"])
                finally:
                    reloading["vae"] = False
                self.model.vae = fresh
                gc.collect()
                mx.clear_cache()
                status["vae_reloaded_lazily"] = True

            def call_in_loop(self, *a, **k):
                pass

            def call_after_loop(self, *a, **k):
                pass

        orig_register = CallbackManager.register_callbacks

        def register_callbacks(*a, **k):
            result = orig_register(*a, **k)  # MemorySaver first: it releases the text encoder at before_loop
            model = k.get("model", a[1] if len(a) > 1 else None)
            model.callbacks.register(VaeLifetime(model))
            return result

        CallbackManager.register_callbacks = staticmethod(register_callbacks)
    return status


def main(req_path: str, res_path: str) -> int:
    req = json.load(open(req_path))
    result = {"ok": False}
    try:
        import importlib.metadata as md

        import mlx.core as mx
        from mflux.models.qwen21.cli import qwen21_edit_generate as cli

        defer = _defer_transformer_load() if req.get("defer_transformer_load", False) else {"installed": False}
        policy = _install_lifetime_policy(req)  # before the probes, so the probes measure the patched lifecycle
        _install_probes(mx)
        _footprint_now("startup")
        argv = ["mflux-generate-qwen-2.1-edit",
                "--model", req["model_path"], "--base-model", req["base_model"],
                f"--prompt={req['prompt']}",  # '=' form so instructions starting with '-' are not parsed as flags
                "--image-paths", req["image_path"],
                "--seed", str(req["seed"]), "--steps", str(req["steps"]),
                "--output-resolution", str(req["output_resolution"]),
                "--low-ram", "--output", req["output_path"]]
        sys.argv = argv
        cli.main()
        _footprint_now("end")
        if not os.path.exists(req["output_path"]):
            raise RuntimeError("mflux returned without writing the output image")
        ts = _probe["step_timestamps"]
        # ts = [before_loop, in_loop(step0), ..., in_loop(stepN-1), after_loop]; step i spans in_loop(i)->in_loop(i+1)
        # (in_loop fires after each step's update, so step 0 spans before_loop -> in_loop(0)).
        steps = [round(b - a, 3) for a, b in zip(ts[:-2], ts[1:-1])] if len(ts) >= 3 else []
        ph = _probe["phases"]
        gen = ph.get("generate_total", {}).get("seconds")
        pre = sum(ph.get(k, {}).get("seconds", 0.0) for k in ("text_encode", "vae_encode", "vae_decode"))
        model = _probe["model"]
        result = {
            "ok": True,
            "argv": argv[1:],
            "phases": {**ph, "denoise_seconds": round(ts[-1] - ts[0], 3) if len(ts) >= 2 else None,
                       "other_seconds": round(gen - pre - (ts[-1] - ts[0]), 3) if gen and len(ts) >= 2 else None},
            "step_seconds": steps,
            "mlx_peak_gb": max((p.get("mlx_peak_gb", 0) for p in ph.values() if isinstance(p, dict)), default=None),
            "denoise_mlx_peak_gb": _probe.get("denoise_mlx_peak_gb"),
            "active_gb": _probe["active_gb"],
            "versions": {p: md.version(p) for p in ("mflux", "mlx", "mlx-metal", "transformers", "torch")},
            "mlx_device": str(mx.default_device()),
            "vae_tiling": _probe.get("tiling"),
            "text_encoder_released": getattr(model, "text_encoder", "?") is None if model is not None else None,
            "transformer_released": getattr(model, "transformer", "?") is None if model is not None else None,
            "bits": getattr(model, "bits", None) if model is not None else None,
            "defer_transformer_load": defer,
            "memory_policy": {"defer_transformer_load": bool(req.get("defer_transformer_load", False)), **policy},
            "footprint_gb": _probe["footprint_gb"],
            "denoise_active_gb_max": _probe.get("denoise_active_gb_max"),
        }
    except BaseException as e:  # noqa: BLE001 — report everything, including SystemExit from argparse
        result = {"ok": False, "error_type": type(e).__name__, "error": str(e), "traceback": traceback.format_exc()}
    result["process_seconds"] = round(time.perf_counter() - _T0, 3)
    fp = _lifetime_max_footprint_bytes()
    result["peak_footprint_gb"] = round(fp / 1e9, 3) if fp else None
    with open(res_path, "w") as f:
        json.dump(result, f, indent=1)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
