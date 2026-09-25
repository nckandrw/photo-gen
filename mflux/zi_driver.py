"""Instrumented launcher for the *unmodified* mflux Z-Image-Turbo CLI (mflux 0.20.0).

Runs mflux.models.z_image.cli.z_image_turbo_generate.main() with the given argv. The only additions are
timing/memory probes wrapped around existing methods; arguments and return values pass through untouched.
Probes: wall-clock per phase and MLX active/peak memory (mx.get_active_memory / mx.get_peak_memory, bytes
allocated by MLX's Metal allocator). Peak is reset at each phase start so each phase reports its own peak.
Writes a JSON line to $ZI_PHASES (path) at exit.
Also records whether torch was imported and whether any torch tensor op ran on MPS (it should not).
"""
import atexit, json, os, sys, time

import mlx.core as mx

import mflux.models.z_image.variants.z_image as zmod
from mflux.models.z_image.cli import z_image_turbo_generate as cli

ZI = zmod.ZImage
rec = {"argv": sys.argv[1:], "phases": {}}
_t0 = time.perf_counter()


def _phase(name, fn):
    def wrapped(*a, **k):
        mx.synchronize()
        mx.reset_peak_memory()
        s, act0 = time.perf_counter(), mx.get_active_memory()
        out = fn(*a, **k)
        if isinstance(out, mx.array):
            mx.eval(out)
        elif isinstance(out, tuple):
            mx.eval([x for x in out if isinstance(x, mx.array)])
        mx.synchronize()
        rec["phases"].setdefault(name, []).append({
            "t_start": round(s - _t0, 3), "sec": round(time.perf_counter() - s, 3),
            "active_before_gb": round(act0 / 1e9, 3), "active_after_gb": round(mx.get_active_memory() / 1e9, 3),
            "mlx_peak_gb": round(mx.get_peak_memory() / 1e9, 3), "cache_gb": round(mx.get_cache_memory() / 1e9, 3)})
        return out
    return wrapped


_orig_init = ZI.__init__
ZI.__init__ = lambda self, *a, **k: _phase("load_init", _orig_init)(self, *a, **k)
ZI._encode_prompts = _phase("text_encode", ZI._encode_prompts)
ZI._decode_latents = _phase("vae_decode", ZI._decode_latents)
from mflux.callbacks.instances.memory_saver import MemorySaver as _MS


def _after(name, fn):
    def wrapped(self, *a, **k):
        out = fn(self, *a, **k)
        mx.synchronize()
        rec["phases"].setdefault(name, []).append({"t": round(time.perf_counter() - _t0, 3),
            "active_after_gb": round(mx.get_active_memory() / 1e9, 3), "cache_gb": round(mx.get_cache_memory() / 1e9, 3),
            "model_text_encoder_is_none": getattr(self.model, "text_encoder", "n/a") is None,
            "model_transformer_is_none": getattr(self.model, "transformer", "n/a") is None})
        return out
    return wrapped


_MS.call_before_loop = _after("memsaver_before_loop", _MS.call_before_loop)
_MS.call_after_loop = _after("memsaver_after_loop", _MS.call_after_loop)
_orig_gen = ZI.generate_image
ZI.generate_image = _phase("generate_image_total", _orig_gen)


@atexit.register
def _dump():
    ph = rec["phases"]
    g = ph.get("generate_image_total", [{}])[0].get("sec", 0)
    te = ph.get("text_encode", [{}])[0].get("sec", 0)
    va = ph.get("vae_decode", [{}])[0].get("sec", 0)
    rec["denoise_sec_derived"] = round(g - te - va, 3) if g else None  # generate minus TE minus VAE (includes latent init + callbacks)
    rec["process_wall_sec"] = round(time.perf_counter() - _t0, 3)
    rec["torch_imported"] = "torch" in sys.modules
    try:
        import torch
        rec["torch_mps_allocated_bytes"] = int(torch.mps.current_allocated_memory()) if torch.backends.mps.is_available() else None
    except Exception as e:  # noqa: BLE001
        rec["torch_mps_allocated_bytes"] = f"err:{e}"
    rec["mlx_version"] = mx.__version__
    rec["device"] = str(mx.default_device())
    with open(os.environ["ZI_PHASES"], "w") as f:
        json.dump(rec, f, indent=1)


if __name__ == "__main__":
    sys.argv = ["mflux-generate-z-image-turbo"] + sys.argv[1:]
    cli.main()
