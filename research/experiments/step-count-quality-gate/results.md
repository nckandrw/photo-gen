# Step-count quality gate: Stage A results (bf16 + 8 vs bf16 + 4)

Protocol: `protocol.md`, pre-registered in commit `f49604c` before any image. Production is unchanged.

## Run integrity
- 150/150 runs rc = 0 (6 cold + 3 × 48 sustained), 2026-09-29 10:09–12:47, uninterrupted.
- Cold 8-step runs reproduce the production FAST hashes: 512² `0b9cc20a`, 768² `20ff9e2c`, 1024² `7b45cfbe`.
- Blind:
  - three directories, keys sealed until all three score files were frozen;
  - frozen sha256: 512² `d5420575…`, 768² `c692a300…`, 1024² `597ed1b1…`;
  - mapping in `blind-mapping.json`, per-composite scores in `scores.csv`.

## Summary table
| resolution | steps | blind (8-better / 4-better / ties) | quality verdict | wall (cold) | denoise (cold) | paired denoise ratio 4/8 (sustained) | peak GB | status |
|---|---:|---|---|---:|---:|---:|---:|---|
| 512² | 4 | 1 / 0 / 23 | **VALIDATED** | 9.5 s | 5.9 s | 0.509 | 5.41 | CANDIDATE → validated at 512² (no production change yet) |
| 768² | 4 | 1 / 0 / 23 | **REJECTED** (literal criterion 1; narrowest possible failure) | 17.5 s | 13.2 s | 0.503 | 5.92 | EXPERIMENTAL |
| 1024² | 4 | 3 / 1 / 20 | **REJECTED** (criteria 1 and 4: text) | 30.0 s | 24.6 s | 0.502 | 5.84 | EXPERIMENTAL |
| 512²–1024² | 5 | — | not yet tested (Stage B) | | | | | PENDING |
| 512²–1024² | 6 | — | not yet tested (Stage C) | | | | | PENDING |

**Context (unchanged, cold, same day):**
- FAST bf16 + 8: 512² 15.6 s wall / 11.5 s denoise; 768² 30.4 / 26.0 s; 1024² 54.4 / 49.1 s.
- REFERENCE fp32 + 9 (earlier cold runs): 512² 21.2 / 17.4 s; 768² 44.7 / 40.4 s; 1024² 83.4 / 78.3 s.

Paired wall ratios 4/8 (sustained): 512² 0.594 · 768² 0.551 · 1024² 0.540. Per-step time is unchanged between 4 and 8 steps, so the saving is exactly the step count.

## Criteria per resolution
| # | criterion | 512² | 768² | 1024² |
|---|---|---|---|---|
| 1 | no text regression (p05/p07, 4 pairs) | **PASS** (4/4 equal) | **FAIL (borderline):** p07-s7331, the 4-step image duplicates the subtitle "Island of Fire"; the other seed is equal. The protocol allows one *minor*-worse pair. A whole duplicated phrase is judged **not minor**. | **FAIL:** both p07 pairs are worse at 4 steps (s2026: a ghosted, semi-transparent duplicate "SIQUIJOR"; s7331: a malformed final letter) |
| 2 | no systematic artifact (net ≥ 2) | PASS (none) | PASS (1 text duplicate) | PASS narrowly: ghosting/under-denoising in 2 four-step images (duplicate text, ghost plates) vs 1 eight-step image (ghost glasses) → net 1 |
| 3 | 8-better ≤ 4-better + 3 | PASS (1 ≤ 3) | PASS (1 ≤ 3) | PASS (3 ≤ 4) |
| 4 | no class-level failure | PASS | PASS | **FAIL:** the text class (p07) is 8-better in both seeds on text |
| 5 | grid16 ≤ 2.0 unless seen blind | PASS (4-step max 1.33) | PASS (1.62) | PASS (1.24) |
| 6 | operational (rc, footprint ≤ +0.1 GB, swap) | PASS | PASS | PASS |
| 7 | speed (denoise ratio ≤ 0.60) | PASS (0.509) | PASS (0.503) | PASS (0.502) |

## What the 4-step failures look like
Every blind loss for 4 steps was an **under-denoising signature**: a ghosted duplicate or partially formed object or glyph.
- p07 at 1024²: a translucent second "SIQUIJOR"; a malformed "R".
- p12 at 1024²: faint ghost plates hovering above the cups.
- p07 at 768²: the subtitle rendered twice.

**Not observed:** the 16-px grid artifact of the rejected base-LoRA path (Turbo 4-step grid16 ≤ 1.62 everywhere; objective detail 0.91–0.95 of 8-step by Laplacian variance). There was also no softness, no anatomy defects, and no count regressions that 8-step didn't share.

**Why resolution matters (hypothesis, consistent with the pre-registered σ analysis):** at 1024², the 4-step schedule takes its final step from σ = 0.51, a large jump to a clean image. That leaves structures committed at σ ≈ 0.76 partially resolved. At 512² the final step starts at σ = 0.39 and the defects did not appear.

## Reconciling with the 4-step probe control (discrepancy clause)
- The probe's control (1024², seeds 4242/6174) found Turbo 4 vs 8 at **2 / 3 / 19 ties**. This gate (1024², seeds 2026/7331) found **3 / 1 / 20** in favour of 8 steps, with the text class failing.
- **Pooled 1024², 48 pairs:** 8-better 5, 4-better 4, ties 39. The overall preference is balanced, but the **4-step losses concentrate on text and ghosting.** In the probe, both arms also had text errors (8-step duplicated "IMAGE"; 4-step garbled a line).
- **Interpretation:** at 1024², 4-step text rendering is fragile. The earlier single comparison was encouraging but did not generalise to fresh seeds on the pre-registered text criterion. The pre-registered gate is the stronger evidence, and it governs.

## Verdicts and consequences
- **512²: VALIDATED.** bf16 + 4 is blind-equivalent to FAST at 0.51× denoise (cold wall 9.5 vs 15.6 s).
- **768²: REJECTED** on a single text pair under the literal pre-registered rule. It is flagged as the **narrowest possible failure**. A revisit needs new evidence (e.g. a larger text-focused sample), not a re-reading of this one.
- **1024²: REJECTED** (text class-level failure).
- **Production:** unchanged. An ULTRA profile (bf16 + 4) could be defined **at 512² only**, as a separate production change that needs the user's approval.
- **Confirmatory run:** not triggered (4 steps did not pass at all three resolutions).

**Next (per protocol):**
- **Stage B** (bf16 + 5, seeds 6502/1729) and **Stage C** (bf16 + 6, seeds 8086/5150).
- At 768²/1024², 5 or 6 steps is now the useful question: the last-step σ drops (1024²: 0.51 → 0.44 at N = 5 → 0.39 at N = 6; 768²: 0.44 → 0.37 → 0.32), which may remove the ghosting at ≈ 0.63–0.75× denoise.
