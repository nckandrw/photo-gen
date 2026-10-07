# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is
photo-gen is a local image-generation service (CLI + localhost HTTP API) for **one machine**: a MacBook Air M5, 16 GB. It runs Z-Image-Turbo on mflux 0.20.0 / MLX 0.32.2 with the pre-quantized `mflux-community/z-image-turbo-mflux-q4` @ `d2d30500`, always with `--low-ram`.

Since Phase 4 (2026-10-07) it also has an **image-edit task, which is a research opt-in only**. Phase 5's real-photograph gate G2 **REJECTED** it at 512 and 1024 (`research/editing/real-world/results.md`). It runs Qwen-Image-2.1 @ `d26bb61` (Qwen Research License, **non-commercial**), local q4 export, on **mflux 0.21.0 in a separate venv `mflux-qwen/.venv`** (same MLX 0.32.2). PHOTO-GEN is model-selective: one explicitly chosen backend per task (`text-to-image` → Z-Image, `image-edit` → Qwen); no automatic model selection.

The project has two halves:
- `app/`: the production application.
- `research/`: an evidence trail. Every production behaviour has a report behind it.

Git: private repo `nckandrw/photo-gen` (branch `main`); validated builds are tagged `photo-gen-m5-16gb-v1`, `-v2` and `-v3` (v3 = Phase 4 close, `401e400`; immutable; see `docs/RELEASE-NOTES.md`). Model weights, `mflux/` toolchain, `data/`, `outputs/` and research PNGs are not versioned (see `.gitignore`, `docs/REPRODUCIBILITY.md`). Stage files explicitly; never `git add .`.

## Commands
```sh
bin/photo-gen verify [--full]          # versions + model hashes + mflux capability cross-check
bin/photo-gen serve                    # API on 127.0.0.1:8765
bin/photo-gen generate -p "..." --seed 42 [--profile reference|fast|balanced|ultra] [--json]
bin/photo-gen edit --image <abs-or-rel path> -p "<instruction>" --seed 42 [--output-resolution 512|…|1024] --allow-experimental [--json]
bin/photo-gen verify --edit [--full]   # the image-edit backend: its venv versions + 18 export hashes
bin/photo-gen capabilities | jobs | job <id> | status

# tests (stdlib unittest; FakeRuntime means no GPU is needed, except test_worker_lifetime, which imports mflux)
cd app/tests && PHOTOGEN_ROOT=../.. PYTHONPATH=..:. ../../mflux/.venv/bin/python3.12 -m unittest -v
# single test
cd app/tests && PHOTOGEN_ROOT=../.. PYTHONPATH=..:. ../../mflux/.venv/bin/python3.12 -m unittest test_core.ValidationTests.test_profiles
```
- **Interpreter:** always use `mflux/.venv/bin/python3.12`. System `python3` lacks PIL and mlx. `bin/photo-gen` sets `PYTHONPATH=app` and `HF_HUB_OFFLINE=1`.
- **Edit-backend interpreter:** `mflux-qwen/.venv/bin/python3.12` (mflux 0.21.0). Only the edit worker and Qwen research scripts run in it. **Never run Z-Image in it, and never install mflux 0.21.0 into `mflux/.venv`**: 0.21.0's bf16-stream default (#803) and lifetime change (#802) would change every REFERENCE hash.
- **Other tooling:** `source mflux/env.sh` for the project-local uv/HF toolchain. There is no linter or build step.

## Architecture (app/photogen)
- **Request flow:** `cli.py` / `api.py` (stdlib ThreadingHTTPServer) → `service.py` → `jobs.JobManager` → `tasks.TaskRouter` → the task's runtime.
  - `JobManager` handles a SQLite queue (`store.py`) and a machine-wide flock GPU lock at `data/gpu.lock`, so there is only one generation **or edit** at a time across the CLI and server. One queue serves both tasks.
  - The task is `request["task"]`; rows without one load as `text-to-image`.
  - **Each runtime owns its request type and its sidecar:** `photogen.generation/1` (Z-Image, unchanged since v1; pinned by `app/tests/data/zimage-sidecar-golden.json`) and `photogen.edit/1` (Qwen).
  - **Backend identity (Phase 5):**
    - every job row has `backend_id`, stamped from the runtime's manifest at submit; the `schema_migrations` migration in `store.py` backfilled legacy rows;
    - at execute time `jobs._execute` refuses a row whose backend, or (edits) whose recorded model, revision or manifest sha256, no longer matches the manifest (`IdentityMismatchError`);
    - workers' reported package versions are checked against the manifest pins.
  - **Health is per backend.** Z-Image decides the service status; an unavailable edit backend only makes `POST /edit` / `edit` return 503.
  - API additions are additive only: `POST /edit`, `task` on jobs, `tasks` on `/capabilities` and `/status`, `backends` on `/health`. `POST /generate` stays text-to-image only.
- **Runtime:** `runtimes/mflux_zimage.py` (`MFluxZImageRuntime`). `normalize()` is the single validation point.
  - Unknown parameters and the ones in `REJECTED` (negative_prompt, guidance, scheduler, …) raise errors; they are never silently ignored.
  - It resolves `profile` into precision + steps and decides `validated` against `VALIDATED_COMBINATIONS` (exact precision + steps + resolution; anything else needs `allow_experimental`).
- **Worker process:** each job spawns `runtimes/mflux_zimage_worker.py` in a fresh process, which calls the unmodified mflux CLI `main()` with in-process patches:
  - `_apply_bf16_stream`: opt-in bf16 activations.
  - `_install_transformer_release`: on by default. Frees the DiT that mflux's compiled `predict` closure keeps alive during VAE decode.
  - Passive probes: phase and step timings, peak footprint via libproc, `compile_calls`.
  - Cancellation is a killpg.
- **Edit runtime:** `runtimes/mflux_qwen_edit.py` (`MFluxQwenImageEditRuntime`) + `runtimes/mflux_qwen_edit_worker.py`.
  - The worker runs in the edit venv and calls mflux's `mflux-generate-qwen-2.1-edit` `main()` unmodified, with upstream defaults: 40 steps, guidance 1.0, prefix KV cache, linear schedule, `--low-ram`.
  - `REJECTED` covers CFG, scheduler, width/height (derived from `output_resolution` + input aspect, multiples of 32), multi-reference, and the mflux-only mask/strength/enhance/verify/step-cache options.
  - **Every edit is experimental** (`validated=false`; needs `allow_experimental`).
  - **G2 (Phase 5): REJECTED** for both gated configurations, `configuration_id` `3cd79615…` (512) and `fffe8df3…` (1024).
    - Preservation failed 4/16 at each budget: incidental text elsewhere in the photo is garbled, and edits leak to adjacent or similar objects. Adherence: 0 FAIL.
    - 1024 is also MARGINAL on wall time (≈ 592 s per edit).
    - No validated-configuration table exists; adding one needs a new pre-registered gate. Don't promote on G0/G2 adherence.
  - Lifetime fix `_defer_transformer_load` (default on, `DEFER_TRANSFORMER_LOAD`): pixel-identical; lowers the peak footprint 12.63 → 8.85 GB at 512.
  - Phase 5 lifetime policy P2 (worker `_install_lifetime_policy`; default on, `RELEASE_TEXT_ENCODER_AFTER_ENCODE` + `RELEASE_VAE_DURING_DENOISE`):
    - drops the text encoder right after encoding, and keeps only a lazy VAE copy during denoise;
    - exact parity on 5/5 pairs;
    - 1024 peak footprint −1.35 GB (12.08 → ~10.8), 512 peak 8.9 → 8.2 GB;
    - evidence: `research/qwen/QWEN-MEMORY-LIFETIME.md`.
  - Edit sidecar identity (Phase 5):
    - `configuration` / `configuration_id` = what a gate validates: manifest identity + steps + output resolution;
    - `edit_identity` / `edit_id` = what determines the pixels: + input pixels, instruction, seed;
    - `execution.memory_policy` = the policy the worker reports it applied. It is pixel-neutral, so it is not part of either id.
  - Manifest: `config/backend-qwen21-edit-mflux.json` (immutable, like the Z-Image one).
- **Inputs:** `inputs.py` stages every input image at submit time: EXIF orientation applied; opaque PNG/JPEG/WebP only (a camera MPO multi-picture JPEG is staged as its primary image, with a warning: Phase 5 G2 finding); canonical RGB PNG at `data/inputs/<pixel_sha256>.png`; re-verified before every run. Output identity stays RGB `pixel_sha256`; the edit sidecar adds `output_alpha` (mflux writes RGBA).
- **Configuration:**
  - `config/backend-zimage-mflux.json` is the **immutable** manifest: pinned versions, model file hashes, validated resolutions and steps, limits. Drift must be investigated, never "fixed" by editing it.
  - `config/photogen.toml` holds user settings.
  - `config/text-encoders.json` is the text-encoder substitution registry. It's currently empty (stock only).
- **Integrity:** `integrity.py` hashes model files, with a cache keyed on inode/size/mtime. `imaging.py` computes the canonical pixel SHA-256 over raw RGB and rejects blank images.

## Profiles and reference hashes
| profile | precision | steps | status |
|---|---|---|---|
| reference (default when no profile is given) | fp32 | 9 | permanent reference |
| fast | bf16 | 8 | validated at 512², 768², 1024² (direct blinded gates) |
| balanced | bf16 | 5 | validated at **1024² only** (Stage B gate 0/0/24); 768² NOT CONFIRMED (Stage B narrowest pass 3/0/21; focused confirmation 3/1/28 failed criterion 4, poster subtitle), stays FAST; 512² not offered (ULTRA dominates) |
| ultra | bf16 | 4 | validated at **512² only** (Stage A gate); REJECTED at 768²/1024² (text/object-resolution failures) |

- **Lower step counts:** 7–4 steps are experimental.
- **NFE:** in mflux, N steps = N NFE. The reference therefore runs 9 NFE; FAST at 1024² ≈ the official 8-NFE recipe.
- **Validity is per exact combination** (`VALIDATED_COMBINATIONS`): fp32+9 and bf16+8 at 512²/768²/1024²; bf16+9 at 1024² only; bf16+5 (BALANCED) at 1024² only; bf16+4 (ULTRA) at 512² only. Never mark a combination valid because a nearby one was gated. A regression test pins the table.
- **Regression hashes** (p01 "a red apple on a wooden table, soft window light", seed 42):
  - 1024²: reference `fe47d88d…`, fast `7b45cfbe…`, balanced `befe1b3c…`, bf16/9 `11b19277…`;
  - 768²: reference `94a023d3…`, fast `20ff9e2c…`;
  - 512²: reference `9ae59f59…`, fast `0b9cc20a…`, ultra `6aa2b842…`.
- **REFERENCE's "fp32" relies on MLX's `MLX_ENABLE_TF32=1` default** (matmuls/attention run on NAX with TF32 math; `research/experiments/nax-status.md`). The worker strips `MLX_*` from its env; keep it that way or the hashes change.

## Hard constraints (from the project owner)
- **Don't modify or upgrade** mflux, MLX, the venv's packages, model weights, quantization or the scheduler. Change behaviour only through in-process patches in the worker, each backed by evidence. This applies to **both** venvs (`mflux/.venv` = 0.20.0 for Z-Image, `mflux-qwen/.venv` = 0.21.0 for editing; locks in `config/`).
- **Qwen-Image-2.1 is research-licensed (non-commercial).** Never commit or redistribute its weights or the q4 export, and keep the licence label on every edit surface.
- **No global installs, no sudo, no system changes.** In particular don't touch `iogpu.wired_limit_mb`, Metal settings or system Python, and don't use `trust_remote_code`.
- **Networking:** the API binds to 127.0.0.1. No telemetry. Models are never auto-downloaded.
- **Never delete or overwrite** research data, logs, hashes, benchmark CSVs or failed outputs. If an artifact is corrupted, record an incident instead.
- **Evidence standard:** a production change needs pixel parity (exact changes) or a blinded quality gate (numeric changes). Speed claims must name their baseline (cold vs sustained, fp32 vs bf16); never multiply percentages.
- **Discrepancies:** stop and surface them before a consequential change.
- **Blind reviews:** use `research/experiments/blind_stage.py` (prepare → freeze → unblind). Rules are in `research/experiments/BLIND-PROTOCOL.md`.

## Research layout
- **Where to start:** `research/experiments/STATUS.md` is the status register (adopted/rejected/blocked) and the place to look first. Tier timings are in `research/experiments/PERFORMANCE-MAP.md`.
- **Phase 3 records:** `phase3-plan.md`, `phase3-record-audit.md`, `phase3-scorecard.md`, `sigma-schedule-audit.md` (closed), `fast-resolution-gates-report.md`, `nax-status.md`, `kernel-profile.md`, `block-sensitivity-map.md`, `ffn-reduction-design.md`, `quantization-map.md`, `distillation-feasibility.md`, `4step-probe-acquisition.md`, `4step-probe/`.
- **Planning:** `research/EXPERIMENT-BACKLOG.md` holds the next frontier (structured reduction, quantization formats, kernels, few-step distillation).
- **Architecture notes:** `z-image-architecture-map.md`.
- **Experiment harnesses:**
  - `exp_zimage.py`: research worker with flags.
  - `prod_runner.py`: drives the production worker.
  - `ab_runner.py`, `pair_metrics.py`.
  - All run sequentially with `research/monitor.sh`, and must not share the GPU with other runs.
- **Upstream reports:** mflux-community/mflux #760 and #761 (`upstream-mflux-issue-SUBMITTED.md`). Both were closed 2026-10-01, fixed upstream in 0.21.0 (#802, #803); production stays on 0.20.0.
- **Phase 4 (editing):**
  - **Resume index:** `research/qwen/PHASE4-INDEX.md` (start there after MEMORY.md for anything editing-related).
  - **Phase 5:** `research/qwen/PHASE5-INDEX.md` is the resume index. It covers:
    - backend identity;
    - asset provenance (`QWEN-ASSET-PROVENANCE.md`);
    - the memory lifetime A/B (`research/qwen/memory/`, `QWEN-MEMORY-LIFETIME.md`);
    - the real-photograph gate G2 (`research/editing/real-world/`: 16 CC0/PD Commons photos; images never committed).
  - `research/editing/` is the **model-independent** editing benchmark: suite v1, sources, regions, rubric, gates G0/G1, `edit_metrics.py`, `review_sheet.py`.
  - `research/qwen/` holds the Qwen backend evidence: `QWEN-SOURCE-AUDIT.md`, `QWEN-RUNTIME-COMPARISON.md`, `QWEN-EDITING-BASELINE.md`, `QWEN-EDITING-QUALITY.md` (G0, G1, G2), `QWEN-MEMORY-LIFETIME.md`, `QWEN-ASSET-PROVENANCE.md` (source checkpoint: RETAIN LOCALLY, with a DELETE trigger), `INCIDENTS.md`, `runs/<id>/`, `g0/`, `g1/`.
  - G2 blind tooling (`research/editing/real-world/`): `g2_blind.py` (prepare → freeze → unblind), `make_items.py`, `check_scores_format.py`, `analyze_g2.py`. The rater is a fresh subagent that reads only `g2/blind/`.
  - Harness: `research/qwen/run_edit.sh` with modes `app`, `plain`, `worker0/1` and `sdcpp`. It runs the 1 Hz monitor with abort thresholds and records the git HEAD per run. It also **bypasses `gpu.lock`**, so run no photo-gen jobs during its chains.
  - Never edit a script, `app/` or `config/` while a chain that uses them is running (incidents 2026-10-07).

## Repository, docs and licensing
- **Docs:**
  - `docs/photo-gen-guide.html`: full guide.
  - `docs/HARDWARE.md`: the only validated machine is MacBook Air M5 16 GB, macOS 27.0; never generalize benchmarks beyond it.
  - `docs/REPRODUCIBILITY.md`: rebuild steps and hashes.
  - `docs/RELEASE-NOTES.md`: tags.
  - `docs/THIRD-PARTY-LICENSES.md`, `docs/USAGE.md`.
- **Licensing:** `LICENSE` is MIT for photo-gen's own code only. It never relicenses mflux/MLX/models. The production q4 pack declares no license (flagged in THIRD-PARTY-LICENSES).
- **Git:**
  - Push via HTTPS with `-c credential.helper= -c credential.helper='!gh auth git-credential'` (SSH is not authorized).
  - Tags v1/v2/v3 are immutable restore points.
  - Commit text evidence (reports, JSON/JSONL, manifests). Never commit weights, PNGs, `.gputrace`, `data/` or `mflux/`.
- **Research-only models** go in `models/research/` (gitignored), always with an acquisition audit (license, revision, sha256) before download. Currently: Z-Image base q4 + the alibaba-pai 4-step LoRA (`research/experiments/4step-probe/`).
- **Long GPU chains:**
  - Run them as a top-level `nohup zsh script > log 2>&1 < /dev/null & disown`. A chain started inside a compound shell command was killed once.
  - Only one GPU job at a time. Research harnesses bypass `data/gpu.lock`, so don't run photo-gen generations while a chain is running.
  - Record each chain's script, log and completion marker in MEMORY.md.
- **Research harness caveats learned the hard way:**
  - Synthetic MLX blocks default norm weights to fp32, which silently promotes bf16. Cast to bf16 as in the real pack.
  - mflux bakes LoRAs by default (`--no-bake-lora` for runtime adapters).
  - mflux's Z-Image *base* CLI defaults to the `flow_match_euler_discrete` scheduler, not `linear`.
  - Instrumented (uncompiled) runs change numerics; compare against uncompiled baselines.

## Memory ledger (MEMORY.md)
`MEMORY.md` at the repo root is the persistent work ledger. It's how a new session resumes without loss.
- **At session start:** read `MEMORY.md` first. The "Current state" block says what's in production, the regression hashes, open items and whether anything is running. Then follow its pointers (usually `research/experiments/STATUS.md`).
- **At the end of every working session, or after any milestone:**
  - Update the "Current state" block.
  - Add a dated entry at the top of the ledger: directive or goal, what was done, evidence paths, disclosed deviations, open items.
- **Keep entries as pointers plus key numbers.** Detail belongs in the research reports.
- **Never rewrite past entries.** Append corrections as new entries.
- **Background runs:** if a background run is in flight when a session ends, record its script, console log and expected completion marker (e.g. `CHAIN6B_DONE`) so it can be picked up.
