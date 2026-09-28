# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is
photo-gen is a local image-generation service (CLI + localhost HTTP API) for **one machine**: a MacBook Air M5, 16 GB. It runs Z-Image-Turbo on mflux 0.20.0 / MLX 0.32.2 with the pre-quantized `mflux-community/z-image-turbo-mflux-q4` @ `d2d30500`, always with `--low-ram`.

The project has two halves:
- `app/`: the production application.
- `research/`: an evidence trail. Every production behaviour has a report behind it.

Git: private repo `nckandrw/photo-gen` (branch `main`); validated builds are tagged `photo-gen-m5-16gb-v1` and `-v2` (immutable; see `docs/RELEASE-NOTES.md`). Model weights, `mflux/` toolchain, `data/`, `outputs/` and research PNGs are not versioned (see `.gitignore`, `docs/REPRODUCIBILITY.md`). Stage files explicitly; never `git add .`.

## Commands
```sh
bin/photo-gen verify [--full]          # versions + model hashes + mflux capability cross-check
bin/photo-gen serve                    # API on 127.0.0.1:8765
bin/photo-gen generate -p "..." --seed 42 [--profile reference|fast] [--json]
bin/photo-gen capabilities | jobs | job <id> | status

# tests (stdlib unittest; FakeRuntime means no GPU is needed, except test_worker_lifetime, which imports mflux)
cd app/tests && PHOTOGEN_ROOT=../.. PYTHONPATH=..:. ../../mflux/.venv/bin/python3.12 -m unittest -v
# single test
cd app/tests && PHOTOGEN_ROOT=../.. PYTHONPATH=..:. ../../mflux/.venv/bin/python3.12 -m unittest test_core.ValidationTests.test_profiles
```
- **Interpreter:** always use `mflux/.venv/bin/python3.12`. System `python3` lacks PIL and mlx. `bin/photo-gen` sets `PYTHONPATH=app` and `HF_HUB_OFFLINE=1`.
- **Other tooling:** `source mflux/env.sh` for the project-local uv/HF toolchain. There is no linter or build step.

## Architecture (app/photogen)
- **Request flow:** `cli.py` / `api.py` (stdlib ThreadingHTTPServer) → `service.py` → `jobs.JobManager`.
  - `JobManager` handles a SQLite queue (`store.py`) and a machine-wide flock GPU lock at `data/gpu.lock`, so there is only one generation at a time across the CLI and server.
  - It writes a metadata sidecar per image (schema `photogen.generation/1`).
- **Runtime:** `runtimes/mflux_zimage.py` (`MFluxZImageRuntime`). `normalize()` is the single validation point.
  - Unknown parameters and the ones in `REJECTED` (negative_prompt, guidance, scheduler, …) raise errors; they are never silently ignored.
  - It resolves `profile` into precision + steps and decides `validated` against `VALIDATED_COMBINATIONS` (exact precision + steps + resolution; anything else needs `allow_experimental`).
- **Worker process:** each job spawns `runtimes/mflux_zimage_worker.py` in a fresh process, which calls the unmodified mflux CLI `main()` with in-process patches:
  - `_apply_bf16_stream`: opt-in bf16 activations.
  - `_install_transformer_release`: on by default. Frees the DiT that mflux's compiled `predict` closure keeps alive during VAE decode.
  - Passive probes: phase and step timings, peak footprint via libproc, `compile_calls`.
  - Cancellation is a killpg.
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

- **Lower step counts:** 7–4 steps are experimental.
- **NFE:** in mflux, N steps = N NFE. The reference therefore runs 9 NFE; FAST at 1024² ≈ the official 8-NFE recipe.
- **Regression hashes** (p01 "a red apple on a wooden table, soft window light", seed 42, 1024²): reference `fe47d88d…`, fast `7b45cfbe…`, bf16/9 `11b19277…`. 512² reference: `9ae59f59…`.

## Hard constraints (from the project owner)
- **Don't modify or upgrade** mflux, MLX, the venv's packages, model weights, quantization or the scheduler. Change behaviour only through in-process patches in the worker, each backed by evidence.
- **No global installs, no sudo, no system changes.** In particular don't touch `iogpu.wired_limit_mb`, Metal settings or system Python, and don't use `trust_remote_code`.
- **Networking:** the API binds to 127.0.0.1. No telemetry. Models are never auto-downloaded.
- **Never delete or overwrite** research data, logs, hashes, benchmark CSVs or failed outputs. If an artifact is corrupted, record an incident instead.
- **Evidence standard:** a production change needs pixel parity (exact changes) or a blinded quality gate (numeric changes). Speed claims must name their baseline (cold vs sustained, fp32 vs bf16); never multiply percentages.
- **Discrepancies:** stop and surface them before a consequential change.
- **Blind reviews:** use `research/experiments/blind_stage.py` (prepare → freeze → unblind). Rules are in `research/experiments/BLIND-PROTOCOL.md`.

## Research layout
- **Where to start:** `research/experiments/STATUS.md` is the status register (adopted/rejected/blocked) and the place to look first. Tier timings are in `research/experiments/PERFORMANCE-MAP.md`.
- **Planning:** `research/EXPERIMENT-BACKLOG.md` holds the next frontier (structured reduction, quantization formats, kernels, few-step distillation).
- **Architecture notes:** `z-image-architecture-map.md`.
- **Experiment harnesses:**
  - `exp_zimage.py`: research worker with flags.
  - `prod_runner.py`: drives the production worker.
  - `ab_runner.py`, `pair_metrics.py`.
  - All run sequentially with `research/monitor.sh`, and must not share the GPU with other runs.
- **Upstream reports:** mflux-community/mflux #760 and #761 (`upstream-mflux-issue-SUBMITTED.md`).

## Memory ledger (MEMORY.md)
`MEMORY.md` at the repo root is the persistent work ledger. It's how a new session resumes without loss.
- **At session start:** read `MEMORY.md` first. The "Current state" block says what's in production, the regression hashes, open items and whether anything is running. Then follow its pointers (usually `research/experiments/STATUS.md`).
- **At the end of every working session, or after any milestone:**
  - Update the "Current state" block.
  - Add a dated entry at the top of the ledger: directive or goal, what was done, evidence paths, disclosed deviations, open items.
- **Keep entries as pointers plus key numbers.** Detail belongs in the research reports.
- **Never rewrite past entries.** Append corrections as new entries.
- **Background runs:** if a background run is in flight when a session ends, record its script, console log and expected completion marker (e.g. `CHAIN6B_DONE`) so it can be picked up.
