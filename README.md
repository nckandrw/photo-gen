# photo-gen

> **Validated target: MacBook Air M5, 16 GB unified memory, 8-core GPU, macOS 27.0 (26A428).**
>
> Performance figures and production profile validation in this repository are specific to this machine and environment unless explicitly stated otherwise. This is **not** currently a general-purpose, cross-platform image-generation package.

A local text-to-image application: a CLI and a localhost HTTP API around Z-Image-Turbo (q4) running on mflux / MLX. It has a persistent job queue, a fresh worker process per image, startup integrity checks and reproducible pixel hashes. It doubles as an inference-research platform (`research/`).

This repository contains the photo-gen application and research environment developed and validated on a MacBook Air M5 with 16 GB unified memory. Other Apple Silicon or non-Apple hardware may require changes and has not been validated unless explicitly documented.

## Current status
| | |
|---|---|
| build | working; 42/42 tests pass |
| hardware | **MacBook Air M5 16 GB: validated** (the only validated machine) |
| runtime | Python 3.12.14 · mflux 0.20.0 · MLX 0.32.2 · mlx-metal 0.32.2 · Z-Image-Turbo q4 @ `d2d30500` · `--low-ram` |
| **REFERENCE** (default) | fp32 + 9 steps (9 NFE): canonical reproducibility baseline at 512², 768², 1024² |
| **FAST** | bf16 + 8 steps (8 NFE): **validated at 512², 768², 1024²** (direct blinded gates vs REFERENCE, 72 pairs: 2 / 1 / 69 ties) |
| **BALANCED** | bf16 + 5 steps (5 NFE): **validated at 1024² only** (blind vs FAST 0 / 0 / 24; cold wall 54.4 → 36.1 s). 768²: gate passed by the narrowest margin, held pending a focused confirmation; 512²: not offered (ULTRA is faster there). |
| **ULTRA** | bf16 + 4 steps (4 NFE): **validated at 512² only** (blind vs FAST 1 / 0 / 23; cold wall 15.6 → 9.5 s). Not validated at 768²/1024²: 4-step Turbo showed specific text/object-resolution failures at 768² and 1024² under the fresh-seed blinded gate. |

**The current validated production profiles are REFERENCE (fp32 + 9), FAST (bf16 + 8), BALANCED (bf16 + 5, 1024² only) and ULTRA (bf16 + 4, 512² only).** FAST has been validated at 512², 768² and 1024² on the target M5 16 GB system; BALANCED only at 1024²; ULTRA only at 512². These are different operating points with different evidence, not a ranking: REFERENCE for reproducibility and regression testing, FAST for general use at every size, BALANCED for lower-latency 1024², ULTRA for minimum-latency 512². Any other combination (BALANCED at 512²/768², ULTRA at 768²/1024², bf16 + 6/7, bf16 + 9 outside 1024², other sizes) is experimental and needs `--allow-experimental`. Validity is checked per exact precision + steps + resolution.

## Requirements
- The validated machine above.
- The project-local toolchain in `mflux/` and the model in `models/mflux/z-image-turbo-mflux-q4/`. **Neither is in Git.** Rebuild both from [docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md), with exact versions and every model file's digest.
- Nothing is installed globally. photo-gen never downloads anything and runs offline.

## Quick start
```sh
bin/photo-gen verify                        # versions + model hashes; must end "ok": true
bin/photo-gen serve                         # HTTP API on 127.0.0.1:8765 (no web page at /; see the guide)

P="a red apple on a wooden table, soft window light"
bin/photo-gen generate -p "$P" --seed 42 --profile fast        # FAST, 1024²      → pixel_sha256 7b45cfbe…
bin/photo-gen generate -p "$P" --seed 42 --profile reference   # REFERENCE, 1024² → fe47d88d…
bin/photo-gen generate -p "$P" --seed 42 --profile balanced  # BALANCED, 1024² only → befe1b3c…
bin/photo-gen generate -p "$P" --seed 42 --profile ultra --width 512 --height 512   # ULTRA, 512² only → 6aa2b842…

curl -s -X POST http://127.0.0.1:8765/generate -H 'Content-Type: application/json' \
     -d '{"prompt":"a lighthouse at dawn","profile":"fast","seed":42}'   # → job_id
curl -s "http://127.0.0.1:8765/jobs/<job_id>?wait=300"                  # wait for the result
```
Outputs go to `data/outputs/YYYY/MM/DD/<job_id>.png`, each with a JSON metadata sidecar.

## Documentation
- [docs/photo-gen-guide.html](docs/photo-gen-guide.html): the full guide (usage, API, architecture, troubleshooting, development). Self-contained; open it in a browser.
- [docs/HARDWARE.md](docs/HARDWARE.md): validated machine, validation status, what is *not* validated.
- [docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md): rebuild the exact environment and prove it with the reference hashes.
- [docs/USAGE.md](docs/USAGE.md): the previous detailed README, kept as a markdown reference.
- [docs/RELEASE-NOTES.md](docs/RELEASE-NOTES.md): validated tags (v1, v2) and what changed.
- [docs/THIRD-PARTY-LICENSES.md](docs/THIRD-PARTY-LICENSES.md): third-party software and model licences, separate from photo-gen's MIT licence.

## Research
Evidence for every production behaviour, including rejected and blocked ideas:
- [research/experiments/STATUS.md](research/experiments/STATUS.md): status register (start here).
- [research/experiments/PERFORMANCE-MAP.md](research/experiments/PERFORMANCE-MAP.md): measured timings, cold vs sustained.
- [research/COMPONENT-SOURCES.md](research/COMPONENT-SOURCES.md): what is reused, adapted or built, and licences.
- [research/EXPERIMENT-BACKLOG.md](research/EXPERIMENT-BACKLOG.md), [research/PAPER-RESEARCH-MAP.md](research/PAPER-RESEARCH-MAP.md), [research/z-image-architecture-map.md](research/z-image-architecture-map.md).

Research PNGs are not in Git. Their hashes are in [research/EXCLUDED-IMAGES.sha256](research/EXCLUDED-IMAGES.sha256).

## Provenance and licences
| part | what | licence |
|---|---|---|
| photo-gen code | `app/`, `bin/`, `config/`, docs, research scripts | **MIT** ([LICENSE](LICENSE)). Covers photo-gen's own code only. |
| third-party runtime | mflux 0.20.0 (MIT), MLX / mlx-metal 0.32.2 (MIT), Pillow, the Python stdlib | installed into `mflux/.venv`, **not** vendored |
| external model | Z-Image-Turbo (Tongyi-MAI, Apache-2.0), q4 pack by mflux-community | downloaded separately, pinned by digest |
| external research | papers and upstream issues referenced in `research/` | cited, not copied |

No third-party source code is copied into this repository (see `research/COMPONENT-SOURCES.md`).
