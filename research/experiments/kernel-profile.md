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
