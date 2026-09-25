# Z-Image-Turbo vs Qwen-Image-2.1 + Heretic: measured comparison on a MacBook Air M5 16 GB

**Date:** 2026-09-24. All numbers below were **measured on this machine today** unless labelled otherwise.
**Evidence:**
- `z-image-tests.md`, `z-image-bench.csv`, `QWEN-BASELINE-20260924.md`, `qwen-bench-clean.csv`
- `quality-rubric.md` + `quality-results.md`
- `runs/<id>/` (raw logs, 1 Hz monitors, `time -l`), `outputs/`

No overall score or "best" verdict is given. Advantages are stated per dimension.

## Hardware and environment
- MacBook Air, Apple M5, 10-core CPU (4P+6E), **8-core GPU**, Metal 4 (MTLGPUFamilyApple10), **16 GiB** unified memory, macOS 27.0 (26A428). Metal `recommendedMaxWorkingSetSize` 12.71 GB; `maxBufferLength` 9.53 GB.
- All comparison runs used **AC power**, with only Finder, Terminal and Claude Code running (Safari quit, Office already closed). Residual swap of 0.8–2.4 GB was carried across the session; per-run swap Δ is reported.
- Monitoring: 1 Hz sampler (kernel pressure level, free %, swap, compressor, wired, process RSS/footprint) plus `/usr/bin/time -l` (kernel peak memory footprint), with pmset thermal state before and after each run.

## Exact software versions
- stable-diffusion.cpp release `master-908-88411ef` (commit 88411ef1e0688ff2df1010aeeb5d92b2d8cea2be).
  - zip sha256 `acf9cd22…386d5a` matches the GitHub asset digest.
  - Universal binary, Metal backend MTL0, auto-fit default.
  - No Python, MLX, ComfyUI or MFLUX was installed.
- Only one runtime was used for both models, so runtime differences don't confound the comparison. Model-specific settings follow each model's official/validated configuration.

## Exact model revisions (all sha256-verified on disk)
| Model | Role | Repo @ revision | File | SHA256 |
|---|---|---|---|---|
| Z-Image-Turbo | DiT | leejet/Z-Image-Turbo-GGUF @ c61c0e4 | z_image_turbo-Q4_K.gguf | 14b375ab4f226bc5378f68f37e899ef3c2242b8541e61e2bc1aff40976086fbd |
| | TE | Qwen/Qwen3-4B-GGUF @ bc64014 | Qwen3-4B-Q4_K_M.gguf | 7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5 |
| | VAE | Comfy-Org/z_image_turbo @ 6fc90a3 | split_files/vae/ae.safetensors | afc8e28272cd15db3919bacdb6918ce9c1ed22e96cb12c4d5ed0fba823529e38 |
| Qwen-Image-2.1 | DiT | leejet/Qwen-Image-2.1-GGUF @ cc11433 | qwen_image_2.1-Q4_K.gguf | 29f9c83c249ff0292fb2943fceddfa2319b446601866c82a4f8be062abea72c2 |
| | TE | pottokao/Qwen-Image-2.1-Text-Encoder-Heretic-GGUF @ e21acf0 | qwen3vl_8b_heretic-Q4_K_M.gguf | 1338274ac7a6344f262a16c7a52d1bd7fe789307d252733b23ea421126e5d343 |
| | VAE | Comfy-Org/Qwen-Image-2.1 @ 9a44dbd | vae/qwen_image_2.1_vae_bf16.safetensors | bb21f7473051e1ac368515dd3f2e15cd44d7a11748ee8823e1ddca3e4876b7c9 |

**Inference configurations:**
- **Z-Image-Turbo:** 9 steps, guidance 0 (sd.cpp `--cfg-scale 1`; `--cfg-scale 0` is sd.cpp's *unconditioned* mode), euler, sd.cpp model-default scheduler, seed 42.
- **Qwen-Image-2.1:** 25 steps, cfg 1, euler, sd.cpp model-default (resolution-dependent flow) scheduler, seed 42, no mmproj.

## Two separate questions (do not combine)

### A. Real-world deployment configuration (what each model needs to be correct here)
- **Z-Image:** Metal tensor API **disabled** (`GGML_METAL_TENSOR_DISABLE=1`). This is required: with the tensor API enabled, Z-Image outputs uniform white images (sd.cpp #1990, reproduced here).
- **Qwen:** Metal tensor API **enabled** (default). Its output is correct on this path.

### B. Backend diagnostic (cost of the M5 tensor path, 512²)
| Model | Tensor API ON | Tensor API OFF | Effect |
|---|---|---|---|
| Z-Image denoise | 45.08 s (**output blank white: FAIL**) | 69.30 s / 69.03 s (correct) | ON is faster but incorrect |
| Qwen denoise (25 steps) | 147.58 s (correct) | 254.56 s (correct; visually identical, not byte-identical) | ON is **1.72×** faster |

The tensor-off penalty on Z-Image is a **current sd.cpp/ggml Metal backend limitation on M5**, not a model property. A future fix could change it, and today's broken tensor path doesn't show what a fixed one would run at.

## Results by resolution (real-world configuration)

| Res | Model | Result | TE (s) | Denoise (s) | s/step | VAE (s) | Wall (s) | Peak footprint (GB) | Swap Δ (GB) | Pressure (samples at warn) | Min free |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| 512² | Z-Image | PASS | 3.49 | 69.03 | 7.67 | 3.80 | 76.6 | 7.26 | 0.00 | 0/66 | 17% |
| 512² | Qwen | PASS | 6.01 | 147.58 | 5.90 | 5.87 | 159.7 | 9.70 | +0.56 | 129/137 | 7% |
| 768² | Z-Image | PASS | 3.41 | 156.37 | 17.37 | 8.30 | 168.4 | 7.10 | +0.18 | 7/142 (VAE decode) | 8% |
| 768² | Qwen | CONDITIONAL PASS¹ | 5.94 | 379.55 | 15.18 | 23.74 | 409.6 | 9.85 | +0.81 | 2/353 | 4% |
| 1024² | Z-Image (n=19) | CONDITIONAL PASS¹ | 3.28 | **325.5** (314–339) | 36.2 | 31.5 | **360.6** (349–373) | **6.84** (6.75–6.88) | 0.01 (0–0.27) | 0 in 18/19 runs | ≥8% |
| 1024² | Qwen (n=6) | CONDITIONAL PASS¹ | 6.04 | **765.9** (747–780) | 30.6 | 41.5 | **813.9** (795–829) | **9.96** (9.92–10.02) | 0.32 (0–0.86) | up to 61/708 | 2% |

¹ sd.cpp logged `VAE decode ran out of memory; retrying with spatial tiling`: its model manager refused the untiled decode allocation and fell back to tiled decode automatically. No process died, and every output is valid. It's labelled CONDITIONAL because the directive's PASS requires "no OOM". **At 1024², Z-Image was ≈1.1 GB short of an untiled decode (needed 7.26 GB, had 6.12 GB); Qwen was ≈5.0 GB short (needed 8.77 GB, had 3.82 GB).** Qwen at 1024² also split its first denoising step into 34 graph segments, and wired memory reached 15.19 GB (above the 12.71 GB Metal working set).

**1024² feasibility:**
- **Z-Image-Turbo generates 1024² reliably on this Mac:**
  - 19 of 19 runs produced valid, byte-identical output (seed 42, apple prompt), plus 5 other prompts;
  - pressure normal, no swap growth, 6.8 GB peak.
  - The only flag is the self-handled VAE tiling fallback.
- **Qwen-Image-2.1 also completes 1024²** (6 of 6 valid), but runs close to memory exhaustion:
  - 2% minimum free memory;
  - wired memory above the Metal working set;
  - graph segmentation plus VAE fallback.

## Memory comparison
- Resident model params (sd.cpp auto-fit places all three components on the GPU at once):
  - Z-Image: **6.22 GB** (DiT 3.69 + TE 2.38 + VAE 0.16).
  - Qwen: **8.95 GB** (DiT 4.00 + TE 4.30 + VAE 0.64).
- Kernel peak footprint at 1024²: Z-Image **6.84 GB** vs Qwen **9.96 GB** (−31%).
- Z-Image's footprint is flat across resolutions (7.26 → 7.10 → 6.84 GB): sd.cpp tiles the VAE at 1024² instead of allocating more. Qwen is ~9.7–10.0 GB at every size.

## Swap comparison
- **Z-Image:** Δ 0.00 GB in 18 of 19 1024² runs. The one exception (+0.27 GB, thermal-3 run 2) coincided with a system-wide wired-memory spike, while sd-cli's own footprint stayed flat.
- **Qwen:** Δ +0.14 to +0.86 GB at 768²/1024² on most runs.

## Speed comparison (1024², real-world configuration)
- **Seconds per image:** Z-Image **360.6 s (6.0 min)** vs Qwen **813.9 s (13.6 min)**. Z-Image takes **0.44×** Qwen's wall time.
- **Steps per image:** 9 vs 25.
- **Seconds per DiT step:** Z-Image 36.2 (tensor API off) vs Qwen 30.6 (tensor API on). Per step, Z-Image is *slower* in today's deployment configuration because it can't use the tensor path. Its per-image advantage comes entirely from needing fewer steps.
- **Other stages:** text encode 3.3 s vs 6.0 s; VAE 31.5 s vs 41.5 s.
- **Estimate check:** the research report modeled Z-Image at ~0.31× Qwen's DiT time, assuming the same backend. Measured, the DiT ratio is 325.5 / 765.9 = **0.42×**. The difference is consistent with Z-Image losing the 1.5–1.7× tensor-path speedup that Qwen keeps.
- Step counts are each model's intended configuration. Fewer steps is **not** a quality claim (see Quality).

## Thermal comparison
- **Z-Image, sustained:**
  - 3 consecutive 1024² runs: denoise 324.7 → 338.7 → 336.6 s (+3.6–4.3%).
  - 10 consecutive 1024² runs (after ~3.5 h of near-continuous GPU load): 314.0–328.4 s, r10/r1 = 1.037, no monotonic degradation, no pmset thermal warnings.
  - All outputs byte-identical.
- **Qwen:** no dedicated 3- or 10-run series. That series was specified only for Z-Image, so Qwen's sustained behaviour is **not measured**. Qwen's 6 quality runs were interleaved with Z-Image runs, spanning ~2 h: denoise 747–780 s with no upward trend and no pmset warnings.
- pmset on this Mac doesn't report CPU_Speed_Limit, so throttling can only be inferred from timing. Measured drift was ≤4.6%.

## Quality observations (`quality-results.md`: 6 prompts, 1 seed each, rubric fixed before generation, single rater)
| Dimension | Observation |
|---|---|
| Prompt adherence and spatial layout | Qwen met every explicit layout instruction: mug behind notebook, plant far background, subject on a third-line, alley context. Z-Image missed the rule of thirds (subject centred) and two depth relations, and gave weaker scene context on 2 prompts. |
| Text legibility | Both rendered `QWEN IMAGE 2.1` exactly. On "readable text through the glass", Z-Image produced crisp but nonsense text ("Ohsnmad houch") printed on the glass, and Qwen produced no text. |
| Photorealism / fine detail | No separable difference at the viewing scale used. Both were rated 2/2 on every prompt. |
| Hands / transparency | Z-Image: two clearly separate hands with plausible refraction. Qwen: stronger caustics and reflections, but the hand count is ambiguous. |
| Artifacting | Qwen: a clock-dial numeral error, a possible faint grid texture in dark regions, and slight over-sharpening. None noted in Z-Image. |
| Locale specificity (Cebu) | Qwen showed stronger Philippine-specific cues (wiring, sari-sari stores, a tricycle). Z-Image's street was generic tropical. |

With one seed per prompt and a single rater, this is **descriptive, not statistically powered**.

## Editing capability
- **Z-Image-Turbo currently has no official instruction-editing model available.** Z-Image-Edit and Omni-Base are still "To be released" (see `Z-IMAGE-TURBO-REPORT.md` §1a). Z-Image offers only img2img and ControlNet (structure guidance).
- Qwen-Image-2.1 has native editing. It was **not tested today**. The research predicts 16–19 GB for a 1024² reference edit (proxy measurement), and today's measurements show Qwen t2i alone already near memory exhaustion at 1024², so editing remains an open, likely memory-limited question.

## Runtime complexity and reproducibility
- Both run on the same single sd.cpp binary, with zero Python dependencies, pinned model revisions and verified hashes.
- Z-Image needs one process-scoped environment variable (`GGML_METAL_TENSOR_DISABLE=1`) until sd.cpp #1990 is fixed. Without it, the failure is **silent** (exit 0, white image), so a correctness check on the output is necessary.
- Determinism: Z-Image outputs are byte-identical across 19 runs at 1024², and across both 512² runs. Qwen tensor-on vs tensor-off at 512² differ at the pixel level but look identical.
- Reproduction: `zsh research/zrun.sh <id> 1024 1024 "<prompt>"` and `zsh research/qrun.sh <id> 1024 1024 "<prompt>" on`, with models at the paths and hashes above (`research/fetch.sh` downloads with verification).

## Known limitations of this experiment
1. The quality comparison has n=1 seed per prompt, a single rater and downscaled viewing.
2. No Qwen 3- or 10-run thermal series.
3. Only 512² was measured with tensor-off vs tensor-on for Qwen.
4. Residual swap (0.8–2.4 GB) was carried across the session. Deltas are reported, but a reboot baseline wasn't taken.
5. The kernel pressure level proved noisy (Qwen 512²: 129/137 samples at warn, but 768²: 2/353), so swap Δ, min-free and footprint are the more reliable indicators.
6. Only sd.cpp was tested. MFLUX/MLX, ComfyUI and the Heretic Z-Image TE are untested.
7. `--vae-tiling` and the other memory flags were not tested. The baseline completed, so under the directive they weren't needed.

## Research gaps
- Whether a future sd.cpp release fixes #1990, and what Z-Image speed a *correct* tensor path would give.
- Whether MLX (mflux) avoids the M5 tensor-kernel problem and uses the M5 GPU tensor units correctly.
- Qwen-Image-2.1 editing on this Mac.
- Multi-seed / multi-rater quality statistics.
- Heretic TE A/B for Z-Image (`Lockout/qwen3-4b-heretic-zimage`); format and compatibility unverified.

## Advantages by dimension (measured; no overall winner)
| Dimension | Advantage | Basis |
|---|---|---|
| Time per 1024² image | Z-Image | 360.6 s vs 813.9 s (0.44×) |
| Time per DiT step | Qwen | 30.6 s vs 36.2 s (Qwen keeps the M5 tensor path) |
| Peak memory / swap / pressure | Z-Image | 6.84 vs 9.96 GB; swap Δ ~0 vs up to +0.86 GB; min free ≥8% vs 2% |
| Memory headroom at 1024² | Z-Image | VAE-fallback shortfall 1.1 GB vs 5.0 GB; no graph segmentation |
| Correctness out of the box | Qwen | Z-Image needs the #1990 workaround; the failure is silent |
| Prompt adherence / layout | Qwen | 6 prompts, rubric scores (limitations above) |
| Exact text rendering (short string) | Neither | Both exact |
| Artifacts | Z-Image (slight) | Qwen showed 3 minor defects; none noted in Z-Image |
| Editing | Qwen (by capability) | Z-Image has no editing model; Qwen editing untested here |
| Sustained thermal stability | Z-Image measured stable | 10-run drift ≤4.6%; Qwen not series-tested |
| License | Z-Image | Apache-2.0 vs Qwen Research License (non-commercial) |
