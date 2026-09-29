# 768² BALANCED confirmation: bf16 + 5 vs bf16 + 8 (PRE-REGISTERED before any confirmation image)

Written 2026-09-29, after Stage B and before any confirmation image existed. Committed before generation. This text is not edited after generation; deviations are appended to `results.md`.

## Question (the only one)
Is **bf16 + 5 NFE at 768²** robust enough to be treated as a production-quality operating point, i.e. added to the BALANCED profile?

This experiment decides nothing about 4 or 6 steps, other resolutions, models, pruning, quantization or LoRAs.

## Why a confirmation is needed (Stage B facts, unchanged)
- **Stage B 768²:** 8-better 3 / 5-better 0 / ties 21. Every non-tie favoured 8 steps (p03 ghosted text, p07 faded subtitle, p09 duplicate balloon).
- **It passed by the narrowest possible margin:**
  - criterion 3 held at equality;
  - criterion 1 held only because the faded subtitle was frozen as "minor".
  - A different classification of that one defect, or pooling the duplicate balloon with ghosting, would have REJECTED it.
- **Owner decision (directive "PHOTO-GEN NEXT PASS", 2026-09-29):** 768² bf16 + 5 is held as **PROMISING / CONFIRMATION PENDING**, not production-validated. This is a production-status decision; the Stage B gate verdict itself stays as recorded.

## Fixed configuration
Identical to Stage B, except for prompts and seeds.
- **Model and runtime:** Z-Image-Turbo q4 @ d2d30500, mflux 0.20.0 / MLX 0.32.2.
- **Worker:** the production worker via `prod_runner.py`, with `--low-ram`, bf16, transformer release, guidance 0.
- **Scheduler:** the validated mflux default (`linear`, resolution-dependent shift). At 5 steps, 768² takes its last step from σ = 0.368.
- **Arms:** A = bf16 + 8 (FAST), B = bf16 + 5. **768² only.**

## Design
- **Prompts:** `prompts-confirm768.json`, 16 prompts, weighted toward the Stage B failure modes but not purely adversarial.

  | group | prompts | targets |
  |---|---|---|
  | text | c01–c08 | text on glass (c01), text on a label seen through glass (c02), headline + small subtitle (c03, c06, c07), title (c04), neon (c05), chalk (c08) |
  | counting / duplicate-object risk | c09–c12 | exact counts, a single kite (the Stage B duplicate-balloon mode) |
  | ordinary controls | c13–c16 | portrait placement, a busy street scene, fur detail, low light |

  Eight prompts (c04, c05, c09, c10, c13–c16) are copied verbatim from `confirm-prompts.json`. That file was written before Stage A results and never generated. The other eight are new.
- **Seeds:** **3141, 9091**. Checked unused by any research JSON/JSONL/CSV/MD (2718 and 1618 were rejected as already used).
- **Size:** 16 × 2 = **32 pairs, 64 images**. Order is ABBA per pair (`jobs-K768.json`). Sustained runs only.
  - No cold runs: speed at 768² is already measured (Stage B cold 20.9 vs 30.4 s; paired denoise 0.630). Paired ratios are recorded descriptively.
  - Estimated ≈ 45 min, against Stage B's ≈ 2.5 h.
- **Blind:** `blind_stage.py`, one directory `blind-K768` (rng **2909311**). The key stays sealed until the score file is frozen.
  - Scoring is lexicographic: adherence > composition > visual quality.
  - Same failure-mode checklist as Stage A/B, plus the family tag defined below.

## Sample-size rationale
- **Coverage:** the text criterion rests on **16 text pairs** (Stage B had 4) and the duplicate/count risk on 8 pairs, at about 30% of Stage B's machine time.
- **What the result can tell apart:**
  - **Robust pass:** few or no 5-step losses, text parity. Stage B's 3/24 then looks like noise.
  - **Likely failure:** repeated under-denoising signatures or net text regressions. Stage B's pattern replicates at 4× the text coverage.
  - **Continued ambiguity:** a loss rate like Stage B's (≈ 1 in 8 pairs, all one-sided) would give about 4/0/28. That lands on the criterion 3 boundary, which is a truthful "still borderline" answer rather than a manufactured pass.
- **Limit:** 32 pairs cannot distinguish a small true deficit (e.g. 5% of pairs) from zero. The criteria below target *material or systematic* loss, as in every earlier gate.

## Improvement Clause (invoked before any image)
| | |
|---|---|
| **Original** (Stage B rules) | Criterion 1: p05/p07 only (4 pairs); "at most one pair minor-worse". "Minor" = present exactly once, readable, glyph-level defect. Low contrast / fading was not named. Criterion 2 counts each checklist type separately. Criterion 3: 8-better ≤ N-better + 3 of 24. |
| **Proposed** | **(a)** The text criterion covers all 8 text prompts (16 pairs). **(b)** Faded, low-contrast, semi-transparent or doubled text elements are explicitly **not minor** (they count as "partially formed"). **(c)** An **under-denoising family** is counted pooled, in addition to per-type counts: ghosted/doubled text, faded/partially formed text or objects, ghost objects, duplicate objects. **(d)** Preference balance is scaled to 32 pairs: 8-better ≤ 5-better + 4. |
| **Evidence** | Stage B's 768² pass hinged on exactly the two ambiguities that (b) and (c) settle: the faded subtitle, and whether the solid duplicate balloon belongs with ghosting. |
| **Why better** | A confirmation should close the loopholes that made the original result borderline, not reuse them. (b) and (c) make the gate *stricter* in the direction of the observed failure modes; (a) raises text coverage 4×; (d) keeps Stage B's ratio (3/24 = 12.5% → 4/32). |
| **Expected information gain** | A pass is now a pass under the strict reading; a fail identifies which failure mode replicated. Either result is decision-ready. |
| **What it replaces** | Stage B criteria 1–3 for this confirmation only. Stage A/B verdicts are unchanged. |

## Pass criteria (all must hold)
1. **Text.** Over the 16 text pairs (c01–c08 × 2 seeds):
   - the number of pairs where the 5-step text is worse by a *not-minor* defect is ≤ the number where the 8-step text is worse by a not-minor defect; **and**
   - total 5-worse text pairs ≤ total 8-worse text pairs + 2.
2. **Artifacts.**
   - No checklist type appears in the 5-step arm ≥ 2 more times than in the 8-step arm (net ≥ 2 fails).
   - **And** the pooled under-denoising family has net (5 − 8) ≤ 1.
3. **Preference balance.** 8-better ≤ 5-better + 4 (of 32).
4. **No class-level failure.** No prompt where 8 steps is better in both seeds on the same dimension, unless the difference is minor micro-detail only.
5. **Objective guard.** No 5-step image with grid16 > 2.0 (`stage_metrics.py` implementation), unless also seen blind.
6. **Operational.** rc = 0 for all 64 runs; 5-step peak footprint ≤ 8-step + 0.1 GB; no attributable swap growth.

## Verdicts and consequences (fixed now)
| verdict | condition | consequence |
|---|---|---|
| **CONFIRMED** | all criteria pass | BALANCED becomes bf16 + 5 at **768² + 1024²** (a separate production change with tests and docs) |
| **AMBIGUOUS** | criteria 1, 2, 5, 6 pass, but 3 or 4 fails narrowly (8-better − 5-better = 5, or a class-level micro-detail issue) | 768² stays FAST; report; no further automatic run |
| **FAILED** | criterion 1 or 2 fails, or 8-better − 5-better ≥ 6 | 768² stays FAST; a 6-step gate at 768² may be proposed to the user, **not started automatically** |
| **INCONCLUSIVE** | a blinding or technical problem makes the comparison unreliable | report; no production change |

**No pooling with Stage B.** The confirmation is judged on its own sheet. Stage B + confirmation totals are reported descriptively only.

## Disclosed limitations (before running)
- **Single AI rater.** The rater has seen Stage B's 768² failure pattern. Fresh prompts, fresh seeds and blinding limit this, but the rater's attention is primed toward text and duplicates in *both* arms.
- **Detail difference:** the Stage B paired Laplacian-variance ratio 5/8 at 768² was 0.95. A subtle detail difference could make arms partially recognisable; the rater never learns which label is which before freezing.
- **No production change during the confirmation:** REFERENCE, FAST, ULTRA 512² and BALANCED 1024² are unchanged.
