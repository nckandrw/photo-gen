# Z-Image-Turbo on a MacBook Air M5 (16 GB): research addendum

> **Correction (2026-09-25):** this report quotes the model card's "9 steps (8 DiT forwards)". That was a diffusers artifact. In mflux, 9 steps = 9 NFE, and the official Turbo recipe is 8 NFE with a static shift of 3.0. See `experiments/scheduler-nfe-note.md` and `experiments/sigma-schedule-audit.md`. The original text is kept below unchanged.

**Date:** 2026-09-24. **Scope:** research only. Nothing was installed or downloaded. The only network reads were HF/GitHub API calls and two safetensors *header* range-reads (≈50 KB).
**Machine** (measured in the Qwen project): Apple M5, 8-core GPU, Metal 4 (Apple10), 16 GiB unified memory. Metal `recommendedMaxWorkingSetSize` 12.71 GB, `maxBufferLength` 9.53 GB, macOS 27.0.
**Baseline for comparison:** Qwen-Image-2.1 + Heretic Q4_K_M, which has **one real measurement on this Mac** (`research/tests.md`, run `p5-512-s8-seed42`). That run was confounded: on battery, with apps open, 6.5 GB of swap.

Labels: **VERIFIED · STRONGLY SUPPORTED · REPORTED · ESTIMATE · UNVERIFIED · CONFLICTING**. For numbers, I also use **MEASURED** (this Mac) and **MODELED** (arithmetic from verified configs, method shown).

---

## 1. Executive conclusion

**No overall ranking is given (as instructed).** Per dimension:

| Dimension | Finding | Label |
|---|---|---|
| Memory on 16 GB | Z-Image-Turbo is materially lighter. In sd.cpp, the co-resident weights would be ≈ **6.7 GB**, vs **8.95 GB measured** for Qwen-2.1 (MODELED from verified file sizes plus the auto-fit behaviour measured here). The mflux 4-bit pack is 5.9 GB, and `--low-ram` drops the text encoder (2.26 GB) before denoising (VERIFIED in source). | MODELED / VERIFIED |
| Generation speed | About **⅓ of the DiT evaluations** (9 steps / 8 NFEs vs 25), and each step costs about **0.87×** as much (MODELED from configs). DiT time per image ≈ 0.31× Qwen-2.1's. **Not measured on this Mac.** | MODELED |
| Resolution ceiling | Z-Image's paper says "arbitrary resolutions up to the 1k–1.5k range". **2048² is outside the documented range.** Qwen-2.1 is *native* at 2048² (but that's not viable on 16 GB). | VERIFIED (paper) |
| **Editing** | **Z-Image-Turbo does not edit.** **Z-Image-Edit and Z-Image-Omni-Base are still "To be released"** about 10 months after being announced. The official repo has had no push since 2026-02-09, and 12 open issues ask about Edit. Available instead: img2img, and ControlNet Union 2.1 (a separate PAI checkpoint; about 20 steps; not instruction editing). Qwen-2.1 edits natively. | VERIFIED |
| Text rendering | Official numbers exist, but **only against Qwen-Image v1 (20B), not Qwen-Image-2.1**. On CVTG-2K, Z-Image-Turbo scores 0.8585 vs Qwen-Image 0.8288. On LongText-Bench EN, it's 0.917 vs 0.943. **No head-to-head with 2.1 exists.** | VERIFIED (vendor paper) / gap |
| Apple-Silicon maturity | mflux has supported it since v0.13.0 (2025-12-03), and it has been refined through v0.20.0 (2026-09-21). sd.cpp support is also mature. ComfyUI works natively. By contrast, Qwen-2.1 support is 4–10 days old everywhere. | VERIFIED |
| License | Apache-2.0 for **both** code and weights: commercial use allowed. Qwen-2.1 is under the Qwen Research License (non-commercial). | VERIFIED |
| M5 / 16 GB evidence | **No base-M5 or 16 GB Z-Image measurement was found.** The best primary figure is M4 Max (128 GB), mflux q8, 512²: 1.8 s/it, 17.1 s total. | VERIFIED (indirect) |

**Bottom line (evidence, not a verdict).**
- For **text-to-image at ≤1024²** on this Mac, Z-Image-Turbo is favoured by every *modeled* resource metric: memory, step count, runtime maturity and license.
- For **editing**, it has **no official capability**. That is the material discrepancy in §1a.
- Whether Turbo's image quality matches Qwen-2.1 is **unestablished**: no independent comparison against 2.1 exists. Answering it requires the A/B benchmark in §21 (validation plan).

### 1a. Discrepancies

```text
DISCREPANCY DETECTED  (material)

Previous evidence:
The addendum (§4, §15) treats Z-Image-Edit as a current model to be researched for Mac
and MFLUX support.

New evidence:
- The Tongyi-MAI HF org has only Z-Image-Turbo (2025-11-25) and Z-Image (2026-01-23).
- The official Model Zoo lists Z-Image-Edit and Z-Image-Omni-Base as "To be released" on
  both the HF card (rev f332072, 2026-01-30) and the GitHub README (last push 2026-02-09).
- 12 open GitHub issues ask about Edit, the latest dated 2026-09-20.
- mflux v0.20.0 has no Z-Image edit command.

Why this matters:
"Editing capability" is one of the 15 comparison dimensions. Qwen-2.1 has native
multi-reference editing. Z-Image today has only img2img plus a ControlNet (structure
guidance), which isn't instruction editing. The editing half of §15/§23 has no model
to test.

Possible interpretations:
1. Z-Image is a text-to-image-only candidate. Editing stays with Qwen-2.1, or is
   dropped as a goal on this Mac.
2. Wait for Z-Image-Edit. There is no date, and 10 months have passed without a release.
3. Split architecture: Z-Image-Turbo for t2i + Qwen-2.1 for editing, which means two
   model stacks on disk and two runtimes to maintain.

Recommended next action: your decision. I haven't adopted any option. Option 1
keeps the comparison clean and is what I've planned tests around.
```

```text
DISCREPANCY (minor, logged and resolved)

sd.cpp docs (commit 88411ef, docs/z_image.md) pair Z-Image with Qwen3-4B-Instruct-2507 GGUF.
The official Z-Image text encoder is Qwen3-4B (the original hybrid-thinking model, not the
2507 Instruct):
  - shards 1–2 byte-identical (sha256 328a91d3…, 6cd087b3…);
  - shard 3 has identical tensor names/shapes/offsets, but layer-35/final-norm data differs.
    The official pipeline takes hidden_states[-2], so those tensors are never used.
Resolution: test plan uses the official Qwen/Qwen3-4B-GGUF @ bc64014 (Q4_K_M 2,497,280,256 B),
not the Instruct-2507 build. Effect of the doc's substitution on quality: UNVERIFIED.
```

## 2. Exact model identity (VERIFIED unless noted)

| Item | Value | Source |
|---|---|---|
| Organization | **Tongyi-MAI** (Alibaba Tongyi Lab) | HF org, GitHub `Tongyi-MAI/Z-Image` |
| Model repo | `Tongyi-MAI/Z-Image-Turbo` @ **`f332072aa78be7aecdf3ee76d5c247082da564a6`** (last modified 2026-01-30). Commit history since 2025-11-26 is README/assets only, so the **weights are unchanged since release**. | HF API |
| Pipeline | `ZImagePipeline` (diffusers ≥ the release that merged PRs #12703/#12715) | model_index.json |
| DiT | `ZImageTransformer2DModel` (S3-DiT, single-stream): dim 3840, 30 layers + 2 refiner layers, 30 heads, qk_norm, in_channels 16, patch 2, cap_feat_dim 2560 | transformer/config.json |
| Params | **6.15 B** (paper). The HF transformer is stored in **fp32**: 3 shards = 24.62 GB. mflux README: "weights are large (~31GB)". | paper, HF API |
| Text encoder | Qwen3 36-layer, hidden 2560, vocab 151936 (`Qwen3ForCausalLM`). Functionally **Qwen/Qwen3-4B**; see §1a (STRONGLY SUPPORTED). Uses `hidden_states[-2]`, chat template with `enable_thinking=True`, **max_sequence_length 512**. | config, HF hashes, diffusers pipeline_z_image.py |
| Tokenizer | Qwen2Tokenizer (same tokenizer.json sha as the Qwen family, `aeb13307…`) | HF |
| VAE | `AutoencoderKL`, `_name_or_path: flux-dev`: **FLUX.1 VAE**, 16 latent channels, 8× spatial, scaling 0.3611 / shift 0.1159. 167.7 MB. | vae/config.json |
| Scheduler | `FlowMatchEulerDiscreteScheduler`, **static shift 3.0**, no dynamic shifting | scheduler_config.json |
| Distillation | Decoupled-DMD (arXiv 2511.22677) + DMDR RL (arXiv 2511.13649). "8 NFEs". | card, papers |
| Official inference | `num_inference_steps=9` ("results in 8 DiT forwards"), **`guidance_scale=0.0`**, 1024×1024 example, bf16 | card |
| Resolutions | "arbitrary resolutions up to the 1k–1.5k range" | paper (via arXiv HTML) |
| License | **Apache-2.0**: HF card `license: apache-2.0`; GitHub repo SPDX Apache-2.0 | HF API, GitHub API |
| Competing "Z-Image-Turbo" artifacts | Many derivatives: fine-tunes (e.g. RunDiffusion Juggernaut, CyberRealistic), NSFW merges, "De-Turbo", DeJPEG LoRA, and MiniMax-H3×Z-Image hybrids. **None are the official model.** Only `Tongyi-MAI/Z-Image-Turbo` and its lossless repacks (Comfy-Org bf16) are treated as Z-Image-Turbo here. | HF search |

## 3. Current release state (2026-09-24)

| Component | State |
|---|---|
| Z-Image-Turbo | Released 2025-11-26; weights unchanged since |
| Z-Image (base) | Released 2026-01-27 (`Tongyi-MAI/Z-Image` @ 04cc4ab; transformer bf16, 12.31 GB) |
| Z-Image-Edit / Omni-Base | **Unreleased** (see §1a) |
| Official GitHub | `Tongyi-MAI/Z-Image`, 12,048★, last push **2026-02-09**. The latest merged PR is an MPS Flash-Attention backend (#137, 2026-01-30). |
| mflux | **v0.20.0** (2026-09-21); Z-Image fixes in 0.19.x/0.20.0 (seed stability #715, ControlNet strength #733) |
| sd.cpp | Z-Image support since late 2025; docs at `docs/z_image.md` (commit 88411ef). **This Mac already has the Metal-verified binary.** |
| ComfyUI | Native; `Comfy-Org/z_image_turbo` @ 6fc90a3 (updated 2026-09-23) ships bf16 12.31 GB, int8_convrot 6.2 GB, nvfp4 4.51 GB, TE qwen_3_4b bf16 8.04 GB / fp8_mixed 5.63 / fp4_mixed 3.48, VAE ae 0.34 GB |

## 4. Model architecture: memory-relevant numbers (MODELED from verified configs)

- **Image tokens are identical to Qwen-2.1 at every resolution.** Z-Image uses a Flux VAE (8×) with patch 2, so it gets (W/16)·(H/16) tokens: 1024 at 512², 4096 at 1024², 9216 at 1536², 16384 at 2048². Qwen-2.1 uses a 16× VAE with patch 1, giving the same counts.
- **Per-token DiT compute ratio (Z : Qwen-2.1):**
  - Linear layers scale with parameters: 6.15 B / 7.12 B ≈ **0.86**.
  - Attention scales with layers × dim: 30·3840 / 32·4096 ≈ **0.88**.
  - So each step costs **≈ 0.87×** as much (MODELED).
- **Steps:** 9 vs 25, i.e. 0.36×. **DiT time per image ≈ 0.31× Qwen-2.1** (MODELED).
- **Text encoder:** 4 B vs 8 B (Qwen3-VL-8B). No vision tower is needed for t2i on either model.
- **VAE:** Flux 2D VAE (84 M params) vs Qwen-2.1's Wan-2.2-derived 3D VAE. The latter took 23.6 s to decode 512² on this Mac (MEASURED). The Flux VAE should be much cheaper, but that is **UNVERIFIED on Metal**.

## 5. Z-Image family map

| Class | Artifact | Relationship | Tasks | Status |
|---|---|---|---|---|
| **Base** | `Tongyi-MAI/Z-Image` | Foundation (pre-train + SFT); 50 steps, CFG | t2i, negative prompts, fine-tuning | Released |
| **Turbo** | `Tongyi-MAI/Z-Image-Turbo` | Distilled from base + RL; 8 NFEs, no CFG | t2i (+ img2img in runtimes) | Released |
| **Edit** | Z-Image-Edit | Fine-tune of base for editing (uses SigLIP 2 reference features per paper) | Instruction editing | **Unreleased** |
| **Omni-Base** | Z-Image-Omni-Base | Gen + editing raw base | both | **Unreleased** |
| ControlNet (third-party, same company) | `alibaba-pai/Z-Image-Turbo-Fun-Controlnet-Union-2.1` (and 8-step variants) | Adds canny/depth/pose/hed/mlsd control to Turbo | Structure-guided t2i | Released; mflux supports it |
| Quantized (official-runtime) | `mflux-community/z-image-turbo-mflux-q3…q8, bf16` (all created 2026-08-03). q4: TE 2.26 + DiT 3.46 + VAE 0.16 = **5.88 GB**. q8: 4.27 + 6.54 + 0.17 = 10.98 GB. | MLX-native repacks | t2i | Community (mflux maintainers' org) |
| GGUF | `leejet/Z-Image-Turbo-GGUF` @ c61c0e4 (Q2_K 2.59 … Q4_K 3.86 … Q8_0 6.58 GB); `unsloth/Z-Image-Turbo-GGUF` @ 6c80814 (Q4_K_M 5.02 GB, etc.) | DiT only; TE and VAE separate | t2i | Community |
| ComfyUI | `Comfy-Org/z_image_turbo` | Lossless/quantized repacks | t2i | Comfy-Org |
| Other MLX | `deepsweet/…-MLX-Q4/Q8`, `andrevp/…`, `mlx-community/Z-Image-Turbo-bf16` (0 downloads) | Various formats, **not mflux-verified** | — | Community |

**Compatibility does not transfer.** GGUF files are for sd.cpp / ComfyUI-GGUF. mflux packs are for mflux only. The ControlNet requires Turbo. None of these gives you Edit.

## 6. Runtime comparison

| Runtime | Z-Image-Turbo | Apple Silicon | M5 evidence | 16 GB feasibility | Editing | LoRA | ControlNet | Low-mem mechanisms | Maturity for ZIT |
|---|---|---|---|---|---|---|---|---|---|
| **mflux 0.20.0 (MLX)** | Yes, `mflux-generate-z-image-turbo` | Native MLX; `mx.compile` enabled on M3+ (disabled on M1/M2) | none | STRONGLY SUPPORTED: q4 pack 5.9 GB; `--low-ram` drops TE, sets a 1 GB MLX cache limit and tiles the VAE | img2img only | Yes | Yes (Union 2.1) | `--low-ram`, `--vae-tiling`, `--vae-tile-size`, `-q 3…8` | ~10 months |
| **sd.cpp master-908 (Metal)** | Yes | Metal (this binary verified) | **This Mac, for Qwen only** | MODELED ~6.7 GB co-resident (auto-fit keeps all three resident, as measured with Qwen) | img2img | Yes | partial | auto-fit, `--params-backend`, `--offload-to-cpu`, `--vae-tiling`, `--diffusion-fa` | ~10 months; binary already installed |
| ComfyUI + MPS | Native nodes | MPS; TE on CPU (see Qwen report) | none | REPORTED: "~24 GB RAM" for bf16 (search snippet only, UNVERIFIED); int8/fp4 TE files would lower it | img2img | Yes | Yes | smart memory, fp8 **not** usable on MPS | ~10 months |
| Diffusers + MPS | `ZImagePipeline` | MPS | none | bf16 DiT 12.3 GB + TE 8 GB, so not without quantization. `enable_model_cpu_offload` doesn't help on unified memory. | img2img pipeline | Yes | via PAI | limited | Official reference |
| Official repo inference | `inference.py`, optional `mps-flash-attn` backend (PR #137) | MPS | none | bf16, same as diffusers | — | — | — | MPS flash attention ("enables 2048² that OOMs with math backend": PR claim, REPORTED) | Inactive since Feb |
| Draw Things (app) | Yes | Native, closed source | none | REPORTED: "~4 GiB when 6-bit" (blog) | — | Yes | Yes | proprietary | Not auditable, so excluded as a primary candidate |

## 7. mflux source audit (v0.20.0, read in source)

- **Implementation.** It's a native MLX re-implementation, not a PyTorch wrapper. Files:
  - `models/z_image/variants/z_image.py`, which holds `ZImage(nn.Module)`;
  - its own TE, transformer and VAE modules;
  - a weight mapping from the HF layout.

  Apple Silicon is first-class.
- **Dependencies:** `mlx>=0.32.0,<0.33.0` (darwin), `huggingface-hub`, `hf-transfer`, `matplotlib`, and others (pyproject). Requires Python **≥3.10**; this Mac has only 3.9.6, so a venv with a newer Python is needed.
- **Quantization.** `quantization_predicate` quantizes **any module with `to_quantized`**, and that **includes the Z-Image text encoder**. This differs from mflux's Qwen-2.1 path, where the TE stays bf16. The q4 pack's TE is 2.26 GB, which confirms it.
- **Text encoder residency.**
  - By default the TE **stays resident**: `generate_image` never releases it.
  - With `--low-ram`, `MemorySaver.call_before_loop` sets `text_encoder = None` and runs `gc.collect()` plus `mx.clear_cache()` **before denoising**, for single-seed runs.
  - All three components are constructed at init (`ZImageInitializer`), so **peak at load ≈ the full pack size**. That is STRONGLY SUPPORTED from code structure; the exact peak is UNVERIFIED.
- **Cache.** `--low-ram` sets `mx.set_cache_limit(1 GB)`. After the loop it runs `gc.collect()` and `mx.clear_cache()` between seeds, which is the fix for MLX accumulating freed buffers.
- **VAE tiling.** `--low-ram` implies tiled decode (v0.14.0). `--vae-tiling` and `--vae-tile-size` are explicit (v0.19.0).
- **Scheduler.** Turbo uses `LinearScheduler`: linspace(1, 1/n), then a **resolution-dependent** exponential shift (`requires_sigma_shift=True`, Flux-style mu).
  - Official: static shift 3.0.
  - At 1024², mu=1.15 gives e^mu ≈ 3.16 ≈ 3.0.
  - At 512² the two diverge (≈2.05 vs 3.0).
  - **CONFLICTING (minor).** Test at 1024² to stay close to the official schedule.
- **Defaults.** The Python API defaults to `num_inference_steps=4`, while the CLI keys the default off the model (9). **Always pass `--steps 9`.**
- **Determinism.** v0.20.0 fixed seed instability caused by lazily built RoPE tables (#714/#715).
- **Known issue class.** mflux #748: a "purple/green static" Qwen-2.1 image traced to a **corrupt HF download** from the same `mflux-community` org, so sha256 verification is mandatory.

## 8. Apple Silicon compatibility

- **MLX / mflux:** native (VERIFIED). **sd.cpp:** Metal verified on this exact Mac (`--list-devices` → MTL0 Apple M5, `has tensor = true`).
- **ComfyUI / diffusers on MPS:** functional, but the MPS dtype caveat applies: fp8 is unsupported, which excludes the Comfy `fp8_mixed` TE on MPS. That comes from the Qwen report's evidence (ComfyUI #13200/#14770).
- **Flux VAE on MPS:** the ComfyUI MPS VAE-*encode* bug (#16433) is specific to the Wan-2.2-style `AvgDown3D` module. The Flux 2D VAE doesn't use that module (STRONGLY SUPPORTED by architecture; not tested).
- sd.cpp #1030 ("600 s/it on M3") was **a release binary without Metal** (Dec 2025, per leejet). The current release **does** include Metal (verified on this Mac). **Resolved, and it doesn't apply.**

## 9. M5-specific evidence

- **No direct M5 (base), M5 Air or 16 GB Z-Image measurement was found**, in either primary or secondary sources.
- **The closest primary measurement:** mflux maintainer PR #686, **M4 Max 128 GB, z-image-turbo q8, 512², 9 steps: 17.1 s total, ≈1.8 s/it** (VERIFIED from the PR body). The same PR says **sustained sessions throttled ~1.7× on M4 Max**.
- **Why extrapolation is weak:**
  - M4 Max has ~5× this Mac's GPU cores and far more bandwidth.
  - The M5 has GPU tensor units that ggml detects (`has tensor = true`). Whether MLX 0.32 uses them is UNVERIFIED.
  - The Air is fanless.
- **Better anchor: this Mac's own Qwen measurement** (§12).

## 10. 16 GB memory analysis

**Measured baseline (Qwen-2.1, sd.cpp, 512²):** 8.95 GB params co-resident on MTL0, peak footprint 9.7 GB, pressure "warn" for the whole run and "critical" at VAE decode, 6.5 GB swap. Confounded by ~4.9 GB of genuinely free RAM at start (apps open).

**Z-Image-Turbo (MODELED):**

| Bucket | sd.cpp (Q4_K DiT + Qwen3-4B Q4_K_M + ae) | mflux q4 `--low-ram` |
|---|---:|---:|
| DiT weights | 3.86 (file) | 3.46 |
| TE weights | 2.50 (file); stays resident under default auto-fit | 2.26 at load; **freed before denoise** |
| VAE weights | 0.34 | 0.16 |
| Params resident during denoise | **≈ 6.7** | **≈ 3.6** |
| Params at load peak | ≈ 6.7 | ≈ 5.9 |
| Activations at 1024² (4096 img + ≤512 text tokens, dim 3840) | ~0.5–1.5 | ~0.5–1.5 (fused SDPA) |
| VAE decode 1024² | Flux VAE: ~1–2 untiled | tiled under `--low-ram` |
| sd.cpp compute reserves (auto-fit reported 2048 MiB per component for Qwen) | up to ~4 | n/a (MLX cache limit 1 GB) |

- **At 1024², both routes should fit below the 12.71 GB Metal working set** (MODELED).
- With apps closed, mflux `--low-ram` should leave the most headroom.
- **1536²:** 9216 tokens gives ~2.2× the activations. The top end of the documented range, so plausible. **2048²:** outside the documented resolution range (§2), whatever the memory.
- Single-buffer cap: 9.53 GB. No single Z-Image tensor approaches it at ≤1536² (MODELED).

### 10.1 16 GB feasibility matrix

| Resolution | Precision | Runtime | Peak memory | Expected viability | Evidence |
|---|---|---|---:|---|---|
| 512² | q4 (MLX) | mflux `--low-ram` | ~6 GB (load peak ≈ pack size 5.9) | Viable | MODELED |
| 512² | Q4_K + Q4_K_M TE | sd.cpp | ~7–8 GB | Viable | MODELED (anchored to the measured Qwen auto-fit behaviour) |
| 768² | q4 / Q4_K | mflux / sd.cpp | ~6–8.5 GB | Viable | MODELED |
| 1024² | q4 | mflux `--low-ram` | ~6–7.5 GB | Viable (official target resolution) | MODELED |
| 1024² | Q4_K + Q4_K_M TE | sd.cpp | ~8–10 GB | Likely viable; pressure depends on open apps | MODELED |
| 1024² | q8 | mflux `--low-ram` | ~11 GB load peak (pack 10.98) | Tight; load peak near the working set | MODELED |
| 1536² | q4 | mflux `--low-ram` | ~7–9 GB | Plausible; top of documented range | MODELED |
| 2048² | any | any | ~9–12 GB+ | **Outside documented resolution range**; memory uncertain | VERIFIED (range) / MODELED (memory) |

No Z-Image value in this matrix is measured on this Mac.

## 11. Quantization analysis

| Format | DiT size | Runtime | Quality evidence | Speed caveat |
|---|---:|---|---|---|
| bf16 (Comfy) / fp32 (HF) | 12.31 / 24.62 GB | ComfyUI, diffusers, mflux (quantizes on load) | Reference | Doesn't fit comfortably with TE on 16 GB |
| mflux q8 | 6.54 (+TE 4.27) | mflux | Maintainer benchmark runs use q8 | — |
| mflux q4 | 3.46 (+TE 2.26) | mflux | mflux README uses 4-bit in its example; no quantitative quality number | Lower-bit **can be slower** on Apple GPUs from dequant cost (KGP: Qwen-2.1 Q4 slower than Q8 on MPS; city96 #236). **UNVERIFIED for MLX affine q4.** |
| GGUF Q4_K / Q4_0 / Q8_0 | 3.86 / 3.68 / 6.58 | sd.cpp, ComfyUI-GGUF | sd.cpp publishes a visual comparison grid bf16→q2_K (no metric) | ggml-Metal runs K-quants natively (this Mac: Qwen Q4_K ran cleanly) |
| Comfy int8_convrot / nvfp4 | 6.2 / 4.51 | ComfyUI | — | int8_convrot ran on M5 Pro for Qwen (REPORTED). nvfp4 is Blackwell-only. |

## 12. Speed evidence

| Source | HW | Runtime / quant | Res / steps | Result | Label |
|---|---|---|---|---|---|
| mflux PR #686 | M4 Max 128 GB | mflux q8 | 512², 9 | 17.1 s total, ~1.8 s/it | VERIFIED (indirect) |
| sd.cpp #1030 | M3 (RAM ?) | ComfyUI (quant ?) | 1024×512 | "19 s/it" | REPORTED |
| Search snippets (M4 Pro 14–15 s/it; M2 Max 14 s/image) | — | — | — | primary pages didn't show these numbers | UNVERIFIED |
| **This Mac, Qwen-2.1 (anchor)** | M5 8-GPU 16 GB | sd.cpp Q4_K | 512², 8 | steady ≈ **5.4 s/it** (excl. first 12.95 s), VAE 23.6 s | MEASURED (confounded by swap) |

**ESTIMATE for this Mac, Z-Image-Turbo at 1024², 9 steps.** Method:
- Take the anchor's 5.4 s/it at 512² and scale ×4.5–5.5 for 4× the tokens (linear ×4; attention grows faster), giving Qwen-2.1 at 1024² ≈ 24–30 s/it.
- Apply the 0.87 per-step ratio: Z-Image ≈ **21–26 s/it**.
- × 9 steps ≈ **3.2–3.9 min of DiT**, plus TE (~5–10 s) and VAE (UNVERIFIED).
- The same model gives Qwen-2.1 at 25 steps ≈ 10–12.5 min.
- Cross-check against M4 Max (1.8 s/it at 512² ×5 core ratio ≈ 9 s/it at 512²). That is ~2× slower than the sd.cpp-anchored figure, so the **uncertainty is at least ±2×**.

## 13. Thermal analysis

- The per-image sustained load is ~⅓ of Qwen-2.1's (MODELED), so each image ends before long-duration throttling sets in.
- That doesn't make repeated generation thermally cheap. The mflux maintainer measured **~1.7× throttling in sustained sessions on an actively cooled M4 Max** (REPORTED, PR #686). A fanless Air should be expected to throttle at least as much. Magnitude: UNVERIFIED.
- The test plan measures the 3-run and 10-run series using the same method as Qwen Phase 9.

## 14. Quality evidence

| Benchmark | Z-Image-Turbo | Z-Image | Comparator | Source class |
|---|---:|---:|---|---|
| CVTG-2K word acc. / NED | 0.8585 / 0.9281 | 0.8671 / 0.9367 | Qwen-Image **v1** 0.8288 / 0.9116; GPT Image 1 0.8569; FLUX.1 dev 0.4965 | Official paper (vendor) |
| LongText-Bench EN / ZH | 0.917 / 0.926 | 0.935 / 0.936 | Qwen-Image **v1** 0.943 / 0.946 | Official paper |
| Alibaba AI Arena Elo | 1025 (rank 4) | — | Qwen-Image v1 1008 (rank 6) | Vendor arena (same parent company) |
| Artificial Analysis Elo | 1161, #1 open-source at time of paper | — | — | Third-party, as cited in the paper |
| Human pref. vs FLUX.2 dev | 87.4% good/acceptable | | | Paper |

- **Qwen-Image-2.1 has no comparable published numbers** besides Qwen's own Qwen-Image-Bench (60.28, vendor). **No head-to-head Z-Image-Turbo vs Qwen-Image-2.1 exists.**
- Official claims are not independent benchmarks. The community impressions found (blogs, app sites) are promotional and are excluded as evidence.
- **Photorealism** (skin, hands, eyes, transparency): only showcase images from the vendor were found. No independent systematic study was found (gap). The model card itself rates Turbo "Diversity: Low", so expect weaker seed-to-seed variety than the base model.

## 15. Text rendering

- **Official evidence:** strong multi-region English (CVTG-2K ≈ GPT Image 1) and bilingual Chinese/English. Long text is slightly below Qwen-Image v1 (LongText-Bench).
- **Versus Qwen-2.1:** unknown. The 2.1 card claims "Improved typography". Resolve with the §21 A/B text-rendering prompt.

## 16. Editing analysis

- **Z-Image-Turbo:** img2img only (strength-based re-noising), not instruction editing.
- **Z-Image-Edit:** unreleased (§1a).
  - Paper architecture: SigLIP 2 reference features. Size is unknown, as are reference count, resolution and Mac support.
  - It **cannot be evaluated for 16 GB feasibility.**
- **ControlNet Union 2.1** (mflux-supported): structure-preserving regeneration (canny/depth/pose), about 20 steps because "the 2.1 checkpoint lost part of Turbo's distillation" (mflux README). It adds a checkpoint on top of Turbo.
- **Versus Qwen:** Qwen's single model family gives native editing, but on this Mac that editing is memory-limited (16–19 GB proxy) and has open MPS bugs. **Practical disadvantage of Z-Image on this hardware:** there is no editing path at all today. **Practical advantage:** a t2i stack that doesn't carry an edit-capable vision tower.

## 17. License analysis

| Model | Weights | Code | Commercial |
|---|---|---|---|
| Z-Image-Turbo | Apache-2.0 (HF card) | Apache-2.0 (GitHub) | Allowed |
| Z-Image-Edit | unreleased, so unknown | — | — |
| Qwen3-4B TE | Apache-2.0 | — | Allowed |
| Qwen-Image-2.1 (DiT/VAE) | Qwen Research License | Qwen Research License | **Non-commercial** |
| FLUX.2 klein-4B / klein-9B | Apache-2.0 / flux-non-commercial-license (gated) | — | 4B allowed / 9B not |

## 18. Safety / refusal analysis

- The model card has **zero mentions** of safety, NSFW, filters or refusal (grep). The diffusers `pipeline_z_image.py` has **no safety checker or watermark** (grep). Any filtering is outside the model, in hosted demos (UNVERIFIED) and apps.
- **Refusal in the TE:** Qwen3-4B is an instruct/chat LLM that *can* refuse in generated text. As with Qwen-2.1, **the image pipeline uses hidden states, not generated text**, so text-refusal rates don't directly measure image behaviour.
- **Heretic-style variant exists:** `Lockout/qwen3-4b-heretic-zimage` (Apache-2.0, 2025-12-16). Card: "I ran the actual TE from z-image through heretic… V2 version from new heretic has lower KLD." No numbers are given beyond screenshots.
  - Format: HF safetensors layout. mflux/GGUF compatibility is UNVERIFIED.
  - It's a separate artifact with separate provenance and was **not substituted**.
  - Also present: `BennyDaBall/Qwen3-4b-Z-Image-Turbo-AbliteratedV1`.
- Labels "uncensored", "safe" etc. are **not assigned** (no evidence).

## 19. Supply-chain analysis

| Artifact | Format | Risk notes |
|---|---|---|
| Official weights | safetensors | No pickle. The pipeline is in diffusers core, so **no `trust_remote_code`**. |
| mflux 0.20.0 | Python package (PyPI/GitHub, MIT) | Pure Python + MLX; no install scripts noted. Pin version; install in a venv only. |
| mflux-community packs | safetensors (MLX) | Same org had a **corrupt Qwen-2.1 q4 upload** (#748). Verify LFS sha256 before use. |
| GGUF (leejet) | GGUF (data) | leejet is the sd.cpp author. Pin revision c61c0e4 + sha256. |
| Qwen/Qwen3-4B-GGUF | GGUF | Official Qwen org. Pin bc64014. |
| Draw Things, ZImageApp, "one-click" Mac apps | closed binaries | Excluded (not auditable). |
| Official repo `mps-flash-attn` (PR #137) | third-party pip package with native code | Not needed for mflux/sd.cpp; avoid unless required. |

## 20. Direct comparison with the Qwen research

| Category | Qwen Image 2.1 + Heretic | Z-Image-Turbo |
|---|---|---|
| Parameters | DiT 7.12 B + TE 8.19 B (Qwen3-VL-8B) | DiT 6.15 B + TE ~4 B (Qwen3-4B) |
| Text encoder | Qwen3-VL-8B; Heretic Q4_K_M 5.03 GB (+1.16 GB mmproj for edit) | Qwen3-4B; Q4_K_M 2.50 GB / mflux q4 2.26 GB. Heretic variant exists (unassessed). |
| Runtime | sd.cpp / ComfyUI+patch / mflux (TE bf16) | sd.cpp / mflux / ComfyUI native |
| Best Mac runtime | Undetermined (bake-off paused) | Candidates: mflux `--low-ram` and sd.cpp. Undetermined. |
| 16 GB feasibility | 512² ran, but with warn/critical pressure and 6.5 GB swap (MEASURED, confounded) | MODELED lighter (§10.1); unmeasured |
| 1024² evidence | None on this Mac; proxy ~11 GB process on M5 Max | None on this Mac; no 16 GB report found |
| 1024² expected memory | ~10–13 GB if TE freed; 16+ if resident (REPORT §7) | ~6–10 GB depending on runtime (MODELED) |
| Speed | ESTIMATE ~10–12.5 min/image at 25 steps (§12 method) | ESTIMATE ~3.2–3.9 min DiT at 9 steps, ±2× |
| Text rendering | Claimed improved over v1; no numbers | CVTG-2K 0.8585, LongText EN 0.917 (vendor, vs Qwen v1) |
| Photorealism | No independent data | Vendor showcase + arena Elo only |
| Prompt adherence | No independent data | Vendor claims only |
| Editing | Native, multi-reference; on this Mac memory-limited + MPS bugs (ComfyUI) | **None official** (Edit unreleased); img2img / ControlNet only |
| Quantization | GGUF (sd.cpp, ComfyUI-GGUF+patch); fp8 unusable on MPS | GGUF, mflux q3–q8, Comfy int8/nvfp4 |
| M5 evidence | M5 Pro/Max (REPORTED) + this Mac 512² (MEASURED) | None |
| Community evidence | 4–10 days old | ~10 months; large ecosystem (LoRAs, ControlNet) |
| Known Mac bugs | ComfyUI #16433 MPS VAE encode, #16435 edit grid, GGUF node staleness | None Z-Image-specific open in mflux (as of v0.20.0); sd.cpp #1030 resolved (no-Metal binary) |
| Dependency complexity | sd.cpp: none. ComfyUI: Python + 2 custom nodes. | sd.cpp: none (binary present). mflux: Python ≥3.10 venv + mlx 0.32. |
| License | Non-commercial (DiT) | Apache-2.0 |
| Safety/refusal | Heretic TE (measured on text gen only) | Stock TE; Heretic variant exists, unassessed |

**Material differences:**
1. Editing exists only on the Qwen side.
2. Resource cost (memory, steps) favours Z-Image by a modeled ~⅓ in time and ~25% less resident weight in sd.cpp.
3. Z-Image's licence is permissive.
4. The quality relationship to 2.1 is unknown.

## 21. Recommended validation plan

This is only a plan. It needs your authorization to implement. It reuses `run.sh` / `monitor.sh` / `bench.csv` and the same prompts and seeds as the Qwen experiment.

| Phase | Action | New installs | Downloads (pinned + sha256) |
|---|---|---|---|
| 1 | Metadata/version validation (done in this report) | none | none |
| 2 | **sd.cpp smoke test.** Same Metal-verified binary `master-908-88411ef`. | **none** | `leejet/Z-Image-Turbo-GGUF@c61c0e4 z_image_turbo-Q4_K.gguf` (3.86 GB), `Qwen/Qwen3-4B-GGUF@bc64014 Qwen3-4B-Q4_K_M.gguf` (2.50 GB), `Comfy-Org/z_image_turbo@6fc90a3 split_files/vae/ae.safetensors` (0.34 GB, sha256 `afc8e282…`) |
| 3 | 512², `--steps 9 --cfg-scale 1 -s 42`, default auto-fit | — | — |
| 4 | 768² | — | — |
| 5 | 1024²: A default auto-fit, B `--offload-to-cpu`, C `--params-backend te=disk` (same pre-declared variants as Qwen) | — | — |
| 6 | 3× then 10× repeated 1024² (thermal) | — | — |
| 7 | **mflux arm** (only if you approve a Python install): venv with Python ≥3.10, `mflux==0.20.0`, `mlx 0.32.x`; `mflux-community/z-image-turbo-mflux-q4@d2d3050` (5.88 GB); `--steps 9 --low-ram`; same prompts at 1024² | Python venv | 5.88 GB |
| 8 | Quality benchmark: the 6 fixed prompts, 1024², seed 42. **Paired against Qwen-2.1** once Qwen Phase 6+ is complete. Blind side-by-side scoring of prompt adherence and text legibility, defined per prompt. | — | — |
| 9 | Editing: **not testable** (no Edit model). Optionally img2img at strength 0.6 is recorded as "img2img", *not* "editing". | — | — |

Measurement conditions (same as Qwen): **AC power, heavy apps closed**, `time -l` peak footprint, 1 Hz monitor.

## 22. Research gaps

1. Any Z-Image-Turbo measurement on base M5, M5 Air or any 16 GB Mac.
2. A head-to-head quality comparison against **Qwen-Image-2.1** (all vendor numbers compare to Qwen-Image v1).
3. Whether MLX 0.32 uses the M5 GPU tensor units, and the MLX q4-vs-q8 speed on the M5.
4. The Flux-VAE decode time on Metal/MLX on this Mac.
5. mflux's exact load-time peak (all components are constructed at init).
6. Quality effect of sd.cpp's documented TE substitution (Qwen3-4B-Instruct-2507 instead of Qwen3-4B).
7. Z-Image-Edit: release date, size, Mac support. Nothing is published.
8. Independent photorealism/hands studies.
9. Reddit: no Z-Image Mac posts were retrievable. The only search hits were app/marketing sites and the snippets marked UNVERIFIED.
10. Draw Things' Z-Image numbers were relative ratios only (no absolute timings).

## 23. Sources

- Tongyi-MAI/Z-Image-Turbo (rev f332072): https://huggingface.co/Tongyi-MAI/Z-Image-Turbo · Tongyi-MAI/Z-Image (rev 04cc4ab): https://huggingface.co/Tongyi-MAI/Z-Image
- GitHub Tongyi-MAI/Z-Image (last push 2026-02-09), PR #137 (MPS flash attn), issues #45, #89, #121, #164–#169, #172, #174 (Edit): https://github.com/Tongyi-MAI/Z-Image
- Paper arXiv 2511.22699 (https://arxiv.org/abs/2511.22699); Decoupled-DMD 2511.22677; DMDR 2511.13649
- diffusers `src/diffusers/pipelines/z_image/pipeline_z_image.py` (main)
- Qwen/Qwen3-4B, Qwen/Qwen3-4B-Instruct-2507, Qwen/Qwen3-4B-GGUF@bc64014 (HF API hashes)
- mflux v0.20.0 source: `src/mflux/models/z_image/**`, `callbacks/instances/memory_saver.py`, `models/common/schedulers/linear_scheduler.py`, `models/common/config/model_config.py`, `pyproject.toml`; releases v0.13.0 → v0.20.0; PR #686 (benchmark harness, M4 Max numbers); issues #714/#715, #748: https://github.com/mflux-community/mflux
- mflux-community/z-image-turbo-mflux-{q4,q8,bf16} (HF API)
- stable-diffusion.cpp `docs/z_image.md` @ 88411ef; issue #1030: https://github.com/leejet/stable-diffusion.cpp/issues/1030
- leejet/Z-Image-Turbo-GGUF@c61c0e4; unsloth/Z-Image-Turbo-GGUF@6c80814; Comfy-Org/z_image_turbo@6fc90a3
- black-forest-labs/FLUX.2-klein-4B / -9B (HF API license fields)
- Lockout/qwen3-4b-heretic-zimage; BennyDaBall/Qwen3-4b-Z-Image-Turbo-AbliteratedV1 (HF)
- Secondary: https://releases.drawthings.ai/p/quantify-z-image-turbo-efficiency (relative ratios only); https://miroleon.github.io/z-image-turbo-benchmark/ (M4 Pro 24 GB listed; per-run numbers not extractable); search snippets flagged UNVERIFIED in §12

## 24. Research log
Kept separately: `research/z-image-research-log.md`.
