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
| EXPERIMENTAL | bf16 + 7/6/5/4 | research only; not quality-equivalent (step-sweep-report.md) |

## Notes
- Denoise per step at 1024² in the sustained block rises from 8.8 to 9.3 s toward the middle of the ramp: thermal state, not step count.
- Per-step cost is the same for every step count once thermal state is matched (cold bf16: 55.1/9 = 6.12 s, 48.7/8 = 6.09 s).
- Memory depends on precision and resolution, not step count. Transformer release makes it flat run to run.
