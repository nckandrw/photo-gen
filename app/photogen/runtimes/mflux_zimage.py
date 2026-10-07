"""Z-Image-Turbo on mflux/MLX — the research-validated production backend.

Each job runs in a fresh worker process (see mflux_zimage_worker.py) so the measured --low-ram memory
behaviour is reproduced exactly, cancellation is a clean SIGTERM, and a Metal/MLX crash cannot take down
the service.
"""
from __future__ import annotations

import importlib.util
import json
import logging
import os
import secrets
import signal
import subprocess
import sys
import time
from pathlib import Path

from ..config import AppConfig
from ..errors import (GenerationError, JobCancelledError, OutputCorruptedError, RuntimeUnavailableError,
                      UnsupportedParameterError, ValidationError)
from ..imaging import check_output, inspect_image
from ..integrity import check_versions, verify_model_files
from ..models import GenerationRequest, GenerationResult, JobStatus, utcnow
from ..tasks import TEXT_TO_IMAGE
from ..text_encoders import STOCK, load_registry, verify_entry
from .base import CancelToken, Capabilities, ImageRuntime, RuntimeHealth, check_worker_versions

log = logging.getLogger(__name__)

ACCEPTED = {"task", "prompt", "width", "height", "steps", "seed", "output_format", "output_name", "allow_experimental",
            "precision", "text_encoder", "profile"}
# Parameters that exist elsewhere but are NOT honoured by this backend: reject instead of silently ignoring.
REJECTED = {
    "negative_prompt": "Z-Image-Turbo runs without CFG in mflux; a negative prompt would never be encoded",
    "guidance": "Z-Image-Turbo is guidance-distilled; mflux forces guidance to 0.0",
    "cfg": "Z-Image-Turbo is guidance-distilled; mflux forces guidance to 0.0",
    "cfg_scale": "Z-Image-Turbo is guidance-distilled; mflux forces guidance to 0.0",
    "scheduler": "the scheduler is fixed to the validated mflux default",
    "low_ram": "--low-ram is mandatory on this 16 GB machine (12.8 GB footprint and critical memory pressure without it)",
    "model": "only the validated Z-Image-Turbo q4 model is available",
    "quantize": "quantization is fixed by the validated pre-quantized q4 model",
    "lora": "LoRA is not validated on this backend",
    "loras": "LoRA is not validated on this backend",
    "image": "image-to-image/editing is not enabled on this backend",
    "images": "image-to-image/editing is not enabled on this backend",
    "strength": "image-to-image/editing is not enabled on this backend",
}
PRECISIONS = ("fp32", "bf16")
# Named, evidence-backed configurations. REFERENCE is the default and canonical reproducibility configuration.
PROFILES = {
    "reference": {"precision": "fp32", "steps": 9},   # permanent research reference (production-memory-fix-report.md)
    "fast": {"precision": "bf16", "steps": 8},        # gated: bf16-quality-report.md + 8step-quality-gate-report.md
    "balanced": {"precision": "bf16", "steps": 5},    # gated at 1024x1024 ONLY: step-count-quality-gate/results.md § Stage B
    "ultra": {"precision": "bf16", "steps": 4},       # gated at 512x512 ONLY: step-count-quality-gate/results.md
}
# The ONLY (precision, steps) -> resolutions combinations that are validated. Validation applies to the exact
# combination of model + precision + steps + scheduler + resolution; anything not listed is experimental and
# requires allow_experimental. Never derive validity from a nearby configuration.
#   fp32 + 9 (REFERENCE): research reference at every manifest resolution (MFLUX-ZIMAGE-RESULTS.md)
#   bf16 + 8 (FAST): direct blinded REFERENCE-vs-FAST gates at all three sizes
#     (research/experiments/fast-resolution-gates-report.md, 2026-09-25: pooled 72 pairs REF 2 / FAST 1 / 69 ties)
#   bf16 + 9: blinded gate vs fp32/9 at 1024x1024 ONLY (research/experiments/bf16-quality-report.md, 0/2/22)
#   bf16 + 5 (BALANCED): 1024x1024 ONLY (research/experiments/step-count-quality-gate/results.md § Stage B)
#   bf16 + 4 (ULTRA): 512x512 ONLY (research/experiments/step-count-quality-gate/results.md)
VALIDATED_COMBINATIONS = {
    ("fp32", 9): ((512, 512), (768, 768), (1024, 1024)),
    ("bf16", 8): ((512, 512), (768, 768), (1024, 1024)),
    ("bf16", 9): ((1024, 1024),),
    # bf16 + 4 (ULTRA): direct blinded gate vs FAST at 512x512 only (1/0/23, 2026-09-29). REJECTED at 768x768 and
    # 1024x1024 (text/object-resolution failures: ghost duplicate text, malformed glyphs), so NOT listed there.
    ("bf16", 4): ((512, 512),),
    # bf16 + 5 (BALANCED): direct blinded gate vs FAST at 1024x1024 (0/0/24, Stage B 2026-09-29). NOT listed at
    # 768x768 (Stage B narrowest pass 3/0/21, then the focused confirmation was NOT CONFIRMED, 3/1/28:
    # step-count-quality-gate/results.md) nor at 512x512 (dominated by ULTRA; no production use).
    ("bf16", 5): ((1024, 1024),),
}
MAX_SEED = 2**32 - 1
WORKER_MODULE = "photogen.runtimes.mflux_zimage_worker"
KILL_GRACE_SECONDS = 10
WORKER_TIMEOUT_SECONDS = 30 * 60  # generous upper bound (sustained 1024² ≈ 134 s); guards against hangs


class MFluxZImageRuntime(ImageRuntime):
    name = "mflux-zimage-turbo"
    task = TEXT_TO_IMAGE

    def __init__(self, config: AppConfig):
        self.cfg = config
        self.m = config.backend
        self.text_encoders = load_registry(config.root / "config" / "text-encoders.json", config.root)

    @property
    def backend_id(self) -> str:
        return self.m.backend_id

    # ---------- capabilities / health ----------
    def capabilities(self) -> Capabilities:
        return Capabilities(
            runtime="mflux",
            runtime_version=self.m.packages["mflux"],
            supported_models=(f"{self.m.model_name} ({self.m.model_repo}@{self.m.model_revision[:7]})",),
            supported_tasks=("text-to-image",),
            validated_resolutions=self.m.validated_resolutions,
            supports_seed=True,
            supports_negative_prompt=False,
            supports_guidance=False,
            supports_editing=False,
            supports_lora=False,
            output_formats=("png",),
            precisions=PRECISIONS,
            profiles={k: dict(v) for k, v in PROFILES.items()},
            text_encoders=(STOCK, *sorted(n for n, e in self.text_encoders.items() if e.enabled)),
            memory_profile={"low_ram": True, "transformer_release": True,
                            "measured_peak_footprint_gb_1024": {"fp32": 6.56, "bf16": 5.84},
                            "measured_peak_footprint_gb_512": {"fp32": 5.93, "bf16": 5.41},
                            "concurrency": 1, "source": "research/MFLUX-ZIMAGE-RESULTS.md"},
        )

    def health(self, full_verify: bool = False) -> RuntimeHealth:
        checks: dict = {}
        versions = check_versions(self.m)
        checks["versions"] = {"ok": all(v["ok"] for v in versions.values()), "detail": versions}
        checks["entry_point"] = {"ok": importlib.util.find_spec(self.m.entry_point.split(":")[0]) is not None,
                                 "detail": self.m.entry_point}
        if not self.m.model_path.is_dir():
            checks["model"] = {"ok": False, "detail": "model directory missing (will not be downloaded automatically)"}
        else:
            t = time.perf_counter()
            files = verify_model_files(self.m, self.cfg.integrity_cache_path, full=full_verify)
            bad = [f.__dict__ for f in files if not f.ok]
            checks["model"] = {"ok": not bad, "detail": {
                "revision": self.m.model_revision, "files": len(files), "failed": bad,
                "hashed_now": sum(f.hashed for f in files), "seconds": round(time.perf_counter() - t, 2)}}
        checks["mflux_capabilities"] = self._capability_crosscheck()
        checks["low_ram"] = {"ok": self.m.low_ram, "detail": "--low-ram is always passed"}
        checks["offline"] = {"ok": True, "detail": "workers run with HF_HUB_OFFLINE=1"}
        return RuntimeHealth(ok=all(c["ok"] for c in checks.values()), checks=checks)

    def _capability_crosscheck(self) -> dict:
        """Cross-check our parameter policy against mflux's own declarations (`mflux-capabilities`, ADAPTED
        from the approach in fxd0h/ComfyUI-mflux-AnyModel). Runs in a short-lived subprocess so the server
        process never imports mflux/torch. Drift (e.g. mflux starting to honor --negative-prompt) is reported,
        not auto-adapted."""
        code = ("import json;from mflux.cli.capabilities import describe_command;"
                "print(json.dumps(describe_command('mflux-generate-z-image-turbo',"
                "'mflux.models.z_image.cli.z_image_turbo_generate')))")
        try:
            out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60,
                                 env={**os.environ, "HF_HUB_OFFLINE": "1"})
            desc = json.loads(out.stdout)
        except (OSError, subprocess.SubprocessError, ValueError) as e:
            return {"ok": False, "detail": f"could not query mflux capabilities: {e}"}
        status = {o["flag"]: o["status"] for o in desc.get("options", [])}
        ignored = {f for f, s in status.items() if s == "ignored"}
        expected_ignored = {"--negative-prompt", "--guidance"}
        required_honored = ["--low-ram", "--steps", "--seed", "--width", "--height", "--model", "--base-model",
                            "--output", "--prompt"]
        problems = []
        if ignored != expected_ignored:
            problems.append(f"mflux ignored-option set changed: {sorted(ignored)} (expected {sorted(expected_ignored)})")
        problems += [f"{f} is not honored by mflux" for f in required_honored if status.get(f) != "honored"]
        return {"ok": not problems, "detail": problems or {"ignored_by_mflux": sorted(ignored),
                                                           "verified_honored": required_honored}}

    # ---------- request normalization ----------
    def normalize(self, params: dict, defaults: dict) -> GenerationRequest:
        for k, why in REJECTED.items():
            if k in params and params[k] not in (None, ""):
                if k == "low_ram" and params[k] is True:
                    continue
                raise UnsupportedParameterError(f"'{k}' is not supported: {why}", parameter=k)
        unknown = sorted(set(params) - ACCEPTED - set(REJECTED))
        if unknown:
            raise UnsupportedParameterError(f"unknown parameter(s): {', '.join(unknown)}", parameters=unknown)

        task = params.get("task", TEXT_TO_IMAGE)
        if task != TEXT_TO_IMAGE:
            raise UnsupportedParameterError(f"task '{task}' is not supported by this backend")
        prompt = params.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValidationError("'prompt' must be a non-empty string")
        if len(prompt) > 4000:
            raise ValidationError("'prompt' is longer than 4000 characters (text encoder max is 512 tokens)")

        width = _as_int(params.get("width", defaults["width"]), "width")
        height = _as_int(params.get("height", defaults["height"]), "height")
        profile = params.get("profile")
        if profile is not None:
            if profile not in PROFILES:
                raise ValidationError(f"profile must be one of {', '.join(PROFILES)}")
            for k, v in PROFILES[profile].items():
                if k in params and params[k] not in (None, v):
                    raise ValidationError(f"profile '{profile}' fixes {k}={v}; got {k}={params[k]!r}")
            params = {**params, **PROFILES[profile]}
        steps = _as_int(params.get("steps", defaults["steps"]), "steps")
        precision_param = params.get("precision", "fp32")
        combo_res = VALIDATED_COMBINATIONS.get((precision_param, steps))
        allow_exp = bool(params.get("allow_experimental", False))
        warnings: list[str] = []

        validated_res = (width, height) in self.m.validated_resolutions
        if not validated_res:
            m = self.m
            if width % m.dimension_multiple or height % m.dimension_multiple:
                raise ValidationError(f"width and height must be multiples of {m.dimension_multiple}")
            if not (m.min_dimension <= width <= m.max_dimension and m.min_dimension <= height <= m.max_dimension):
                raise ValidationError(f"each dimension must be within {m.min_dimension}..{m.max_dimension}")
            if width * height > m.max_pixels:
                raise ValidationError(f"{width}x{height} exceeds the largest validated pixel count ({m.max_pixels});"
                                      " larger images are not supported on this 16 GB machine")
            if not allow_exp:
                raise ValidationError(f"{width}x{height} is not a validated resolution "
                                      f"({', '.join(f'{a}x{b}' for a, b in m.validated_resolutions)}); "
                                      "pass allow_experimental=true to run it as an experimental request")
            warnings.append(f"experimental resolution {width}x{height} (not research-validated)")
        if not 1 <= steps <= 50:
            raise ValidationError("steps must be within 1..50")
        steps_validated = bool(combo_res and (width, height) in combo_res)
        if combo_res and not steps_validated:
            sizes = ", ".join(f"{a}x{b}" for a, b in combo_res)
            if not allow_exp:
                raise ValidationError(f"{precision_param} + {steps} steps is validated only at {sizes}; "
                                      f"pass allow_experimental=true to run it at {width}x{height}")
            warnings.append(f"{precision_param} + {steps} steps is validated only at {sizes}; "
                            f"{width}x{height} is unvalidated")
        elif not combo_res:
            if not allow_exp:
                raise ValidationError(f"{precision_param} + {steps} steps is not a validated combination; "
                                      "pass allow_experimental=true to run it as an experimental request")
            warnings.append(f"experimental combination {precision_param} + {steps} steps (not research-validated)")

        seed_param = params.get("seed", defaults["seed"])
        if seed_param in (None, "random"):
            seed, seed_source = secrets.randbelow(MAX_SEED + 1), "random"
        else:
            seed = _as_int(seed_param, "seed")
            if not 0 <= seed <= MAX_SEED:
                raise ValidationError(f"seed must be within 0..{MAX_SEED}")
            seed_source = "explicit"

        fmt = str(params.get("output_format", "png")).lower()
        if fmt != "png":
            raise UnsupportedParameterError(f"output_format '{fmt}' is not supported (png only)")
        name = params.get("output_name")
        if name is not None and (not isinstance(name, str) or not name or "/" in name or name.startswith(".")
                                 or len(name) > 100):
            raise ValidationError("output_name must be a plain file name without path separators")

        precision = params.get("precision", "fp32")
        if precision not in PRECISIONS:
            raise ValidationError(f"precision must be one of {', '.join(PRECISIONS)}")
        text_encoder = params.get("text_encoder", STOCK)
        if text_encoder != STOCK:
            entry = self.text_encoders.get(text_encoder) if isinstance(text_encoder, str) else None
            if entry is None or not entry.enabled:
                avail = ", ".join((STOCK, *sorted(n for n, e in self.text_encoders.items() if e.enabled)))
                raise ValidationError(f"text_encoder must be one of: {avail}")

        return GenerationRequest(task=task, prompt=prompt, width=width, height=height, steps=steps, seed=seed,
                                 seed_source=seed_source, output_format=fmt,
                                 validated=validated_res and steps_validated,
                                 warnings=tuple(warnings), output_name=name, precision=precision,
                                 text_encoder=text_encoder, profile=profile)

    # ---------- generation ----------
    def generate(self, job_id: str, request: GenerationRequest, output_path: str, work_dir: str,
                 cancel: CancelToken) -> GenerationResult:
        work = Path(work_dir)
        work.mkdir(parents=True, exist_ok=True)
        req_file, res_file, log_file = work / "worker-request.json", work / "worker-result.json", work / "worker.log"
        res_file.unlink(missing_ok=True)
        model_path, te_info = self.m.model_path, {"name": STOCK}
        if request.text_encoder != STOCK:
            entry = self.text_encoders[request.text_encoder]
            te_info = {"name": entry.name, **verify_entry(entry, self.m.model_path, self.cfg.integrity_cache_path),
                       **entry.info}
            model_path = entry.composite_path
        req_file.write_text(json.dumps({
            "model_path": str(model_path), "base_model": self.m.base_model, "prompt": request.prompt,
            "width": request.width, "height": request.height, "steps": request.steps, "seed": request.seed,
            "precision": request.precision, "release_transformer": True,  # production default (exact fix)
            "output_path": output_path}, indent=1))

        env = {k: v for k, v in os.environ.items() if not k.startswith(("HF_", "GGML_", "LOWRAM", "MLX_"))}
        env.update({"HF_HUB_OFFLINE": "1", "HF_HUB_DISABLE_TELEMETRY": "1",
                    "HF_HOME": str(self.cfg.root / "mflux" / "hf"),
                    "PYTHONPATH": str(Path(__file__).resolve().parents[2]),
                    "TQDM_DISABLE": "0"})
        cmd = [sys.executable, "-m", WORKER_MODULE, str(req_file), str(res_file)]
        log.debug("job %s: launching worker %s", job_id, cmd)
        t0 = time.perf_counter()
        with log_file.open("wb") as lf:
            proc = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT, env=env, cwd=str(work),
                                    start_new_session=True)
            cancel.on_cancel(lambda: _terminate(proc))
            try:
                rc = proc.wait(timeout=WORKER_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                _terminate(proc)
                raise GenerationError(f"worker exceeded {WORKER_TIMEOUT_SECONDS}s and was terminated",
                                      log=str(log_file))
        wall = round(time.perf_counter() - t0, 3)
        if cancel.cancelled:
            Path(output_path).unlink(missing_ok=True)
            raise JobCancelledError("cancelled while running")

        try:
            res = json.loads(res_file.read_text())
        except (OSError, ValueError):
            res = {"ok": False, "error": f"worker exited with code {rc} and wrote no result", "error_type": "Crash"}
        if rc != 0 or not res.get("ok"):
            detail = res.get("error") or f"exit code {rc}"
            if rc < 0:
                detail = f"worker killed by signal {-rc} (possible out-of-memory or crash); {detail}"
            raise GenerationError(f"generation failed: {detail}", error_type=res.get("error_type"),
                                  exit_code=rc, log=str(log_file))

        check_worker_versions(res.get("versions"), self.m.packages, self.m.backend_id)
        ident = inspect_image(Path(output_path))
        check_output(ident, request.width, request.height)
        return GenerationResult(
            output_path=output_path, width=ident.width, height=ident.height,
            pixel_sha256=ident.pixel_sha256, file_sha256=ident.file_sha256, generation_seconds=wall,
            phases=res.get("phases", {}), step_seconds=res.get("step_seconds", []),
            memory={"peak_footprint_gb": res.get("peak_footprint_gb"), "mlx_peak_gb": res.get("mlx_peak_gb")},
            # identity stamped from the trusted local manifest (the sidecar, photogen.generation/1, is unchanged)
            runtime_info={"runtime": "mflux", "versions": res.get("versions"), "device": res.get("mlx_device"),
                          "backend_id": self.m.backend_id, "model_manifest_sha256": self.m.sha256,
                          "model": self.m.model_name, "model_repo": self.m.model_repo,
                          "model_revision": self.m.model_revision, "quantization": self.m.quantization,
                          "model_path": str(model_path), "text_encoder": te_info},
            effective_parameters={"guidance": self.m.guidance, "scheduler": self.m.scheduler, "low_ram": True,
                                  "precision": res.get("precision"), "dit_dtypes": res.get("dit_dtypes"),
                                  "transformer_release": res.get("transformer_release"),
                                  "compile_calls": res.get("compile_calls"),
                                  "argv": res.get("argv")},
        )

    # ---------- metadata sidecar (schema photogen.generation/1; unchanged since v1) ----------
    def sidecar(self, job_id: str, req: GenerationRequest, result: GenerationResult, before: dict,
                after: dict) -> dict:
        caps = self.capabilities()
        m = self.m
        return {
            "schema": "photogen.generation/1",
            "timestamp": utcnow(),
            "job_id": job_id,
            "status": JobStatus.COMPLETED.value,
            "runtime": caps.runtime,
            "runtime_version": caps.runtime_version,
            "runtime_versions": result.runtime_info.get("versions"),
            "model": m.model_name,
            "model_repo": m.model_repo,
            "model_revision": m.model_revision,
            "quantization": m.quantization,
            "task": req.task,
            "prompt": req.prompt,
            "negative_prompt": None,  # not supported by this backend (requests containing one are rejected)
            "width": req.width,
            "height": req.height,
            "steps": req.steps,
            "guidance": result.effective_parameters.get("guidance"),
            "scheduler": result.effective_parameters.get("scheduler"),
            "low_ram": result.effective_parameters.get("low_ram"),
            "profile": req.profile,
            "precision": req.precision,
            "text_encoder": result.runtime_info.get("text_encoder", {"name": req.text_encoder}),
            "seed": req.seed,
            "seed_source": req.seed_source,
            "validated_configuration": req.validated,
            "warnings": list(req.warnings),
            "generation_time_seconds": result.generation_seconds,
            "phases": result.phases,
            "step_seconds": result.step_seconds,
            "memory": result.memory,
            "output_path": result.output_path,
            "pixel_sha256": result.pixel_sha256,
            "file_sha256": result.file_sha256,
            "system_before": before,
            "system_after": after,
            "reproduce": {"cli": _repro_cli(req)},
        }


def _repro_cli(req: GenerationRequest) -> str:
    prompt = req.prompt.replace("'", "'\\''")
    extra = " --allow-experimental" if not req.validated else ""
    if req.profile:
        extra += f" --profile {req.profile}"
    elif req.precision != "fp32":
        extra += f" --precision {req.precision}"
    if req.text_encoder != "stock":
        extra += f" --text-encoder {req.text_encoder}"
    steps = "" if req.profile else f" --steps {req.steps}"
    return (f"bin/photo-gen generate --prompt '{prompt}' --width {req.width} --height {req.height}"
            f"{steps} --seed {req.seed}{extra}")


def _as_int(v, name: str) -> int:
    if isinstance(v, bool):
        raise ValidationError(f"'{name}' must be an integer")
    try:
        iv = int(v)
    except (TypeError, ValueError):
        raise ValidationError(f"'{name}' must be an integer") from None
    if isinstance(v, float) and v != iv:
        raise ValidationError(f"'{name}' must be an integer")
    return iv


def _terminate(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
        try:
            proc.wait(timeout=KILL_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
