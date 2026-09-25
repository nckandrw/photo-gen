# Phase 3 §1: experiment-record audit (2026-09-25)

Directive §1 asks for three discrepancies to be resolved explicitly. Every figure here comes from the named report or data file; nothing is re-derived.

**Path note.** The directive names `research/STATUS.md` and `research/PERFORMANCE-MAP.md`. Both files live in `research/experiments/`. The "two blinded gates" wording was in `PERFORMANCE-MAP.md` (§Tiers), not in `STATUS.md`.

## A. "Two blinded gates"
**Finding.** The wording is literally true: two formal, pre-registered 24-pair gates exist. But it was **ambiguous**, because neither gate compared FAST (bf16/8) with REFERENCE (fp32/9) directly. The 1024² FAST validation is a **chain** of two non-inferiority gates:

`REFERENCE fp32/9 ≈ bf16/9` (gate 1), then `bf16/9 ≈ FAST bf16/8` (gate 2).

| | Gate 1: bf16 hidden stream | Gate 2: 8 steps |
|---|---|---|
| report | `bf16-quality-report.md` | `8step-quality-gate-report.md` |
| arms | A = fp32/9, B = bf16/9 | A = bf16/9, B = bf16/8 |
| resolution | 1024² | 1024² |
| prompts | 12 (the established suite, `prompts.json`) | 12 (same suite) |
| seeds | 2 (42, 7) | 2 primary (7, 1234) + 1 secondary (42, contaminated, not counted) |
| pairs counted | **24** | **24** primary (+12 secondary, reported separately) |
| reviewer | Claude, single rater | Claude, single rater |
| blind protocol | `pair_metrics.py blind`: random L/R key file, scores frozen and sha256-recorded before the key was read (`bf16ab/blind-scores.sha256`). This predates `blind_stage.py`. | `blind_stage.py` prepare → freeze → unblind (BLIND-PROTOCOL.md); RNG seeds 250925 / 250926 |
| generation harness | `exp_zimage.py` (research worker, before the transformer-release fix) | `prod_runner.py` (production worker, transformer release on) |
| result | fp32 better 0 / bf16 better 2 / ties 22: **PASS** | 9 better 0 / 8 better 1 / ties 23: **PASS** |

**Consequence.**
- "Two blinded gates" is replaced by "a chain of two blinded 24-pair gates (fp32/9 → bf16/9 → bf16/8); no direct REFERENCE-vs-FAST gate" in `PERFORMANCE-MAP.md`, `STATUS.md` and the README.
- Non-inferiority does not compose strictly. Each gate can hide a small effect below its resolution, and the two effects could add. The chain therefore supports the FAST claim at 1024² but is weaker than a direct gate.
- Status of the 1024² FAST cell: **VALIDATED (chained)**. It is not re-labelled; the qualifier is added.
- The 512²/768² gates in Phase 3 compare REFERENCE and FAST **directly**. See the Improvement-Clause note in `phase3-plan.md` about adding a direct 1024² gate so all three cells rest on the same kind of evidence.
- Additional disclosure: the gate-2 primary review is logged as 07:11–07:15 (24 composites in about 4 minutes, `8step-quality-gate-report.md`). Review speed is not a protocol violation, but it is recorded here as a limitation of a single-rater review.

## B. Quality vs timing datasets
Quality and timing samples are **different datasets** and must not be merged into one sample size.

| dataset | purpose | n | seeds | where |
|---|---|---:|---|---|
| gate 1 blinded review | quality | 24 pairs | 42, 7 | `bf16ab/blind-scores.json` |
| gate 1 ABBA timing | performance (bf16/9 vs fp32/9, sustained, pre-memfix footprint ≈7.34 GB) | 24 pairs (the same 48 runs) | 42, 7 | `bf16ab/results.jsonl` |
| gate 2 blinded review | quality | **24 pairs** (primary) | 7, 1234 | `gate8/blind-primary/SCORES-FROZEN.txt` |
| gate 2 ABBA timing | performance (bf16/8 vs bf16/9, sustained) | **36 pairs** (all 72 runs, including seed 42) | 42, 7, 1234 | `gate8/results.jsonl` |
| performance map, cold | performance | 1 run per configuration | 42 | `perfmap/cold-results.jsonl` |
| performance map, sustained | performance | 2 positions (ABBA) per configuration | 42 | `perfmap/sustained-results.jsonl` |

- "Denoise ratio 0.887" comes from the 36 timing pairs. "0 worse / 1 better / 23 ties" comes from the 24 quality pairs. The 12 seed-42 pairs count toward timing but **not** toward quality.
- "Denoise ratio 0.70" (gate 1) comes from 24 sustained pairs on the research harness. The cold 0.70 figure comes from one cold pair (performance map). They agree, but they are separate measurements.

## C. Terminology
Canonical wording from now on:

| tier | definition | NFE | status of the schedule |
|---|---|---|---|
| **REFERENCE** | fp32 + 9 steps | **9 NFE** (mflux: 1 step = 1 NFE) | intentionally conservative reproducibility baseline. **Not** the official Turbo count. |
| **FAST** | bf16 + 8 steps | **8 NFE** | matches the official Turbo NFE count (8) as currently understood. At 1024² its sigmas are within 0.013 of the official static-shift-3.0 schedule. At 512²/768² mflux's sigmas differ (see `sigma-schedule-audit.md`). |

Remaining loose uses found by grep and fixed with dated inline corrections, not rewrites:
- `research/z-image-architecture-map.md`: "Cross-step redundancy is low at 8 NFE (E05)". The cache audit ran 9 steps = 9 NFE.
- `research/Z-IMAGE-TURBO-REPORT.md` and `research/z-image-research-log.md` (Pass 1) quote the model card's "9 steps (8 DiT forwards)". These are historical records of what the card said. A correction pointer was added to the report; the log is left as a log.

Already correct: `README.md` §Resolutions and steps, `CLAUDE.md`, `scheduler-nfe-note.md`.

## Other discrepancies found during the audit (flagged, not silently reconciled)
1. **"32 blocks" (directive §9) vs the architecture.** `z-image-architecture-map.md` records **30 main blocks + 2 noise-refiner + 2 context-refiner = 34** transformer blocks. The sensitivity map covers all 34 and reports the 30 main blocks separately. To be verified against the loaded model at instrumentation time.
2. **The directive treats the 512² e^μ value as a single "MFLUX 512²" number.** It is resolution-dependent everywhere: e^μ = 1.878 (512²), 2.332 (768²), 3.158 (1024²). Details in `sigma-schedule-audit.md`.
3. **The directive's "36 ABBA pairs" timing dataset includes seed 42**, whose images the rater had already seen. That doesn't matter for timing, but it is one more reason the timing and quality datasets must stay separate.
