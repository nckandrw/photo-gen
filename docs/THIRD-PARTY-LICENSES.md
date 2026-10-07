# Licensing: photo-gen code vs third-party software vs external models

**Scope of the MIT license in [`LICENSE`](../LICENSE):** only the original photo-gen code and documentation authored for this repository. It does **not** relicense, sublicense or change the terms of any third-party software, model, weight, LoRA, dataset, paper or other external asset listed below. Each of those remains under its own upstream terms.

Sources were inspected on 2026-09-28:
- package metadata (`importlib.metadata`: `License-Expression` / `License` / classifiers) from the installed `mflux/.venv`;
- GitHub's detected repository licenses;
- Hugging Face model-card metadata at the pinned revisions.

Where a source declares nothing, this file says so rather than guessing.

## 1. photo-gen original code (MIT)
| component | path | license | notes |
|---|---|---|---|
| application | `app/photogen/`, `app/tests/` | MIT | the service, CLI, API, queue, store, integrity, runtime adapter, worker patches |
| launcher | `bin/photo-gen` | MIT | |
| configuration | `config/` | MIT | The manifest *records* third-party identities and hashes; that does not license those assets. |
| documentation | `docs/`, `README.md`, `CLAUDE.md`, `MEMORY.md` | MIT | |
| research scripts and reports | `research/` | MIT | Reports cite external papers and upstream issues. Citations are not copies, and cited works keep their own terms. |

**No third-party source code is vendored.** This matches `research/COMPONENT-SOURCES.md`: ideas were adapted, no code was copied. photo-gen imports mflux/MLX at runtime from the separately installed venv.

## 2. Third-party software (installed separately, not in Git)
Installed into the project-local `mflux/.venv` (never committed); exact versions are in [`config/python-requirements.lock.txt`](../config/python-requirements.lock.txt). **Code included in this repository: none.**

| component | version | source | license (as declared) | how photo-gen uses it |
|---|---|---|---|---|
| mflux | 0.20.0 | PyPI; github.com/mflux-community/mflux | MIT (package metadata "MIT License"; GitHub: MIT) | inference runtime; its Turbo CLI `main()` runs unmodified in the worker |
| mlx | 0.32.2 | PyPI; github.com/ml-explore/mlx | MIT | array framework (via mflux) |
| mlx-metal | 0.32.2 | PyPI | MIT | Metal backend / metallib (via mlx) |
| Pillow | 12.3.0 | PyPI | MIT-CMU | image decode and pixel hashing (`imaging.py`) |
| numpy | 2.5.3 | PyPI | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | via mflux; research metrics |
| torch | 2.14.0 | PyPI | Apache-2.0 AND Apache-2.0 WITH LLVM-exception AND BSD-2-Clause AND BSD-3-Clause AND BSL-1.0 AND MIT | a hard dependency of mflux (imported by its weight loader; not used for compute on this path) |
| transformers | 5.17.0 | PyPI | "Apache 2.0 License" | dependency of mflux (tokenizer path) |
| tokenizers | 0.23.2 | PyPI | Apache (classifier only) | dependency of mflux |
| safetensors | 0.8.0 | PyPI | Apache (classifier only) | weight file format |
| huggingface_hub | 1.32.0 | PyPI | Apache-2.0 | used offline only (`HF_HUB_OFFLINE=1`); `hf download` for manual model acquisition |
| opencv-python | 4.14.0.94 | PyPI | "Apache 2.0" | dependency of mflux |
| other transitive packages | see lock file | PyPI | MIT / BSD / Apache-2.0 / MPL-2.0 (certifi, tqdm) / PSF-2.0 / ISC. `hf_transfer` declares no license in its metadata. | not used directly by photo-gen |
| Python | 3.12.14 | python-build-standalone via uv | PSF-2.0 | interpreter |
| uv | 0.12.18 | github.com/astral-sh/uv | not verified in this audit | toolchain installer only |

Photo-gen's own code imports only the Python standard library, Pillow and (inside the worker) mflux/MLX.

## 3. External models and weights (downloaded separately, never in Git)
**Weights included in this repository: none.** File digests are recorded in `config/backend-zimage-mflux.json`; recording a digest does not grant or change any license.

| asset | source | revision | license (as declared) | how it is used |
|---|---|---|---|---|
| **Z-Image-Turbo q4 pack** (the production model) | `mflux-community/z-image-turbo-mflux-q4` | `d2d30500c4bc0d19770bd952951df3e7c635ae9e` | **No license declared.** At this revision the repo contains only the model folders and `.gitattributes`: no README, no model card, no license file, no `license` metadata. | production inference (text encoder, DiT, VAE, tokenizer) |
| ↳ upstream model | `Tongyi-MAI/Z-Image-Turbo` (HF) and `Tongyi-MAI/Z-Image` (GitHub code) | HF main `f332072a` (inspected); GitHub `26f23eda` | **Apache-2.0** (HF card metadata `license: apache-2.0`; GitHub repo license Apache-2.0) | the q4 pack is a quantized conversion of this model |
| ↳ its text encoder | Qwen3-4B (bundled in Z-Image-Turbo) | as bundled | Apache-2.0 (`Qwen/Qwen3-4B` card) | prompt encoding |

**Assessment of the q4 pack (flagged, not resolved by assumption):**
- The pack is a derivative of an Apache-2.0 model. Apache-2.0 permits redistribution of derivatives, but it expects the license and notices to travel with them. The mflux-community pack does not state one.
- photo-gen **does not redistribute** the weights. It only records their identity and downloads them for local use.
- The effective terms are therefore taken to be those of the upstream Apache-2.0 model. This is **UNVERIFIED** as a statement by the redistributor.
- Before any redistribution of these weights (not planned), get an explicit statement from mflux-community, or re-quantize from the upstream Apache-2.0 weights.

## 4. Research-only external assets (Pass 1 comparison; not used by photo-gen's production path, not in Git)
The Qwen-Image 2.1 / Z-Image GGUF files, Qwen3 GGUF text encoders, VAEs, and the stable-diffusion.cpp build under `models/diffusion_models`, `models/text_encoders`, `models/vae` and `sdcpp/`.
- Their sources and pins are in `research/model-pins.txt`, `research/z-image-model-pins.txt` and `research/REPORT.md`.
- `research/REPORT.md` records a **conflicting** licence statement for one Qwen-2.1 derivative (the derivative's card says Apache-2.0, the official card says the Qwen Research License). The official license governs.

## 5. Image-edit backend (Phase 4; research opt-in, G2 REJECTED; installed and downloaded separately, never in Git)
Inspected 2026-10-07 (package metadata in `mflux-qwen/.venv`; HF card metadata and LICENSE at the pinned revisions). Full audit: [`research/qwen/QWEN-SOURCE-AUDIT.md`](../research/qwen/QWEN-SOURCE-AUDIT.md).

**Software** (separate project-local venv `mflux-qwen/.venv`; lock in [`config/qwen-python-requirements.lock.txt`](../config/qwen-python-requirements.lock.txt); code included in this repository: none):

| component | version | license (as declared) | use |
|---|---|---|---|
| mflux | 0.21.0 (wheel sha256 `b2e38fd3…`) | MIT | its `mflux-generate-qwen-2.1-edit` `main()` runs unmodified in the edit worker. Its `qwen21/reference/` code adapted from Diffusers carries Apache-2.0 attribution (`LICENSE.diffusers`, shipped in the wheel) |
| mlx / mlx-metal | 0.32.2 | MIT | as in production |
| torch | 2.13.0 | Apache-2.0 AND … (as §2) | mflux dependency |
| transformers / tokenizers | 5.15.0 / 0.22.2 | Apache-2.0 | Qwen3-VL processor and tokenizer (via mflux) |
| pillow, numpy, safetensors, huggingface-hub, opencv-python | 12.3.0, 2.4.1, 0.8.0, 1.28.0, 4.13.0.90 | as §2 | mflux dependencies |

**Models and weights** (gitignored; digests in [`config/backend-qwen21-edit-mflux.json`](../config/backend-qwen21-edit-mflux.json) and `research/qwen/upstream-file-manifest.json`):

| asset | source @ revision | license (as declared) | use |
|---|---|---|---|
| **Qwen-Image-2.1** (DiT, Qwen3-VL-8B text/vision encoder, RGBA VAE) | `Qwen/Qwen-Image-2.1` @ `d26bb61` (weights identical to `b3179ad`, `790c926`, `840b4ad`) | **Qwen Research License Agreement** (release date 2026-09-20): **non-commercial**, defined as "research or evaluation purposes only"; commercial use requires a separate license from the licensor | the image-edit backend (research / evaluation) |
| ↳ local q4 export | derived locally with mflux 0.21.0 (`research/qwen/export_q4.py`) | a derivative of the above; the same terms apply | the files the edit worker loads |
| Qwen3-VL-8B-Instruct GGUF Q4_K_M + mmproj F16 | `Qwen/Qwen3-VL-8B-Instruct-GGUF` @ `f982a07` | Apache-2.0 | sd.cpp **comparator only** (research) |

**Consequences (accepted by the user 2026-10-07 for research use):**
- Qwen-Image-2.1 weights and their q4 export are **never committed and never redistributed**. photo-gen records only their identity.
- The edit backend is labelled *"Qwen Research License (non-commercial)"* in `/capabilities`, job metadata and docs.
- **Any commercial use of the edit backend is blocked by the licence**, independent of engineering status.
- **Licence boundary.**
  ```text
  photo-gen code          → MIT (LICENSE): photo-gen's own code only
  Qwen-Image-2.1 weights  → Qwen Research License: research/evaluation, non-commercial
  ```
  - photo-gen's MIT licence grants **no** rights to the Qwen weights or their q4 export.
  - The Phase 5 quality gate (G2: REJECTED) is a technical result. A validation would not have changed the licence either.
  - Any public distribution of an editing feature would need its own licensing review first.
- The Apache-2.0 alternative (`Qwen/Qwen-Image-Edit-2509/2511`, a 20B DiT) does not fit this 16 GB machine (audit §3).
- **Discrepancy (D2):** `mlx-community/Qwen-Image-2.1-mflux-q4` declares Apache-2.0 for its conversion of the research-licensed checkpoint. The upstream LICENSE governs; that pack is not used.

## 5a. Real-photograph benchmark sources (Phase 5 gate G2; not in Git)
- **What:** 16 photographs from Wikimedia Commons, 14 CC0 and 2 public domain. The licence of each was re-read from the Commons API at download time.
- **Records:** per-file creator, credit, URL, licence and hashes are in [`research/editing/real-world/source-manifest.json`](../research/editing/real-world/source-manifest.json).
- **Not redistributed:** the images aren't committed (repository image policy, even though CC0/PD would allow it). They live in `data/benchmark/real-world/` (gitignored), and edited outputs aren't published.
- **People:** adults only, no public figures.

## 6. Candidate experimental assets (not downloaded)
See [`research/experiments/4step-probe-acquisition.md`](../research/experiments/4step-probe-acquisition.md). Nothing listed there is part of photo-gen, and nothing there is licensed through photo-gen's MIT license.
