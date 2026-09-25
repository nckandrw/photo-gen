# FAST resolution gates: REFERENCE (fp32 + 9) vs FAST (bf16 + 8), direct, at 512², 768² (and 1024²)

Status: **PROTOCOL PRE-REGISTERED 2026-09-25 (file written before chain P3A was launched at 14:06:41; no gate image existed yet).** Results are appended below; the protocol is not edited after generation.

## Question
At each resolution, does FAST (bf16, 8 steps = 8 NFE) show a systematic or material quality regression **directly against** REFERENCE (fp32, 9 steps = 9 NFE)?

- Pixel identity is not required.
- Both arms use mflux's default schedule, so the gate tests production behaviour as it is. The schedule question is audited separately (`sigma-schedule-audit.md`).

## Generation
- Production worker via `prod_runner.py`: transformer release on, `--low-ram`, q4 @ d2d30500, mflux default scheduler.
- Arms: **A = REFERENCE** (fp32/9), **B = FAST** (bf16/8).
- ABBA per pair (pair i even: A then B; odd: B then A), back to back, with the 1 Hz monitor.
- Suite: the established 12 prompts (`prompts.json`). They cover every class the directive lists:
  - photorealism: p01, p02, p10;
  - text: p05, p07 (and p03's text-through-glass);
  - hands: p03;
  - object layout: p04, p12;
  - fine texture: p08, p10;
  - difficult composition: p09, p11;
  - Philippine/local scenes: p06 Cebu, p09 Manila.
- Seeds **1618 and 8128**: never used in this project, and disjoint from the sigma-audit seeds (2718, 31415), so no gate image has been seen by the rater.

| gate | res | pairs | notes |
|---|---|---:|---|
| G512 | 512² | 24 | directive §3 |
| G768 | 768² | 24 | directive §4 |
| G1024-direct | 1024² | 24 | **added under the Improvement Clause** (`phase3-plan.md`). The existing 1024² validation is a chain of two gates, not a direct comparison. |

## Recorded
- **Per run:** wall, denoise, VAE, peak footprint, swap Δ, pressure max, pixel hash.
- **Per pair:** PSNR/SSIM (descriptive), paired denoise and wall ratios.
- **Blinded:** `blind_stage.py` (one directory per gate), recording per composite:
  - quality (overall preference L / R / =);
  - text correctness (where applicable);
  - composition;
  - fine texture/detail;
  - prompt adherence;
  - artifact type, with notes.

## Pass criteria (ALL must hold, per gate, 24 pairs)
1. **No text regression:** in p05 and p07 (4 pairs), FAST text is at least as correct as REFERENCE in every pair, or at most one pair is minor-worse with the other seed equal or better.
2. **No systematic artifact:** no artifact type appears in ≥2 FAST images that is absent from their REFERENCE counterparts.
3. **Preference balance:** REFERENCE-better (overall) ≤ FAST-better + 3 (of 24). This is the 8-step gate's margin; the direct comparison combines both changes, so the looser of the two prior margins is used.
4. **No class-level failure:** no prompt class where REFERENCE is better in both seeds on the *same* dimension, unless the difference is minor micro-detail only.
5. **Operational:** rc = 0 for all runs; FAST peak footprint ≤ REFERENCE peak footprint + 0.1 GB; no swap growth > 16 MB attributable to FAST.

## Verdicts
- **VALIDATED:** all criteria pass. `GATED_STEPS` may add the resolution, as a separate, recorded code change.
- **EXPERIMENTAL:** fails only criterion 3 or 4 on micro-detail, with no text or artifact failure. The resolution stays behind `allow_experimental`, and what degraded is recorded.
- **REJECTED:** a text regression, a systematic artifact, or an operational failure.

## Limits declared in advance
- Single rater (Claude), 24 pairs per gate, 2 seeds.
- Timings are sustained, back-to-back ABBA. They are reported as paired ratios, not as absolute cold figures. Cold figures come from the separate cold runs (`PERFORMANCE-MAP.md`).

## Results
(appended after generation and unblinding)

### G512 (512², 24 pairs, seeds 1618 + 8128). Generated 16:22–17:11 with two interruptions.
**Interruptions (disclosed):**
- A planned pause at 16:19, before the block, for guide validation.
- An **unplanned stop at ~16:53** (incident: process-group cleanup; see `phase3-chainA-console.log`). The G512 remainder resumed at 17:07.
- Pair p08-s8128 straddles the stop, so its timing is not comparable. Quality is unaffected (deterministic).

**Run integrity:** 48/48 rc = 0; `compile_calls` = 1.

**Blinded review** (`fastgate/blind-512/`):
- key sha256 `fc3c34ce…`;
- frozen scores `04faa272…`;
- unblinded key saved as `fastgate/key-512-unblinded.json`.

**Tally: REFERENCE better 0 · FAST better 0 · ties 24.**
- p05 ("QWEN IMAGE 2.1") and p07 ("VISIT SIQUIJOR" / "Island of Fire") are exact in both arms, both seeds.
- p03 text-through-glass is gibberish or absent in both arms.
- p12 fails identically in both arms (3 plates instead of 2).

**Objective (FAST vs REFERENCE, `fastgate/summary-512.json`):**
| metric | value |
|---|---|
| denoise ratio FAST/REF | median **0.658** (sustained; cold single-pair figure 11.4/17.4 = 0.655) |
| wall ratio | median 0.699 |
| PSNR | median 26.7 dB |
| SSIM | median 0.928 |
| peak footprint | FAST max **5.43 GB** vs REFERENCE max 5.96 GB |
| pressure max | 2 in both arms |

**Swap (disclosed literal deviation from criterion 5):**
- System-wide swap grew by more than 16 MB in 10 runs between 16:22 and 16:50: 6 FAST (max 1,092 MB) and 4 REFERENCE (max 2,228 MB).
- Growth occurred in both arms and coincided with inflated wall times (up to 106 s vs ~45 s). The workers' own footprints were normal.
- During that window the machine also ran Safari (the documentation check) and large `du`/`find` scans (a cleanup inventory).
- Judged **not attributable to FAST**: FAST's footprint is 0.52 GB *lower*, and the largest growth was in a REFERENCE run.
- The swap numbers are recorded, not hidden. Timing ratios from those pairs are noisy; the median is robust.

**Criteria**
| # | criterion | result |
|---|---|---|
| 1 | no text regression | **PASS** (4/4 equal) |
| 2 | no systematic FAST artifact | **PASS** (none) |
| 3 | REF-better ≤ FAST-better + 3 | **PASS** (0 ≤ 3) |
| 4 | no class-level failure | **PASS** |
| 5 | operational | **PASS**: rc = 0; footprint 5.43 ≤ 5.96 + 0.1. The swap deviation is disclosed above. |

**Verdict: G512 VALIDATED.** FAST (bf16 + 8) shows no systematic or material quality regression directly against REFERENCE (fp32 + 9) at 512² on this 24-pair set. Limits: single AI rater, fast review (see `sigma-schedule-audit.md` §3.4 disclosure), 24 pairs.
**Production consequence (per protocol):** adding 512² to `GATED_STEPS` is a separate, recorded code change. It is deferred until G768 and G1024 are reviewed, so that the production matrix changes once, with tests.

### G768 (768², 24 pairs, seeds 1618 + 8128). Generated 17:11–18:08, uninterrupted.
**Run integrity:** 48/48 rc = 0; `compile_calls` = 1. Swap growth 0 in every run; pressure max 1 (normal).

**Blinded review** (`fastgate/blind-768/`):
- key sha256 `c518b53e…`;
- frozen scores `c58952ab…`.

| composite | pair | preference (blind) | winner after unblind |
|---|---|---|---|
| C09 | p09-s1618 (Manila market) | R: the L image had a **duplicated red balloon** | **REFERENCE** (the FAST image had the artifact) |
| C15 | p03-s8128 (hands + glass) | R (minor): text through the glass visible (gibberish) vs barely visible in L | **REFERENCE** |
| other 22 | — | = | tie |

**Tally: REFERENCE better 2 · FAST better 0 · ties 22.**
- p05 and p07 text is exact in both arms, both seeds.
- p12 counts are correct in both arms (3 cups + 2 plates).

**Objective (FAST vs REFERENCE)**
| metric | value |
|---|---|
| denoise ratio | median **0.647** (0.59–0.79) |
| wall ratio | median 0.669 |
| PSNR / SSIM | median 28.0 dB / 0.954 |
| peak footprint | FAST 5.95 GB vs REFERENCE 6.34 GB |

**Criteria**
| # | criterion | result |
|---|---|---|
| 1 | no text regression (p05/p07) | **PASS** (4/4 equal). C15 concerns p03's text-through-glass: gibberish in both arms, differing only in visibility. Minor, and outside criterion 1's scope, but disclosed. |
| 2 | no systematic FAST artifact (≥ 2 images) | **PASS**: one FAST image had a duplicated object. The same failure class appeared in bf16/8 images at 512² in the sigma audit, but also in REFERENCE-precision images in earlier gates. |
| 3 | REF-better ≤ FAST-better + 3 | **PASS** (2 ≤ 3) |
| 4 | no class-level failure | **PASS**: the two REFERENCE wins are in different classes and seeds |
| 5 | operational | **PASS** (rc = 0; footprint 5.95 ≤ 6.34 + 0.1; no swap growth) |

**Verdict: G768 VALIDATED**, with a disclosed directional lean: every non-tie favoured REFERENCE (2–0).
- This is within the pre-registered margin, and it is exactly the kind of small effect the protocol's +3 margin accepts.
- It is noted so it can be tracked across gates, not explained away.

### G1024-direct (1024², 24 pairs, seeds 1618 + 8128). Generated 18:08–19:47, uninterrupted. Added under the Improvement Clause.
**Run integrity:** 48/48 rc = 0; `compile_calls` = 1; pressure max 1; swap growth ≤ 1.7 MB.

**Blinded review** (`fastgate/blind-1024/`):
- key sha256 `c5acc9cf…`;
- frozen scores `10ef4e33…`.

| composite | pair | preference (blind) | winner after unblind |
|---|---|---|---|
| C04 | p04-s1618 (desk, five objects) | L: the R image had **two pens** (the prompt asks for one) | **FAST** (the REFERENCE image had the duplicated object) |
| other 23 | — | = | tie |

**Tally: REFERENCE better 0 · FAST better 1 · ties 23.**
- Text exact in both arms for p05 and p07, both seeds.
- p09-s1618 has two balloons in *both* arms, an identical failure.
- p12 fails identically in both arms (3 plates).

**Objective:** denoise ratio FAST/REF median **0.622** (sustained; 88.8 vs 142.4 s); wall ratio 0.639; PSNR 26.6 dB; SSIM 0.945; peak footprint FAST 5.85 vs REF 6.58 GB.

**Criteria:** 1 PASS · 2 PASS · 3 PASS (0 ≤ 4) · 4 PASS · 5 PASS.

**Verdict: G1024 VALIDATED DIRECTLY.** The 1024² FAST cell no longer rests only on the chain of two gates.

## Summary across the three direct gates (72 pairs)
| gate | REF better | FAST better | ties | verdict |
|---|---:|---:|---:|---|
| G512 | 0 | 0 | 24 | VALIDATED |
| G768 | 2 | 0 | 22 | VALIDATED (lean toward REF, within margin) |
| G1024 | 0 | 1 | 23 | VALIDATED |
| **pooled** | **2** | **1** | **69** | no directional effect |

- All five non-ties across 72 pairs were object-level failures (duplicated or inconsistent objects) or text-visibility differences. They are split between the arms.
- The G768 lean does not persist in the pooled data.

**Final profile matrix**
| | REFERENCE fp32 + 9 | FAST bf16 + 8 |
|---|---|---|
| 512² | REFERENCE | **VALIDATED** (direct gate) |
| 768² | REFERENCE | **VALIDATED** (direct gate) |
| 1024² | REFERENCE | **VALIDATED** (direct gate + the earlier chain) |

**Limits (all gates):** single AI rater with a fast review, 24 pairs per gate, and two seeds, so a small effect in either direction is not excluded.
