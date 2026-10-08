# Hardware and compatibility

> **Validated target: MacBook Air M5, 16 GB unified memory, 8-core GPU, macOS 27.0.1 (26A434).** Historical baseline: macOS 27.0 (26A428), the OS of every measurement taken before 2026-09-29 22:50. [`config/machine-profile-m5-16gb.json`](../config/machine-profile-m5-16gb.json) remains the dated 2026-09-25 read-out and still records 27.0.
>
> Performance figures and production profile validation in this repository are specific to this machine and environment unless explicitly stated otherwise.
>
> photo-gen is **not** currently a general-purpose, cross-platform image-generation package. That is intentional. Other hardware may work, but has not been validated by this project.

Values below were read from the machine on 2026-09-25 (editing section: 2026-10-07) (`system_profiler`, `sw_vers`, `mx.device_info()`, `importlib.metadata`). The same data is in machine-readable form in [`config/machine-profile-m5-16gb.json`](../config/machine-profile-m5-16gb.json).

## Validated machine
| item | value |
|---|---|
| model | MacBook Air (`Mac17,3`), fanless |
| chip | Apple M5: 10-core CPU (4 super + 6 efficiency), **8-core GPU** |
| GPU architecture (MLX) | `applegpu_g17g` |
| unified memory | **16 GB** (Metal recommended working set 12.71 GB) |
| OS | **macOS 27.0.1 (26A434)**, current since 2026-09-29 22:50 (`system_profiler SPInstallHistoryDataType`). **Historical baseline: macOS 27.0 (26A428)**, the OS of the 2026-09-25 read-out and of every measurement before 2026-09-29; older benchmark records keep their original environment. Evidence on 27.0.1: Phases 4–9; Z-Image REFERENCE 512² `9ae59f59` and ULTRA 512² `6aa2b842` re-checked exact through the CLI on 2026-10-08. *(Updated 2026-10-09, Phase 9; the 2026-10-09 Phase 8 discrepancy note is superseded by this row.)* |
| power during validation | AC power |

## Validated software
| component | version |
|---|---|
| Python | 3.12.14 (uv-managed, project-local `mflux/.venv`) |
| mflux | 0.20.0 (unmodified) |
| MLX | 0.32.2 |
| mlx-metal | 0.32.2 |
| full package set | [`config/python-requirements.lock.txt`](../config/python-requirements.lock.txt) (56 packages) |

## Validated inference
- **Model:** Z-Image-Turbo, `mflux-community/z-image-turbo-mflux-q4` @ `d2d30500c4bc0d19770bd952951df3e7c635ae9e` (MLX affine 4-bit, group 64). Every file is pinned by digest in [`config/backend-zimage-mflux.json`](../config/backend-zimage-mflux.json).
- **`--low-ram` is always on**, plus photo-gen's transformer-release fix. Without `--low-ram`, this machine measured a 12.8 GB footprint and critical memory pressure.
- **One generation at a time**, in a fresh worker process per image.

## Validation status
| configuration | 512² | 768² | 1024² |
|---|---|---|---|
| **REFERENCE**: fp32 + 9 steps (9 NFE) | REFERENCE (hash-pinned) | REFERENCE (hash recorded 2026-09-25) | REFERENCE (hash-pinned) |
| **FAST**: bf16 + 8 steps (8 NFE) | **VALIDATED** (direct blinded gate, 0 / 0 / 24) | **VALIDATED** (direct blinded gate, 2 / 0 / 22) | **VALIDATED** (direct gate 0 / 1 / 23, plus the earlier two-gate chain) |
| bf16 + 9 steps (not a profile) | EXPERIMENTAL | EXPERIMENTAL | VALIDATED (bf16 gate vs fp32/9, 24 pairs) |
| **BALANCED**: bf16 + 5 steps (5 NFE) | EXPERIMENTAL (gate passed 1 / 0 / 23; not offered: ULTRA is faster) | NOT CONFIRMED (Stage B narrowest pass 3 / 0 / 21; focused confirmation 3 / 1 / 28, class-level subtitle failure) | **VALIDATED** (blind gate 0 / 0 / 24) |
| **ULTRA**: bf16 + 4 steps (4 NFE) | **VALIDATED** (blind gate 1 / 0 / 23) | REJECTED (text) | REJECTED (text/ghosting) |
| bf16 + 7/6 steps | EXPERIMENTAL | EXPERIMENTAL | EXPERIMENTAL |

Validity applies to the exact combination of model + precision + steps + scheduler + resolution. Everything not marked VALIDATED or REFERENCE needs `--allow-experimental`.

**What was actually benchmarked on this machine** (cold = one run after 600 s idle; production worker; prompt "a red apple…", seed 42):

| res | configuration | wall (s) | denoise (s) | peak footprint (GB) |
|---|---|---:|---:|---:|
| 1024² | REFERENCE fp32/9 | 83.4 | 78.3 | 6.56 |
| 1024² | FAST bf16/8 | 54.2 | 48.7 | 5.84 |
| 1024² | BALANCED bf16/5 (2026-09-29) | 36.1 | 30.6 | 5.84 |
| 768² | REFERENCE fp32/9 | 44.7 | 40.4 | 6.33 |
| 768² | FAST bf16/8 | 30.6 | 26.1 | 5.93 |
| 512² | REFERENCE fp32/9 | 21.2 | 17.4 | 5.93 |
| 512² | FAST bf16/8 | 15.0 | 11.4 | 5.41 |

- The Air is fanless. Back-to-back runs throttle: 1024² REFERENCE reached ≈112–134 s per image once heat-soaked.
- Cold and sustained figures are never averaged together. Details: [`research/experiments/PERFORMANCE-MAP.md`](../research/experiments/PERFORMANCE-MAP.md).
- **These numbers are measurements of this exact machine, not predictions for any other hardware.**

## Image editing on this machine (Phase 4; gated in Phase 5: G2 REJECTED, research opt-in only)
The image-edit task (Qwen-Image-2.1, research licence) runs on the same machine, in a separate venv (`mflux-qwen/.venv`: mflux 0.21.0, MLX 0.32.2, Python 3.12.14; lock [`config/qwen-python-requirements.lock.txt`](../config/qwen-python-requirements.lock.txt)), one job at a time through the shared GPU lock.
- **Model:** `Qwen/Qwen-Image-2.1` @ `d26bb61`, local q4 export (DiT + Qwen3-VL text/vision encoder q4, VAE fp32), 10.64 GB, pinned in [`config/backend-qwen21-edit-mflux.json`](../config/backend-qwen21-edit-mflux.json).
- **Memory** (16 GB is the binding constraint):

  | lifecycle | peak footprint at 512 | at 1024 | memory pressure |
  |---|---:|---:|---|
  | mflux stock (all components loaded first) | 12.63 GB | 14.20 GB | **critical** episodes |
  | Phase 4: deferred DiT load (pixel-identical) | 8.85 GB | 12.08 GB | normal at 512; warn but never critical at 1024 |
  | **production since Phase 5: P2** (deferred DiT + text encoder released after encoding + lazy VAE during denoise; pixel-identical, [`QWEN-MEMORY-LIFETIME.md`](../research/qwen/QWEN-MEMORY-LIFETIME.md)) | **8.16 GB** (G2 median, 23 runs) | **10.87 GB** (G2 median, 22 runs) | 512: swap growth ≤ 0.04 GB; 1024: swap growth 0.10–1.19 GB, warn ≤ 2.7% of samples, never critical |

- **Timings** (apps closed, AC, 40 steps):
  - G2 (Phase 5, P2, **sustained chain**, 20 s between runs): 512 median **104 s** (80–115 s); the first, cool runs took about 80 s and the time rose with chain position. 1024 median **592 s** (523–634 s; first run 523 s), of which denoise is 571 s.
  - Phase 4 (deferred load only): 1024 cold (after 600 s idle) **496.8 s**; 512 sustained 83–112 s; 1024 sustained median 556 s (478–601 s).
- **Memory/UX class (G2, protocol §8):** 512 **COMFORTABLE**; 1024 **MARGINAL**. At 1024 the limit is wall time (about 10 min per edit, against 6 min for USABLE), not memory. An accepted edit usually takes several attempts.
- **Not validated.**
  - The real-photograph quality gate G2 **rejected** both budgets: incidental text is garbled and edits leak to adjacent or similar objects ([`research/editing/real-world/results.md`](../research/editing/real-world/results.md)).
  - Every edit reports `validated: false` and needs `--allow-experimental`.
  - On other hardware nothing about editing is known.
  - Edits above a 1024 budget are not offered on 16 GB.

## Not yet validated
None of the following has been tested by this project. Nothing here means "unsupported forever"; each would need its own validation (versions, memory profile, timings, pixel parity / quality gates).

| category | examples |
|---|---|
| other Apple Silicon chips | M5 Pro, M5 Max, M4, M3, M2, M1 |
| other Mac models | MacBook Pro, Mac mini, Mac Studio, iMac |
| other memory sizes | 8 GB, 24 GB, 32 GB and larger |
| other OS versions | any macOS other than 27.0.1 (26A434) (current) and 27.0 (26A428) (historical baseline) |
| non-Apple platforms | NVIDIA/CUDA, AMD, Windows, Linux |

Known hardware-specific facts that make this boundary real, not cosmetic:
- **16 GB determines the architecture.** The per-job worker process and the mandatory `--low-ram` exist because of this memory size. Larger machines might prefer a different lifecycle, and smaller ones may not fit at all.
- **M5-specific kernels.** MLX dispatches `*_nax` kernels on `applegpu_g17g` (M5 neural accelerators; see [`research/experiments/nax-status.md`](../research/experiments/nax-status.md)). Numerics, and therefore the pinned pixel hashes, may differ on other GPUs.
- **Fanless thermals.** The sustained timings reflect this chassis.
- **Startup checks refuse drift** in Python/mflux/MLX versions and model files. They do *not* check the hardware model. Running on another Mac is possible, but results there are unvalidated.

**Cloneable ≠ validated on that hardware.**
