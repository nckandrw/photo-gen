# photo-gen component sources & sourcing decisions

**Started:** 2026-09-24, photo-gen 0.1.0. Applies the architecture addendum ("our chassis, best OEM parts").
**Decision vocabulary:** REUSE / ADAPT / WRAP / FORK / BUILD / STUDY (reference only).
**No third-party source code has been copied into photo-gen.** Where an idea was adapted, it's noted as such and nothing was copied.

## 1. Subsystem decisions

| Subsystem | Decision | Component | Evidence / rationale |
|---|---|---|---|
| Diffusion inference (Z-Image-Turbo) | **REUSE** | mflux 0.20.0 (MIT) + MLX 0.32.2 / mlx-metal 0.32.2 (MIT), unmodified | Research-validated (pixel-deterministic, 7.3 GB, 84.6 / 133.7 s). The photo-gen worker calls mflux's own Turbo CLI entry point `main()` with the validated arguments. |
| Runtime lifecycle (process-per-job, `--low-ram`) | **BUILD** | `app/photogen/runtimes/mflux_zimage*.py` | Every reference keeps a model resident in-process: comfyui-zimage-mlx `_PIPELINE_CACHE`; mflux-webui `ModelCache` with idle TTL. None apply `--low-ram`'s MemorySaver, which deletes the TE per run and can't coexist with in-process reuse. Without `--low-ram` this Mac measured 12.81 GB footprint and critical pressure. Cost of our design: ≈2.6 s/job (≈3% at 1024²). Benefits: exact validated memory profile, SIGTERM cancellation, crash isolation. **Parity gate passed** (`PHOTO-GEN-PARITY-20260924.md`). |
| Parameter/capability policy | **ADAPT** (idea, no code) | Idea from fxd0h/ComfyUI-mflux-AnyModel `capability.py`: use mflux's own declarations as ground truth. Source of truth: mflux's `mflux-capabilities` (`mflux.cli.capabilities.describe_command`) | At startup photo-gen cross-checks its rejected-parameter table against mflux (`--negative-prompt` and `--guidance` are "ignored" for the Turbo CLI; all required flags "honored"). Drift is reported, not auto-adapted. Runs in a short subprocess so the server never imports mflux/torch. |
| Job queue / state machine | **BUILD** | `app/photogen/jobs.py`, `store.py` | Alternatives: mflux-webui (in-memory, single thread, no persistence, no running-job cancel; mflux 0.18.1). ComfyUI's queue (GPL-3.0, tied to its torch execution engine). Neither offers persistence plus a cross-process single-GPU guarantee. Ours: persistent SQLite, atomic transitions, flock GPU lock across CLI and server, orphan recovery. Parity: 30 unit/API tests. |
| HTTP server | **REUSE** | Python stdlib `http.server` (PSF) | Single-user localhost API. Adds no dependency to the validated venv. Limitation: no websocket/progress streaming (long-poll `?wait=` instead). Revisit (e.g. aiohttp) only if streaming progress becomes a requirement. |
| Persistence | **REUSE** | Python stdlib `sqlite3` (SQLite, public domain) + JSON sidecars | Job history, status, and search by pixel hash. |
| Config | **REUSE** | stdlib `tomllib` + JSON manifest | — |
| Image decode / hashing | **REUSE** | Pillow 12.3.0 (already in the validated venv; MIT-CMU/HPND licence; GitHub reports NOASSERTION) | Pixel SHA-256 uses the same definition as the research tool (raw 8-bit RGB), so hashes are comparable with research evidence. |
| Image metadata | **REUSE + BUILD** | mflux's own PNG metadata (eXIf/iTXt/tEXt, written by mflux) is kept untouched. photo-gen adds a JSON sidecar (`photogen.generation/1`). | Adding our own PNG chunks would change file bytes (not pixels). ComfyUI's `prompt`/`workflow` PNG text-chunk convention (STUDY) only makes sense once a workflow graph exists. |
| Model integrity / version guard | **BUILD** | `app/photogen/integrity.py` | No reference implements it (comfyui-zimage-mlx and mflux-webui download on demand). Full sha256/git-blob verification with an inode/size/mtime cache. |
| System telemetry | **BUILD** | `app/photogen/system.py` | macOS built-ins only (sysctl, vm_stat, memory_pressure, pmset). No temperature is fabricated. |
| Workflow / graph engine | **STUDY, not built** | ComfyUI v0.37.0 (GPL-3.0) API-format graphs | A single-model text-to-image service doesn't need a graph engine yet. If needed later, prefer ComfyUI-compatible graph JSON over a bespoke format. |
| Frontend / GUI | **not built** (future: WRAP) | Option: ComfyUI frontend in a *separate* env, with a thin photo-gen node that calls the photo-gen HTTP API | Keeps the GPL boundary at a process/HTTP boundary and keeps ComfyUI's torch/av/scipy/SQLAlchemy stack out of the validated venv. The node itself would need license review (GPL context). |
| Model downloading | **not built, by policy** | — | Offline by design: missing or mismatched models are reported, never auto-fetched (`research/fetch.sh` remains the manual, hash-verified path). |

## 2. Component records

```text
component: mflux
source_repository: https://github.com/mflux-community/mflux
source_revision: v.0.20.0 (PyPI wheel sha256 5d60a278…; sdist 8fec3407…; installed tree byte-identical to audited sdist)
license: MIT
what_we_reused: inference (Z-Image-Turbo CLI entry point, --low-ram MemorySaver, MLX models); mflux-capabilities declarations
why: research-validated, pixel-deterministic, fastest measured path on this Mac
known_limitations: --low-ram's transformer release before VAE is ineffective (closure reference; ~3.5 GB stays resident);
                   hard deps on torch/transformers (imported, not used for compute); BatterySaver stops runs at ≤5% battery;
                   thermal throttling to ~134 s/image sustained (hardware)
dependency_impact: 56 packages in the project-local venv (already present; photo-gen adds none)
performance_impact: baseline
whether_modified: no (runtime probes wrap methods in the worker process only)

component: MLX / mlx-metal
source_repository: https://github.com/ml-explore/mlx
source_revision: 0.32.2 (macosx_26_0 wheel; contains NAX kernels)
license: MIT
what_we_reused: array framework / Metal backend (via mflux)
whether_modified: no

component: ComfyUI-mflux-AnyModel (reference)
source_repository: https://github.com/fxd0h/ComfyUI-mflux-AnyModel
source_revision: 3b3e67813e67b375e24761ecb8b9ec1ac335c381
license: MIT
what_we_reused: IDEA ONLY — derive capability policy from mflux's own declarations; no code copied
known_limitations: in-process model reuse; requires ComfyUI
whether_modified: n/a

component: comfyui-zimage-mlx (reference)
source_repository: https://github.com/tanis2000/comfyui-zimage-mlx (pyproject points at vrgamegirl19/comfyui-zimage-mlx — provenance oddity)
source_revision: b707cc564fedc7c4e44be8b219af5b6314a1899a
license: MIT
what_we_reused: nothing. Studied as the reference for "ComfyUI node → mflux ZImage → MLX".
lessons (do-not-build-it-this-way): in-process pipeline cache without --low-ram (12.8 GB-class footprint on this Mac);
   default num_inference_steps=4 (Turbo spec is 9); exposes guidance/negative_prompt that Turbo ignores;
   dimensions up to 2048 with no memory guard; default 8-bit third-party repo downloaded on demand; mflux unpinned.

component: Mflux-ComfyUI (reference)
source_repository: https://github.com/raysers/Mflux-ComfyUI
source_revision: 0112a4ef9a6b663b5e46dc98476aff77de5cdd41 (last commit 2024-12-05)
license: MIT
what_we_reused: nothing — pins mflux==0.4.1 (would downgrade the validated runtime); no Z-Image support. Historical reference only.

component: mflux-webui (reference)
source_repository: https://github.com/wyf0931/mflux-webui
source_revision: ecb285688c88caf891362908e5322f28a21071f6
license: MIT
what_we_reused: nothing. Studied: Flask + single worker thread + in-memory task list + idle-TTL model cache; pins mflux==0.18.1.

component: MFLUX-WEBUI (reference)
source_repository: https://github.com/CharafChnioune/MFLUX-WEBUI
source_revision: fab6cc1791cbe95a93f8cad46661a369b200bd96
license: NONE declared → all rights reserved; study only, no code reuse possible
notes: pins mflux>=0.18,<0.19 and mlx 0.30.x; broad feature surface (managers per model family)

component: ComfyUI (reference)
source_repository: https://github.com/Comfy-Org/ComfyUI
source_revision: v0.37.0 = 73c9bad4d21e7addbe1d13bc92eee0f1431b017d
license: GPL-3.0
what_we_reused: nothing (studied: /prompt, /queue, /history, /interrupt, /api/jobs/{id}, /api/jobs/{id}/cancel, /view, /system_stats;
   PNG text-chunk metadata `prompt` + `workflow`)
dependency_impact if adopted: torch, torchvision, torchaudio, av, scipy, SQLAlchemy, alembic, frontend packages → separate env required
```

## Additions — research pass 2 (2026-09-24/25)
```
component: bf16 hidden-stream patch (photo-gen worker, opt-in `precision: bf16`)
classification: BUILD (4 in-process casts around unmodified mflux 0.20.0 modules; no mflux files changed)
evidence: research/experiments/E02-RESULTS.md, bf16-quality-report.md (gate passed; parity: photo-gen output == experiment output)

component: text-encoder registry + composite model directory (photo-gen `text_encoder`)
classification: BUILD (config/text-encoders.json with pinned digests; symlinked composite; verified per job)

component: heretic V2 text encoder (registered, disabled)
source_repository: https://huggingface.co/Lockout/qwen3-4b-heretic-zimage (subfolder qwen-4b-zimage-hereticV2)
source_revision: 1dd80c38813bd0f791c5abfd3bf605f739cf9f84
license: base model Qwen3-4B is Apache-2.0; the derivative repo's own license was NOT present in the 12 downloaded files → verify on the model card before any redistribution
local artifact: models/mflux/text-encoders/heretic-v2-q4/0.safetensors sha256 c13dc3e0fd09814caf8b1248bfcb8b3822719882461d3dd340c8b53eb7931bc6 (converted locally, see te-heretic-v2-report.md)
```
