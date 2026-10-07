"""Qwen-Image-2.1 instruction editing on mflux 0.21.0 / MLX 0.32.2. RESEARCH / EXPERIMENTAL (Phase 4).

Selected in research/qwen/QWEN-SOURCE-AUDIT.md. The checkpoint is under the Qwen Research License
(non-commercial: research or evaluation only); it is never committed or redistributed.

Isolation: this backend runs in its OWN project-local venv (mflux-qwen/.venv, mflux 0.21.0). The production venv
(mflux/.venv, mflux 0.20.0) is never touched: 0.21.0 changes Z-Image numerics (upstream #802/#803). The PHOTO-GEN
process imports neither venv's mflux; each job runs mflux_qwen_edit_worker.py in a fresh process of this backend's
interpreter, exactly like the Z-Image worker (memory returns to the OS, cancellation is a killpg).

The canonical workflow is the upstream-equivalent one only (Diffusers QwenImage21Pipeline @ 80c7ed2 defaults):
one input image + an instruction, 40 steps, no CFG (guidance 1.0), prefix KV cache on, linear flow-match schedule,
output size derived from output_resolution and the input's aspect ratio. mflux-only additions (masks, auto-mask,
strength, prompt enhancement, verification, step cache) are rejected, not ignored.

Every edit is experimental (validated=false) and needs allow_experimental until an edit configuration passes a gate.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import secrets
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from ..config import AppConfig, ModelFile
from ..errors import (GenerationError, IdentityMismatchError, JobCancelledError, OutputCorruptedError,
                      RuntimeUnavailableError, UnsupportedParameterError, ValidationError)
from ..imaging import check_output, inspect_image
from ..inputs import stage_input_image, verify_staged
from ..integrity import _check_file
from ..models import EditRequest, GenerationResult, JobStatus, utcnow
from ..tasks import IMAGE_EDIT
from .base import CancelToken, Capabilities, ImageRuntime, RuntimeHealth, check_worker_versions
from .mflux_zimage import KILL_GRACE_SECONDS, MAX_SEED, _as_int, _terminate

log = logging.getLogger(__name__)

MANIFEST_NAME = "backend-qwen21-edit-mflux.json"
WORKER_MODULE = "photogen.runtimes.mflux_qwen_edit_worker"
WORKER_TIMEOUT_SECONDS = 90 * 60  # generous upper bound; guards against hangs
# Lifetime-only memory fix (worker _defer_transformer_load), production default since 2026-10-07: the q4 DiT is
# read from the export at denoising step 0 instead of at load, so it is never resident together with the text
# encoder. Pixel-identical (RGB and RGBA) to the stock lifecycle and to the plain mflux CLI; at 512 it lowers the
# peak footprint 12.63 -> 8.85 GB and removed the critical-pressure episode (research/qwen/QWEN-EDITING-BASELINE.md).
DEFER_TRANSFORMER_LOAD = True

ACCEPTED = {"task", "prompt", "image", "seed", "steps", "output_resolution", "output_format", "output_name",
            "allow_experimental"}
_NO_CFG = "Qwen-Image-2.1 is sampled without guidance (official default true_cfg_scale=1.0); CFG is not offered"
_MFLUX_ONLY = "an mflux-only addition (not part of the upstream pipeline); not enabled for editing"
REJECTED = {
    "negative_prompt": _NO_CFG, "guidance": _NO_CFG, "cfg": _NO_CFG, "cfg_scale": _NO_CFG, "true_cfg_scale": _NO_CFG,
    "scheduler": "the schedule is fixed to the parity-tested linear flow-match default (mflux 0.21.0 ignores "
                 "--scheduler for edits: mflux #831)",
    "low_ram": "--low-ram is mandatory on this 16 GB machine",
    "model": "only the pinned Qwen-Image-2.1 q4 export is available for editing",
    "quantize": "quantization is fixed by the pinned q4 export",
    "lora": "LoRA is not validated for editing", "loras": "LoRA is not validated for editing",
    "images": "multi-reference editing is not enabled (one input image)",
    "image_paths": "multi-reference editing is not enabled (one input image)",
    "width": "the output size is derived from output_resolution and the input's aspect ratio (upstream behaviour)",
    "height": "the output size is derived from output_resolution and the input's aspect ratio (upstream behaviour)",
    "use_kv_cache": "the prefix KV cache is always on (upstream default; cached and uncached runs differ)",
    "mask": _MFLUX_ONLY, "mask_image": _MFLUX_ONLY, "auto_mask": _MFLUX_ONLY, "strength": _MFLUX_ONLY,
    "enhance_prompt": _MFLUX_ONLY, "verify": _MFLUX_ONLY, "use_step_cache": _MFLUX_ONLY, "step_cache": _MFLUX_ONLY,
    "precision": "not applicable to the Qwen edit backend (bf16 activations, q4 weights, fp32 VAE)",
    "text_encoder": "not applicable to the Qwen edit backend",
    "profile": "no edit profiles exist yet",
}
EXPERIMENTAL_WARNING = ("image-edit with Qwen-Image-2.1 is RESEARCH/EXPERIMENTAL: no edit configuration has passed a "
                        "quality gate (research/qwen/); Qwen Research License (non-commercial)")
# Numeric precision of the pinned export as executed by mflux 0.21.0 (part of the configuration identity).
PRECISION = "q4 weights (MLX affine, group 64) for the DiT and the Qwen3-VL encoder; bf16 activations; fp32 VAE"
WORKER_PATH = Path(__file__).with_name("mflux_qwen_edit_worker.py")


def canonical_sha256(obj) -> str:
    """sha256 of the canonical JSON form of obj (sorted keys, no whitespace): the identity of a configuration."""
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                          .encode()).hexdigest()


@dataclass(frozen=True)
class QwenEditManifest:
    """Pinned identity of the edit backend: interpreter, packages, source checkpoint, q4 export. Read-only."""
    backend_id: str
    status: str
    interpreter: Path
    python_version: str
    packages: dict
    entry_point: str
    model_name: str
    model_repo: str
    model_revision: str
    model_license: str
    model_path: Path
    quantization: str
    model_files: tuple[ModelFile, ...]
    defaults: dict
    limits: dict
    raw: dict

    @classmethod
    def load(cls, path: Path, root: Path) -> "QwenEditManifest":
        raw = json.loads(Path(path).read_text())
        rt, m = raw["runtime"], raw["model"]
        return cls(backend_id=raw["backend_id"], status=raw["status"], interpreter=root / rt["interpreter"],
                   python_version=rt["python"], packages=dict(rt["packages"]), entry_point=rt["entry_point"],
                   model_name=m["name"], model_repo=m["repo"], model_revision=m["revision"], model_license=m["license"],
                   model_path=(root / m["local_path"]), quantization=m["quantization"],
                   model_files=tuple(ModelFile(**f) for f in m["files"]), defaults=dict(raw["defaults"]),
                   limits=dict(raw["limits"]), raw=raw)


def output_dimensions(resolution: int, ratio: float) -> tuple[int, int]:
    """mflux 0.21.0 QwenImage21LatentCreator.dimensions (= Diffusers calculate_dimensions on resolution², rounded to
    multiples of 32): the reference is resized to this, and it is the output size when width/height are omitted."""
    width = math.sqrt(resolution * resolution * ratio)
    return max(32, round(width / 32) * 32), max(32, round(width / ratio / 32) * 32)


class MFluxQwenImageEditRuntime(ImageRuntime):
    name = "mflux-qwen-image-2.1-edit"
    task = IMAGE_EDIT

    def __init__(self, config: AppConfig, manifest_path: Path | None = None):
        self.cfg = config
        self.manifest_path = Path(manifest_path or config.root / "config" / MANIFEST_NAME)
        self._manifest: QwenEditManifest | None = None
        self._manifest_error: str | None = None
        self._manifest_sha256: str | None = None
        try:
            self._manifest = QwenEditManifest.load(self.manifest_path, config.root)
            self._manifest_sha256 = hashlib.sha256(self.manifest_path.read_bytes()).hexdigest()
        except FileNotFoundError:
            self._manifest_error = f"edit backend manifest {self.manifest_path} not found (backend not installed)"
        except (OSError, KeyError, TypeError, ValueError) as e:
            self._manifest_error = f"cannot load edit backend manifest {self.manifest_path}: {e}"

    @property
    def m(self) -> QwenEditManifest:
        if self._manifest is None:
            raise RuntimeUnavailableError(f"image-edit backend unavailable: {self._manifest_error}")
        return self._manifest

    @property
    def backend_id(self) -> str | None:
        return self._manifest.backend_id if self._manifest else None

    # ---------- authoritative identity (Phase 5) ----------
    def verify_identity(self, request: EditRequest) -> None:
        """A stored edit runs only against the manifest it was submitted under. Rows from before a field existed
        (None) are not rejected for lacking it; any recorded value must equal the trusted local manifest."""
        m = self.m
        current = {"backend_id": m.backend_id, "model": m.model_name, "model_revision": m.model_revision,
                   "manifest_sha256": self._manifest_sha256}
        drift = {k: {"recorded": getattr(request, k), "manifest": v} for k, v in current.items()
                 if getattr(request, k) is not None and getattr(request, k) != v}
        if drift:
            raise IdentityMismatchError("the image-edit backend manifest changed since this job was submitted; "
                                        "resubmit it", drift=drift)

    def configuration(self, req: EditRequest) -> dict:
        """The output-determining identity of an edit configuration (what a quality gate validates), entirely from the
        trusted local manifest plus the request's steps and output budget. Input, instruction and seed are not part
        of it (see edit_identity); memory-lifetime policy is not either: those patches are pixel-identical by their
        parity gates and are recorded separately under `execution`."""
        m = self.m
        return {"task": IMAGE_EDIT, "backend_id": m.backend_id, "model": m.model_name, "model_repo": m.model_repo,
                "model_revision": m.model_revision, "model_manifest_sha256": self._manifest_sha256,
                "quantization": m.quantization, "precision": PRECISION, "runtime": m.raw["runtime"]["name"],
                "runtime_versions": dict(sorted(m.packages.items())), "entry_point": m.entry_point,
                "base_model": m.defaults["base_model"], "steps": req.steps, "guidance": m.defaults["guidance"],
                "scheduler": m.defaults["scheduler"], "use_kv_cache": True, "low_ram": True,
                "output_resolution": req.output_resolution, "adapters": []}

    def edit_identity(self, req: EditRequest) -> dict:
        """Everything that determines an edit's pixels: configuration + input pixels + instruction + seed (+ the size
        derived from the input's aspect ratio). Same edit_id on the same machine/software => same pixels."""
        return {"configuration_id": canonical_sha256(self.configuration(req)),
                "input_pixel_sha256": req.input_image["pixel_sha256"], "instruction": req.prompt, "seed": req.seed,
                "width": req.width, "height": req.height}

    # ---------- capabilities / health ----------
    def capabilities(self) -> Capabilities:
        m = self._manifest
        return Capabilities(
            runtime="mflux",
            runtime_version=(m.packages.get("mflux") if m else None),
            supported_models=((f"{m.model_name} ({m.model_repo}@{m.model_revision[:7]}; {m.model_license})",)
                              if m else ()),
            supported_tasks=(IMAGE_EDIT,),
            validated_resolutions=(),
            supports_seed=True,
            supports_negative_prompt=False,
            supports_guidance=False,
            supports_editing=True,
            supports_lora=False,
            output_formats=("png",),
            precisions=("bf16",),
            text_encoders=("stock",),
            profiles={},
            memory_profile={"low_ram": True, "status": (m.status if m else "unavailable"),
                            "defaults": (m.defaults if m else {}), "limits": (m.limits if m else {}),
                            "concurrency": 1, "source": "research/qwen/QWEN-EDITING-BASELINE.md"},
        )

    def health(self, full_verify: bool = False) -> RuntimeHealth:
        if self._manifest is None:
            return RuntimeHealth(ok=False, checks={"manifest": {"ok": False, "detail": self._manifest_error}})
        m = self._manifest
        checks: dict = {"manifest": {"ok": True, "detail": str(self.manifest_path.relative_to(self.cfg.root))}}
        if not m.interpreter.is_file():
            checks["interpreter"] = {"ok": False, "detail": f"{m.interpreter} missing (nothing is installed "
                                                            "automatically; see docs/REPRODUCIBILITY.md)"}
        else:
            checks["interpreter"] = self._versions_check()
        if not m.model_path.is_dir():
            checks["model"] = {"ok": False, "detail": "q4 export directory missing (never downloaded automatically)"}
        else:
            t = time.perf_counter()
            files = self._verify_files(full_verify)
            bad = [f.__dict__ for f in files if not f.ok]
            checks["model"] = {"ok": not bad, "detail": {
                "revision": m.model_revision, "files": len(files), "failed": bad,
                "hashed_now": sum(f.hashed for f in files), "seconds": round(time.perf_counter() - t, 2)}}
        checks["low_ram"] = {"ok": True, "detail": "--low-ram is always passed"}
        checks["offline"] = {"ok": True, "detail": "workers run with HF_HUB_OFFLINE=1"}
        return RuntimeHealth(ok=all(c["ok"] for c in checks.values()), checks=checks)

    def _versions_check(self) -> dict:
        """Query the backend interpreter (a separate venv) for its Python and package versions."""
        m = self.m
        code = ("import json,platform,importlib.metadata as md;"
                f"print(json.dumps({{'python':platform.python_version(),"
                f"**{{p:md.version(p) for p in {sorted(m.packages)!r}}}}}))")
        try:
            out = subprocess.run([str(m.interpreter), "-c", code], capture_output=True, text=True, timeout=60,
                                 env=_worker_env(self.cfg))
            found = json.loads(out.stdout)
        except (OSError, subprocess.SubprocessError, ValueError) as e:
            return {"ok": False, "detail": f"could not query {m.interpreter}: {e}"}
        want = {"python": m.python_version, **m.packages}
        detail = {k: {"ok": found.get(k) == v, "expected": v, "found": found.get(k)} for k, v in want.items()}
        return {"ok": all(d["ok"] for d in detail.values()), "detail": detail}

    def _verify_files(self, full: bool):
        try:
            cache = json.loads(self.cfg.integrity_cache_path.read_text()) if self.cfg.integrity_cache_path.exists() \
                else {}
        except (OSError, ValueError):
            cache = {}
        new_cache: dict = {}
        files = [_check_file(self.m.model_path, f, cache, new_cache, full) for f in self.m.model_files]
        try:
            cache.update(new_cache)  # keep entries owned by the Z-Image manifest and the TE registry
            self.cfg.integrity_cache_path.write_text(json.dumps(cache, indent=1))
        except OSError as e:
            log.warning("could not write integrity cache: %s", e)
        return files

    # ---------- request normalization ----------
    def normalize(self, params: dict, defaults: dict) -> EditRequest:
        for k, why in REJECTED.items():
            if k in params and params[k] not in (None, ""):
                if k == "low_ram" and params[k] is True:
                    continue
                raise UnsupportedParameterError(f"'{k}' is not supported for image-edit: {why}", parameter=k)
        unknown = sorted(set(params) - ACCEPTED - set(REJECTED))
        if unknown:
            raise UnsupportedParameterError(f"unknown parameter(s): {', '.join(unknown)}", parameters=unknown)
        task = params.get("task", IMAGE_EDIT)
        if task != IMAGE_EDIT:
            raise UnsupportedParameterError(f"task '{task}' is not supported by the image-edit backend")
        m = self.m  # raises RuntimeUnavailableError (503) if the backend is not installed
        prompt = params.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValidationError("'prompt' (the edit instruction) must be a non-empty string")
        if len(prompt) > 4000:
            raise ValidationError("'prompt' is longer than 4000 characters")
        if "image" not in params:
            raise ValidationError("'image' (absolute path of the input image) is required for image-edit")

        lim = m.limits
        resolution = _as_int(params.get("output_resolution", m.defaults["output_resolution"]), "output_resolution")
        if resolution % 32 or not lim["min_output_resolution"] <= resolution <= lim["max_output_resolution"]:
            raise ValidationError(f"output_resolution must be a multiple of 32 within "
                                  f"{lim['min_output_resolution']}..{lim['max_output_resolution']}")
        steps = _as_int(params.get("steps", m.defaults["steps"]), "steps")
        if not lim["min_steps"] <= steps <= lim["max_steps"]:
            raise ValidationError(f"steps must be within {lim['min_steps']}..{lim['max_steps']}")
        seed_param = params.get("seed", defaults.get("seed", "random"))
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
        if not params.get("allow_experimental", False):
            raise ValidationError("image-edit is RESEARCH/EXPERIMENTAL (no edit configuration is gated yet); "
                                  "pass allow_experimental=true to run it")

        inp, input_warnings = stage_input_image(params["image"], self.cfg.inputs_dir)
        width, height = output_dimensions(resolution, inp.width / inp.height)
        return EditRequest(task=IMAGE_EDIT, prompt=prompt, width=width, height=height, steps=steps, seed=seed,
                           seed_source=seed_source, output_format=fmt, validated=False, input_image=inp.to_dict(),
                           output_resolution=resolution, warnings=(EXPERIMENTAL_WARNING, *input_warnings),
                           output_name=name, backend_id=m.backend_id, model=m.model_name,
                           model_revision=m.model_revision, manifest_sha256=self._manifest_sha256)

    def request_from_dict(self, d: dict) -> EditRequest:
        return EditRequest.from_dict(d)

    # ---------- execution ----------
    def generate(self, job_id: str, request: EditRequest, output_path: str, work_dir: str,
                 cancel: CancelToken) -> GenerationResult:
        m = self.m
        verify_staged(request.input_image["staged_path"], request.input_image["pixel_sha256"])
        bad = [f.__dict__ for f in self._verify_files(False) if not f.ok]
        if bad:
            raise RuntimeUnavailableError("image-edit model files failed verification; nothing was repaired",
                                          failed=bad)
        work = Path(work_dir)
        work.mkdir(parents=True, exist_ok=True)
        req_file, res_file, log_file = work / "worker-request.json", work / "worker-result.json", work / "worker.log"
        res_file.unlink(missing_ok=True)
        req_file.write_text(json.dumps({
            "model_path": str(m.model_path), "base_model": m.defaults["base_model"], "prompt": request.prompt,
            "image_path": request.input_image["staged_path"], "seed": request.seed, "steps": request.steps,
            "output_resolution": request.output_resolution, "output_path": output_path,
            "defer_transformer_load": DEFER_TRANSFORMER_LOAD, "expected_size": [request.width, request.height]},
            indent=1))
        memory_policy = {"defer_transformer_load": DEFER_TRANSFORMER_LOAD}
        cmd = [str(m.interpreter), "-m", WORKER_MODULE, str(req_file), str(res_file)]
        log.debug("job %s: launching edit worker %s", job_id, cmd)
        worker_sha256 = hashlib.sha256(WORKER_PATH.read_bytes()).hexdigest()  # the module this launch executes
        t0 = time.perf_counter()
        with log_file.open("wb") as lf:
            proc = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT, env=_worker_env(self.cfg),
                                    cwd=str(work), start_new_session=True)
            cancel.on_cancel(lambda: _terminate(proc))
            try:
                rc = proc.wait(timeout=WORKER_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                _terminate(proc)
                raise GenerationError(f"edit worker exceeded {WORKER_TIMEOUT_SECONDS}s and was terminated",
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
            raise GenerationError(f"edit failed: {detail}", error_type=res.get("error_type"), exit_code=rc,
                                  log=str(log_file))
        check_worker_versions(res.get("versions"), m.packages, m.backend_id)
        ident = inspect_image(Path(output_path))
        check_output(ident, request.width, request.height)
        alpha = _alpha_identity(Path(output_path))
        return GenerationResult(
            output_path=output_path, width=ident.width, height=ident.height, pixel_sha256=ident.pixel_sha256,
            file_sha256=ident.file_sha256, generation_seconds=wall, phases=res.get("phases", {}),
            step_seconds=res.get("step_seconds", []),
            memory={"peak_footprint_gb": res.get("peak_footprint_gb"), "mlx_peak_gb": res.get("mlx_peak_gb"),
                    "denoise_mlx_peak_gb": res.get("denoise_mlx_peak_gb")},
            runtime_info={"runtime": "mflux", "versions": res.get("versions"), "device": res.get("mlx_device"),
                          "backend_id": m.backend_id, "model": m.model_name, "model_repo": m.model_repo,
                          "model_revision": m.model_revision, "model_license": m.model_license,
                          "quantization": m.quantization, "model_path": str(m.model_path),
                          "interpreter": str(m.interpreter), "output_alpha": alpha,
                          "model_manifest_sha256": self._manifest_sha256, "worker_module": WORKER_MODULE,
                          "worker_sha256": worker_sha256},
            effective_parameters={"guidance": m.defaults["guidance"], "scheduler": m.defaults["scheduler"],
                                  "use_kv_cache": True, "low_ram": True, "vae_tiling": res.get("vae_tiling"),
                                  "output_resolution": request.output_resolution,
                                  "text_encoder_released": res.get("text_encoder_released"),
                                  "transformer_released": res.get("transformer_released"),
                                  "defer_transformer_load": res.get("defer_transformer_load"), "argv": res.get("argv"),
                                  "memory_policy": memory_policy},
        )

    # ---------- metadata sidecar (schema photogen.edit/1) ----------
    def sidecar(self, job_id: str, req: EditRequest, result: GenerationResult, before: dict, after: dict) -> dict:
        m = self.m
        return {
            "schema": "photogen.edit/1",
            "timestamp": utcnow(),
            "job_id": job_id,
            "status": JobStatus.COMPLETED.value,
            "task": req.task,
            "backend_id": m.backend_id,
            "backend_status": m.status,
            "runtime": "mflux",
            "runtime_version": m.packages.get("mflux"),
            "runtime_versions": result.runtime_info.get("versions"),
            "interpreter": result.runtime_info.get("interpreter"),
            "model": m.model_name,
            "model_repo": m.model_repo,
            "model_revision": m.model_revision,
            "model_license": m.model_license,
            "quantization": m.quantization,
            "model_export": m.raw["model"].get("export"),
            # the pinned manifest lists every export file's sha256; all were verified before this run
            "model_manifest": {"path": str(self.manifest_path.relative_to(self.cfg.root))
                               if self.manifest_path.is_relative_to(self.cfg.root) else str(self.manifest_path),
                               "sha256": self._manifest_sha256, "files_verified_before_run": True},
            "prompt": req.prompt,
            "input_image": req.input_image,
            "output_resolution": req.output_resolution,
            "width": req.width,
            "height": req.height,
            "steps": req.steps,
            "guidance": result.effective_parameters.get("guidance"),
            "negative_prompt": None,  # CFG is not offered (requests containing one are rejected)
            "scheduler": result.effective_parameters.get("scheduler"),
            "use_kv_cache": True,
            "low_ram": True,
            "defer_transformer_load": result.effective_parameters.get("defer_transformer_load"),
            "adapters": [],  # no LoRA/adapters
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
            "output_alpha": result.runtime_info.get("output_alpha"),
            # Phase 5 configuration identity (additive). configuration_id: what a gate validates; edit_id: what
            # determines the pixels; execution: how it ran (pixel-neutral by evidence, recorded for audit).
            "configuration": (config := self.configuration(req)),
            "configuration_id": canonical_sha256(config),
            "edit_identity": (ident := self.edit_identity(req)),
            "edit_id": canonical_sha256(ident),
            "execution": {"worker_module": result.runtime_info.get("worker_module"),
                          "worker_sha256": result.runtime_info.get("worker_sha256"),
                          "interpreter": result.runtime_info.get("interpreter"),
                          "memory_policy": result.effective_parameters.get("memory_policy")},
            "determinism":"same input pixels + instruction + seed + steps + resolution + model export on the same "
                           "machine/software are expected to reproduce the same pixels (verified per backend in "
                           "research/qwen/QWEN-EDITING-BASELINE.md); MLX and PyTorch RNGs differ, so seeds do not "
                           "transfer to other implementations",
            "system_before": before,
            "system_after": after,
            "reproduce": {"cli": _repro_cli(req)},
        }


def _alpha_identity(path: Path) -> dict:
    """mflux writes Qwen-Image-2.1 outputs as RGBA. pixel_sha256 covers RGB (the project-wide definition);
    alpha is reported separately so the identity is complete."""
    import hashlib
    with Image.open(path) as im:
        if im.mode != "RGBA":
            return {"mode": im.mode, "has_alpha": False}
        im.load()
        lo, hi = im.getchannel("A").getextrema()
        return {"mode": "RGBA", "has_alpha": True, "alpha_min": lo, "alpha_max": hi, "opaque": lo == 255,
                "rgba_sha256": hashlib.sha256(im.tobytes()).hexdigest()}


def _worker_env(cfg: AppConfig) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("HF_", "GGML_", "LOWRAM", "MLX_", "PYTHON"))}
    env.update({"HF_HUB_OFFLINE": "1", "HF_HUB_DISABLE_TELEMETRY": "1", "HF_HOME": str(cfg.root / "mflux" / "hf"),
                "PYTHONPATH": str(Path(__file__).resolve().parents[2]), "PYTHONDONTWRITEBYTECODE": "1",
                "TQDM_DISABLE": "0"})
    return env


def _repro_cli(req: EditRequest) -> str:
    prompt = req.prompt.replace("'", "'\\''")
    return (f"bin/photo-gen edit --image '{req.input_image['staged_path']}' --prompt '{prompt}' "
            f"--output-resolution {req.output_resolution} --steps {req.steps} --seed {req.seed} --allow-experimental")


__all__ = ["MFluxQwenImageEditRuntime", "QwenEditManifest", "output_dimensions", "KILL_GRACE_SECONDS"]
