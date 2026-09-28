# Kernel profile of the M5 denoise path (Phase 3 §12)

Status: **METHOD 2026-09-25.** Measurements come from chain P3B; results are appended below. Nothing is optimized on the basis of this document unless the profile shows the target is material.

## Profiling environment (kept with the results)
| item | value |
|---|---|
| machine | MacBook Air M5, 16 GB, `applegpu_g17g`, macOS 27.0, on AC power (recorded per chain) |
| runtime | mflux 0.20.0, MLX 0.32.2 (wheel), Python 3.12.14, `mflux/.venv` |
| model | Z-Image-Turbo q4 @ d2d30500 (real-model probes); synthetic N(0, 0.02) weights quantized q4 group 64 (op-level probes) |
| env | `HF_HUB_OFFLINE=1`. `MLX_*` unset unless stated. `MLX_DISABLE_COMPILE=1` only in the instrumented block probe. `MTL_CAPTURE_ENABLED=1` only in capture runs. |
| scripts | `op_profile.py`, `nax_probe.py`, `quant_microbench.py`, `p3_block_probe.py` (time mode), `phase3-chainB.sh` |
| GPU sharing | none; chains run strictly sequentially |

## Three layers of measurement and what each is valid for
| layer | tool | validity | NOT valid for |
|---|---|---|---|
| A. op level, one real mflux `ZImageTransformerBlock` class, synthetic weights, production shapes (L = 4128 / 1056) | `op_profile.py` | ranking of ops by time; effective TFLOPS/GBps (analytic FLOPs and bytes); compiled-vs-uncompiled block delta | absolute production step time: isolated ops are each forced to materialise, which over-counts fusable elementwise work |
| B. block level, real model, per-block synchronised | `p3_block_probe.py time` (uncompiled) | top blocks by time; attention vs FFN split per block, on real weights and real inputs | production timings: compile disabled, a sync after each half-block |
| C. kernel level, Metal capture | `.gputrace` from `op_profile.py` / `nax_probe.py` | which pipelines (kernel names) are dispatched and how many per block, compiled vs uncompiled (materialised intermediates = dispatch-count delta) | timing (capture perturbs execution) |

Production end-to-end timings remain those of `PERFORMANCE-MAP.md`. The profile is for identifying bottlenecks only.

## Questions → where answered
| directive item | source |
|---|---|
| top operations by runtime | layer A (per op), cross-checked with layer B (attention/FFN halves) |
| top operations by memory traffic | layer A: analytic bytes per op and achieved GB/s. There are no hardware counters without Instruments; this is disclosed. |
| top transformer blocks by runtime | layer B |
| attention vs FFN runtime | layers A and B |
| kernel counts | layer C (compiled vs uncompiled capture) |
| materialized intermediates | layer C dispatch-count delta, plus layer A isolated-sum vs compiled block |

## Results
(appended after chain P3B)

## Smoke test (2026-09-28, `p3b/smoke/`; tiny shapes; plumbing only, not results)
- `op_profile.py bf16 256`: 19 ops recorded; compiled vs uncompiled block 13.6 vs 14.0 ms.
- `quant_microbench.py bf16 256`: all 19 formats ran, no errors.
- `p3_block_probe.py` (512², 2 steps):
  - `time`, `stats` and `ffn_calib` each record 34 blocks × 2 steps;
  - the hooks do not change the output: all three produce the same pixel hash, `55bba0c0`;
  - `perturb skip` changes the output as intended.
- **Instrumentation confound, quantified:** the uncompiled 8-step baseline (`f8f1a654`) differs from the compiled production hash (`0b9cc20a`), because compilation changes numerics. All perturbation comparisons therefore use the uncompiled baseline, as designed.

## Results (chain P3B, 2026-09-28)
**Harness bug found and fixed before use (disclosed).** The first op-profile run gave "bf16" ≈ fp32 (272.7 vs 265.9 ms per block). That contradicted production's measured 0.70 ratio.
- **Cause:** MLX's default float32 RMSNorm weights silently promoted the bf16 activations to fp32. The real q4 pack stores all norm weights as BF16 (safetensors header checked).
- **Fix:** norm and bias weights are cast to bf16, and bf16 mode applies the **production** bf16 patch set (`_apply_bf16_stream`, which includes the SDPA mask cast).
- The faulty outputs are kept in `p3b/superseded/`.
- After the fix: bf16 177.2 ms vs fp32 261.7 ms per compiled block, a ratio of **0.68**, consistent with production (0.70).

### A. Op level, one block, production shapes (compiled block time; op shares from the isolated sum)
| group | fp32, L4128 (REFERENCE, 1024²) | **bf16, L4128 (FAST, 1024²)** | bf16, L1056 (FAST, 512²) |
|---|---:|---:|---:|
| compiled block | 261.7 ms | **177.2 ms** | 41.0 ms |
| FFN matmuls (w1, w3, w2) | 45.9% | **49.3%** | 53.8% |
| QKV + out-proj matmuls | 22.3% | **24.8%** | 28.1% |
| SDPA | 17.2% | **14.6%** | 4.8% |
| RoPE (q, k) | 6.2% | 4.6% | 4.2% |
| norms, gating, residuals, SiLU·mul, transposes | 8.4% | 6.7% | 9.1% |
| matmul throughput (q4, NAX) | 6.9–7.9 TFLOPS | **10.3–10.6 TFLOPS** | 9.6–10.1 TFLOPS |
| SDPA throughput | 5.4 TFLOPS | 9.5 TFLOPS | 7.8 TFLOPS |
| compile gain (uncompiled → compiled) | 5.3% | **2.7%** | 2.3% |

### B. Block level, real model, 1024², per-block synchronised (`p3b/time-1024-*.json`)
- **Heat-soaked chip:** 9.9 s/step bf16, matching the sustained regime. Absolute ms are therefore ≈ 1.7× the cold microbench; the ratios are what matter.
- **The 30 main blocks are equal-cost:**
  - bf16: 293–330 ms each, median 307;
  - fp32: 422–475 ms, median 440;
  - the spread is run noise, not structure.
- **Within a block:** FFN 52%, attention half (QKV + SDPA + RoPE + out-proj) 48%, in both precisions.
- **Noise-refiner blocks** cost the same as main blocks. **Context-refiner blocks** cost 8–11 ms each (< 3%).
- **The 30 main blocks = 94%** of per-step transformer time.

### C. Kernel counts and materialised intermediates: **NOT MEASURED**
- A text scan of the full-block `.gputrace` bundles returns the *process's* pipeline inventory: identical 74-name lists for compiled, uncompiled, fp32 and bf16. It does not return per-capture dispatch counts.
- Dispatch counts need Xcode GPU-trace replay, which was not used. Instead, the compile gain (2.7% in bf16) bounds the fusion already achieved.

### What this says about where the remaining compute goes (FAST, 1024²)
1. **≈ 74% is q4 matmuls already running on the M5 matrix units** (NAX, verified) at ≈ 10.4 TFLOPS.
   - The hardware peak is unknown (no counters), so the remaining headroom is **UNKNOWN**.
   - The only levers for this share are *doing fewer matmul FLOPs* (width, depth, steps) or better kernels.
2. **≈ 15% is SDPA** (9.5 TFLOPS on NAX). It scales with L²: 4.8% at 512², 14.6% at 1024².
3. **≈ 11% is RoPE + elementwise.** Compile already fuses part of it (2.7% gain). Even a perfect fusion of *all* of it would be ≤ 11% of the block, realistically a few %. **Custom-kernel work on non-matmul ops has a low ceiling.**
4. **`mask=None` SDPA** saves 1.5 ms of 27.6 (≈ 0.8% of the block). This matches E04 (REJECTED); not reopened.
