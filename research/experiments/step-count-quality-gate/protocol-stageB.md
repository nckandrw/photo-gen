# Stage B protocol: bf16 + 5 vs bf16 + 8 (PRE-REGISTERED before any Stage B image)

Written 2026-09-29, before any Stage B image existed, and committed before generation. Stage B inherits every rule of `protocol.md` (Stage A) except those listed here. Production (REFERENCE, FAST, ULTRA at 512²) is unchanged during Stage B.

## Changes from Stage A
| item | Stage B |
|---|---|
| arms | A = bf16 + 8 (FAST), B = **bf16 + 5** (5 NFE) |
| seeds | **6502, 1729**, pre-assigned in `protocol.md` and verified unused by any project image |
| resolutions | 512², 768², 1024², each with its own verdict |
| blind directories | `blind-B512` (rng 2909301), `blind-B768` (rng 2909302), `blind-B1024` (rng 2909303). All three keys stay sealed until all three score files are frozen. |
| speed criterion 7 | median paired denoise ratio 5/8 **≤ 0.70** (pre-registered in `protocol.md`) |
| cold runs | p01 seed 42 at **5 steps** at each size, each after 600 s idle. The cold 8-step figures are the same-day Stage A cold runs (a documented baseline: same machine, same day, same idle protocol). |
| σ context | last-step start: 512² 0.319, 768² 0.368, 1024² 0.441 (vs 4 steps: 0.385 / 0.437 / 0.513) |

## Improvement Clause: an explicit definition of a "minor" text error
| | |
|---|---|
| Original | Criterion 1 allows "at most one pair minor-worse", with "minor" undefined. Stage A had to judge it at review time (768²). |
| Proposed | **Defined before any image:** a text difference is *minor* only when the intended string is still present exactly once and readable, and the defect is glyph-level (stroke weight, kerning, a slightly misshapen letter that doesn't change the word). **Not minor:** a duplicated, missing, extra or wrong word or phrase; a letter that changes or obscures the word; ghosted or partially formed text. |
| Evidence | the Stage A 768² verdict hinged on this judgment |
| Why better | it removes the reviewer's discretion from the decisive criterion. It is the same judgment Stage A applied, now written down in advance. |
| Impact | Stage B verdicts are reproducible from the frozen score sheets. Stage A verdicts are unchanged: this is the definition Stage A applied. |

## Stage-B-specific question (pre-stated)
The Stage A 4-step failures were under-denoising signatures: ghosted duplicate text, malformed glyphs, ghost objects. For each resolution, Stage B also records whether 5 steps **eliminates**, **reduces** or **shifts** these. It counts ghosting / duplicate-text / malformed-glyph failure modes per arm from the frozen checklist.

## Verdict rules
As in `protocol.md`: **VALIDATED / PROMISING / REJECTED / INCONCLUSIVE**, applied per resolution and unchanged after seeing results.
