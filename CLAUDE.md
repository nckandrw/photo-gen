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
- **Validity is per exact combination** (`VALIDATED_COMBINATIONS`): fp32+9 and bf16+8 at 512²/768²/1024²; bf16+9 at 1024² only. Never mark a combination valid because a nearby one was gated. A regression test pins the table.
- **Regression hashes** (p01 "a red apple on a wooden table, soft window light", seed 42):
  - 1024²: reference `fe47d88d…`, fast `7b45cfbe…`, bf16/9 `11b19277…`;
  - 768²: reference `94a023d3…`, fast `20ff9e2c…`;
  - 512²: reference `9ae59f59…`, fast `0b9cc20a…`.
- **REFERENCE's "fp32" relies on MLX's `MLX_ENABLE_TF32=1` default** (matmuls/attention run on NAX with TF32 math; `research/experiments/nax-status.md`). The worker strips `MLX_*` from its env; keep it that way or the hashes change.

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
- **Phase 3 records:** `phase3-plan.md`, `phase3-record-audit.md`, `phase3-scorecard.md`, `sigma-schedule-audit.md` (closed), `fast-resolution-gates-report.md`, `nax-status.md`, `kernel-profile.md`, `block-sensitivity-map.md`, `ffn-reduction-design.md`, `quantization-map.md`, `distillation-feasibility.md`, `4step-probe-acquisition.md`, `4step-probe/`.
- **Planning:** `research/EXPERIMENT-BACKLOG.md` holds the next frontier (structured reduction, quantization formats, kernels, few-step distillation).
- **Architecture notes:** `z-image-architecture-map.md`.
- **Experiment harnesses:**
  - `exp_zimage.py`: research worker with flags.
  - `prod_runner.py`: drives the production worker.
  - `ab_runner.py`, `pair_metrics.py`.
  - All run sequentially with `research/monitor.sh`, and must not share the GPU with other runs.
- **Upstream reports:** mflux-community/mflux #760 and #761 (`upstream-mflux-issue-SUBMITTED.md`).

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
  - Tags v1/v2 are immutable restore points.
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
