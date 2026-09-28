"""4-step probe worker (research only; research/experiments/4step-probe/).

Runs ONE generation in a fresh process, like the production worker, and reuses the production worker's own
patches and probes (bf16 stream, transformer release, compile counter, phase/step probes, libproc footprint).
Nothing in app/ is modified. Candidate C uses mflux's Z-Image *base* CLI (`z_image_generate.main`) with a LoRA.
Candidates A/B use the Turbo CLI exactly as production does.

Request JSON: {cli: "turbo"|"base", model_path, base_model, prompt, width, height, steps, seed, precision,
               release_transformer, output_path, [lora_path, lora_scale, scheduler, guidance]}
"""
import json
import os
import sys
import time
import traceback

from photogen.runtimes import mflux_zimage_worker as W


def main(req_path, res_path):
    req = json.load(open(req_path))
    result = {"ok": False}
    try:
        import importlib.metadata as md
        import mlx.core as mx
        if req["cli"] == "turbo":
            from mflux.models.z_image.cli import z_image_turbo_generate as cli
            prog = "mflux-generate-z-image-turbo"
        else:
            from mflux.models.z_image.cli import z_image_generate as cli
            prog = "mflux-generate-z-image"
        precision = req.get("precision", "fp32")
        dtype_probe = W._apply_bf16_stream(mx) if precision == "bf16" else None
        release = W._install_transformer_release(mx) if req.get("release_transformer", True) else {"installed": False}
        compiles = W._count_compiles(mx)
        W._install_probes(mx)
        argv = [prog, "--model", req["model_path"], "--base-model", req["base_model"], f"--prompt={req['prompt']}",
                "--width", str(req["width"]), "--height", str(req["height"]), "--steps", str(req["steps"]),
                "--seed", str(req["seed"]), "--low-ram", "--output", req["output_path"]]
        if req.get("lora_path"):
            argv += ["--lora-paths", req["lora_path"], "--lora-scales", str(req.get("lora_scale", 1.0))]
        if req.get("scheduler"):
            argv += ["--scheduler", req["scheduler"]]
        if req.get("guidance") is not None:
            argv += ["--guidance", str(req["guidance"])]
        sys.argv = argv
        cli.main()
        if not os.path.exists(req["output_path"]):
            raise RuntimeError("mflux returned without writing the output image")
        ts = W._probe["step_timestamps"]
        ph = W._probe["phases"]
        gen = ph.get("generate_total", {}).get("seconds")
        te = ph.get("text_encode", {}).get("seconds", 0.0)
        vae = ph.get("vae_decode", {}).get("seconds", 0.0)
        result = {"ok": True, "argv": argv[1:],
                  "phases": {**ph, "denoise_seconds": round(gen - te - vae, 3) if gen else None},
                  "step_seconds": [round(b - a, 3) for a, b in zip(ts[1:], ts[2:])] if len(ts) >= 3 else [],
                  "versions": {p: md.version(p) for p in ("mflux", "mlx", "mlx-metal")},
                  "precision": precision, "transformer_release": release, "compile_calls": compiles["calls"],
                  "dit_dtypes": {k: sorted(v) for k, v in dtype_probe.items()} if dtype_probe is not None else None}
    except BaseException as e:  # noqa: BLE001 — report everything, including SystemExit from argparse
        result = {"ok": False, "error_type": type(e).__name__, "error": str(e), "traceback": traceback.format_exc()}
    result["process_seconds"] = round(time.perf_counter() - W._T0, 3)
    fp = W._lifetime_max_footprint_bytes()
    result["peak_footprint_gb"] = round(fp / 1e9, 3) if fp else None
    json.dump(result, open(res_path, "w"), indent=1)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
