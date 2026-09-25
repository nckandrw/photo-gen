# Few-step (< 8 NFE) distillation: feasibility study (Phase 3 §15)

**Decision boundary (directive):** no training, and no large compute spend, before a concrete plan exists. This document is that plan's feasibility layer. **Nothing was trained or downloaded.** The only network reads were HF/arXiv/GitHub metadata and one ≈77 KB safetensors header.

## 1. The starting point
- FAST = bf16 + 8 NFE. At 1024² cold that is 48.7 s denoise / 54.2 s wall (`PERFORMANCE-MAP.md`).
- The Turbo step sweep: 7–6 steps are draft quality, 5–4 preview quality (`step-sweep-report.md`). Simply running Turbo with fewer steps is **not** a quality-equivalent path.
- A true < 8-NFE model needs weights (full or LoRA) trained for that NFE.

## 2. New finding: first-party few-step LoRAs exist, but for Z-Image *base*, not Turbo
`alibaba-pai/Z-Image-Fun-Lora-Distill` (Alibaba PAI, Apache-2.0, last modified 2026-03-02):
- LoRAs for **2, 4 and 8 steps** (versions 2602 and 2603), each 568 MB, bf16, rank 128.
- Card: "distills both steps and CFG … **does not use any Z-Image-Turbo related weights** and is trained from scratch", and "will slightly reduce the output quality and change the output composition". Its purpose is fast generation for Z-Image-*derivative* models, "not to replace Z-Image-Turbo".
- 2603 versions add a random-timestep strategy "better adapted to sigmas below 0.5". The 2-step model recommends a second-step sigma in a stated range.
- **mflux compatibility (LIKELY, not verified):**
  - The header of `…-4-Steps-2603-ComfyUI.safetensors` has 612 tensors keyed `diffusion_model.{layers,context_refiner,noise_refiner}.N.{attention.to_q/k/v, feed_forward.w1/w2/w3}.{lora_down,lora_up,alpha}`.
  - mflux 0.20.0's `z_image_lora_mapping.py` accepts exactly the `diffusion_model.*.lora_down/lora_up/alpha` pattern.
  - `mflux-community/z-image-base-mflux-q4` exists.
- **Runtime cost in mflux:** LoRA is applied unfused (`linear_lora_layer.py`: `base(x) + scale·(x·A)·B`). At rank 128 that is ≈ 4.6–6.7% extra FLOPs on the adapted linears (≈ 5% on the block), plus 0.57 GB resident.

## 3. Requirements for training our own few-step student (if §4 step 0 justifies it)
| item | assessment | confidence |
|---|---|---|
| training data | **prompts only.** A data-free recipe is possible: the teacher (Turbo at 8 NFE, CFG-free) generates targets. Decoupled-DMD's CFG-augmentation "engine" needs a CFG teacher (Z-Image base). With Turbo as teacher, the objective reduces to trajectory or distribution matching without CA. | medium (paper abstract; details not read) |
| teacher | Turbo (8 NFE) for a 4-step student; or base Z-Image + CFG for a DMD-style student | high |
| models in memory | DMD-family: student + teacher + fake-score critic = 3 × 6B. bf16 weights alone ≈ 37 GB. Full fine-tuning adds Adam states (≈ 12 B/param → ≈ 72 GB per trained model). **LoRA student + LoRA critic** avoids the optimizer blow-up. | high (arithmetic) |
| GPU | full fine-tuning: multi-GPU 80 GB class. LoRA-DMD: plausibly **1× 80–141 GB GPU** (H100/H200) with activation checkpointing. | medium (ESTIMATE) |
| GPU hours | **UNKNOWN.** Neither the Z-Image nor the Decoupled-DMD abstract states distillation cost. The whole Z-Image pipeline was 314K H800 GPU-h (≈ $630K, arXiv 2511.22699); distillation is a small but unstated fraction. | — |
| cloud | rented H100/H200 by the hour. Price: ESTIMATE, market-dependent, not verified here. | low |
| local feasibility | **none.** The 16 GB M5 cannot hold one bf16 copy of the DiT plus training state. | high |
| conversion path | PyTorch LoRA (diffusers/VideoX-Fun) → ComfyUI key format (`diffusion_model.*`) → mflux LoRA on the q4 base (runtime, unfused), **or** merge into bf16 and re-quantize to q4 with mflux's own save path. Merge + re-quantize removes the ≈ 5% LoRA overhead but changes the q4 weights (needs its own parity/quality gate). | medium |
| mflux compatibility | LoRA loading: LIKELY (key pattern matches). Merge + q4 re-quantize: supported by mflux tooling, but not tested here. | medium |
| expected benefit | 8 → 4 NFE ≈ −50% denoise. Cold 1024²: 48.7 → ≈ 24–26 s denoise (incl. LoRA overhead), wall ≈ 31 s. 2 NFE: ≈ 13 s denoise. **Quality: UNKNOWN.** | high for time (per-step cost is constant, measured); quality unknown |

## 4. Minimum viable experiment (ordered, each step gates the next)
0. **Zero-training probe** (needs approval: ≈ 6 GB base q4 pack + 0.57 GB LoRA):
   - Z-Image base q4 + PAI 4-step-2603 LoRA (and 2-step) in mflux at 1024², bf16.
   - Blinded A/B vs FAST on 12 prompts × 2 fresh seeds.
   - Answers three questions with no training at all:
     - does mflux load and run it;
     - what does 4 NFE cost end to end on the M5;
     - how far is first-party 4-step quality from Turbo-8?
   - If it is within the FAST gate criteria, a "turbo-4" tier needs no training at all.
1. Only if 0 shows a quality gap worth closing: a costed LoRA-distillation plan with Turbo as teacher (4-step student, rank 128, prompts from the project suite plus a public prompt set). First, a 1-GPU pilot capped at a fixed budget, measuring convergence per GPU-hour.
2. Convert and gate exactly like any other production change (pixel parity is not applicable; blinded gate required).

## 5. Status
- **Few-step distillation training:** **DEFERRED** (no concrete need; FAST solves the immediate problem).
- **Zero-training PAI LoRA probe (§4 step 0):** **PROPOSED**, blocked on a download approval. It replaces "estimate GPU hours" as the highest-information next step: it answers the quality question for 4/2 NFE on this exact runtime before any money is spent.
