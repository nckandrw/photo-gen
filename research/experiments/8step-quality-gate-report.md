# 8-step blinded quality gate: bf16 + 9 steps (A) vs bf16 + 8 steps (B)

## Pre-registered protocol (written 2026-09-25 ~05:30, BEFORE any gate composite was viewed)

**Question.** Can the fast production path reduce denoising from 9 to 8 steps without a systematic or material quality regression?
- Not compared against fp32.
- Context (scheduler-nfe-note.md): in mflux, 9 steps = 9 NFE. 8 steps @1024² ≈ the official Turbo 8-NFE sigma schedule (e^μ 3.16 vs static 3.0).

**Generation**
- Production worker via `prod_runner.py`: `release_transformer` on, bf16, 1024², `--low-ram`, mflux default scheduler.
- Arm order alternates per pair (9→8, then 8→9). Output filenames carry the arm but are never viewed; the rater sees only blinded composites.
- Suite: the established 12-prompt suite (`prompts.json`) covers every class the directive lists:
  - photoreal object (p01), portrait (p02), hands + glass/transparency (p03);
  - multi-object layout + spatial relations (p04), neon/signage text (p05), Cebu/Philippine environment (p06);
  - multi-word text (p07), fine materials (p08), complex prompt adherence (p09);
  - fine detail/animal (p10), low light/reflections (p11), counting/attributes (p12).

**Seeds and a disclosed contamination (D5)**
- Seed 42's 8- and 9-step images are deterministic and identical to the E03 step-sweep outputs, which the rater (Claude) already viewed, labelled, as 400 px contact sheets. Confirmed by hash: p01-s42 8-step = 7b45cfbe… in both.
- **Primary evidence:** seeds **7 and 1234** (24 pairs, never viewed by the rater).
- **Secondary:** seed 42 (12 pairs). Scored under the same blinding but reported separately and not counted toward the pass criteria.

**Blinding:** `blind_stage.py` (BLIND-PROTOCOL.md)
- One blind directory per seed group, each with its own RNG seed: `gate8/blind-primary` (seed 250925) and `gate8/blind-secondary` (seed 250926).
- The key is written atomically before the composites; scores are frozen and hashed before `unblind`.
- Composite order is the pairs-file order (prompt/seed), which reveals nothing about arms.

**Recorded per pair:** prompt, seed, arm identity (after unblinding), steps, wall, denoise, VAE, peak footprint, pixel hash; plus rater judgements on text correctness, composition, prompt adherence, fine detail, artifact type and overall preference (`L` / `R` / `=`), with notes.

**Pass criteria (ALL must hold, primary 24 pairs)**
1. **No text regression:** in p05 and p07 (4 pairs), the 8-step text is at least as correct as the 9-step text in every pair, or at most one pair is minor-worse with the other seed equal or better.
2. **No systematic artifact:** no artifact type appears in ≥2 of the 8-step images that is absent from their 9-step counterparts.
3. **Preference balance:** 9-better (overall) ≤ 8-better + 3 (of 24). This is slightly looser than the bf16 gate's +2 because two steps fewer is expected to cost *some* micro-detail. "Material" means a systematic difference, not an isolated preference.
4. **No class-level failure:** no prompt class with 9-better in both of its seeds on the *same* dimension, unless the difference is minor micro-detail only.
5. **Operational:** rc=0 for all runs; peak footprint within +0.1 GB of 9 steps.

**Failure path:** keep bf16 + 9 steps as FAST, and record exactly what degraded (text / micro-detail / composition / adherence / artifacts / which classes).

## Results (review 2026-09-25 07:11–07:15, scores frozen per MANIFEST.json; data in `gate8/`)

### Run integrity
- 72/72 runs rc=0 on the production worker (transformer release on), 05:23–07:10.
- Determinism cross-check: p01-s42 at 8 steps = 7b45cfbe…, identical to the earlier step-sweep output.
- 9-step p01-s42 = 11b19277…, the gated bf16 reference.

### Operational (all 36 pairs, same session, ABBA)
| | 9 steps | 8 steps |
|---|---:|---:|
| denoise median (s) | 87.1 | 77.0 |
| wall median (s) | 93.3 | 83.2 |
| per-pair denoise ratio 8/9 | — | median **0.887** (range 0.876–1.053*) |
| peak footprint max (GB) | 5.854 | 5.852 |
| memory pressure max | 2 | 2 |
| swap growth max (MB) | 0 | 1.8 (one run, disclosed) |

\* The ratio exceeds 1 only for p01-s42, the first pair of the block (9-step run on a cooler chip at 05:23, cold→warm transition). The median is the robust figure, and it matches the per-step prediction (8/9 = 0.889).

### Blinded review, PRIMARY (seeds 7 + 1234, 24 pairs)
- Frozen scores: `gate8/blind-primary/SCORES-FROZEN.txt`, sha256 2aa7a681…
- **Tally:** 9-step better 0, 8-step better 1 (C08 p08-s7: marginally more copper scratch detail; minor, detail only), ties 23.
- **Text:**
  - p05 "QWEN IMAGE 2.1" exact in both arms, both seeds.
  - p07 "VISIT SIQUIJOR" / "Island of Fire" exact once in both arms, both seeds.
  - p03 text-through-glass: gibberish in both arms (a model limitation).
- **Counting:** p12 fails identically in both arms (3 cups + 3 plates vs the requested 2 plates).
- **No artifact type** appeared in any 8-step image that was absent from its 9-step pair.

### Blinded review, SECONDARY (seed 42, contaminated; not counted)
- Frozen: sha256 dcce1edb…
- 11 ties; 1 preference: p07-s42, where the **8-step** image renders "Island of Fire" once and the 9-step image duplicates it. This matches the unblinded step-sweep observation.

### Criteria
| # | criterion | result |
|---|---|---|
| 1 | no text regression (p05/p07) | **PASS** (4/4 equal) |
| 2 | no systematic 8-step artifact | **PASS** (none observed) |
| 3 | 9-better ≤ 8-better + 3 | **PASS** (0 ≤ 4) |
| 4 | no class-level failure | **PASS** |
| 5 | operational | **PASS** (rc=0; footprint Δ −0.002 GB) |

### Verdict: GATE PASSED
**bf16 + 8 steps shows no systematic or material quality regression vs bf16 + 9 steps**, at ≈11% less denoise time (same session, paired).

**Interpretation**
- In mflux, 8 steps @1024² ≈ the official Turbo 8-NFE schedule (scheduler-nfe-note.md), so this result is expected rather than surprising.
- The 9th step mostly re-samples fine detail.

**Limits**
- Single rater (Claude), 24 primary pairs, 1024² only.
- 512² at 8 steps is not gated. mflux's weaker shift at 512² is an open question.

**Consequence (§5):** promote the FAST profile = bf16 + 8 steps. REFERENCE = fp32 + 9 steps stays the default and canonical configuration.

## Production check (2026-09-25 ~08:50)
- `bin/photo-gen generate … --seed 42 --profile fast` (p01, 1024²) → pixel sha256 **7b45cfbe…**, identical to the gated 8-step output.
- Metadata: `profile: fast`, `precision: bf16`, `steps: 8`, `validated_configuration: true`; `reproduce.cli` ends with `--profile fast`.
- `--profile reference` and no-profile both give fe47d88d… (reference unchanged). Details: `e2e/summary.json`.
