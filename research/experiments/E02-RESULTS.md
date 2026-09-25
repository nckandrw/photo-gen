# E02 — bf16 hidden stream in the Z-Image DiT (mflux 0.20.0 / MLX 0.32.2, MacBook Air M5 16 GB)

> **CORRECTION (2026-09-25, E10 ablation, `experiments/e10/`, `e10_promotion_ablation.py`).**
> - **Pad tokens are NOT a promotion source.** `x_pad_token`/`cap_pad_token` are stored as BF16 in the checkpoint and loaded over the `mx.zeros` init (dtype after load: bfloat16). The pad-token cast in the patch is a harmless no-op.
> - **Promotion comes from two sources that must BOTH be fixed:**
>   1. the float32 TimestepEmbedder output (adaLN modulation);
>   2. the float32 RoPE tables (`_apply_rotary_emb` returns float32).
> - Measured per variant:
>   - none → SDPA q / FFN in = fp32/fp32;
>   - temb only → fp32/fp32 (RoPE re-promotes q/k, and attention output promotes the residual);
>   - rope only → fp32/fp32;
>   - temb+rope → **bf16/bf16**;
>   - pad+temb+rope → bf16/bf16 (identical).
> - The earlier statements "three sources" and "each sufficient on its own" were wrong. The measured speed/quality results are unaffected (the full patch set was used throughout).

**Finding (E01):** production mflux 0.20.0 runs the Z-Image DiT hidden stream in **float32** although inputs and weights-scales are bf16 (`ModelConfig.precision = bfloat16`). Promotion sources: (1) `x_pad_token`/`cap_pad_token = mx.zeros(...)` (float32) via `mx.where`; (2) float32 timestep embedding feeding adaLN modulation; (3) float32 RoPE tables in `_apply_rotary_emb` (re-promotes q/k at every attention). Not reported upstream (mflux issues/PRs searched 2026-09-24).

**Patch (experiment-only, runtime, no files modified):** pad tokens → bf16; TimestepEmbedder output → bf16; RoPE output cast back to the input dtype (diffusers semantics: rotary math in fp32 tables, result in model dtype); SDPA additive mask cast to q dtype. Script: `experiments/e02_bf16_hidden_stream.py` (`--baseline` disables every numeric patch; same harness for both arms).

## Controlled A/B (1024², apple, seed 42, 9 steps, --low-ram; each arm after 10-min idle; AC; Finder/Terminal only)
| Arm | dtypes observed (all calls) | denoise (s) | s/step (min–max) | generate_image (s) | peak footprint (GB) | MLX peak (GB) | output |
|---|---|---:|---|---:|---:|---:|---|
| fp32 baseline (production behaviour) | attention input {bf16 (first refiner call), fp32}, sdpa q fp32, ffn fp32 | **78.33** | 8.54–9.23 | 80.32 | 7.28 | 5.70 | pixel sha fe47d88d… = production reference ✔ |
| bf16 stream | attention/sdpa/ffn all bf16 | **55.55** | 6.05–6.75 | 57.71 | 7.35 | 5.70 | pixel sha 11b19277…; identical to earlier bf16 run ✔ (deterministic) |

**Speed-up: denoise −29.1% (1.41×)**, matching the E00 synthetic block prediction (1.41×). The uncontrolled E02b run (72.1 s) started on a warm chip — thermal state, not a partial effect.

## Quality (vs fp32 production outputs, same seeds)
| Prompt | PSNR vs fp32 | mean \|Δ\| | p99 \|Δ\| | Visual inspection |
|---|---:|---:|---:|---|
| apple 1024² | 42.32 dB | 0.92 | 7 | same composition, droplets, lighting |
| neon text 1024² | 34.57 dB | 1.50 | 18 | text `QWEN IMAGE 2.1` exact; same layout and glow |

Not pixel-identical (expected for a numeric-precision change). n = 2 prompts, single rater — **insufficient for adoption**; requires E08-grade evaluation.

## Not yet measured
Sustained/throttled behaviour with bf16 (faster steps may change power/thermal profile); resolutions other than 1024²; the uncast-RoPE variant's quality (E02 without RoPE cast gave no speed-up because the stream re-promoted).

## Status
BENCHMARK complete (speed, memory, determinism). **Not adopted** into photo-gen production: quality evaluation (E08) and an explicit, versioned runtime option are prerequisites. Candidate upstream report to mflux (user decision).
