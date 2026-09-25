# Step sweep 9 → 4 (E03) — bf16 stream, 1024², seed 42

**Design.**
- 12 prompts (`prompts.json`) × steps {8, 7, 6, 5, 4} = 60 runs, 21:21–22:30.
- Step order alternates per prompt (8→4, then 4→8) to spread thermal drift.
- The 9-step references are the bf16 arm of the gated A/B (`bf16ab/pXX-s42-bf16.png`, same seed and precision).
- Settings: `--low-ram`, mflux default scheduler. mflux recomputes the sigma schedule for the requested step count, so these are genuine N-step runs, not truncated 9-step runs.
- Data: `stepsweep/results.jsonl`, `stepsweep/metrics.json`, contact sheets and 100% crops in `stepsweep/sheets/`.
- All 60 runs rc=0.

## Time and memory (sustained regime)
| steps | denoise median (s) | mean s/step | Δ denoise vs the 98.0 s bf16/9 A/B arm (different session; hotter) | peak footprint max (GB) |
|---:|---:|---:|---:|---:|
| 9 (ref, A/B) | 98.0 | 10.86 | — | 7.37 |
| 8 | 82.6 | 10.29 | −16% | 7.37 |
| 7 | 72.4 | 10.31 | −26% | 7.37 |
| 6 | 62.2 | 10.31 | −37% | 7.36 |
| 5 | 51.8 | 10.31 | −47% | 7.37 |
| 4 | 41.8 | 10.37 | −57% | 7.37 |

- Per-step cost is constant; time is linear in steps. The reference's slightly higher s/step comes from the A/B's hotter segment, so the true saving per removed step is ≈11%.
- Memory is independent of the step count.

## Fidelity to the 9-step output (PSNR / SSIM vs the same seed at 9 steps)
| steps | PSNR median (min) | SSIM median (min) |
|---:|---|---|
| 8 | 31.3 (16.8) dB | 0.975 (0.702) |
| 7 | 28.2 (15.0) dB | 0.948 (0.614) |
| 6 | 24.7 (13.9) dB | 0.911 (0.560) |
| 5 | 23.0 (13.1) dB | 0.886 (0.512) |
| 4 | 20.7 (12.7) dB | 0.840 (0.481) |

- Fidelity falls monotonically. The minima are the busy scenes: p09 market, p07 poster, p06 street.
- Low PSNR here mostly reflects content and layout drift (for example, which vendor stands where), not degradation. Visual review decides quality.

## Visual review (single rater, not blinded: the step count is visible in the images)
Contact sheets at 9/8/7/6/5/4 for all 12 prompts, plus 100% crops of p10 (fur), p08 (metal/condensation) and p09 (faces/market) at 9/6/4.

**Composition and prompt adherence hold down to 4 steps on all 12 prompts.**
- No collapse, no noise and no broken anatomy were observed.
- **Text:**
  - p05 "QWEN IMAGE 2.1" is exact at every step count. The only change is a colour shift of "2.1" to pink at ≤7 steps.
  - p07 "VISIT SIQUIJOR" / "Island of Fire" is exact at every step count. At 9 steps this seed *duplicates* the subtitle; at ≤8 it appears once. That is one seed, so anecdotal, not a trend.
  - p03's text through the glass is gibberish at every step count; the model can't render it either way.
- **Counting:** p12 gives the same wrong count (3 cups, 4 plates) at every step count.

**Fine detail is what degrades, gradually.**
- **8 steps:** indistinguishable in quality from 9 at normal and 100% viewing.
- **6 steps:** the scratch density on the copper kettle is reduced, the condensation droplet is gone, and the linen weave is slightly smoother. The cat's fur and whiskers are still crisp.
- **4 steps:** a visible softening of micro-texture: fewer scratches, a smoother napkin, slightly softer fur. One composition anomaly: p08 gains an extra wine glass intruding at the right edge. Faces in p09 are still coherent.

## Verdict
| steps | classification | use |
|---|---|---|
| 8 | **No observed regression** (unblinded, single seed), ≈ −11% denoise vs 9 steps (per-step cost, same session) | candidate for a validated "fast" preset (needs a blinded multi-seed A/B like the bf16 gate before adoption) |
| 7 / 6 | 7: slight (not crop-inspected); 6: visible micro-detail loss at 100% | "draft" use (≈22–33% less denoise vs bf16/9 by per-step cost) |
| 4–5 | clear micro-detail softening, occasional layout anomaly; composition intact | previews/iteration (4 steps ≈2.25× less denoise vs bf16/9 by per-step cost, same session) |

**Production:**
- **No change.** photo-gen already exposes any step count as `allow_experimental`, and results are labelled `validated_configuration: false`.
- **Pending:** promoting 8 steps to "validated" needs the E08-grade blinded gate, which this unblinded, single-seed sweep doesn't provide.
- **Speed context (baselines named; superseded by the same-session performance map in PERFORMANCE-MAP.md):**
  - bf16/4 denoise 41.8 s (this sweep) vs bf16/9 98.0 s (bf16 arm of the earlier A/B, a hotter segment): 2.35× by ratio of medians. Per-step cost within this sweep (≈10.3 s): 9/4 = 2.25×.
  - vs the fp32/9 A/B median (135.3 s, sustained): 3.2×. vs the 10-run sustained fp32 series (133.7 s): 3.2×.
  - These mix sessions and thermal states; they are not a combined-configuration measurement (directive §18).
