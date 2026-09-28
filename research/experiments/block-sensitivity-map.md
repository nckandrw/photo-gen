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

## Results (chain P3B, 2026-09-28; `p3b/sensitivity-metrics.json`, `p3b/time-1024-*.json`, `p3b/stats-1024-*.json`, contact sheets `p3b/sheet-sens*.png` (PNGs not in Git))
**Compute (measured, real model, 1024² bf16):**
- The equal-cost claim holds: main blocks cost 293–330 ms each (median 307), and the noise refiner costs the same.
- Context refiner: 8–9 ms per block. FFN is 52% of each main block.

**Importance = mean (1 − SSIM) under a single-block skip, over 3 prompts at 512²** (uncompiled baseline; 1024² p01 skip and 512² scale-0.9 for consistency):

| group | blocks (512² importance) | what skipping does (contact sheets) |
|---|---|---|
| **critical, cheap** | cr0 (0.70), cr1 (0.60) | **cr0 skip destroys the image** (pure noise pattern) at both sizes. cr1 is also severe. Low compute, highest importance. |
| high | L19 0.48 · L20 0.45 · L3 0.45 · L18 · L21 · L17 · L16 · L2 · nr0 · L5 · L15 · L29 (0.41–0.44) | coherent images with a **different composition/framing** (zoom, lighting). L2 at 1024² also loses material detail. |
| medium | L22 … L9 (0.34–0.39) | smaller composition shifts |
| **lowest** | L10 0.29 · L25 · L27 · L26 · nr1 · L28 · L0 · L12 (0.29–0.32) | composition preserved, small detail/lighting changes. These are the candidates for any future depth-reduction study. |

- **Consistency:** Spearman ρ between the 512² and 1024² skip rankings is **0.75**; between skip and scale-0.9 it is **0.61**. The ranking is moderately stable, not precise.
- **No single block is removable without visible change:** the least important skip leaves SSIM ≈ 0.71 at 512² (L10). At 1024² the smallest change is L28, SSIM 0.95. 0/170 perturbed images matched their baseline.
- The **mid-stack** (L15–L21) and the **early** blocks (L2, L3, L5) carry composition. The **late** blocks (L25–L28) mostly refine.
- Activation stats (`stats-*`) show a residual update ‖out − in‖/‖in‖ of 0.1–0.2 in main blocks. Full per-step tables are in the JSON.

**Quadrant classification** (compute axis: context refiner vs everything else):

| | low importance | high importance |
|---|---|---|
| **high compute** (main / noise-refiner, ≈ 307 ms each) | L10, L25–L28, L0, L12, nr1 | L2, L3, L5, L15–L21, nr0, L29 |
| **low compute** (context refiner, ≈ 8 ms) | — | **cr0, cr1** |

**Verdict:** a **measured map exists.** It says depth reduction is *not* free. The best candidates (late blocks) still change images. Any removal study must test *combinations* (skip effects are not additive) and likely needs recovery training. **No block was removed from any model.**
