# Qwen-Image-2.1 on a MacBook Air M5 (16 GB): research report

**Investigation date:** 2026-09-24. Qwen-Image-2.1 was released 2026-09-14 on Hugging Face, with the public announcement and community GGUFs on 2026-09-20. Everything here is **4–10 days old**. Expect repositories to change weekly.
**Machine, measured read-only this session:** Apple M5 · 10 CPU (4P+6E) · **8-core GPU** · Metal 4 · 16 GiB · macOS 27.0 (26A428) · Metal `recommendedMaxWorkingSetSize` **12.71 GB** · `maxBufferLength` **9.53 GB** · 284 GiB free disk · system Python 3.9.6 only · no cmake/uv · Homebrew present · Xcode present.
**Nothing was installed, downloaded, or modified.** The only thing written is this folder (`research/`).

Confidence labels: **VERIFIED** (read in a primary source this session) · **STRONGLY SUPPORTED** · **REPORTED** (one secondary source) · **ESTIMATE** (my arithmetic, method shown) · **UNVERIFIED** · **CONFLICTING**.

---

## 0. Stop conditions (§22): read these first

You asked me to stop before recommending installation if any of these fired. Several did, at least partly:

| # | Stop condition | Status | Evidence |
|---|---|---|---|
| S1 | Q4_K_M file not compatible with intended loader | **FIRED (partly)**. The stock `city96/ComfyUI-GGUF` cannot load it for Qwen-Image-2.1. You get a `[1, 512, 12288]` shape error because upstream only attaches the mmproj vision tower for `qwen2vl`. It works only via (a) a 1-day-old, 0-star patch node, or (b) the `molbal` fork. | pottokao README; `city96 loader.py` L482–501 (mmproj only for qwen2vl) |
| S2 | Required custom node abandoned/broken | **FIRED (partly)**. `city96/ComfyUI-GGUF` last commit was `6ea2651` on **2026-01-12**. leejet's HF card says it "appears to no longer be actively maintained". Three competing forks now exist. | GitHub API |
| S3 | Workflow requires >16 GB in practice | **FIRED for 1024² editing.** The closest proxy config measured **16–19 GB** ComfyUI process memory for a single-reference edit (M5 Max 36 GB). **Not fired** for 1024² text-to-image: the same proxy measured **~11 GB**. | KGP Talkie, 2026-09-21 |
| S4 | Dependency incompatible with Apple Silicon | **FIRED for FP8 files.** PyTorch MPS has no float8 support (pytorch#132624 is still open), so `qwen3vl_8b_fp8_heretic.safetensors` is not an option on this Mac. **Also:** ComfyUI's Qwen-2.1 VAE **encode** is broken on MPS (#16433, open). Edits are silently corrupted unless you use `--cpu-vae`. | ComfyUI #13200, #14770, #16433 |
| S5 | Materially better implementation than the proposed one | **POSSIBLY.** `stable-diffusion.cpp` has had native Qwen-Image-2.1 support since 2026-09-18. It ships a macOS arm64 binary, runs on Metal, loads a Qwen3-VL GGUF text encoder plus mmproj with **no patch** (`--llm` / `--llm_vision`), uses the resolution-dependent schedule, and has OOM fallback for the prefix cache. There is **no Mac performance data** for it. | sd.cpp `docs/qwen_image_2.1.md`, release `master-908-88411ef` |

**What this means.** I am **not** recommending a straight "install ComfyUI" plan. §10–§12 give a **gated** plan. A small bake-off (stable-diffusion.cpp vs ComfyUI) at 1024² text-to-image decides the route. Editing is treated as an experiment with a reduced reference size.

---

## A. Executive technical conclusion

| Question | Verdict | Basis |
|---|---|---|
| 1024×1024 text-to-image with Q4 DiT + Heretic Q4_K_M TE on M5/16 GB | **LIKELY**, but tight | Proxy measured ~11 GB process at 1024 (KGP). Leaves ~5 GB for macOS if other apps are closed. Needs the TE freed or paged out before denoising. **No base-M5 16 GB report exists.** |
| Heretic Q4_K_M GGUF TE works on a Mac at all | **UNCERTAIN** | Maintainer: "Not tested on a Mac." Both published Mac benchmarks used safetensors TEs (int8_convrot, w4a8). |
| 1024×1024 image editing | **NOT VIABLE as-is**. Reduced reference (≤768 grid) is **UNCERTAIN** | 16–19 GB measured for 1 reference at 1024 (proxy). There is also a separate open 1024-grid edit artifact bug (#16435) and an MPS VAE-encode bug (#16433). |
| 1536×1536 | **UNCERTAIN, leaning not viable** | Proxy: 14–18 GB process at 1536–2048 with Q4. 9216 image tokens. |
| Batch > 1 | **NOT VIABLE**. Run sequentially | Linear activation growth on an already-tight budget |
| Native 2048² (model's default) | **NOT VIABLE** | Model card default is 2048², 40 steps. Proxy memory 14–18 GB+. |
| Speed at 1024², 25 steps | **ESTIMATE ≈ 6–12 min/image** | Scaled by GPU-core count from the M5 Pro (20-core, int8, 25 steps) and M5 Max (core count UNVERIFIED, Q4, 40 steps) measurements. Method in §17 item 11. The fanless Air will throttle on sustained runs. |

**Bottom line.** 1024² text-to-image with the Heretic Q4_K_M encoder is *probably* achievable on this machine. It will be slow (minutes per image). Nobody has published proof for this exact hardware and file combination, so the first tests exist to confirm or kill it cheaply. Editing at the model's intended resolutions does not fit in 16 GB with current implementations.

---

## 1. What you are actually trying to run

- **Qwen-Image-2.1** (`Qwen/Qwen-Image-2.1`, rev `790c926`, last modified 2026-09-21). One model covers text-to-image, editing (up to 10 refs), and RGBA transparency.
  - **DiT:** `QwenImage21Transformer2DModel`, 32 single-stream layers, 32 heads × 128, context_in_dim 4096, in_channels 64, patch_size 1, block-causal attention. The card says "7B"; the GGUF metadata counts **7,115,124,736** params. **VERIFIED.**
  - **Text encoder:** `Qwen3VLForConditionalGeneration`, i.e. **Qwen3-VL-8B-Instruct** used unmodified. 36 layers, hidden 4096, plus a 27-layer vision tower (hidden 1152, deepstack at 8/16/24). **VERIFIED** from `text_encoder/config.json`.
  - **VAE:** `AutoencoderKLQwenImage21`, z_dim 64, 16× spatial compression, RGBA (in/out channels 4). ComfyUI implements it with the **Wan 2.2 VAE module** (PR #16400). **VERIFIED.**
  - **Scheduler:** `FlowMatchEulerDiscreteScheduler`, dynamic exponential shift (base 0.5 @ 256 tokens → max 0.9 @ 8192), shift_terminal 0.02. **VERIFIED.**
  - **License: Qwen Research License, non-commercial.** This applies to the DiT and VAE and every DiT GGUF redistribution. **VERIFIED.**
- **Your text encoder:** `pottokao/Qwen-Image-2.1-Text-Encoder-Heretic-GGUF`, file `qwen3vl_8b_heretic-Q4_K_M.gguf`. It is a refusal-ablated Qwen3-VL-8B-Instruct, Apache-2.0.

Latent tokens per image = (W/16)·(H/16). That is **4096 tokens at 1024²**, 9216 at 1536², and 16384 at 2048².

## 2. Current ecosystem and release state (as of 2026-09-24)

| Item | State | Source / revision |
|---|---|---|
| macOS on this Mac | 27.0 (26A428) | `sw_vers` |
| ComfyUI | **v0.37.0** (2026-09-21). Qwen-2.1 support merged in PR #16400 (`6bfaacc`, 2026-09-19). v0.36.0 is the minimum per pottokao; 0.34.2 lacks `TextEncodeQwenImage21`. `requires-python >=3.10`. | GitHub releases, pyproject |
| city96/ComfyUI-GGUF | `6ea2651` (2026-01-12). **Stale for 8 months.** Has no qwen3vl mmproj handling. | GitHub API |
| leejet/ComfyUI-GGUF (fork) | `edd981b` (2026-09-21). Adds **DiT** detection for `qwen_image21` only. TE mmproj is still qwen2vl-only (loader.py L503). | GitHub API / diff |
| molbal/ComfyUI-GGUF (fork) | `48de657` (2026-09-20). Handles qwen3vl + mmproj natively. Heavily diverged (custom INT4/INT8 formats, LoRA paths). | GitHub API / loader.py |
| pottokao-dotcom/ComfyUI-GGUF-Qwen3VL-TE (patch) | `81b1cee` (2026-09-23). Created 2026-09-23, 0 stars, 1 file (`__init__.py`, 7.6 KB). Monkey-patches city96 at import time. | GitHub API, source read in full (§9) |
| stable-diffusion.cpp | `master-908-88411ef` (2026-09-23). Qwen-2.1 support since PR #1994 (2026-09-18), prefix cache since #2035. Ships `sd-master-88411ef-bin-Darwin-macOS-26.6.2-arm64.zip`. | GitHub releases |
| mflux (MLX) | **v0.20.0** (2026-09-21) adds `mflux-generate-qwen-2.1`: txt2img, img2img, `-q 8/-q 4`. **TE stays bf16 (~16 GB)**, so it can't use your GGUF. Reference editing is an open PR (#741, #749). | GitHub releases |
| mlx-serve | Qwen-2.1 is **unreleased** (branch `feat/qwen-image-2.1`, PR #477) | ddalcu HF card |
| Diffusers | `QwenImage21Pipeline` requires diffusers from **git main** plus `transformers>=5.17`. The official card targets `cuda`. | Qwen HF card |
| llama.cpp | Supports `qwen3vl` GGUF (Qwen publishes official `Qwen3VL-8B-Instruct-*.gguf` + mmproj). **It cannot run the diffusion model.** It is only useful for the optional PE-T2I prompt rewriter. | HF API |
| PyTorch MPS fp8 | Unsupported (pytorch#132624 open per ComfyUI #14770, 2026-07) | ComfyUI #14770 |
| M5-specific issues | ComfyUI #13200: fp8 on M5 Pro/Max/**Air** ("Macbook M5 air – same"). No M5-specific Qwen-2.1 bug found. | GitHub |

## 3. Exact model components

### 3.1 The text encoder you specified (VERIFIED via HF API, repo sha `e21acf0`, modified 2026-09-24)

| Property | Value |
|---|---|
| File | `qwen3vl_8b_heretic-Q4_K_M.gguf`, **5,027,785,376 B** (5.03 GB), sha256 `1338274ac7a6344f262a16c7a52d1bd7fe789307d252733b23ea421126e5d343` |
| Required companion | `mmproj-qwen3vl_8b_heretic-f16.gguf`, **1,159,030,464 B** (1.16 GB), sha256 `4649839491c8df1ebc9bed2de158ad2a45b53ed1d3b311d92a69056b6764f101`. Vision tower, f16. **Required** for the patch node and for editing. Do not rename either file (matched by name). |
| GGUF `general.architecture` | `qwen3vl` (read from GGUF metadata via HF API, not inferred from the filename) |
| Params (GGUF metadata) | 8,190,735,360. **Identical** to official `Qwen/Qwen3-VL-8B-Instruct-GGUF`. |
| Context length (metadata) | 262,144 (the model's max). Qwen-Image-2.1 uses far less: ComfyUI's error trace shows 512-token sequences. |
| Quant | Q4_K_M LM weights (llama.cpp k-quant mix); vision tower separate f16 |
| Size vs official | Official `Qwen3VL-8B-Instruct-Q4_K_M.gguf` = 5,027,784,800 B. The 576 B difference is metadata. **Structurally interchangeable (STRONGLY SUPPORTED).** |
| Maintainer recommendation | Q4_K_M is the "Smallest (GGUF)" option. All showcase images used Q4_K_M everywhere. For "Mac / non-CUDA, no extra nodes" the maintainer recommends the **bf16 17.5 GB** file instead, which is impossible on 16 GB. |
| Runtimes | ComfyUI via `CLIPLoaderGGUF` + patch (maintainer). llama.cpp (as a chat LLM). stable-diffusion.cpp `--llm` / `--llm_vision` (**inferred** from metadata identity with the file sd.cpp documents; **UNVERIFIED by test**). MLX: **no**. mflux loads HF safetensors, and conversion would lose the Q4 point. |
| Conversion needed? | No, for ComfyUI or sd.cpp. |
| Tested on Mac? | **No.** "Verified 2026-09-23 on ComfyUI 0.36.0 + ComfyUI-GGUF `6ea2651` (NVIDIA GPU)… Not tested on a Mac." |

### 3.2 Full pipeline: components

**Text-to-image**

| Component | Exact file (candidate) | Size | Format | Required? | Runtime | Memory (weights) | Source |
|---|---|---:|---|---|---|---:|---|
| Tokenizer / processor | embedded in GGUF (ComfyUI-GGUF rebuilds it from metadata); HF `processor/` for diffusers | ~16 MB | json | yes | CPU | negligible | Qwen HF |
| Text encoder LM | `qwen3vl_8b_heretic-Q4_K_M.gguf` | 5.03 GB | GGUF Q4_K_M | yes | ComfyUI: **CPU** on Mac (see §7) / sd.cpp: Metal or CPU | ~5.0 GB + dequant scratch | pottokao |
| Vision tower | `mmproj-qwen3vl_8b_heretic-f16.gguf` | 1.16 GB | GGUF f16 | patch node requires it even for t2i. molbal fork injects placeholders if absent. sd.cpp only needs it for editing. | same as TE | 1.16 GB | pottokao |
| DiT | `pottokao: qwen_image_2.1-Q4_K_M.gguf` (4.34 GB, sha in HF) **or** `leejet: qwen_image_2.1-Q4_0.gguf` / `Q4_K.gguf` (4.20 GB) | 4.2–4.3 GB | GGUF | yes | MPS / Metal | ~4.3 GB | HF API |
| VAE | `Comfy-Org/Qwen-Image-2.1: vae/qwen_image_2.1_vae_bf16.safetensors` | 675,509,688 B | safetensors bf16 | yes | MPS decode OK. **Encode must be CPU on MPS** (#16433) | 0.68 GB + large activations | Comfy-Org, sha256 `bb21f747…b7c9` (matches the hash quoted in #16433) |
| Scheduler / sampler | built-in: euler / simple, 25 steps, cfg 1 (ComfyUI template). sd.cpp: euler, auto resolution-dependent schedule. | — | — | yes | — | — | Comfy docs, sd.cpp docs |
| Prompt rewriter (PE-T2I) | optional; `pottokao/…PE-T2I-Heretic-GGUF` or Comfy-Org int8 9.47 GB | ~5 GB (Q4) | GGUF | **no** | llama.cpp | would compete for RAM, so run it separately | pottokao / Comfy-Org |

**Image-to-image / editing:** all of the above, plus:
- The mmproj vision tower is **mandatory** (reference image goes through it).
- **VAE encode** of each reference goes through `TextEncodeQwenImage21` with a `vae` input. It is spliced as latents into the vision positions.
- The **prefix KV cache** (`QwenImage21Cache` node / sd.cpp built-in) holds text + reference K/V. ESTIMATE: 32 layers × 2 × 4096 dim × 2 B ≈ **0.5 MB per prefix token in bf16**, so a 1024² reference (~4096 tokens) ≈ **2.2 GB bf16 / 4.4 GB fp32 per condition**. sd.cpp documents "about 4 GiB per condition" for a 4096-token prefix in FP32, which matches. cfg > 1 doubles it (positive + negative).

**Image understanding / multimodal conditioning:** in Qwen-Image-2.1 this is not a separate workflow. The Qwen3-VL vision tower inside the text encoder *is* the multimodal conditioning path. ComfyUI drops vision hidden states when a VAE is attached and splices VAE latents instead (PR #16400).

### 3.3 Heretic modification: validation (claims separated)

| Question | Maintainer claim | Independent evidence | Status / your test |
|---|---|---|---|
| What changed | Directional ablation (p-e-w/heretic @`3521f86`) on `o_proj` + `down_proj` of Qwen3-VL-8B-Instruct. Bf16, same shapes and param count. MERGE export. | GGUF metadata param count identical to official (VERIFIED). No weight diff examined. | Structural: VERIFIED. Content: maintainer claim. |
| Only TE modified? | "Only the text encoder is modified. The DiT and VAE… are untouched." | DiT GGUFs are separately converted from official bf16 | STRONGLY SUPPORTED |
| Safety / refusal | 100/100 → 5/100 refusals (mlabonne/harmful_behaviors), KL 0.0220 (harmless_alpaca). Re-check 0/20 and 4/4 benign. | None | Maintainer claim. **These measure text generation.** Qwen-Image uses the TE's **hidden states**, never generated text, so refusal rate is not directly an image-pipeline metric. |
| Image quality / adherence | "match the bf16 encoder's output for the same seed up to Q4 quantization noise" | None | Compares against **their own Heretic bf16**, not the stock encoder. Change vs stock is **UNVERIFIED** → use the A/B in §14. |
| Compatibility | "Drop-in replacement" | Metadata identical to official GGUF | STRONGLY SUPPORTED |
| Reversible | n/a | Stock weights exist (official GGUF / Comfy-Org). Swap the file to revert. | VERIFIED |
| Evaluation data | Refusal/KL table, Pareto front, NVFP4 round-trip error | None independent | — |

**CONFLICTING:** pottokao labels W4A8 and int8-convrot as "CUDA". Both formats (stock versions) ran on MPS in the M5 Pro/Max reports.
**CONFLICTING:** license. ddalcu's MLX-Serve card declares Apache-2.0 for a quantized Qwen-Image-2.1, but the official model is under the Qwen Research License. Treat the official license as binding.
**CONFLICTING:** steps and cfg. The model card uses 40 steps at 2048². ComfyUI/pottokao use 25 steps, cfg 1. sd.cpp examples use `--cfg-scale 6.0`. cfg > 1 doubles per-step compute and adds a second prefix-cache condition.

## 4. M5 16 GB feasibility

**What is measured (indirect: bigger M5 variants, same software generation):**

| Source (date) | HW | Stack | Config | Result |
|---|---|---|---|---|
| dev.to / K. Mullin (2026-09-22) — REPORTED | M5 Pro 20-GPU, 48 GB, macOS 27.0 | ComfyUI 0.37.0, PyTorch 2.12.1, MPS | DiT int8_convrot + TE int8_convrot, 25 steps euler/simple cfg 1 | 1024²: warm **143.5 s**. 1536²: warm **343.5 s**. 1024 edit: **172.5 s**. No peak-memory figure. |
| KGP Talkie (2026-09-21) — REPORTED | M5 Max, 36 GB, macOS 27.0 | ComfyUI 0.37.0 + ComfyUI-GGUF, PyTorch 2.14 | **"Q4": DiT GGUF 4.2 GB + TE w4a8 6.3 GB** (≈ your 5.03 + 1.16 = 6.19 GB), 40 steps euler cfg 1 | 1024²: **218 s**, **~11 GB** process. 1536–2048: **14–18 GB**. 1-ref edit: **16–19 GB**. 2-ref: **22 GB**. **Q4 was 28%–2× *slower* than Q8.** |
| Ivan Fioravanti on X — REPORTED (search snippet only) | M5 Max | custom mflux, bf16 | 1600×672 | ~1.78 s/step, **peak 31 GB** |
| ddalcu mlx-serve card — REPORTED | M1 Pro 32 GB | mlx-serve branch, 4-bit, TE freed before denoise | 1024², 3 steps | peak **9.55 GB** |
| JoyFusionAI card — REPORTED | M1 Max | mflux `--low-ram`, 8-bit DiT, bf16 TE | 768² | peak **~10 GB** (33–36 GB without `--low-ram`), 6.7 s/step |

**No M5 (base) or 16 GB Qwen-Image-2.1 report was found.** Search on Reddit returned nothing relevant (see §17).

**Hardware facts that matter here:**
- **Unified memory means "CPU offload" does not reduce the footprint.** CPU and GPU share the same 16 GB. `enable_model_cpu_offload`, ComfyUI running the TE "on CPU", and sd.cpp `--offload-to-cpu` only move *where compute happens*. They do not create memory. The things that actually cut peak memory are:
  - quantization;
  - **sequential residency** (free the TE before the DiT runs);
  - mmap-backed weights that the OS can evict;
  - tiling (VAE) and attention chunking.
- **Metal limits (measured):** a 12.71 GB recommended GPU working set, and a **9.53 GB max single buffer**. Large VAE/attention tensors at 1536+ can hit the buffer cap. There is a precedent with the same VAE module: ComfyUI #11628 "MPSGraph does not support tensor dims larger than INT_MAX when encoding with WanVAE".
- **ComfyUI places text encoders on CPU on Apple Silicon.** `text_encoder_device()` returns CPU for `VRAMState.SHARED` unless `--gpu-only` or "aimdo" dynamic VRAM is active (v0.37.0 `model_management.py` L1219). PR #14770 to change this is still **open**. Consequence: the Q4_K_M TE runs on the **CPU cores** (slower encode, same RAM pool). Whether dynamic VRAM (aimdo) is active on MPS in 0.37 is **UNVERIFIED**, so check the startup log.
- **K-quants on MPS:** city96 #177 (open since 2024-12) reports "Q*_K models don't work on macbooks (green noise)" for Flux. City96 notes that CLIP GGUFs work because ComfyUI runs them on CPU. KGP ran a Q4 DiT GGUF on M5 Max successfully in 2026, and pottokao's DiT Q4_K_M is mostly Q4_K/Q6_K tensors. **Whether #177 still reproduces on current PyTorch + M5 is UNVERIFIED.** Test 4 is designed to catch it, with fallback to leejet `Q4_0` / `Q8_0`.
- **M5 "neural accelerators" in the GPU:** whether PyTorch MPS, MLX, or ggml-Metal use them for this workload is **UNVERIFIED** this session. Don't count on it.
- **Fanless Air:** sustained 6–12 min GPU runs will likely throttle (**ESTIMATE**; no measurement). Monitor it (§14).

## 5. GTX 1650 Ti 4 GB comparison (no scores, technical differences)

| Aspect | M5 Air 16 GB | Acer Nitro 5 / GTX 1650 Ti |
|---|---|---|
| Memory model | 16 GB unified, shared by OS + CPU + GPU. No "offload" escape. | 4 GB dedicated VRAM + separate system RAM (**amount UNVERIFIED**; tell me). Offload to system RAM *does* free VRAM, at PCIe cost. |
| Q4 DiT (4.2–4.3 GB) | Fits in RAM; runs fully on GPU | **Does not fit in 4 GB VRAM** with activations. Requires per-step block streaming over PCIe (ComfyUI lowvram / sd.cpp `--offload-to-cpu`). Expect large slowdowns. **ESTIMATE**, no evidence gathered. |
| TE Q4_K_M (5 GB) | CPU in ComfyUI, same pool | Runs on CPU in system RAM; VRAM unaffected |
| Numerics | bf16 supported on MPS | Turing (sm_75): **no native bf16 tensor cores**, so bf16 runs emulated or as fp16. fp16 overflow risk with this model **UNVERIFIED**. |
| Low-precision formats | fp8 unsupported; int8_convrot/w4a8 **ran** on M5 Pro/Max (CONFLICTING with pottokao's "CUDA" label) | fp8 compute needs Ada+. int8_convrot/w4a8 kernel support on sm_75 **UNVERIFIED**. NVFP4 is Blackwell-only. |
| Toolchain | Metal/MPS: fewer kernels, more MPS-specific bugs (#16433) | CUDA: the reference platform for every Qwen-2.1 implementation (vLLM-Omni, SGLang, LightX2V, ComfyUI testing) |
| Where it helps | Primary machine | A **correctness oracle**: run the same seed/prompt on CUDA to tell "MPS bug" apart from "model/quant behaviour", e.g. #16433 vs #16435. Speed is probably worse than the M5 unless system RAM is large. **UNVERIFIED.** |

## 6. Runtime comparison (factual, no scores)

| Runtime | Qwen-2.1 support | Apple Silicon | M5 evidence | 16 GB feasibility | Your GGUF TE | Editing | Ease | Performance evidence |
|---|---|---|---|---|---|---|---|---|
| **ComfyUI 0.37 + GGUF loader** | Native (PR #16400) + GGUF DiT via loader | MPS; TE on CPU; VAE encode bug → `--cpu-vae` | M5 Pro/Max measured (safetensors & GGUF DiT) | T2I 1024 likely (~11 GB proxy); edit 1024 no | Only via patch node or molbal fork | Yes, but #16433 (MPS encode) + #16435 (1024 grid) + 16–19 GB | Medium: Python env + 2 custom nodes | Measured on M5 Pro/Max |
| **ComfyUI native safetensors** | Native | int8_convrot/w4a8 ran on M5 Pro/Max; fp8 fails | Yes (the M5 Pro run used exactly this) | int8 DiT (7.26 GB) is ≈3 GB larger than Q4. Like the GGUF route, it depends on the TE and DiT not being co-resident. **Uncertain.** | No (not GGUF). Heretic W4A8 exists (6.31 GB) | Same bugs | Easiest: zero custom nodes | Measured (M5 Pro, 25 steps) |
| **stable-diffusion.cpp** | Native (#1994), prefix cache, RGBA | Metal backend; prebuilt macOS arm64 zip | **None** for Qwen-2.1 on Mac besides an M4 Max RGBA bug report (#2024) | Unknown; has auto-fit memory planning & OOM fallback | **Yes, natively** (`--llm` + `--llm_vision`), metadata-identical to documented file | Yes (`-r`), multi-ref | Easy: one binary, no Python | None on Mac |
| **mflux 0.20 (MLX)** | txt2img, img2img; ref-editing PRs open | MLX native | M5 Max bf16 (Fioravanti) | Only with `--low-ram` (~10 GB peak @768 on M1 Max, 8-bit DiT); TE bf16 ~16 GB loaded then freed, so on 16 GB that means swap | **No**: needs HF safetensors; TE forced bf16 | Not reference editing yet | Easy (pip) | Measured on M1/M5 Max |
| **mlx-serve** | Unreleased branch | MLX | None | Designed for 16 GB ("10.7 GB 4-bit pack") | No; drops vision tower | img2img only | Requires Zig build of an unmerged branch | M1 Pro only |
| **Diffusers** | `QwenImage21Pipeline` on git main | MPS possible; card targets CUDA | None | bf16 is ~33 GB; `enable_model_cpu_offload` does **not** help on unified memory | No (GGUF TE not in example) | Yes | Medium | None on Mac |
| **llama.cpp** | **No diffusion.** TE / PE rewriter only | Metal | n/a | n/a | Yes, as chat LLM | n/a | Easy | n/a |

**Trade-offs in short.**
- ComfyUI has the only real Mac measurements and the richest workflow. It is also where your specific GGUF file needs unproven glue, and where two open edit bugs live.
- stable-diffusion.cpp is the cleanest match for "GGUF everything on 16 GB" (no Python, no patch, native mmproj), but it is unmeasured on Mac.
- mflux is the most Mac-native, but it cannot use the file you care about.

## 7. Memory analysis: where the 16 GB goes

**Weights on disk (VERIFIED sizes):** DiT Q4_K_M 4.34 + TE Q4_K_M 5.03 + mmproj 1.16 + VAE 0.68 = **11.21 GB**.
**GPU working-set limit:** 12.71 GB (measured). **Current idle footprint of this session's apps:** ~10 GB summed RSS (over-counts shared pages), with WebKit/Safari/Office the largest. Close them for runs.

**Scenario A: 1024² t2i, cfg 1, 25 steps (ESTIMATE, anchored to the KGP ~11 GB proxy)**

| Bucket | GB | Notes |
|---|---:|---|
| macOS + WindowServer + minimal apps | 3.5–5 | kernel/wired measured 2.3 GB now; varies by open apps |
| Python + PyTorch + ComfyUI runtime | 0.8–1.5 | not applicable to sd.cpp (~0.1) |
| TE Q4_K_M + mmproj (during encode) | 6.2 (+ ≤1 dequant scratch) | ComfyUI: CPU-resident. **Must be evicted before DiT load or the budget fails.** |
| DiT Q4 weights | 4.3 | GGUF dequantizes per layer on the fly |
| DiT activations 1024² (~4.4k tokens, hidden 4096, MLP 12288) | 0.5–1.5 | attention scores 32×4.4k² ×2 B ≈ 1.2 GB if not chunked |
| Prefix KV cache (text only, ~300 tokens) | ~0.15 | small for t2i |
| VAE decode 1024² | 1–3 | tiled decode lowers it |
| **Peak if TE freed before DiT** | **~10–13** | fits, with memory compression |
| **Peak if TE stays resident** | **~16–19** | swap / possible OOM |

**Evidence that ComfyUI 0.37 on MPS does not keep both models fully resident (REPORTED, indirect).** KGP's **Q8** configuration had ≈17.1 GB of weights (DiT 7.7 GB + int8 TE 9.4 GB), yet the process measured ≈**14 GB** at 1024–1344 px. Either the TE was released or paged before sampling, or the reported metric excludes some memory (e.g. Metal buffers or mmapped pages). This supports sequential residency but does not prove it, so Test 7 measures it directly.

**Verdict: should work only with sequential residency.** Likely failure modes:
- sustained swap and compression, visible as yellow/red memory pressure and 2–10× slowdowns;
- `MPS backend out of memory`.

Required optimizations:
- close other apps;
- ComfyUI: rely on `--cache-ram` pressure eviction (the default in 0.37) and test `--disable-smart-memory` / `--cache-none` (flags **VERIFIED** to exist in v0.37.0 `cli_args.py`);
- let VAE tiling engage.

**Scenario B: 1024² editing, one reference.**
- Adds the mmproj pass, a CPU VAE encode, ~4.1k extra tokens (~8.5k sequence), and a prefix KV of ~2.2 GB bf16 per condition.
- Proxy measured **16–19 GB**.
- **Verdict: not viable as-is.**
- Mitigations to *test*:
  - reference grid 768 (2304 tokens), avoiding exactly 1024 per #16435;
  - cfg 1 (one condition);
  - `QwenImage21Cache` set to off/quantized (the PR says the cache "falls back to RAM, then recompute"; exact options **UNVERIFIED**);
  - `--cpu-vae` (mandatory for correctness on MPS).

**Scenario C: 1536².** 9216 tokens, so ~2.2× the activations of 1024. Attention scores are ~5.4 GB if materialized, which is near the 9.53 GB single-buffer cap once VAE tensors are included. Proxy measured 14–18 GB. **Uncertain, leaning not viable.** Test only after A passes, with tiled VAE.

**Scenario D: batch > 1.** Activations scale linearly on an already-tight budget. **Not viable.** Use sequential queue runs instead.

## 8. Known community findings

Reddit search returned nothing specific to Qwen-Image-2.1 on Mac, M5, 16 GB, or pottokao (search results were empty or off-topic, and Reddit's API blocked scripted access). The recurring issues below come from GitHub, HF, and blogs:

| Finding | Where | Date | HW / SW | Corroborated? |
|---|---|---|---|---|
| MPS VAE **encode** corrupts edits (6.6 dB PSNR). `--cpu-vae` fixes it; `--fp32-vae` does not. Root cause: MPS `F.pad` front-padding in `AvgDown3D`. | ComfyUI #16433 (open) | 2026-09-20 | 128 GB Mac, PyTorch 2.14; reproduced on M3 Max (macOS 26.5, PyTorch 2.13) and M4 Mac mini | **Yes**, 3 independent reports |
| Edit noise at exactly a 1024 reference grid (also on CPU and CUDA at other grids) | ComfyUI #16435 (open) | 2026-09-20 | Mac + RTX 5070 Ti | Partly (CUDA reproduces at a different grid) |
| ComfyUI uses fixed mu = 0.69 (the 1024 value) at all resolutions; "on purpose" per comfyanonymous (grid artifacts) | ComfyUI #16447 | 2026-09-21 | — | Maintainer confirmed it is intentional; disputed by users |
| fp8 unsupported on M5 Pro/Max/**Air** | ComfyUI #13200 | 2026-03→07 | M5 family | Yes, many reports |
| Q4 DiT slower than Q8 on MPS | KGP Talkie; city96 #236 (Flux) | 2026-09-21 / 2025-04 | M5 Max; older Mac | **Yes**, two sources |
| Q*_K GGUF green noise on Mac | city96 #177 (open) | 2024-12 → 2025-02 | M-series, Flux | Old; status on 2026 PyTorch **UNVERIFIED** |
| Memory creep over repeated runs with UnetLoaderGGUF on macOS | city96 #320 (open) | 2025-08 | M2 Mac Studio, Wan 2.2 | Not re-tested for Qwen-2.1 |
| int8_convrot slower than Q8 GGUF (0.37.0) | ComfyUI #16470 | 2026-09-22 | not Mac-specific | single report |
| mflux Qwen-2.1 purple/green static turned out to be a **corrupt download** | mflux #748 | 2026-09-22 | 0.20.0 | Resolved by reporter. **Lesson: verify sha256.** |
| sd.cpp RGBA background decodes opaque on **Metal** | sd.cpp #2024 (open) | 2026-09-22 | M4 Max 36 GB, Q4_K DiT + Qwen3VL Q4_K_M | Single report; only affects transparency |
| Several tutorials say to use the **molbal** fork; leejet says use the **leejet** fork; pottokao says city96 + patch | kombitz / leejet HF / pottokao HF | 2026-09-20→23 | — | **CONFLICTING** recommendations. Fragmentation is itself a risk. |

## 9. Security and supply-chain analysis

| Artifact | Format / exec risk | Provenance | Notes |
|---|---|---|---|
| Heretic TE GGUF + mmproj | GGUF is a data format; no code execution by design. Parser CVEs have historically existed in llama.cpp/ggml. | Community (pottokao), created 2026-09-20; Apache-2.0; methodology + pinned heretic commit `3521f86` documented | Pin repo sha `e21acf0` and verify sha256 (in §3.1) |
| DiT GGUF (pottokao) | GGUF | Community; conversion patches published in `tools/` | Pin sha `14fa5d2`. Alternative leejet (sd.cpp author) sha `cc11433`. |
| VAE safetensors | safetensors: no pickle | Comfy-Org official repack | sha256 `bb21f747…b7c9` |
| ComfyUI core | Python code. Custom nodes run arbitrary Python with your user privileges. | Official, pin tag `v0.37.0` | Avoid ComfyUI-Manager auto-installs |
| city96/ComfyUI-GGUF | Python; deps `gguf`, `sentencepiece`, `protobuf` (per its requirements.txt, **UNVERIFIED** this session) | 4k★, stale | pin `6ea2651` |
| pottokao patch node | **Read in full (7.6 KB).** Only monkey-patches `CLIPLoaderGGUF.load_patcher` and `convert.detect_arch`, reads GGUF metadata, renames tensors. **No network, no subprocess, no eval/exec, no file writes.** | 1 day old, 0★, single author, Apache-2.0 | Pin `81b1cee`. Re-audit on every update. |
| molbal fork | Large diff (custom INT4/INT8 paths, tests) | 75★, active | Not audited. Bigger surface than the 7.6 KB patch. |
| sd.cpp prebuilt zip | Native binary. Signing/notarization status **UNVERIFIED**; Test 1 will show whether Gatekeeper blocks it. | Official GitHub release by CI | Prefer a source build (needs cmake) if you want provenance you control. Otherwise verify the release's digest. |
| `trust_remote_code` | **Not required** on any route here. Diffusers uses in-library classes. | — | Refuse any workflow that asks for it |
| pickle `.ckpt/.pt/.bin` | **None needed** | — | ComfyUI logs "Checkpoint files will always be loaded safely" |

**License reminder:** DiT + VAE are under the **Qwen Research License (non-commercial)**. The Heretic TE is Apache-2.0.

## 10. Recommended architecture, based on evidence

**Gated, two candidates, one decision point.** Nothing is chosen until Tests 1–7 run.

- **Candidate 1: stable-diffusion.cpp (Metal).**
  - Files: DiT `leejet/qwen_image_2.1-Q4_K.gguf` (4.20 GB) + **Heretic Q4_K_M TE** (`--llm`) + mmproj (`--llm_vision`, edit only) + official VAE.
  - K-quants are fine here. City96 #177 concerns ComfyUI-GGUF dequantizing in PyTorch on MPS, whereas ggml-Metal runs K-quants natively. The Heretic TE is itself a K-quant anyway.
  - Why first: fewest moving parts (one binary, no Python, no patch), native GGUF TE, memory planner with OOM fallback, dynamic schedule.
  - Risk: zero Mac perf data. sd.cpp flag behaviour (`--offload-to-cpu`, `--params-backend`, auto-fit on Metal) must be read from `sd-cli -h` in Test 1.
  - On unified memory, `--offload-to-cpu` may *raise* peak memory (a host copy plus Metal buffers). This is **UNVERIFIED**, so Test 7 runs sd.cpp with and without it.
- **Candidate 2: ComfyUI v0.37.0 + city96 `6ea2651` + pottokao patch `81b1cee`.**
  - Files: pottokao DiT Q4_K_M + Heretic TE Q4_K_M + mmproj + official VAE.
  - Launch with `--cpu-vae` always.
  - Why: the only route with published M5 measurements, plus the full node graph for editing and inpainting.
  - Fallbacks if the patch fails: molbal fork `48de657` (replace city96; don't stack both), or Heretic **W4A8** safetensors (6.31 GB) via stock `CLIPLoader` (ran on M5 Max as the stock w4a8).
  - DiT fallback if Test 4 shows K-quant noise on MPS: leejet `Q4_0`. leejet files have no `general.architecture` metadata, so on city96 they load **only** through the patch's DiT detection.
  - Version trade-off: the patch was verified on ComfyUI **0.36.0**; both Mac measurements used **0.37.0**. Pinning 0.37.0 + patch is a combination **nobody has tested**. If Test 3 fails, 0.36.0 is the first thing to try.

**Choose by:** Test 7 success at 1024² t2i → peak memory pressure (stays out of red) → time/image → quality parity on the benchmark set (§14). If both pass, take the lower-peak-memory one for t2i. Keep ComfyUI only if you need its editing graph.

## 11. Preflight checklist

Run `zsh research/preflight.sh | tee research/preflight-<date>.log`. It is read-only, and this session's run is saved in `preflight-20260924.log`.

| Check | Current result | Pass criterion |
|---|---|---|
| macOS / arch | 27.0 / arm64 | arm64, macOS ≥ 26 |
| RAM | 16 GiB | — |
| GPU / Metal | M5, 8-core GPU, Metal 4 | Metal 4 present |
| Metal working set / max buffer | 12.71 / 9.53 GB | note for budgeting |
| Memory free % (idle) | 63% | ≥ 60% before a run (close apps) |
| Swap | 0 MB used | near 0 before a run |
| Disk | 284 GiB free | ≥ 40 GB |
| Python | **3.9.6 system only: FAIL** for ComfyUI (needs ≥3.10; README says 3.13 is "very well supported") | isolated 3.12/3.13 env |
| cmake | **missing** | only needed to build sd.cpp from source |
| uv | missing | optional (recommended env manager) |
| Xcode / clang | present, Apple clang 21 | — |
| torch / MPS | not installed (expected) | after install: `torch.backends.mps.is_available() == True` |
| Thermal | no warnings recorded | recheck during runs |
| Power | **on battery (77%)** | benchmarks on AC only |

## 12. Installation plan (commands deferred; architecture only)

Per your instructions, this section fixes the layout and dependency strategy. Exact install commands come after you approve the gated plan.

```
~/Dev/photo-gen/
├── research/            # this report, preflight logs, benchmark results (CSV/JSON)
├── models/              # single shared model store, read-only after download + sha256 check
│   ├── diffusion_models/  qwen_image_2.1-Q4_K_M.gguf (pottokao) | qwen_image_2.1-Q4_0.gguf (leejet)
│   ├── text_encoders/     qwen3vl_8b_heretic-Q4_K_M.gguf + mmproj-qwen3vl_8b_heretic-f16.gguf
│   └── vae/               qwen_image_2.1_vae_bf16.safetensors
├── sdcpp/               # pinned sd.cpp release (or source build at a pinned commit)
├── comfyui/             # git clone at tag v0.37.0 (only if Candidate 2 proceeds)
│   ├── .venv/           # isolated venv (uv or python.org/Homebrew 3.12/3.13), never system python
│   ├── custom_nodes/    # ComfyUI-GGUF @6ea2651 + ComfyUI-GGUF-Qwen3VL-TE @81b1cee, nothing else
│   └── extra_model_paths.yaml  → points at ../models (no duplicate copies)
├── bench/               # fixed prompts, seeds, reference images, API-format workflow JSONs
└── outputs/
```

- **Dependencies.** Keep everything in a per-project venv with a `requirements.lock` (`pip freeze`) and pinned git SHAs, recorded in `research/versions.md`.
  - PyTorch: use the **stable** release first. ComfyUI's README still says "nightly", but the M5 reports used 2.12.1 and 2.14. Record the exact version.
- **No `sudo`, no global pip, no ComfyUI-Manager auto-installs,** and no changes to `iogpu.wired_limit_mb`.
- **Downloads:** `hf download <repo> <file> --revision <sha>`, then verify with `shasum -a 256`.
- **Rollback:** delete `comfyui/` or `sdcpp/` (self-contained). Models are in one folder. Nothing is touched outside `~/Dev/photo-gen` except the HF cache (`~/.cache/huggingface`, which can be deleted) and optionally Homebrew `cmake` (removed with `brew uninstall`).

## 13. Validation tests (incremental)

Log every test to `research/tests.md` with date, commit, file sha, command, wall time, and peak memory.

| # | What | Expected | Failure symptoms | Diagnose | Likely cause → fix |
|---|---|---|---|---|---|
| 1 | Backend detection: `sd-cli -h` / `--version`. ComfyUI: `python -c "import torch;print(torch.__version__, torch.backends.mps.is_available())"` + startup log | Metal device listed. ComfyUI log shows `Mac Version`, `Total VRAM 16384 MB`, and the TE load device | Gatekeeper block; MPS False | `xattr -l sd-cli`; `python -c 'import platform;print(platform.machine())'` | Quarantine → verify then remove quarantine on that one file. x86 Python → recreate venv with arm64 Python. |
| 2 | Tokenizer: ComfyUI-GGUF rebuilds it from GGUF metadata; sd.cpp at TE load | No tokenizer error | `tokenizer` KeyError | log | wrong/renamed file |
| 3 | Load TE alone: encode 1 prompt (sd.cpp `-v` log / ComfyUI CLIPLoaderGGUF → TextEncodeQwenImage21) | ComfyUI log: `[GGUF-Qwen3VL-TE] added 351 Qwen3-VL vision tensors`; no `[1, 512, 12288]` | shape error; `Missing vision tower` | log; `ls models/text_encoders` | patch not loaded or mmproj misnamed |
| 4 | Load DiT, **512² 8 steps** (not 1024 yet) | coherent image | **green/blocky noise** (K-quant on MPS, city96 #177); `Unknown model architecture` | same seed with leejet Q4_0 / Q8_0 | K-quant MPS bug → switch to Q4_0; arch → patch / leejet file |
| 5 | VAE round-trip (4-node workflow from #16433) with and without `--cpu-vae` | PSNR > 40 dB with `--cpu-vae` | ~6.6 dB | compute PSNR (script in bench/) | #16433 → keep `--cpu-vae` |
| 6 | Minimal t2i 512², 25 steps, cfg 1, seed 42 | clean image | black image / NaN | log `invalid value encountered in cast` | bf16 NaN on MPS (#15804-like) → try `--force-fp32` for the DiT only as a diagnostic |
| 7 | **1024² t2i, 25 steps** (decision gate). sd.cpp: A/B with and without `--offload-to-cpu` | completes. Memory pressure stays green/yellow; swap growth < 2 GB | red pressure, swap > 4 GB, `MPS backend out of memory` | §14 monitor | TE co-resident → `--disable-smart-memory` / `--cache-none` / close apps |
| 8 | Edit: 768 reference grid, cfg 1, `--cpu-vae` (then 896; **never exactly 1024** until #16435 closes) | identity preserved, no speckle | speckle; OOM | same seed at 736/800 | #16435 / memory |
| 9 | Speed: 3 warm runs per config, median; separate TE encode, denoise s/it, VAE decode | stable s/it within ±10% | s/it rising over runs | `pmset -g therm`, `powermetrics` | thermal throttling / memory creep (#320) |
| 10 | Memory: 10 consecutive 1024 t2i runs | flat peak RSS | growth each run | `ps` RSS series | leak (#320) → restart between batches |

## 14. Observability and benchmark plan

**Monitor (run in a second terminal during every test):**
```zsh
# every 2 s: memory pressure level, swap, compressor, and the generator process
while true; do
  print -n "$(date +%T) "; memory_pressure | tail -1 | tr -d '\n'
  print -n " | $(sysctl -n vm.swapusage | awk '{print $6}') swap"
  print -n " | $(vm_stat | awk '/occupied by compressor/{printf "%.1fGB compressed", $5*16384/1e9}')"
  ps -A -o rss=,%cpu=,comm= | grep -E "python|sd-cli" | grep -v grep | awk '{printf " | %s %.2fGB %s%%", $3, $1/1048576, $2}'
  print; sleep 2
done | tee -a research/monitor-$(date +%Y%m%d-%H%M).log
```
- GPU utilization and power: `sudo powermetrics --samplers gpu_power,thermal -i 2000`. This is the only item needing sudo; it is read-only and optional.
- Thermal: `pmset -g therm`.
- Visual check: Activity Monitor → Memory tab (pressure graph colour) and Window → GPU History.
- Load time and s/it: ComfyUI console prints `Prompt executed in … seconds` and the tqdm s/it. sd.cpp `-v` prints per-stage timings and compute-buffer sizes.

**Benchmark set (fixed):** seed 42 (plus 7 and 1234 for variance), 1024², 25 steps, euler/simple, cfg 1 (text prompts: the pottokao split cfg 1→3 at step 15 as a second arm). Fixed model SHAs.

1. simple: "a red apple on a wooden table, soft window light"
2. complex: multi-object spatial layout (5 objects, left/right/behind)
3. text rendering: neon sign reading "QWEN IMAGE 2.1" (the model-card prompt)
4. photorealistic: street scene at dusk, 35 mm
5. composition: rule-of-thirds portrait with a specified background
6. editing: fixed 768² reference photo, "change the background to a sunset beach"
7. difficult: hands holding a transparent glass with refracted text
8. long prompt: ~300-word PE-T2I-style paragraph (tests TE sequence length and memory)

Record per image in `research/bench.csv`:
- date, runtime + commit, DiT/TE file + sha, resolution, steps, cfg, seed;
- TE time, s/it, VAE time, total wall time;
- peak process RSS, peak swap, peak pressure level;
- artifacts noted, prompt adherence (0–2 per stated constraint, scored blind where possible).

**Heretic A/B (§3.3):** run every benchmark prompt with the **stock** `Qwen/Qwen3-VL-8B-Instruct-GGUF` Q4_K_M (5,027,784,800 B) + its mmproj vs Heretic Q4_K_M, same seed and everything else identical. This isolates the ablation's effect on image outputs, which no one has published.

## 15. Troubleshooting decision tree

```
Test 3 (TE load) fails on ComfyUI+patch ─► try molbal fork (remove city96+patch) ─► still fails ─► Heretic W4A8 safetensors (stock CLIPLoader)
Test 4 green/blocky noise (ComfyUI) ──► leejet Q4_0 DiT (needs patch's DiT detection) ─► still bad ─► Q8_0 DiT (7.69 GB; expect memory trouble at 1024)
Test 7 (1024 t2i):
  sd.cpp passes & ComfyUI passes ──────► compare peak memory + s/it + bench quality → pick; keep other as oracle
  only sd.cpp passes ──────────────────► use sd.cpp for t2i; ComfyUI only for experiments at ≤768
  only ComfyUI passes ─────────────────► ComfyUI with --cpu-vae (+ --disable-smart-memory if needed)
  neither passes ──────────────────────► drop to 896² / 768² (verify) → still no ─► mflux 0.20 --low-ram -q 4 (loses your GGUF TE; TE bf16 swaps)
                                          → still no ─► 1650 Ti box as CUDA runner (needs its RAM size first) or hosted inference
Edit (Test 8):
  garbled/noisy at any grid ───────────► confirm --cpu-vae (#16433) → change grid off 1024 (#16435) → disconnect VAE from TextEncodeQwenImage21 (weaker adherence, cleaner)
  OOM ─────────────────────────────────► smaller reference (640/512) → cfg 1 only → cache off/quantized → declare editing out of scope on 16 GB
Quality worse than expected ───────────► A/B stock vs Heretic TE → A/B Q4 vs Q8 DiT at 512 → check schedule (ComfyUI fixed mu 0.69, #16447) vs sd.cpp dynamic
```

## 16. Sources

Primary / official:
- Qwen/Qwen-Image-2.1 model card + configs, rev `790c926`: https://huggingface.co/Qwen/Qwen-Image-2.1 · GitHub https://github.com/QwenLM/Qwen-Image-2.1
- Comfy-Org repack, rev `9a44dbd`: https://huggingface.co/Comfy-Org/Qwen-Image-2.1 · Comfy docs https://docs.comfy.org/tutorials/image/qwen/qwen-image-2-1
- ComfyUI v0.37.0 / v0.36.0 releases, PR #16400: https://github.com/Comfy-Org/ComfyUI/pull/16400
- ComfyUI issues #16433, #16435, #16447, #16470, #14770, #13200, #11628
- city96/ComfyUI-GGUF (`6ea2651`), issues #177, #236, #320: https://github.com/city96/ComfyUI-GGUF
- leejet/ComfyUI-GGUF (`edd981b`), molbal/ComfyUI-GGUF (`48de657`)
- stable-diffusion.cpp docs/qwen_image_2.1.md, docs/performance.md, release master-908-88411ef, issue #2024: https://github.com/leejet/stable-diffusion.cpp
- mflux v0.20.0 release, issues #741, #748, #749: https://github.com/mflux-community/mflux
- Qwen/Qwen3-VL-8B-Instruct-GGUF (official TE GGUF): https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct-GGUF

Maintainer / community artifacts:
- https://huggingface.co/pottokao/Qwen-Image-2.1-Text-Encoder-Heretic-GGUF (sha `e21acf0`)
- https://huggingface.co/pottokao/Qwen-Image-2.1-Text-Encoder-Heretic
- https://huggingface.co/pottokao/Qwen-Image-2.1-DiT-GGUF (sha `14fa5d2`)
- https://github.com/pottokao-dotcom/ComfyUI-GGUF-Qwen3VL-TE (`81b1cee`)
- https://huggingface.co/leejet/Qwen-Image-2.1-GGUF · https://huggingface.co/unsloth/Qwen-Image-2.1-GGUF
- https://huggingface.co/ddalcu/Qwen-Image-2.1-MLX-Serve-4bit · https://huggingface.co/JoyFusionAI/Qwen-Image-2.1-MLX-8bit

Secondary (benchmarks / guides):
- https://dev.to/kevin_mullin_92ba0cf396f8/qwen-image-21-on-a-48-gb-mac-comfyui-tests-and-real-examples-2g5n (M5 Pro 48 GB)
- https://kgptalkie.com/tutorials/llm-benchmarking/qwen-image-2-1-macbook-pro-m5-max-comfyui (M5 Max 36 GB)
- https://x.com/ivanfioravanti/status/2101257247292580045 (search snippet only; not opened)
- https://www.kombitz.com/2026/09/20/how-to-use-qwen-image-2-1-gguf-in-comfyui/ (search snippet only)

## 17. Research gaps (could not verify)

1. **Any Qwen-Image-2.1 run on a base M5 or on any 16 GB Mac.** None found.
2. **Heretic Q4_K_M GGUF TE on macOS** in any runtime. None found; the maintainer explicitly did not test.
3. Whether city96 #177 (K-quant noise on MPS) still reproduces with 2026 PyTorch on M5.
4. Whether ComfyUI 0.37 frees the CPU-resident TE before DiT sampling on MPS (decides Scenario A), and whether "aimdo" dynamic VRAM is active on MPS. Indirect support: KGP's Q8 run measured ≈14 GB process memory against ≈17.1 GB of weights (REPORTED; the metric's definition is unknown).
5. `QwenImage21Cache` exact options (device/quantization/off) and their memory effect.
6. stable-diffusion.cpp Metal memory behaviour (`--offload-to-cpu`, `--params-backend`, auto-fit), and whether it loads pottokao's ComfyUI-layout DiT GGUF (use leejet's file to avoid the question).
7. Whether the sd.cpp prebuilt binary (built on macOS 26.6.2) runs unmodified on macOS 27.0.
8. Use of M5 GPU neural accelerators by PyTorch MPS / MLX / ggml-Metal for this model.
9. Reddit: no relevant posts were retrievable (search empty, API blocked). The Reddit claim table requested in your §18 is left empty rather than filled with guesses.
10. GTX 1650 Ti machine: system RAM, driver/CUDA version, sm_75 support for int8_convrot/w4a8. **Please tell me the Nitro's RAM.**
11. Speed on this machine. The 6–12 min/image figure is an **ESTIMATE**, scaled linearly by GPU cores to this Mac's 8:
    - **M5 Pro** (20-core; int8 DiT + int8 TE; 25 steps): 143.5 s × 20/8 ≈ **6 min**.
    - **M5 Max** (Q4 DiT + w4a8 TE; 40 steps): 218 s × 25/40 ≈ 136 s, then × cores/8. That gives ≈ **9 min** at 32 cores or ≈ **11 min** at 40. The M5 Max core count is **UNVERIFIED**; the 36 GB configuration has historically been the lower-core bin.
    - Caveats: CPU text encoding, VAE, and load time don't scale with GPU cores. Memory bandwidth (base M5 ≈ 153 GB/s, **UNVERIFIED** this session) and fanless throttling are ignored. Q4 vs int8 cost also differs on MPS.

## Appendix: Research log (major claims)

| CLAIM | SOURCE | DATE | VERSION | EVIDENCE | CONFIDENCE |
|---|---|---|---|---|---|
| TE GGUF arch = qwen3vl, 8.19 B params, ctx 262144 | HF API `expand[]=gguf` | 2026-09-24 | sha e21acf0 | metadata | VERIFIED |
| Heretic Q4_K_M structurally identical to official Qwen3VL-8B Q4_K_M | HF API both repos | 2026-09-24 | — | equal param count, 576 B size delta | STRONGLY SUPPORTED |
| Stock city96 loader lacks qwen3vl mmproj | city96 loader.py L482–501; pottokao README | 2026-01-12 / 09-23 | 6ea2651 | code | VERIFIED |
| Patch node is benign | full source read | 2026-09-24 | 81b1cee | no net/exec/writes | VERIFIED (at this commit) |
| ComfyUI TEs run on CPU on Apple Silicon | model_management.py L1219 | v0.37.0 | tag | code; PR #14770 open | VERIFIED (except aimdo path) |
| MPS VAE encode corrupts edits; `--cpu-vae` fixes | ComfyUI #16433 | 2026-09-20 | c194dd0 | 3 independent Macs | STRONGLY SUPPORTED |
| 1024-grid edit artifact | ComfyUI #16435 | 2026-09-20 | master | Mac + CPU; CUDA other grid | REPORTED / partly corroborated |
| ~11 GB process at 1024 t2i with Q4 DiT + 6.3 GB TE | KGP Talkie | 2026-09-21 | ComfyUI 0.37, PyTorch 2.14 | blog measurement | REPORTED (indirect HW) |
| 16–19 GB for 1-ref edit | KGP Talkie | 2026-09-21 | same | blog | REPORTED (indirect HW) |
| Q4 slower than Q8 on MPS | KGP; city96 #236 | 2026-09 / 2025-04 | — | two sources | STRONGLY SUPPORTED |
| fp8 unusable on MPS (incl. M5 Air) | ComfyUI #13200, #14770 | 2026 | — | many reports + PR text | STRONGLY SUPPORTED |
| sd.cpp supports Qwen-2.1 + GGUF TE + mmproj on Metal | sd.cpp docs; #2024 | 2026-09-22/23 | master-908 | docs + M4 Max user run | STRONGLY SUPPORTED (no perf data) |
| mflux keeps TE bf16 | mflux v0.20.0 notes; JoyFusionAI card | 2026-09-21 | 0.20.0 | release notes | VERIFIED |
| Metal working set 12.71 GB / max buffer 9.53 GB on this Mac | Swift Metal query | 2026-09-24 | macOS 27.0 | measured | VERIFIED |
| int8_convrot/W4A8 are CUDA-only | pottokao | 2026-09 | — | contradicted by M5 Pro/Max runs | CONFLICTING |
| Qwen-2.1 derivatives' license: ddalcu MLX card says Apache-2.0; official card says Qwen Research License | ddalcu HF card vs Qwen HF card | 2026-09-20 | — | cards disagree; the official license governs | CONFLICTING |
| ComfyUI fixed mu 0.69 at all resolutions | #16447 + comfyanonymous reply | 2026-09-22 | — | code + maintainer | VERIFIED (intentional) |
