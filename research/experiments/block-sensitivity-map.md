# Z-Image block-sensitivity map (Phase 3 §9)

Status: **PROTOCOL 2026-09-25.** Measurement is queued in chain P3B; results are appended below. No block is removed from any model. Ablations are in-memory measurements in a research harness.

## Blocks
34 transformer blocks (see `phase3-plan.md`, Improvement Clause):

| ids | blocks | tokens |
|---|---|---|
| nr0–nr1 | noise refiner | image tokens only (4096 at 1024²) |
| cr0–cr1 | context refiner | caption tokens only, no timestep |
| L0–L29 | main | unified image + caption, 4128 at 1024² |

The 30 main blocks are the primary set.

## Static facts (from the architecture; not measured)
**Parameters.** Every main and noise-refiner block has the same parameter count:
- attention 4 × 3840²;
- FFN 3 × 3840 × 10240;
- adaLN 256 × 4 × 3840.

That is ≈ 180.9 M logical parameters (58.98 M attention + 117.96 M FFN + 3.93 M adaLN; norms negligible). Context-refiner blocks have no adaLN (≈ 176.9 M).

**Compute per step.**
- All main blocks do identical work (same shapes).
- Noise-refiner blocks do ≈ 99% of it (4096 vs 4128 tokens).
- Context-refiner blocks do < 1% (32 tokens).

**Consequence for the requested quadrant map.** The compute axis is essentially flat across the 32 image-carrying blocks. "High compute / low importance" vs "high compute / high importance" therefore reduces to an **importance ranking among equal-cost blocks**, plus the two cheap context-refiner blocks. This is stated up front so the map isn't read as showing compute variation that doesn't exist. Measured per-block time (below) will test the equal-cost claim.

## Measurements
| quantity | how | run(s) |
|---|---|---|
| execution time (attention half / FFN half) | `p3_block_probe.py time`: synchronised per-block timing, uncompiled | 1024², bf16/8 and fp32/9, p01 s42 |
| activation RMS / variance (in, out) | `stats` mode | 1024², bf16/8, p01/p06/p09 s42 |
| residual contribution ‖out−in‖/‖in‖ | `stats` | same |
| attention contribution ‖gate·norm(attn)‖/‖in‖ | `stats` | same |
| FFN contribution ‖gate·norm(ffn)‖/‖mid‖ | `stats` | same |
| cosine(in, out) | `stats` | same |
| **sensitivity to perturbation** (primary importance signal) | `perturb`: (i) **skip** (block returns its input) at every step, 3 prompts; (ii) **scale 0.9** of the block's update, p01. Metric: PSNR/SSIM of the final image vs the uncompiled unperturbed baseline (same prompt/seed/resolution) | 512², bf16/8, all 34 blocks; 1024² p01 skip, all 34 blocks (rank-agreement check) |

## Instrumentation disclosure
- The probe disables `mx.compile` (`MLX_DISABLE_COMPILE=1`) and reimplements the block's forward with the same operations, to expose intermediates.
- Timings are **per-block synchronised and uncompiled**. They are valid for *relative* comparison between blocks and between attention/FFN, not for comparison with production timings.
- Uncompiled numerics may differ slightly from compiled ones. Every perturbation run is therefore compared against an **uncompiled** baseline from the same harness. The uncompiled-vs-compiled baseline hash difference is recorded.

## Classification (after measurement)
- Importance I_b = mean over prompts of (1 − SSIM) under skip. PSNR is reported alongside.
- Blocks are ranked. The quadrant labels use the median of I and the measured time:
  - high/low compute is only meaningful for context-refiner vs the rest;
  - within equal-cost blocks, the label is "low importance" (I < median) or "high importance".
- Candidates for later depth-reduction or width-reallocation studies are blocks whose skip keeps SSIM high on all 3 prompts and at 1024². Being a candidate is **not** evidence that removing the block is acceptable. Skip effects are not additive across blocks.

## Results
(appended after chain P3B)
