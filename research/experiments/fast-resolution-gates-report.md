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
