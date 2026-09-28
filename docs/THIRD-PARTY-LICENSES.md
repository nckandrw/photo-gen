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

## 4. Research-only external assets (Pass 1 comparison; not used by photo-gen, not in Git)
The Qwen-Image 2.1 / Z-Image GGUF files, Qwen3 GGUF text encoders, VAEs, and the stable-diffusion.cpp build under `models/diffusion_models`, `models/text_encoders`, `models/vae` and `sdcpp/`.
- Their sources and pins are in `research/model-pins.txt`, `research/z-image-model-pins.txt` and `research/REPORT.md`.
- `research/REPORT.md` records a **conflicting** licence statement for one Qwen-2.1 derivative (the derivative's card says Apache-2.0, the official card says the Qwen Research License). The official license governs.

## 5. Candidate experimental assets (not downloaded)
See [`research/experiments/4step-probe-acquisition.md`](../research/experiments/4step-probe-acquisition.md). Nothing listed there is part of photo-gen, and nothing there is licensed through photo-gen's MIT license.
