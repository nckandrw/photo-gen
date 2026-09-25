# Hardware and compatibility

> **Validated target: MacBook Air M5, 16 GB unified memory, 8-core GPU, macOS 27.0.**
>
> Performance figures and production profile validation in this repository are specific to this machine and environment unless explicitly stated otherwise.
>
> photo-gen is **not** currently a general-purpose, cross-platform image-generation package. That is intentional. Other hardware may work, but has not been validated by this project.

Values below were read from the machine on 2026-09-25 (`system_profiler`, `sw_vers`, `mx.device_info()`, `importlib.metadata`). The same data is in machine-readable form in [`config/machine-profile-m5-16gb.json`](../config/machine-profile-m5-16gb.json).

## Validated machine
| item | value |
|---|---|
| model | MacBook Air (`Mac17,3`), fanless |
| chip | Apple M5: 10-core CPU (4 super + 6 efficiency), **8-core GPU** |
| GPU architecture (MLX) | `applegpu_g17g` |
| unified memory | **16 GB** (Metal recommended working set 12.71 GB) |
| OS | **macOS 27.0 (26A428)** |
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
| bf16 + 7/6/5/4 steps | EXPERIMENTAL | EXPERIMENTAL | EXPERIMENTAL (not quality-equivalent) |

**What was actually benchmarked on this machine** (cold = one run after 600 s idle; production worker; prompt "a red apple…", seed 42):

| res | configuration | wall (s) | denoise (s) | peak footprint (GB) |
|---|---|---:|---:|---:|
| 1024² | REFERENCE fp32/9 | 83.4 | 78.3 | 6.56 |
| 1024² | FAST bf16/8 | 54.2 | 48.7 | 5.84 |
| 768² | REFERENCE fp32/9 | 44.7 | 40.4 | 6.33 |
| 768² | FAST bf16/8 | 30.6 | 26.1 | 5.93 |
| 512² | REFERENCE fp32/9 | 21.2 | 17.4 | 5.93 |
| 512² | FAST bf16/8 | 15.0 | 11.4 | 5.41 |

- The Air is fanless. Back-to-back runs throttle: 1024² REFERENCE reached ≈112–134 s per image once heat-soaked.
- Cold and sustained figures are never averaged together. Details: [`research/experiments/PERFORMANCE-MAP.md`](../research/experiments/PERFORMANCE-MAP.md).
- **These numbers are measurements of this exact machine, not predictions for any other hardware.**

## Not yet validated
None of the following has been tested by this project. Nothing here means "unsupported forever"; each would need its own validation (versions, memory profile, timings, pixel parity / quality gates).

| category | examples |
|---|---|
| other Apple Silicon chips | M5 Pro, M5 Max, M4, M3, M2, M1 |
| other Mac models | MacBook Pro, Mac mini, Mac Studio, iMac |
| other memory sizes | 8 GB, 24 GB, 32 GB and larger |
| other OS versions | any macOS other than 27.0 (26A428) |
| non-Apple platforms | NVIDIA/CUDA, AMD, Windows, Linux |

Known hardware-specific facts that make this boundary real, not cosmetic:
- **16 GB determines the architecture.** The per-job worker process and the mandatory `--low-ram` exist because of this memory size. Larger machines might prefer a different lifecycle, and smaller ones may not fit at all.
- **M5-specific kernels.** MLX dispatches `*_nax` kernels on `applegpu_g17g` (M5 neural accelerators; see [`research/experiments/nax-status.md`](../research/experiments/nax-status.md)). Numerics, and therefore the pinned pixel hashes, may differ on other GPUs.
- **Fanless thermals.** The sustained timings reflect this chassis.
- **Startup checks refuse drift** in Python/mflux/MLX versions and model files. They do *not* check the hardware model. Running on another Mac is possible, but results there are unvalidated.

**Cloneable ≠ validated on that hardware.**
