# photo-gen performance map (measured 2026-09-25, production worker, transformer release ON)

**Common settings**
- MacBook Air M5 16 GB, mflux 0.20.0 / MLX 0.32.2, q4, `--low-ram`, prompt p01 (apple), seed 42.
- Harness: `prod_runner.py`. Data: `perfmap/cold-results.jsonl`, `perfmap/sustained-results.jsonl`.
- Every configuration's pixel hash was identical across its runs and equal to its gated reference.

**Baselines are always named.** "wall" = the worker process from spawn to exit (includes model load ≈1.1 s and text encode ≈0.65 s). "denoise" = the DiT loop only.

## Cold (each run after 600 s idle, chip cool)
| tier | res | precision | steps | wall (s) | denoise (s) | VAE (s) | peak footprint (GB) | swap Δ | pressure | output hash | quality status |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| REFERENCE | 1024² | fp32 | 9 | 83.4 | 78.3 | 1.98 | 6.56 | 0 | 1 | fe47d88d… | reference |
| — | 1024² | bf16 | 9 | 60.6 | 55.1 | 1.96 | 5.84 | 0 | 1 | 11b19277… | gated (bf16 gate) |
| **FAST** | 1024² | bf16 | 8 | **54.2** | **48.7** | 1.97 | 5.84 | 0 | 1 | 7b45cfbe… | gated, chained (bf16 gate → 8-step gate) |
| REFERENCE | 512² | fp32 | 9 | 21.2 | 17.4 | 0.37 | 5.93 | 0 | 1 | 9ae59f59… | reference |
| — | 512² | bf16 | 9 | 16.5 | 12.9 | 0.38 | 5.41 | 0 | 1 | c70c38b0… | **experimental** at 512² (bf16/9 gated at 1024² only) |
| FAST | 512² | bf16 | 8 | 15.0 | 11.4 | 0.37 | 5.41 | 0 | 1 | 0b9cc20a… | **validated** (direct gate, 2026-09-25) |
| REFERENCE | 768² | fp32 | 9 | 44.7 | 40.4 | 1.06 | 6.33 | 0 | 2 | 94a023d3… | reference (cold run 2026-09-25) |
| **FAST** | 768² | bf16 | 8 | 30.6 | 26.1 | 1.08 | 5.93 | 0 | 1 | 20ff9e2c… | **validated** (direct gate) |

**Cold 1024², FAST vs REFERENCE (measured directly, not multiplied):**
- wall 83.4 → 54.2 s = **−35% wall, 1.54× speed-up**;
- denoise 78.3 → 48.7 s = **−38%, 1.61×**;
- peak footprint 6.56 → 5.84 GB.

## Sustained sequence (back to back, no idle, ABBA over configurations)
- Order per resolution: warm-up, then fp32/9, bf16/9, 8, 7, 6, 5, 4, then the reverse. Values are the mean of the two positions.
- ⚠ **1024²: the chip was still heating through the block** (fp32/9 denoise 83.1 s at the start vs 129.5 s at the end; bf16/9 69.2 vs 89.0). The means are ABBA-balanced but **not steady-state**. The configurations at the block's edges (fp32/9, bf16/9) span the widest thermal range.
- For fully heat-soaked fp32/9, the earlier 10-run series measured ≈133.7 s wall, consistent with this block's final fp32 run (135.8 s).
- 512² was near-stable (two positions within ±3%).

| res | precision | steps | wall mean (s) | denoise mean (s) | denoise per step (s) | VAE (s) | peak footprint (GB) | swap Δ | pressure |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1024² | fp32 | 9 | 112.2 | 106.3 (83.1 / 129.5) | 11.81 | 2.39 | 6.56 | 0 | 1 |
| 1024² | bf16 | 9 | 85.1 | 79.1 (69.2 / 89.0) | 8.79 | 2.43 | 5.84 | 0 | 1 |
| 1024² | bf16 | 8 | 78.1 | 72.1 (66.2 / 78.0) | 9.02 | 2.47 | 5.83 | 0 | 1 |
| 1024² | bf16 | 7 | 70.2 | 64.1 | 9.16 | 2.49 | 5.84 | 0 | 1 |
| 1024² | bf16 | 6 | 61.6 | 55.6 | 9.26 | 2.50 | 5.83 | 0 | 1 |
| 1024² | bf16 | 5 | 52.5 | 46.4 | 9.28 | 2.52 | 5.84 | 0 | 1 |
| 1024² | bf16 | 4 | 43.1 | 37.1 | 9.27 | 2.50 | 5.80 | 0 | 1 |
| 512² | fp32 | 9 | 33.3 | 29.5 | 3.28 | 0.45 | 5.93 | 0 | 1 |
| 512² | bf16 | 9 | 25.6 | 21.8 | 2.43 | 0.43 | 5.41 | 0 | 1 |
| 512² | bf16 | 8 | 23.0 | 19.2 | 2.40 | 0.44 | 5.41 | 0 | 1 |
| 512² | bf16 | 7 | 20.5 | 16.7 | 2.39 | 0.43 | 5.42 | 0 | 1 |
| 512² | bf16 | 6 | 18.2 | 14.4 | 2.40 | 0.43 | 5.41 | 0 | 1 |
| 512² | bf16 | 5 | 15.9 | 12.1 | 2.43 | 0.43 | 5.41 | 0 | 1 |
| 512² | bf16 | 4 | 13.5 | 9.7 | 2.43 | 0.44 | 5.41 | 0 | 1 |

## Most reliable relative figures (paired, same session)
| comparison | figure | source |
|---|---|---|
| bf16/8 vs bf16/9 denoise (1024²) | ratio **0.887** (median of 36 ABBA **timing** pairs; the quality verdict rests on a different set, 24 primary pairs) | 8step-quality-gate-report.md |
| bf16/9 vs fp32/9 denoise (1024², sustained) | ratio **0.70** (median of 24 ABBA pairs) | bf16-quality-report.md |
| bf16/9 vs fp32/9 denoise (1024², cold) | 55.1 / 78.3 = **0.70** | this map |
| FAST vs REFERENCE end to end (1024², cold) | wall **1.54×**, denoise **1.61×** | this map |
| 512² bf16/9 vs fp32/9 (near-stable) | denoise 0.74 | this map |

## Tiers
| tier | definition | status |
|---|---|---|
| REFERENCE | fp32 + 9 steps (9 NFE) | permanent, canonical, default; intentionally conservative reproducibility baseline, **not** the official Turbo count |
| FAST | bf16 + 8 steps (8 NFE) | **validated at 512², 768², 1024²** by direct blinded REFERENCE-vs-FAST gates (2026-09-25; 72 pairs: REF 2 / FAST 1 / 69 ties; fast-resolution-gates-report.md). 1024² was earlier supported by a chain of two gates (phase3-record-audit.md §A) |
| (no profile) | bf16 + 9 | validated at 1024² only (bf16 gate); **experimental** at 512²/768² |
| ULTRA | bf16 + 4 steps (4 NFE) | **validated at 512² only** (step-count-quality-gate/results.md); REJECTED at 768²/1024² |
| BALANCED | bf16 + 5 steps (5 NFE) | **validated at 1024² only** (Stage B 0/0/24; production 2026-09-29). 768²: NOT CONFIRMED (Stage B narrowest pass 3/0/21; confirmation 3/1/28, criterion 4), stays FAST. 512²: experimental, not offered (ULTRA dominates) |
| EXPERIMENTAL | bf16 + 7/6; 5 at 512²/768²; 4 above 512² | research only; 6 = Stage C, deferred |

**Roles:** REFERENCE: reproducibility, regression testing, reference fidelity. FAST: general-purpose production at every validated size. BALANCED: lower-latency 1024² where the 5-step gate passed. ULTRA: minimum-latency 512² where the 4-step gate passed. Different operating points with different evidence, not a ranking.

**Current production operating points (cold, one run after 600 s idle, p01 seed 42; same-day 2026-09-29 runs):**

| res | profile | wall / denoise (s) | vs FAST (cold wall) |
|---|---|---|---:|
| 1024² | FAST bf16 + 8 | 54.4 / 49.1 | 1.00 |
| 1024² | BALANCED bf16 + 5 | 36.1 / 30.6 | 0.66 |
| 768² | FAST bf16 + 8 | 30.4 / 26.0 | 1.00 |
| 512² | FAST bf16 + 8 | 15.6 / 11.5 | 1.00 |
| 512² | ULTRA bf16 + 4 | 9.5 / 5.9 | 0.61 |

Sustained paired denoise ratios: BALANCED/FAST 0.625 (1024²), ULTRA/FAST 0.509 (512²).

## Notes
- Denoise per step at 1024² in the sustained block rises from 8.8 to 9.3 s toward the middle of the ramp: thermal state, not step count.
- Per-step cost is the same for every step count once thermal state is matched (cold bf16: 55.1/9 = 6.12 s, 48.7/8 = 6.09 s).
- Memory depends on precision and resolution, not step count. Transformer release makes it flat run to run.

## Step-count gate, Stage A (2026-09-29; `step-count-quality-gate/results.md`)
Cold, same day, one run each after 600 s idle; p01 seed 42.

| res | bf16 + 8 (FAST) wall / denoise | bf16 + 4 wall / denoise | paired sustained denoise 4/8 | 4-step quality verdict |
|---|---|---|---:|---|
| 512² | 15.6 / 11.5 s | 9.5 / 5.9 s | 0.509 | **VALIDATED** |
| 768² | 30.4 / 26.0 s | 17.5 / 13.2 s | 0.503 | REJECTED (1 text pair) |
| 1024² | 54.4 / 49.1 s | 30.0 / 24.6 s | 0.502 | REJECTED (text class) |

Peak footprint is identical to FAST at each size.

## Step-count gate, Stage B (2026-09-29; `step-count-quality-gate/results.md`)
Cold, one run each after 600 s idle, p01 seed 42. The 8-step column is the same-day Stage A cold baseline.

| res | bf16 + 8 (FAST) cold wall / denoise | bf16 + 5 cold wall / denoise | cold ratio 5/8 wall / denoise | paired sustained denoise 5/8 | paired sustained wall 5/8 | 5-step quality verdict |
|---|---|---|---|---:|---:|---|
| 512² | 15.6 / 11.5 s | 11.3 / 7.6 s | 0.73 / 0.66 | 0.629 | 0.696 | VALIDATED (dominated by ULTRA) |
| 768² | 30.4 / 26.0 s | 20.9 / 16.5 s | 0.69 / 0.64 | 0.630 | 0.666 | VALIDATED (narrowest possible pass) |
| 1024² | 54.4 / 49.1 s | 36.1 / 30.6 s | 0.66 / 0.62 | 0.625 | 0.652 | VALIDATED |

Peak footprint equals FAST within 0.001 GB. Per-step time is unchanged between 5 and 8 steps, so the saving is the step count, as in Stage A.


## Image editing: Qwen-Image-2.1 q4 (separate venv; G2 REJECTED, research opt-in; added 2026-10-07)
**Settings:** mflux 0.21.0 / MLX 0.32.2 in `mflux-qwen/.venv`; upstream defaults (40 steps, guidance 1.0, prefix KV cache, `--low-ram`); same M5 16 GB machine, AC power, apps closed.
- "wall" is the job's `generation_seconds` (worker spawn to exit, including about 2 s of model load). "denoise" is the 40-step DiT loop.
- **Every row names its baseline.**
  - G2 rows are a **sustained chain** (runs 20 s apart) under the 1 Hz monitor.
  - Wall time rises with chain position: the first two 512 runs took 80.1 s and 82.9 s, the median of runs 5–23 is 105 s, and the first 1024 run took 523 s against a 592 s median. This is consistent with cold versus sustained (thermal) on a fanless machine.
  - It explains the "monitored vs unmonitored" gap noted in `QWEN-MEMORY-LIFETIME.md` §4 at least as well as monitoring overhead does. The cause is not isolated.
- The quality status of every row is **G2 REJECTED** (`research/editing/real-world/results.md`). These are timings, not an endorsement.

| budget | lifetime policy | baseline | n | wall (s) | denoise (s) | VAE decode (s) | peak footprint (GB) | swap Δ (GB) | pressure | source |
|---|---|---|---:|---:|---:|---:|---:|---:|---|---|
| 512 | P2 (production) | G2, sustained chain (monitored) | 23 | **104** median [80–115] | 96 [73–107] | 2.4 | **8.16** [8.07–8.37] | 0.00 [0–0.04] | ≤ 1 warn sample, 0 critical | real-world/benchmark.csv |
| 512 | P2 | single unmonitored production edit (E05), after adoption | 1 | 79.7 | — | — | 8.17 | — | — | QWEN-MEMORY-LIFETIME.md §7 |
| 512 | P0 (deferred DiT only; Phase 4) | G0, sustained | 12 | 83–112 | — | — | 8.85 | ≤ 0.36 | 0 critical | QWEN-EDITING-QUALITY.md |
| 1024 | P2 (production) | G2, sustained chain (monitored) | 22 | **592** median [523–634] | 571 [504–613] | 10.2 | **10.87** [10.72–11.10] | 0.45 [0.10–1.19] | 4–11 warn samples (≤ 2.7%), 0 critical | real-world/benchmark.csv |
| 1024 | P2 | memory A/B, monitored | 3 | 549.5–576.5 | 529.8–555.7 | 9.6–10.8 | 10.73–10.96 (E05) | 0.11–0.37 | 3–5 warn, 0 critical | QWEN-MEMORY-LIFETIME.md §4 |
| 1024 | P0 (Phase 4) | G0, cold after 600 s idle | 1 | 496.8 | 474.1 | 12.8 | 12.08 | — | warn, 0 critical | QWEN-EDITING-BASELINE.md |
| 1024 | P0 (Phase 4) | G0, sustained (non-cold G0 runs) | — | 556 median [478–601] | — | — | 12.08 | 1.3–2.1 | warn, 0 critical | QWEN-EDITING-QUALITY.md |

- **Memory/UX class (G2, `real-world/protocol.md` §8):** 512 COMFORTABLE; 1024 **MARGINAL**. At 1024, wall time binds (median above the 360 s USABLE limit), not memory. Since P2, 1024 shows no critical pressure, and swap growth stays at 1.19 GB or less.
- **Per-step cost:** about 2.4 s at 512 and 14 s at 1024 (G2 denoise ÷ 40). Compare Z-Image FAST at 1024²: 48.7 s for 8 steps.
- **No speed work was done.** Directive §24–§25 gates it on a quality pass, and G2 did not pass.

### Q-Q diagnostic (Phase 6, 2026-10-08): q8 weights vs q4, same chain. **Diagnostic only, not a configuration**
Both arms ran in one interleaved, sustained, monitored chain: production worker, P2, 40 steps (`research/qwen/QWEN-QQ-DIAGNOSTIC.md` §4). The q8 export was deleted afterwards. Its quality result was AGAINST: it did not fix the text failure.

| budget | weights | n | wall (s) | denoise (s) | step (s) | peak footprint (GB) | denoise MLX peak (GB) | swap Δ (GB) | warn samples | critical |
|---|---|---:|---|---:|---:|---|---:|---|---|---:|
| 512 | q4 | 4 | 103.6 [84.0–108.5] | 95.7 | 2.30 | 8.16 | 5.86 | 0.00 | 0% | 0 |
| 512 | q8 | 5 | 133.5 [126.7–137.7] | 115.2 | 2.92 | 12.03 [11.93–12.06] | 9.34 | 1.86 [1.74–2.64] | 9% | 0 |
| 1024 | q4 | 4 | 569.7 [559.7–585.5] | 550.3 | 13.77 | 10.87 | 9.73 | 0.55 [0.42–0.76] | 2% | 0 |
| 1024 | q8 | 5 | 809.7 [766.4–863.8] | 772.4 | 17.95 | 13.76 [13.69–13.83] | 13.19 | 3.08 [2.57–3.65] | 76% | 0 |

- **What q8 costs:**
  - At 512, the q8 text encoder (about 9.4 GB) sets the peak.
  - At 1024, the q8 DiT (7.66 GB) plus activations sets it, and the machine pages for the whole denoise.
  - By G2's memory/UX definitions (descriptive), q8 would be MARGINAL at both budgets.
- **The q8 export itself** (per component): peak footprint 10.8 and 11.2 GB, about 2 minutes in total.
