# Qwen editing backend: source and acquisition audit (Phase 4)

Audited 2026-10-06, before any download. Sources: Hugging Face API metadata at pinned revisions (`upstream-file-manifest.json`), the model card and LICENSE, the mflux 0.21.0 wheel source (sha256 `b2e38fd3cd4e50d497cc226e01555b8fc7856181c9421bde2e043bc53ac12d2e`, read from an unpacked copy, **not installed**), the Diffusers pipeline at `80c7ed2`, the sd.cpp docs, the local sd.cpp `master-908` help text, and the mflux GitHub tracker.

**Status: RESEARCH / EXPERIMENTAL.** Nothing here changes the Z-Image production profiles, the production venv (`mflux/.venv`, mflux 0.20.0), or the v1/v2 tags.

## 1. Question
Which Qwen checkpoint and runtime gives PHOTO-GEN a real, memory-safe, reproducible **instruction-based image-editing** path on this MacBook Air M5 (16 GB)?

Z-Image remains the only generation model. Qwen is added for a capability Z-Image lacks.

## 2. Historical evidence (preserved, unchanged)
`research/QWEN-BASELINE-20260924.md`, `research/REPORT.md`, `research/FINAL-M5-COMPARISON.md` and `research/qwen-bench-clean.csv` hold the 2026-09-24 Qwen-Image-2.1 **text-to-image** baseline:
- sd.cpp `master-908-88411ef`, DiT `leejet/Qwen-Image-2.1-GGUF` Q4_K, heretic Qwen3-VL TE Q4_K_M without mmproj (so t2i only), 25 steps, cfg 1.
- At 1024²: 813.9 s per image, peak footprint 9.96 GB, wired memory 15.19 GB (above the 12.71 GB Metal working set), 2% free, and an automatic VAE-decode OOM fallback (CONDITIONAL PASS).
- Editing was **not tested**. The research predicted 16–19 GB for a 1024² edit.

That evidence stays as is. This audit re-evaluates the ecosystem as of 2026-10-06 rather than assuming that path.

## 3. Qwen model families considered

| family | editing | DiT size | TE | license | 16 GB fit | verdict |
|---|---|---|---|---|---|---|
| **Qwen-Image-2.1** (`Qwen/Qwen-Image-2.1`) | **native**: instruction editing, up to 10 references, RGBA | 7.1B single-stream (14.2 GB bf16; q4 ≈ 4.0 GB) | Qwen3-VL-8B-Instruct, unmodified (17.5 GB bf16 incl. 27-layer vision tower; q4 ≈ 4.6 GB) | **Qwen Research License (non-commercial)** | plausible at q4 (weights ≈ 10 GB incl. fp32 VAE; the text encoder is released before denoise under `--low-ram`). **Unproven; must be measured.** | **SELECTED** (pending licence acceptance, §8) |
| Qwen-Image-Edit-2511 / -2509 (`Qwen/Qwen-Image-Edit-2511` @ `6f3ccc0`) | native instruction editing | 20.4B MMDiT (40.86 GB bf16; q4 ≈ 11.5 GB) | Qwen2.5-VL-7B (16.58 GB bf16) | **Apache-2.0** | **no.** The q4 DiT alone ≈ 11.5 GB, close to the 12.71 GB Metal working set before activations, the 2× edit token stream and the true-CFG second pass (mflux default guidance 4.0 → 2 passes per step). mflux warns that ≤ 6-bit "can degrade the image a lot more" for this family. | REJECTED on memory arithmetic (desk; not downloaded). This is the licence-clean alternative, so the rejection matters (§8). |
| Qwen-Image / -2512 (t2i) | none (txt2img only) | 20B | Qwen2.5-VL-7B | Apache-2.0 | no | out of scope |

**Why 2.1 is "materially improved" for this machine:** a 7B DiT instead of 20B, and a step-independent prefix KV cache (`causal_condition` makes text and reference activations independent of t). That cache is the only reason editing at ≈ 1 MP is even plausible on 16 GB.

## 4. Selected model identity
- **Repository:** `Qwen/Qwen-Image-2.1`.
- **Revision pinned: `d26bb61231c349cf6b7896fa83353113880e1ba3`** (main, lastModified 2026-09-30).
- **Weight identity across revisions.** The 7 weight blobs (LFS sha256) are **identical** at `840b4ad` (the "0919 release checkpoint", the last weight change), `b3179ad` (mflux 0.21.0's validated revision), `790c926` (the revision our 2026-09-24 research recorded) and `d26bb61`. The later commits are README and asset changes only. Verified 2026-10-06; the set digest is the same `6c16cd39…` at all four revisions.
- **Files:** 28 files, 33.13 GB. Every digest is in `upstream-file-manifest.json`.

| component | file(s) | size |
|---|---|---:|
| transformer | `transformer/diffusion_pytorch_model-0000{1,2}-of-00002.safetensors` (`9e6bc2d6…`, `3aaf234d…`) | 9.968 + 4.262 GB |
| text encoder (Qwen3-VL-8B-Instruct + vision tower + untied `lm_head`) | `text_encoder/model-0000{1..4}-of-00004.safetensors` (`dde00291…`, `9047facc…`, `8c541876…`, `5311532a…`) | 17.53 GB |
| VAE (64-ch RGBA, 16× spatial) | `vae/diffusion_pytorch_model.safetensors` (`a07a1b7c…`) | 1.351 GB |
| processor, scheduler, configs | small text files (git-sha1 in the manifest) | — |

- **Precision plan:** quantize the DiT and the text/vision encoder to **q4** with mflux 0.21.0 (MLX affine, the same format family as production Z-Image). The VAE stays fp32 (mflux keeps it unquantized). Activations are bf16 (mflux's 2.1 default dtype).
- **Scheduler:** official Diffusers `QwenImage21Pipeline` uses flow-match Euler with the resolution-dependent shift; mflux's `linear` with `requires_sigma_shift`, `sigma_max_shift 0.9` and `terminal 0.02` is the parity-tested port. No scheduler parameter is exposed (see D6).
- **Sampling defaults (authoritative = Diffusers `80c7ed2` `__call__`):** `num_inference_steps=40`, `true_cfg_scale=1.0` ("meant to be sampled without guidance"), `output_resolution=1024`, `use_kv_cache=True`, and dimensions in multiples of 32. mflux 0.21.0 matches all five.

## 5. Runtime candidates

| candidate | status 2026-10-06 | editing | dependencies | verdict |
|---|---|---|---|---|
| **mflux 0.21.0 `QwenImage21Edit`** (`mflux-generate-qwen-2.1-edit`) | released 2026-10-03; the result of merging #741 and #749, reconciled in #783/#796; parity tests vs Diffusers `80c7ed2` and checkpoint `b3179ad` (35 reference tests) | single- and multi-reference instruction editing, prefix KV cache, q4/q8 quantize-and-export of the **complete vision-capable** checkpoint, `--low-ram` | `mlx>=0.32.0,<0.33` (so it **can run on the exact MLX 0.32.2** used in production); also pulls `torch>=2.13`, `transformers>=5.5` | **PRIMARY**, in a **separate project-local venv** (§7) |
| sd.cpp `master-908-88411ef` (already built locally; latest is `master-929`, 2026-09-27) | Qwen-2.1 editing via `-r` + `--llm_vision` (mmproj), plus the `qwen_image_2_1_prefix_cache` model arg (present in the local `sd-cli-help.txt`) | yes | none new; needs the official `Qwen3VL-8B-Instruct-Q4_K_M.gguf` (5.03 GB) + `mmproj-Qwen3VL-8B-Instruct-F16.gguf` (1.16 GB) | **COMPARATOR**, bounded runs (`QWEN-RUNTIME-COMPARISON.md`) |
| mflux 0.20.0 (installed) `QwenImage21` | t2i + SDEdit img2img only; `QwenImageEdit` is the 20B 2509/2511 path | no instruction editing for 2.1 | — | not applicable |
| Diffusers on MPS (the reference implementation) | authoritative numerics | yes | 33 GB bf16 resident; mflux documented a PyTorch 2.13 MPS temporal-padding bug in VAE encode | infeasible as a runtime on 16 GB; used only as the *authority* |
| ComfyUI (v0.37+, PR #16400) | — | yes | MPS VAE-encode bug #16433 corrupts edits unless `--cpu-vae` (`research/REPORT.md` S4); stock GGUF loader needs patches | rejected (correctness) |
| `mlx-community/Qwen-Image-2.1-mflux-q4` @ `746a585` | text-only export: the TE index has 905 keys, **0 vision keys, no `lm_head`**; needs a non-stock "Rapid-MLX" loader (its own README says so) | **no** | — | rejected (cannot edit); licence discrepancy D2 |
| `JoyFusionAI/Qwen-Image-2.1-MLX-4bit` @ `c78c088` | TE index has 399 keys, **0 vision keys**, TE not quantized (15 GB) | **no** | — | rejected (cannot edit) |

**No pre-quantized, vision-capable MLX pack exists.** The complete checkpoint must be downloaded (33.13 GB, the same size whether or not one quantizes at load) and exported once to q4 with `QwenImage21Edit.save_model`. mflux's README documents this path, and its validation reports pixel-identical output after an 8-bit export/reload.

## 6. Discrepancies (surfaced; none silently resolved)
- **D1. mflux 0.20.0 Qwen-Image-Edit identity.** `qwen/README.md` says the edit model "uses `Qwen/Qwen-Image-Edit-2511`"; `ModelConfig['qwen-image-edit'].model_name` is `Qwen/Qwen-Image-Edit-2509` (2511 is only an alias). Not used here (that family is rejected on memory), but recorded.
- **D2. Third-party licence relabelling.** `mlx-community/Qwen-Image-2.1-mflux-q4` declares `apache-2.0` and states "the original model and this conversion are licensed under Apache-2.0". The upstream checkpoint is the **Qwen Research License (non-commercial)** (`LICENSE` at `d26bb61`, release date 2026-09-20). **Authoritative: the upstream LICENSE.** A conversion cannot relicense the weights.
- **D3. Revision drift since our research.** We recorded `790c926`; main is now `d26bb61`. Weight blobs are identical (§4), so this is not a weight change. We pin `d26bb61` and record `b3179ad` as mflux's validated revision.
- **D4. Guidance.** The sd.cpp `docs/qwen_image_2.1.md` examples use `--cfg-scale 6.0`; the official card, Diffusers (`true_cfg_scale=1.0`) and mflux (guidance 1.0, "trained default") sample **without** CFG. **Authoritative: Diffusers / the official card.** The comparator therefore runs sd.cpp at cfg 1.0.
- **D5. Known quality limitation at 1024².** mflux's `reference/VALIDATION.md` records that the 1024×1024 panda edits (single- and two-reference) **failed visual acceptance in both MLX and a controlled Diffusers reference run**. Successes were 512² single/two-reference edits and an 896×1152 two-reference clothing edit. This is a model/input-level limitation, not a port bug. The directive's "1024² first" baseline therefore measures performance/memory at 1024² but must not presume 1024² edit quality.
- **D6. mflux 0.21.0 open bugs** (#831; fix PR #835 open, not released):
  - `--scheduler` is accepted but ignored by the edit command, which always runs linear;
  - `--enhance-prompt` sees only the first reference;
  - `--verify` reads ambiguously with multiple references.
  PHOTO-GEN uses none of these options and always runs the default linear scheduler, so it is unaffected. Those options are not exposed.
- **D7. mflux 0.21.0 changes Z-Image numerics.** #803 makes the bf16 hidden stream the default (adds `--float32`); #802 changes the `--low-ram` transformer release. Upgrading the production venv would change the REFERENCE hashes. **The production venv stays on 0.20.0**, and the Qwen venv must never run Z-Image.
- **D8. Upstream memory evidence is not from a 16 GB machine.** These are mflux's own runs on 128 GB machines, q8, without `--low-ram`, peak MLX allocation:
  - 512² single-reference edit: 19.5 GB;
  - 896×1152 two-reference edit: 31.5 GB;
  - 1024² dense t2i: 31.9 GB.
  These figures include an unbounded MLX cache. With q4 + `--low-ram` (cache limit 1 GB, text encoder released before denoise), the fit is plausible but **unproven**. The reference-image VAE encode runs **untiled while the text encoder is still resident** (`qwen_image_21_edit.py`). That is the most likely peak, and it is measured first.
- **D9. Two mflux 2.1 commands have different quantization scope.** `qwen21/README.md` (t2i command) says the text encoder "is never quantized and stays resident" (≈ 46 GB peak). `reference/README.md` (the edit command) says quantization "applies to eligible transformer and text/vision encoder layers; the VAE stays in fp32". We use only the edit class. The exported TE must be verified to be quantized (scales present) after export.
- **D10. Historical TE ≠ comparator TE.** The 2026-09-24 baseline used the refusal-ablated `heretic` TE without mmproj. The editing comparator uses the **official** `Qwen/Qwen3-VL-8B-Instruct-GGUF`, Apache-2.0, matching the unmodified TE inside `Qwen/Qwen-Image-2.1`. Results are therefore not directly comparable with the 09-24 t2i rows.

## 7. Environment decision (directive §14)
- **Option A (adapt to the existing venv):** impossible without upgrading mflux in `mflux/.venv` (forbidden; D7).
- **Option C (another implementation):** sd.cpp is kept as the comparator. Diffusers and ComfyUI were rejected in §5.
- **→ Option B: a separate, project-local venv `mflux-qwen/.venv`.** Built with the project-local uv/Python (`source mflux/env.sh`). No global installs.
  - mflux pinned `==0.21.0` (wheel sha256 `b2e38fd3…`).
  - `mlx==0.32.2` and `mlx-metal==0.32.2` pinned explicitly, so both backends share the exact MLX kernels and NAX behaviour.
  - Lock file committed under `config/`.
  - Its workers run with the same environment hygiene as Z-Image (`MLX_*`/`HF_*` stripped, `HF_HUB_OFFLINE=1`).
  - PHOTO-GEN's server process never imports either venv's mflux. It launches each backend's worker with that backend's interpreter.

## 8. Licence assessment
**Qwen Research License, release date 2026-09-20.**
- §1(i) "Non-Commercial" means "for research or evaluation purposes only".
- §2(a) grants use, reproduction and derivatives for non-commercial purposes only; §2(b) commercial use needs a separate licence.
- §3 lets derivatives be distributed only with the licence copy, change notices and the NOTICE attribution.
- §4(c) forbids "Qwen" as the *primary* name of a derivative (descriptive use is fine).

**Consequences for PHOTO-GEN**
- Research/evaluation use on this private machine is permitted.
- PHOTO-GEN's MIT licence covers only its own code and never relicenses the weights (already stated in `LICENSE` / THIRD-PARTY-LICENSES).
- Weights and the q4 export are **never committed** (`models/**` is gitignored) and never redistributed.
- The Qwen backend is labelled *"Qwen-Image-2.1 (Qwen Research License, non-commercial)"* everywhere it is exposed: capabilities, metadata, docs.
- **Production adoption for any commercial use is blocked by the licence, not by engineering.** The only Apache-2.0 editing family (Edit-2511) doesn't fit in 16 GB (§3). This is the user's decision.

## 9. OEM-parts classification (directive §15)

| component | source @ revision | licence | class | use / modifications |
|---|---|---|---|---|
| Qwen-2.1 edit pipeline (prompt encode with vision, prefix KV cache, layout, flow-match Euler, VAE) | mflux 0.21.0 `mflux/models/qwen21/**` (wheel `b2e38fd3`) | MIT (mflux); adapted Diffusers code carries Apache-2.0 attribution (`reference/LICENSE.diffusers`) | **REUSE** (unmodified, called through its CLI `main()` in a worker process) | none; any patch would be in-process in the PHOTO-GEN worker, evidence-backed, like Z-Image |
| q4 export | mflux `QwenImage21Edit(quantize=4).save_model` | MIT | **REUSE** | one-time, scripted, hashed into an immutable manifest |
| Diffusers `QwenImage21Pipeline` @ `80c7ed2` | Apache-2.0 | — | **authority** (not run) | source of defaults (§4) |
| sd.cpp `master-908-88411ef` | MIT | — | **WRAP** (comparator only, via the existing `research/qrun.sh` pattern) | none |
| worker process, probes, job/queue, staging, integrity, metadata | PHOTO-GEN | MIT | **BUILD / ADAPT** (from the Z-Image worker) | new edit worker modelled on `mflux_zimage_worker.py` |

## 10. Acquisition plan (awaiting user approval)

| asset | source @ revision | size | destination (gitignored) | verification |
|---|---|---:|---|---|
| Qwen-Image-2.1 complete checkpoint | `Qwen/Qwen-Image-2.1` @ `d26bb61` | 33.13 GB | `models/research/qwen-image-2.1/` | every file vs `upstream-file-manifest.json` (sha256 / git-sha1) |
| q4 edit export (derived locally) | the above, via mflux 0.21.0 | ≈ 10 GB expected | `models/qwen/qwen-image-2.1-edit-mflux-q4/` | hashed into `config/backend-qwen21-edit-mflux.json` |
| Qwen3-VL-8B-Instruct Q4_K_M + mmproj F16 (comparator) | `Qwen/Qwen3-VL-8B-Instruct-GGUF` @ `f982a07` (Apache-2.0) | 5.03 + 1.16 GB | `models/text_encoders/` | sha256 `67d1659b…`, `ca524100…` |
| Python packages for `mflux-qwen/.venv` | PyPI | ≈ 1–2 GB | `mflux-qwen/` (gitignored) | lock file committed |

- **Storage:** ≈ 50 GB total. 236 GiB were free on 2026-10-06.
- **Downloads** run as a top-level `nohup` job with a completion marker.
- **HF hygiene:** the HF cache stays project-local, and runtime is offline (`HF_HUB_OFFLINE=1`).
- **Status: AUDIT COMPLETE.** Download, venv and licence acceptance await the user's decision.
