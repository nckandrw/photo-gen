# Step-count quality gate: protocol (PRE-REGISTERED before any gate image)

Written 2026-09-29, before any Stage A image existed. It is committed before generation. This protocol text is not edited after generation; deviations are appended to `results.md`.

## Question
Can ordinary Z-Image-Turbo q4 at **bf16 + N steps** (N = 4, then 5, then 6; in mflux N steps = N NFE) replace FAST (bf16 + 8) at a given resolution **without a material or systematic loss** in prompt adherence, composition or visual quality?

Production is untouched: REFERENCE fp32 + 9 and FAST bf16 + 8 (validated at 512², 768², 1024²), the v2 tag, and the model files.

## Fixed configuration (identical in both arms except the step count)
- **Model:** `mflux-community/z-image-turbo-mflux-q4` @ `d2d30500`, verified by `bin/photo-gen verify`.
- **Runtime:** mflux 0.20.0 / MLX 0.32.2. The production worker via `prod_runner.py`: `--low-ram`, transformer release on, bf16 patch, guidance 0.
- **Scheduler:** the validated mflux default (`linear`, resolution-dependent shift). **No scheduler change.** mflux recomputes the schedule for each N.

## Discrepancies surfaced before running
1. **The sigma schedule depends on resolution, so the 1024² evidence may not transfer.** Last-step starting σ for N = 4:

   | resolution | σ schedule | last-step start |
   |---|---|---:|
   | 1024² | 1, 0.905, 0.760, 0.513 → 0 | 0.513 |
   | 768² | 1, 0.875, 0.700, 0.437 → 0 | 0.437 |
   | 512² | 1, 0.849, 0.652, 0.385 → 0 | 0.385 |

   Smaller images take their last step from a lower noise level. This affects detail and residual noise differently at small sizes. **Each resolution gets its own verdict. No verdict is extrapolated.**
2. **Prior 4-step evidence** (probe A-vs-B, 1024², seeds 4242/6174) was seen by the rater. This gate uses **fresh seeds** that no project image has used (checked by scanning all research JSON/JSONL).
3. **Objective tools:** no OCR (tesseract absent) and no LPIPS (a package plus network weights; the no-new-dependency policy stands). Text correctness is therefore judged by the rater reading the blinded composite. Objective support: `grid16` (16-px periodicity, from the probe), Laplacian variance (detail proxy), and PSNR/SSIM (descriptive only).

## Improvement Clause: fresh seed pair per stage
| | |
|---|---|
| Original | the same seeds for all three stages, reusing the bf16/8 images |
| Proposed | **Stage A seeds 2026, 7331. Stage B (N = 5) seeds 6502, 1729. Stage C (N = 6) seeds 8086, 5150.** Each stage generates its own bf16/8 arm. |
| Evidence | Stages are decided sequentially: B runs only after A's verdict. Unblinding A reveals which images were 8-step. Reusing them in B would let the rater recognise the 8-step arm, which breaks blinding. |
| Why better | each stage stays fully blind at the cost of one extra arm of generation per stage (8-step at 1024² ≈ 35 min) |
| Expected impact | valid, independent verdicts per stage. The pooled 8-step reference also gains seeds. |

## Stage A design (N = 4)
- **Prompts:** the established 12-prompt suite (`research/experiments/prompts.json`). It covers photorealism (p01, p10), portrait (p02), hands + glass/transparency + text-through-glass (p03), multi-object spatial layout (p04), neon/low-light text (p05), Cebu street (p06), multi-word poster text (p07), fine materials (p08), a difficult composition in Manila (p09), low light/reflections (p11), and object counting (p12).
- **Seeds:** 2026, 7331. **Resolutions:** 512², 768², 1024².
- 24 pairs per resolution, 72 pairs and 144 images in total.
- **Order:** ABBA per pair within each resolution block (pair i even: 8 then 4; odd: 4 then 8). Run position, start time and the gap since the previous run are recorded.
- **Cold runs:** p01, seed 42, both 8 and 4 at each resolution. That is 6 runs, each after 600 s idle, giving same-day cold pairs.

## Blind review
- `blind_stage.py` with one directory per resolution: `blind-A512` (rng 2909291), `blind-A768` (rng 2909292), `blind-A1024` (rng 2909293).
- **All three keys stay sealed until all three score files are frozen.**
- **Scoring per composite, in the directive's priority:**
  1. prompt adherence;
  2. composition / spatial relations / counts;
  3. visual quality (texture, detail, realism, lighting, artifacts).

  Overall preference is **lexicographic**: the first dimension that differs decides; if none differ, "=".
- **Failure-mode checklist per composite side**, marked when present: duplicate object · missing object · wrong count · wrong spatial relation · text error · softness · grain/grid · patch artifact · anatomical defect · structural distortion · under-denoising.

## Pass criteria per resolution (all must hold; FAST-gate criteria plus failure-mode rules)
1. **No text regression:** in p05 and p07 (4 pairs), bf16/N text is at least as correct as bf16/8 in every pair, or at most one pair is minor-worse with the other seed equal or better.
2. **No systematic artifact:** no failure-mode type appears in ≥ 2 bf16/N images more often than in the paired bf16/8 images, net of the same type in the 8-step arm.
3. **Preference balance:** 8-better ≤ N-better + 3 (of 24).
4. **No class-level failure:** no prompt class where 8 is better in both seeds on the same dimension, unless the difference is minor micro-detail only.
5. **Objective artifact guard:** no bf16/N image with `grid16` > 2.0, **or** it is also seen blind. For reference, in the probe all Turbo images had grid16 ≤ 1.62 and the rejected base-LoRA images 3.9–11.5.
6. **Operational:** rc = 0; bf16/N peak footprint ≤ bf16/8 + 0.1 GB; no attributable swap growth.
7. **Speed:** median paired denoise ratio N/8 ≤ 0.60 (N = 4), ≤ 0.70 (N = 5), ≤ 0.80 (N = 6).

**Verdicts (per resolution):**

| verdict | condition |
|---|---|
| **VALIDATED** | all criteria pass |
| **PROMISING** | criteria 1, 2, 5, 6 pass, but 3 or 4 fails narrowly: 8-better − N-better = 4–5, or a class-level micro-detail issue |
| **REJECTED** | criterion 1 or 2 fails, or 8-better − N-better ≥ 6 |
| **INCONCLUSIVE** | a blinding or technical problem makes the comparison unreliable |

## Sequencing after Stage A
- Stage B (N = 5) runs after Stage A's verdict. Stage C (N = 6) runs after Stage B, or earlier if A is rejected at some resolution, because the 6-step compromise then becomes the useful question.
- If N = 4 is VALIDATED at all three resolutions: a **confirmatory run** with a new prompt subset (12 prompts written *before* seeing Stage A results, stored in `confirm-prompts.json` at registration) × 1 fresh seed (4096) at 1024², 12 pairs blind.
- **No production change within this experiment.** A later, separate change could add an ULTRA profile, only at the resolutions that passed.
