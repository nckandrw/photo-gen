# Z-Image-Turbo research log

Format per addendum §28. Dates are source dates; all checks done 2026-09-24.

---
CLAIM: The official Z-Image-Turbo is Tongyi-MAI/Z-Image-Turbo, and its weights are unchanged since release.
SOURCE: HF API /api/models/Tongyi-MAI/Z-Image-Turbo and /commits/main
DATE: created 2025-11-25; last modified 2026-01-30
VERSION/COMMIT: f332072aa78be7aecdf3ee76d5c247082da564a6
EVIDENCE: commit titles since 2025-11-26 are README/asset/app updates only
CONFIDENCE: VERIFIED
NOTES: The transformer is stored as fp32 (3 shards, 24.62 GB total)

---
CLAIM: The DiT is a 6.15 B-param S3-DiT: dim 3840, 30 layers + 2 refiners, 30 heads, patch 2, 16-ch latent input
SOURCE: transformer/config.json; arXiv 2511.22699
DATE: 2025-11
VERSION/COMMIT: f332072
EVIDENCE: config fields; paper text "6.15B"
CONFIDENCE: VERIFIED
NOTES: —

---
CLAIM: The text encoder is functionally Qwen/Qwen3-4B (not Qwen3-4B-Instruct-2507)
SOURCE: HF LFS sha256 of the text_encoder shards vs Qwen/Qwen3-4B and Qwen3-4B-Instruct-2507; safetensors header range-read of shard 3; diffusers pipeline_z_image.py
DATE: 2026-09-24
VERSION/COMMIT: Z-Image-Turbo f332072; diffusers main
EVIDENCE: shards 1–2 byte-identical to Qwen3-4B (328a91d3…, 6cd087b3…) and different from 2507. Shard 3 has identical tensor names, shapes, dtypes and offsets (layer 35 + norm), but different data. The pipeline uses hidden_states[-2], so layer 35 + the final norm are unused.
CONFIDENCE: STRONGLY SUPPORTED
NOTES: sd.cpp docs recommend the Qwen3-4B-Instruct-2507 GGUF, which is a different model (minor discrepancy). Plan uses Qwen/Qwen3-4B-GGUF@bc64014.

---
CLAIM: The VAE is the FLUX.1 VAE (16-ch, 8×)
SOURCE: vae/config.json (_name_or_path "flux-dev", scaling 0.3611, shift 0.1159)
DATE: 2025-11
VERSION/COMMIT: f332072
EVIDENCE: config
CONFIDENCE: VERIFIED
NOTES: Comfy-Org ae.safetensors sha256 afc8e28272cd15db3919bacdb6918ce9c1ed22e96cb12c4d5ed0fba823529e38

---
CLAIM: Official Turbo inference is 9 scheduler steps (8 DiT forwards), guidance_scale 0.0, 1024² example
SOURCE: HF model card Quick Start
DATE: 2025-11 / 2026-01
VERSION/COMMIT: f332072
EVIDENCE: code comment "This actually results in 8 DiT forwards"; "Guidance should be 0 for the Turbo models"
CONFIDENCE: VERIFIED
NOTES: Scheduler config is static shift 3.0. max_sequence_length is 512 (pipeline).

---
CLAIM: The documented resolution range is up to ~1–1.5k
SOURCE: arXiv 2511.22699 (HTML)
DATE: 2025-11
VERSION/COMMIT: v1 HTML
EVIDENCE: "arbitrary resolutions up to the 1k-1.5k range" (via WebFetch extraction)
CONFIDENCE: STRONGLY SUPPORTED
NOTES: Extracted by a summarizing fetcher; the exact wording should be re-checked in the PDF

---
CLAIM: Z-Image-Edit and Z-Image-Omni-Base are unreleased
SOURCE: HF card Model Zoo; GitHub README; HF org listing; GitHub issues
DATE: README last push 2026-02-09; latest Edit issue #174 dated 2026-09-20
VERSION/COMMIT: GitHub 26f23ed; HF f332072
EVIDENCE: "To be released" for both; the org lists only Turbo + Z-Image; 12 open issues ask for Edit
CONFIDENCE: VERIFIED
NOTES: MATERIAL discrepancy vs the addendum's assumption. The user must decide how editing is handled.

---
CLAIM: License is Apache-2.0 for both weights and code
SOURCE: HF cardData.license; GitHub license SPDX
DATE: 2026-09-24
VERSION/COMMIT: f332072 / 26f23ed
EVIDENCE: "apache-2.0" / "Apache-2.0"
CONFIDENCE: VERIFIED
NOTES: Qwen-Image-2.1 is Qwen Research (non-commercial). FLUX.2-klein-4B is Apache-2.0; klein-9B is flux-non-commercial.

---
CLAIM: mflux has supported Z-Image-Turbo since v0.13.0; the current version is v0.20.0
SOURCE: GitHub releases mflux-community/mflux
DATE: 2025-12-03 → 2026-09-21
VERSION/COMMIT: v.0.20.0
EVIDENCE: release notes
CONFIDENCE: VERIFIED
NOTES: Requires Python ≥3.10 and mlx >=0.32,<0.33

---
CLAIM: mflux --low-ram frees the Z-Image text encoder before denoising (single-seed), caps the MLX cache at 1 GB, and tiles the VAE
SOURCE: src/mflux/callbacks/instances/memory_saver.py
DATE: 2026-09-21
VERSION/COMMIT: v.0.20.0
EVIDENCE: call_before_loop → _delete_text_encoders (text_encoder=None, gc.collect, mx.clear_cache); __init__ mx.set_cache_limit(1000**3); TilingConfig when may_tile_implicitly
CONFIDENCE: VERIFIED (code)
NOTES: Without --low-ram the TE stays resident (generate_image never frees it). All components are loaded at init.

---
CLAIM: mflux quantizes the Z-Image TE too (unlike its Qwen-2.1 path)
SOURCE: z_image_weight_definition.quantization_predicate; mflux-community q4 pack sizes
DATE: 2026-08-03 (packs)
VERSION/COMMIT: v.0.20.0; q4 d2d3050
EVIDENCE: predicate = hasattr(module,"to_quantized"); q4 text_encoder 2.26 GB vs bf16 8.05 GB
CONFIDENCE: VERIFIED
NOTES: —

---
CLAIM: mflux's Turbo schedule is linear sigmas with a resolution-dependent shift; official is static shift 3.0
SOURCE: linear_scheduler.py; model_config.py (requires_sigma_shift=True); scheduler_config.json
DATE: 2026-09
VERSION/COMMIT: v.0.20.0 / f332072
EVIDENCE: code; config
CONFIDENCE: CONFLICTING (minor)
NOTES: ≈equal at 1024² (e^1.15≈3.16), diverges at 512². Python API default steps = 4; the CLI default follows the model.

---
CLAIM: M4 Max 128 GB, mflux q8, z-image-turbo 512², 9 steps: 17.1 s total, ≈1.8 s/it; sustained sessions throttled ~1.7×
SOURCE: mflux PR #686 body
DATE: 2026-08-27
VERSION/COMMIT: PR #686 merged
EVIDENCE: maintainer-reported benchmark
CONFIDENCE: REPORTED (primary, indirect hardware)
NOTES: Not transferable to 8-core M5 without a model; see report §12

---
CLAIM: "Z-Image on M3 Metal: 600 s/it vs 19 s/it ComfyUI" (sd.cpp #1030)
SOURCE: GitHub issue leejet/stable-diffusion.cpp#1030
DATE: 2025-12-02
VERSION/COMMIT: release binary at that time
EVIDENCE: leejet: "The precompiled version does not support Metal"
CONFIDENCE: VERIFIED (cause)
NOTES: Current binary master-908-88411ef includes Metal (verified on this Mac), so this doesn't apply. The ComfyUI 19 s/it (M3, 1024×512) is REPORTED.

---
CLAIM: Text rendering: Z-Image-Turbo CVTG-2K word acc 0.8585 / NED 0.9281; LongText EN 0.917 / ZH 0.926
SOURCE: arXiv 2511.22699
DATE: 2025-11
VERSION/COMMIT: v1
EVIDENCE: paper tables (vendor)
CONFIDENCE: REPORTED (official claim)
NOTES: Comparator is Qwen-Image v1 (0.8288; 0.943/0.946), NOT Qwen-Image-2.1. No head-to-head with 2.1 exists.

---
CLAIM: Qwen-Image-2.1 has no published CVTG/LongText/GenEval/DPG numbers in its official README; the only 2.1 score found is Qwen-Image-Bench 60.28
SOURCE: QwenLM/Qwen-Image-2.1 README grep; buildfastwithai review (search snippet)
DATE: 2026-09
VERSION/COMMIT: README at 2026-09-20 push
EVIDENCE: grep empty; snippet
CONFIDENCE: STRONGLY SUPPORTED (absence in README) / REPORTED (60.28)
NOTES: Qwen-Image-Bench is Qwen's own benchmark

---
CLAIM: Image-token count per resolution is identical for Z-Image and Qwen-2.1
SOURCE: configs (Z: 8× VAE, patch 2; Qwen-2.1: 16× VAE, patch 1)
DATE: —
VERSION/COMMIT: f332072 / 790c926
EVIDENCE: arithmetic
CONFIDENCE: VERIFIED (derived)
NOTES: 4096 tokens at 1024²

---
CLAIM: Per-step DiT compute ≈0.87× Qwen-2.1; per-image DiT time ≈0.31× at 9 vs 25 steps
SOURCE: params 6.15/7.12 B; attention 30·3840 vs 32·4096
DATE: —
VERSION/COMMIT: —
EVIDENCE: arithmetic
CONFIDENCE: ESTIMATE (MODELED)
NOTES: Kernel efficiency, quant format and VAE differences are not modeled

---
CLAIM: No safety checker in the official diffusers pipeline; the model card has no safety statements
SOURCE: pipeline_z_image.py grep; card grep
DATE: 2026-09-24
VERSION/COMMIT: diffusers main; f332072
EVIDENCE: 0 matches for safety/nsfw/watermark/filter/refus
CONFIDENCE: VERIFIED (absence in these files)
NOTES: Hosted demos may filter (UNVERIFIED)

---
CLAIM: A Heretic-ablated Z-Image TE exists
SOURCE: HF Lockout/qwen3-4b-heretic-zimage
DATE: 2025-12-16
VERSION/COMMIT: main
EVIDENCE: model card text
CONFIDENCE: REPORTED
NOTES: No numeric eval in text; format/runtime compatibility UNVERIFIED; separate artifact, not substituted

---
CLAIM: No base-M5 / M5 Air / 16 GB Z-Image-Turbo measurement is public
SOURCE: WebSearch (3 queries), HF, GitHub mflux/sd.cpp/Z-Image issues
DATE: 2026-09-24
VERSION/COMMIT: —
EVIDENCE: absence
CONFIDENCE: STRONGLY SUPPORTED (absence of evidence)
NOTES: Reddit not retrievable directly
