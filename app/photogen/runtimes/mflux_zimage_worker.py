"""Worker process for one Z-Image-Turbo generation via mflux (runs in a fresh interpreter per job).

It invokes the unmodified mflux Turbo CLI entry point with the research-validated arguments, so --low-ram's
MemorySaver behaves exactly as measured. Around it, it adds passive probes only: phase wall times, MLX
allocator peaks, per-step times (from successive in-loop callbacks) and the kernel's lifetime peak memory
footprint. None of the probes alter computation.

Usage: python -m photogen.runtimes.mflux_zimage_worker <request.json> <result.json>
"""
from __future__ import annotations

import ctypes
import json
import os
import sys
import time
import traceback

_T0 = time.perf_counter()
_probe: dict = {"phases": {}, "step_timestamps": []}


def _lifetime_max_footprint_bytes() -> int | None:
    """rusage_info_v4.ri_lifetime_max_phys_footprint via libproc (the value `/usr/bin/time -l` reports)."""
    try:
        libproc = ctypes.CDLL("/usr/lib/libproc.dylib")

        class RUsageInfoV4(ctypes.Structure):
            _fields_ = [("ri_uuid", ctypes.c_uint8 * 16)] + [(f"f{i}", ctypes.c_uint64) for i in range(40)]

        info = RUsageInfoV4()
        if libproc.proc_pid_rusage(os.getpid(), 4, ctypes.byref(info)) != 0:
            return None
        return int(getattr(info, "f28"))  # 29th uint64 after the uuid = ri_lifetime_max_phys_footprint
    except Exception:  # noqa: BLE001 — telemetry must never break a generation
        return None


def _install_probes(mx) -> None:
    import mflux.models.z_image.variants.z_image as zmod
    from mflux.callbacks.callback_manager import CallbackManager

    ZI = zmod.ZImage

    def phase(name, fn):
        def wrapped(*a, **k):
            mx.synchronize()
            mx.reset_peak_memory()
            s = time.perf_counter()
            out = fn(*a, **k)
            if isinstance(out, tuple):
                mx.eval([x for x in out if isinstance(x, mx.array)])
            elif isinstance(out, mx.array):
                mx.eval(out)
            mx.synchronize()
            _probe["phases"][name] = {"seconds": round(time.perf_counter() - s, 3),
                                      "mlx_peak_gb": round(mx.get_peak_memory() / 1e9, 3)}
            return out
        return wrapped

    orig_init = ZI.__init__
    ZI.__init__ = lambda self, *a, **k: phase("load", orig_init)(self, *a, **k)
    ZI._encode_prompts = phase("text_encode", ZI._encode_prompts)
    ZI._decode_latents = phase("vae_decode", ZI._decode_latents)
    ZI.generate_image = phase("generate_total", ZI.generate_image)

    class StepTimer:
        def call_before_loop(self, *a, **k):
            _probe["step_timestamps"].append(time.perf_counter())

        def call_in_loop(self, *a, **k):
            _probe["step_timestamps"].append(time.perf_counter())

        def call_after_loop(self, *a, **k):
            _probe["step_timestamps"].append(time.perf_counter())

    orig_register = CallbackManager.register_callbacks

    def register_callbacks(*a, **k):
        result = orig_register(*a, **k)
        model = k.get("model", a[1] if len(a) > 1 else None)
        model.callbacks.register(StepTimer())
        return result

    CallbackManager.register_callbacks = staticmethod(register_callbacks)


def _apply_bf16_stream(mx) -> dict:
    """Opt-in precision 'bf16': keep the DiT hidden stream in bfloat16 instead of mflux 0.20.0's accidental
    float32 promotion (research/experiments/E02-RESULTS.md; gate: bf16-quality-report.md). Weights, quantization,
    scheduler and every mflux file are unchanged; this only patches, inside this worker process:
      1. x_pad_token / cap_pad_token cast to bf16 (a no-op in practice: the checkpoint stores them as bf16 and
         they are loaded over the mx.zeros init; kept for byte-identical behaviour with the gated experiment),
      2. TimestepEmbedder output (float32 sinusoid path) cast to bf16,
      3. RoPE result cast back to the input dtype (float32 freqs otherwise re-promote q/k),
      4. SDPA additive mask cast to q's dtype (a float32 mask is rejected for bf16 q).
    Identical to research/experiments/exp_zimage.py --precision bf16. Returns a dtype probe dict."""
    import mflux.models.z_image.variants.z_image as zmod
    from mflux.models.z_image.model.z_image_transformer import attention as AT, timestep_embedder as TE

    seen: dict = {}
    o_te = TE.TimestepEmbedder.__call__
    TE.TimestepEmbedder.__call__ = lambda self, *a, **k: o_te(self, *a, **k).astype(mx.bfloat16)
    o_rope = AT.ZImageAttention._apply_rotary_emb
    AT.ZImageAttention._apply_rotary_emb = staticmethod(lambda x, f: o_rope(x, f).astype(x.dtype))
    o_sdpa = AT.scaled_dot_product_attention

    def sdpa(q, k, v, scale=None, mask=None):
        seen.setdefault("sdpa_q", set()).add(str(q.dtype))
        if mask is not None:
            mask = mask.astype(q.dtype)
        return o_sdpa(q, k, v, scale=scale, mask=mask)
    AT.scaled_dot_product_attention = sdpa

    o_init = zmod.ZImage.__init__

    def init(self, *a, **k):
        o_init(self, *a, **k)
        t = self.transformer
        t.x_pad_token = t.x_pad_token.astype(mx.bfloat16)
        t.cap_pad_token = t.cap_pad_token.astype(mx.bfloat16)
    zmod.ZImage.__init__ = init
    return seen


def _install_transformer_release(mx) -> dict:
    """Make --low-ram's transformer release effective before VAE decode (production default since 2026-09-25;
    evidence: research/experiments/vae-lifecycle-report.md, production-memory-fix-report.md).

    Mechanism (mflux 0.20.0):
      MemorySaver.call_after_loop sets model.transformer = None
        -> but ZImage._predict returned mx.compile(predict), and that closure still references the transformer
           (it is kept alive by the `predict` local of generate_image during VAE decode)
        -> the q4 DiT (~3.47 GB) stays resident through VAE decode.
      Fix: the predict closure reads the transformer from a holder dict; after the denoise loop the holder is
      cleared (transformer AND compiled function), then gc.collect() + mx.clear_cache(), so the DiT is reclaimable.
    The predict body is identical to mflux's (same calls, same compile decision), so outputs are pixel-identical.
    Returns a status dict that is filled in when the release happens."""
    import gc
    import mflux.models.z_image.variants.z_image as zmod
    from mflux.callbacks.instances.memory_saver import MemorySaver
    from mflux.utils.apple_silicon import AppleSiliconUtil

    status = {"installed": True, "released": False}
    live: dict = {}

    def _predict(transformer):
        holder = {"t": transformer}

        def predict(latents, timestep, sigmas, text_encodings, negative_encodings, guidance):
            tr = holder["t"]
            noise = tr(timestep=timestep, x=latents, cap_feats=text_encodings, sigmas=sigmas)
            if negative_encodings is None:
                return noise
            negative_noise = tr(timestep=timestep, x=latents, cap_feats=negative_encodings, sigmas=sigmas)
            return noise + guidance * (noise - negative_noise)

        holder["fn"] = predict if AppleSiliconUtil.is_m1_or_m2() else mx.compile(predict)

        def call(*a, **k):
            return holder["fn"](*a, **k)

        def release():
            holder.clear()
            gc.collect()
            mx.clear_cache()
            status["released"] = True
        call.release = release
        live["predict"] = call
        return call

    zmod.ZImage._predict = staticmethod(_predict)
    orig_after = MemorySaver.call_after_loop

    def call_after_loop(self, *a, **k):
        result = orig_after(self, *a, **k)
        if not self.keep_transformer and "predict" in live:
            live.pop("predict").release()
        return result
    MemorySaver.call_after_loop = call_after_loop
    return status


def _count_compiles(mx) -> dict:
    """Passive probe: counts mx.compile calls (detects hidden recompilation). Does not alter computation."""
    counter = {"calls": 0}
    orig = mx.compile

    def compile_(*a, **k):
        counter["calls"] += 1
        return orig(*a, **k)
    mx.compile = compile_
    return counter


def main(req_path: str, res_path: str) -> int:
    req = json.load(open(req_path))
    result = {"ok": False}
    try:
        import mlx.core as mx
        import importlib.metadata as md
        from mflux.models.z_image.cli import z_image_turbo_generate as cli

        precision = req.get("precision", "fp32")
        if precision not in ("fp32", "bf16"):
            raise ValueError(f"unsupported precision {precision!r}")
        dtype_probe = _apply_bf16_stream(mx) if precision == "bf16" else None
        release_transformer = bool(req.get("release_transformer", True))
        release_status = _install_transformer_release(mx) if release_transformer else {"installed": False,
                                                                                         "released": False}
        compiles = _count_compiles(mx)
        _install_probes(mx)
        argv = ["mflux-generate-z-image-turbo",
                "--model", req["model_path"], "--base-model", req["base_model"],
                f"--prompt={req['prompt']}",  # '=' form so prompts starting with '-' are not parsed as flags
                "--width", str(req["width"]), "--height", str(req["height"]),
                "--steps", str(req["steps"]), "--seed", str(req["seed"]),
                "--low-ram", "--output", req["output_path"]]
        sys.argv = argv
        cli.main()
        if not os.path.exists(req["output_path"]):
            raise RuntimeError("mflux returned without writing the output image")
        ts = _probe["step_timestamps"]
        # ts = [before_loop, in_loop(step0), ..., in_loop(stepN-1), after_loop]; step i spans in_loop(i)->in_loop(i+1)
        steps = [round(b - a, 3) for a, b in zip(ts[1:], ts[2:])] if len(ts) >= 3 else []
        ph = _probe["phases"]
        gen = ph.get("generate_total", {}).get("seconds")
        te = ph.get("text_encode", {}).get("seconds", 0.0)
        vae = ph.get("vae_decode", {}).get("seconds", 0.0)
        result = {
            "ok": True,
            "argv": argv[1:],
            "phases": {**ph, "denoise_seconds": round(gen - te - vae, 3) if gen else None},
            "step_seconds": steps,
            "mlx_peak_gb": max((p.get("mlx_peak_gb", 0) for p in ph.values()), default=None),
            "versions": {p: md.version(p) for p in ("mflux", "mlx", "mlx-metal")},
            "mlx_device": str(mx.default_device()),
            "precision": precision,
            "transformer_release": release_status,
            "compile_calls": compiles["calls"],
            "dit_dtypes": {k: sorted(v) for k, v in dtype_probe.items()} if dtype_probe is not None else None,
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
