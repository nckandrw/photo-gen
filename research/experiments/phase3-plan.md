# Phase 3 plan and sequencing decisions (2026-09-25)

Directive: "PHOTO-GEN PHASE 3: resolution validation, scheduler audit, then model/runtime research".
Constraint reminder: the GPU runs one job at a time (`research/monitor.sh`, no overlap). Desk work (docs, reviews, source analysis) runs while GPU chains are in flight.

## Sequence
| # | item | GPU | artifact |
|---|---|---|---|
| 1 | record audit (§1) | no | `phase3-record-audit.md` |
| 2 | sigma desk audit + plumbing parity (§2) | 4 runs | `sigma-schedule-audit.md` §1–2 |
| 3 | **chain P3A**: 768² cold REFERENCE/FAST → sigma A/B (512, 768, 1024 sanity) → FAST gates G512, G768 → G1024-direct | ≈4–5 h | `phase3-chainA.sh`, `sigma/`, `fastgate/`, `perfmap/cold768-results.jsonl` |
| 4 | blinded reviews, in order: sigma audit, then G512/G768, then G1024 | no | reports |
| 5 | NAX source/static analysis; quantization map from existing E00 data; distillation feasibility; scorecard | no | `nax-status.md`, `quantization-map.md`, `distillation-feasibility.md`, `phase3-scorecard.md` |
| 6 | **chain P3B**: kernel profile, block-sensitivity map, NAX runtime check, quantization microbench | after P3A | `kernel-profile.md`, `block-sensitivity-map.md` |
| 7 | FFN-reduction experimental design (§10) | no, or minimal | `ffn-reduction-design.md` |

**Disclosed sequencing choice.** The directive says the 512² FAST gate comes "only after understanding the scheduler behavior".
- Generation for the gates is queued in the same GPU chain as the sigma A/B, to avoid idle GPU time.
- The gate *review and verdict* happen only after the sigma audit is reviewed and unblinded.
- The gate design does not depend on the audit outcome: both gate arms share mflux's schedule and test production as it is. The audit's desk findings (§1 of the audit) were complete before any gate image was generated.

## Improvement Clause: direct 1024² gate
| | |
|---|---|
| Original plan | Keep 1024² FAST as "validated", and run direct REFERENCE-vs-FAST gates only at 512² and 768². |
| Proposed change | Add **G1024-direct**: 24 blinded pairs, fp32/9 vs bf16/8, seeds 1618/8128, the same protocol as G512/G768. |
| Evidence | The 1024² claim rests on a *chain* of two gates, fp32/9≈bf16/9 and bf16/9≈bf16/8 (`phase3-record-audit.md` §A). Non-inferiority does not compose strictly: two sub-threshold effects can add. |
| Why superior | All three matrix cells then rest on the same kind of evidence (a direct gate). Without it, the matrix mixes a chained cell with direct cells. |
| Expected information gain | Moderate. The chain already makes a large regression unlikely; the direct gate removes the composition caveat. |
| Expected engineering benefit | Clean, uniform provenance for the production profile. No code change unless it fails. |
| Cost / what it replaces | ≈80–90 min GPU at the end of chain P3A. It replaces nothing; it runs last, so it delays no requested item. |

## Improvement Clause: block count
| | |
|---|---|
| Original plan | "Characterize all 32 blocks" (§9). |
| Proposed change | Characterize all **34** transformer blocks: 2 noise-refiner + 30 main + 2 context-refiner. The 30 main blocks are reported as the primary set. |
| Evidence | `z-image-architecture-map.md` rows 18–20; the `exp_zimage.py` audit hook enumerates `noise_refiner` + `layers` = 32 image-carrying blocks. The context refiner runs on caption tokens only. |
| Why superior | "32" matches only noise-refiner + main. Stating the partition avoids a silent mismatch. |
| Cost | none |

## Pre-registration record
- Protocol files were written before chain P3A launched (14:06:41): sigma-schedule-audit.md (mtime 14:05:32), fast-resolution-gates-report.md (14:05:50). Their status lines were corrected at ~14:08, after launch but before any A/B image existed (the chain was then in its first 600 s idle). The correction replaced guessed times with the true launch time; no protocol content changed.
- sha256 of the protocol files at that point:
  - 3bbb1ff5e63e756365ac569e525cb87d0aa32361ece0d970ce08787f2daac798  sigma-schedule-audit.md
  - f7eebfebc80e0c026b899b5ac4ae2c2bf1298eb1793cdaf6f4b6dddceb60bbef  fast-resolution-gates-report.md
