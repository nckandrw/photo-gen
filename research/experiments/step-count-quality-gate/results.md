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

---

# Stage B results (bf16 + 8 vs bf16 + 5)

Protocol: `protocol-stageB.md` (inherits `protocol.md`), pre-registered in commit `d638f1b` before any Stage B image. Production is unchanged (REFERENCE, FAST, ULTRA at 512² only).

## Run integrity
- 147/147 runs rc = 0: 3 cold (5-step, p01 s42, each after 600 s idle) and 3 × 48 sustained (ABBA). Console: `stageB-console.log`.
- Blind: three directories (`blind-B512/768/1024`, rng 2909301–3). All three score sheets were frozen before any key was opened.
  - Frozen sha256: 512² `2e2ac624…`, 768² `6ea6b796…`, 1024² `7b34cd41…`.
  - Mapping: `blind-mapping-B.json`. Per-composite scores: `scores-B.csv`. Tallies: `blind-tallies-B.json`. Failure-mode counts per arm (computed by script from the frozen sheets): `failure-modes-B.json`.
- Per-run data: `benchmark-B.csv`. Summary: `metrics-summary-B.json`. Both produced by `stage_metrics.py`.

## Summary table
| resolution | blind (8-better / 5-better / ties) | quality verdict | cold wall 5 vs 8 | cold denoise 5 vs 8 | paired denoise ratio 5/8 (sustained, median) | paired wall ratio 5/8 | peak GB (5 / 8) | status |
|---|---|---|---:|---:|---:|---:|---|---|
| 512² | 1 / 0 / 23 | **VALIDATED** | 11.3 vs 15.6 s | 7.6 vs 11.5 s | 0.629 | 0.696 | 5.415 / 5.416 | validated; no production use (ULTRA bf16 + 4 is faster and already validated here) |
| 768² | 3 / 0 / 21 | **VALIDATED (literal rules; narrowest possible pass)** | 20.9 vs 30.4 s | 16.5 vs 26.0 s | 0.630 | 0.666 | 5.951 / 5.952 | validated, flagged borderline |
| 1024² | 0 / 0 / 24 | **VALIDATED** | 36.1 vs 54.4 s | 30.6 vs 49.1 s | 0.625 | 0.652 | 5.851 / 5.852 | validated |

**Baselines:**
- **Cold:** the 5-step runs are compared with the same-day Stage A cold 8-step runs (`results-A-cold.jsonl`), as pre-registered. Cold ratios 5/8 are: wall 0.73 / 0.69 / 0.66 and denoise 0.66 / 0.64 / 0.62 (512² / 768² / 1024²).
- **Sustained:** the paired ratios are within-pair (same prompt and seed, adjacent ABBA runs).
- **Per-step time** is unchanged between 5 and 8 steps (512² 2.04 vs 2.05 s; 768² 5.40 vs 5.35 s; 1024² 10.54 vs 10.55 s). The sustained per-step times are higher than cold, which is thermal state; this matches Stage A.

## Criteria per resolution
| # | criterion | 512² | 768² | 1024² |
|---|---|---|---|---|
| 1 | no text regression (p05/p07, 4 pairs) | PASS (4/4 equal) | **PASS (borderline):** p07-s6502 is minor-worse at 5 steps. The other seed and both p05 pairs are equal. | PASS (4/4 equal) |
| 2 | no systematic artifact (net ≥ 2 per type) | PASS (all nets 0) | PASS: nets are duplicate object 1, under-denoising 1, text error 1 (3 vs 2) | PASS (all nets 0) |
| 3 | 8-better ≤ 5-better + 3 | PASS (1 ≤ 3) | **PASS at equality (3 ≤ 3)** | PASS (0 ≤ 3) |
| 4 | no class-level failure | PASS | PASS (the three losses are three different classes, each on one seed: p03, p07, p09) | PASS |
| 5 | grid16 ≤ 2.0 | PASS (5-step max 1.30) | PASS (1.16) | PASS (1.11) |
| 6 | operational (rc, footprint ≤ +0.1 GB, swap) | PASS | PASS | PASS |
| 7 | speed (denoise ratio ≤ 0.70) | PASS (0.629) | PASS (0.630) | PASS (0.625) |

### 768²: why this is the narrowest possible pass (disclosed sensitivity)
- **Criterion 1 rests on one frozen "minor" classification.** The frozen line reads:
  `C07 p07-s6502 | L | = | L | L minor (R subtitle present once, readable, low-contrast faded tan) | none / text error (minor) | OVERALL L`, where R = 5 steps.
  - The pre-registered definition makes a defect minor when "the intended string is still present exactly once and readable, and the defect is glyph-level (stroke weight, kerning, a slightly misshapen letter…)". It lists "ghosted or partially formed text" as not minor.
  - A faded, low-contrast but fully formed subtitle is not named in either list.
  - **The frozen classification governs.** It was made blind and was not revisited after unblinding.
- **Criterion 3 passes at exact equality** (3 ≤ 0 + 3).
- **Criterion 2 passes per checklist type.**
  - C03 (p03-s6502) was frozen as *under-denoising* (ghosted, doubled text) on the 5-step side.
  - C21 (p09-s1729) was frozen as a solid *duplicate object* (a second red balloon) on the 5-step side.
  - Stage A's 1024² line pooled translucent ghosts (duplicate text, ghost plates). C21's balloon was frozen as solid, so it is not pooled, and the ghosting family at 768² is 1 vs 0.
- **Sensitivity:** had C07 been classified not-minor, or C21 pooled with ghosting, 768² would be **REJECTED**. PROMISING is not available: it requires criterion 3 or 4 to fail, and neither does.

## Stage-B-specific question: do 5 steps remove the 4-step under-denoising signatures?
| resolution | Stage A (4 steps) | Stage B (5 steps) | outcome |
|---|---|---|---|
| 1024² | ghost "SIQUIJOR", malformed "R", ghost plates | none; text exact in all 4 text pairs in both arms | **eliminated** |
| 768² | duplicated subtitle | one ghosted text overlay (p03), one faded subtitle (p07), one duplicate balloon (p09); all three losses are 5-step | **not eliminated; shifted** from the poster headline to the p03 glass text and the subtitle contrast |
| 512² | none | none (the single loss is a pen type, adherence) | none observed |

**Against the σ hypothesis:** 768² came out worse than 1024², although its last-step σ is lower (0.368 vs 0.441). That is the opposite of the resolution ordering predicted in Stage A.
- With 24 pairs per resolution and 0–3 decisions, the ordering may be noise.
- It weakens the claim that the final-step σ alone explains the failures.
- **Resolution-aware step selection** remains a hypothesis only (per the directive). It is not implemented, and this data does not support a simple σ threshold.

## Objective metrics
- **grid16 (5 / 8 arm max):** 512² 1.30 / 1.25; 768² 1.16 / 1.11; 1024² 1.11 / 1.19. There is no 16-px grid signature (the rejected base-LoRA path scored 3.9–11.5).
- **Laplacian variance, paired median ratio 5/8:** 0.996 / 0.951 / 0.980. Detail is essentially unchanged; Stage A's 4/8 ratio was 0.91–0.95.
- **Memory:** 5-step peak footprint equals 8-step within 0.001 GB at every size.
  - Swap growth: one 512² 5-step run showed +0.5 MB; all other runs 0. The single +0.5 MB is not attributable to the arm.

## Deviations (disclosed)
1. **grid16 re-implementation.** The Stage A grid16 code ran inline and was not preserved.
   - `stage_metrics.py` uses the best of 64 variants fitted against all 144 Stage A per-image values: mean |error| 0.086, max 0.46.
   - Stage A images were re-scored with the same code for a like-for-like comparison (`stageA_grid16_rescored` in `metrics-summary-B.json`).
   - Criterion 5 is unaffected: the worst 5-step value plus the worst fit error is 1.30 + 0.46 < 2.0.
   - Laplacian variance reproduces Stage A exactly.
2. **1024² sheet notes for C01–C08** were transcribed into the draft after a session context break. The judgements (all ties, with the C03/C05/C07 text observations) were made before the break, and the sheet was frozen before any key was opened.
3. **Single AI rater**, as in Stage A.

## Verdicts and consequences
- **512²: VALIDATED.** It has no practical use: ULTRA (bf16 + 4) is already validated at 512² and is faster.
- **768²: VALIDATED (literal rules; narrowest possible pass).** The mirror image of Stage A's 768² "narrowest possible failure".
- **1024²: VALIDATED** (0 / 0 / 24; the 4-step text failures are gone).
- **Production:** unchanged. The candidate change this enables is **FAST at 5 steps for 768² and 1024²** (≈ 0.63× denoise, cold wall 36 vs 54 s at 1024²). That is a separate production decision for the user. Given the 768² borderline, a text-focused confirmatory sample at 768² would be prudent before adopting it there.
- **Confirmatory run:** it was pre-registered for N = 4 only. It is not triggered automatically; it is offered as an option.
- **Stage C** (bf16 + 6, seeds 8086/5150) is **not started**; it is a separate decision. Stage B passing at all three sizes reduces its value: 6 steps would only matter if 768² at 5 steps is judged too borderline to adopt.

## Post-Stage-B production classification (owner decision, 2026-09-29; appended, Stage B text above unchanged)
- **bf16 + 5 @1024²** → ADOPTED as the **BALANCED** profile (`VALIDATED_COMBINATIONS[('bf16', 5)] = (1024²,)`).
- **bf16 + 5 @768²** → **PROMISING / CONFIRMATION PENDING.** The Stage B gate verdict (VALIDATED, narrowest possible pass) stands as recorded. The owner holds it out of production until a focused, pre-registered confirmation (`protocol-confirm768.md`) resolves it.
- **bf16 + 5 @512²** → EXPERIMENTAL: not useful for production, because ULTRA (bf16 + 4) is validated and faster there.
- **Stage C (6 steps)** → DEFERRED.

---

# 768² BALANCED confirmation results (bf16 + 5 vs bf16 + 8, 768² only)

Protocol: `protocol-confirm768.md`, pre-registered in commit `8149bf3` before any image. Production is unchanged during the run.

## Run integrity
- 64/64 runs rc = 0 (32 ABBA pairs; 16 prompts × seeds 3141/9091). 2026-09-29 19:49–20:34, on battery power (disclosed; no effect on the quality criteria). Console: `confirm768-console.log`.
- Blind: `blind-K768` (rng 2909311). Key sha256 `d66b6ab7…`. Frozen scores sha256 `864c590f…`, frozen before unblinding.
- Files: `key-K768-unblinded.json`, `blind-K768-summary.json` (mapping, tallies, failure modes), `benchmark-K768.csv`, `metrics-summary-K768.json`.

## Blind result
**8-better 3 / 5-better 1 / ties 28.**

| composite | pair | winner | decisive dimension | frozen note |
|---|---|---|---|---|
| C03 | c03-s3141 | 8 | visual (text) | both arms rendered the subtitle "Live at the Harbor" **twice**; the 5-step image also had faded, partially formed letters ("Liv") → **not minor** |
| C10 | c10-s3141 | 8 | composition | 5-step showed 3 books instead of 4 (wrong count) |
| C19 | c03-s9091 | 8 | visual (text) | 5-step: a white blob inside the "D" of TIDE, word intact → **minor** |
| C22 | c06-s9091 | 5 | visual (text) | 8-step window decal added a misspelled extra word "BAKEPY" → **not minor** |

## Criteria
| # | criterion | result |
|---|---|---|
| 1a | not-minor text losses: 5-worse ≤ 8-worse (16 text pairs) | **PASS at equality** (1 ≤ 1: C03 vs C22) |
| 1b | all text losses: 5-worse ≤ 8-worse + 2 | PASS (2 ≤ 3) |
| 2 | no type with net ≥ 2; under-denoising family net ≤ 1 | PASS. Per type: wrong count 2/1, under-denoising 1/0, text error 2/2, wrong spatial 2/2. Pooled family, per the pre-registered definition (doubled/faded text, ghost/duplicate objects): the 5-step and 8-step C03 images **both** have doubled text → 1 vs 1, net 0 (net 1 counting tags only; passes either way) |
| 3 | 8-better ≤ 5-better + 4 | PASS (3 ≤ 5) |
| 4 | no class-level failure | **FAIL:** prompt c03 (poster subtitle) is 8-better in **both** seeds on the same dimension (visual/text). The micro-detail exception does not apply, because C03 was frozen as not minor |
| 5 | grid16 ≤ 2.0 | PASS (5-step max 1.15) |
| 6 | operational | PASS (rc 64/64; peak 5.951 vs 5.959 GB; swap growth 0) |

## Verdict: **NOT CONFIRMED** (criterion 4; this outcome is not covered by a pre-registered verdict row)
- **CONFIRMED** requires every criterion to pass.
- **AMBIGUOUS** covers a *narrow* criterion 4 failure, defined as a class-level micro-detail issue. C03 is not micro-detail.
- **FAILED** requires criterion 1 or 2 to fail, or a margin ≥ 6. Neither occurred.
- The label is therefore stated as-is rather than stretched to fit either row. **Consequence (the same under both rows):** 768² stays FAST, BALANCED stays 1024² only, and nothing runs automatically.

**Sensitivity (frozen calls govern; neither is revisited):**
- Had C19's glyph blob been scored a tie → no class-level failure → **CONFIRMED**.
- Had C22's "BAKEPY" decal been treated as incidental text (as the illegible decals in C06 were) → criterion 1a fails (1 vs 0) → **FAILED**.
- **768² at 5 steps remains borderline.** This sample did not demonstrate robustness.

## Findings
- **The poster-subtitle failure recurred** on a fresh prompt and fresh seeds (c03, compare Stage B's p07). At 768², the small-subtitle-under-a-large-headline case is where 5 steps is weakest. In C03 the 8-step arm also doubled the subtitle, so this prompt is hard for both arms.
- 3 of the 4 decisions favour 8 steps (Stage B: 3 of 3).
- Every other text case (glass, label through glass, neon, chalk, wine label, book title) was exact in both arms in all 11 remaining text pairs that were ties.
- **Pooled Stage B + confirmation, 768² (descriptive only, as pre-registered):** 8-better 6 / 5-better 1 / ties 49.
- **Speed (sustained, paired):** denoise ratio 5/8 0.628; wall ratio 0.665. Laplacian-variance ratio 0.933 (Stage B 0.951; descriptive).

## Disclosed limitations
- Single AI rater, who had seen Stage B's 768² failure pattern (disclosed in the protocol).
- The run was on battery power. Timings are sustained and paired, so ratios are within-run.

## Consequences
- **Production is unchanged:** REFERENCE, FAST (all sizes), BALANCED bf16 + 5 at **1024² only**, ULTRA at 512² only. 768² stays FAST.
- **Per directive §17:** whether a dedicated **6-step gate at 768²** is worth running is a decision for the user. It is **not started automatically.**
