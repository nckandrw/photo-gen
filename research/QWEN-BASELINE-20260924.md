# Qwen-Image-2.1 clean baseline — 2026-09-24

## Configuration (unchanged from the Qwen project)
- Runtime: stable-diffusion.cpp `master-908-88411ef` (commit 88411ef), Metal, auto-fit default, no memory flags.
- DiT `leejet/Qwen-Image-2.1-GGUF@cc11433 qwen_image_2.1-Q4_K.gguf` sha256 29f9c83c249ff0292fb2943fceddfa2319b446601866c82a4f8be062abea72c2
- TE `pottokao/Qwen-Image-2.1-Text-Encoder-Heretic-GGUF@e21acf0 qwen3vl_8b_heretic-Q4_K_M.gguf` sha256 1338274ac7a6344f262a16c7a52d1bd7fe789307d252733b23ea421126e5d343 (no mmproj — t2i only)
- VAE `Comfy-Org/Qwen-Image-2.1@9a44dbd vae/qwen_image_2.1_vae_bf16.safetensors` sha256 bb21f7473051e1ac368515dd3f2e15cd44d7a11748ee8823e1ddca3e4876b7c9
- Hashes re-verified 2026-09-24 ~11:00. Sampling: euler, 25 steps, cfg 1, seed 42, sd.cpp model-default scheduler (logged "Flux scheduler" — resolution-dependent flow schedule).
- Wrapper: `research/qrun.sh`; rows in `research/qwen-bench-clean.csv`; monitors `research/qwen-monitor-<id>.log`.

## Environmental conditions
AC power (charging); only Finder + Terminal (+ Claude Code) running; residual swap ~0.8–1.0 GB carried from earlier runs (reported as delta); no pmset thermal warnings. Same Mac, same day, same monitoring (1 Hz monitor + `/usr/bin/time -l`), same wall-time definition as the Z-Image runs.

## CONFOUNDED HISTORICAL BASELINE (do not use for comparison)
`p5-512-s8-seed42` (10:36): battery power, Safari/WebKit + Office open (~4.9 GB free RAM at start), 8 steps, swap 0→6.5 GB, pressure warn/critical, VAE 23.6 s. Retained in `tests.md` / `bench.csv` as evidence only.

## Results
| Test ID | Category | Res | Denoise (s) | s/step | VAE (s) | TE (s) | Wall (s) | Peak footprint (GB) | Swap Δ (GB) | Pressure (L2 samples / total) | Min free | Wired max (GB) | Result |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---|
| qw-p-512 | Qwen tensor-enabled — PRIMARY CONTROL | 512² | 147.58 | 5.90 | 5.87 | 6.01 | 159.72 | 9.70 | +0.56 | 129/137 | 7% | 13.57 | PASS (correct image; sustained warn) |
| qw-diag-512-tensoroff | Qwen tensor-disabled — BACKEND DIAGNOSTIC | 512² | 254.56 | 10.18 | 6.84 | 6.08 | 267.81 | 9.84 | +0.42 | 11/227 | 7% | — | DIAGNOSTIC PASS (visually identical image; not byte-identical) |
| qw-p-768 | PRIMARY CONTROL | 768² | 379.55 | 15.18 | 23.74 | 5.94 | 409.62 | 9.85 | +0.81 | 2/353 | 4% | 14.39 | PASS |
| qw-p-1024 | PRIMARY CONTROL | 1024² | 779.97 | 31.20 | 42.62 | 6.10 | 829.18 | 9.92 | +0.46 | 61/708 | 2% | 15.19 | **CONDITIONAL PASS** |

**1024² detail.** Correct image (red apple, wooden table, blurred window). sd.cpp's auto-fit placed all 8.95 GB of params on MTL0. The first DiT step ran as **34 graph segments**; the rest ran as 1 segment with a 2448 MB compute buffer. It then logged **`WARN backend_fit.cpp:506 - VAE decode ran out of memory; retrying with spatial tiling`** and recovered automatically. Wired memory peaked at 15.19 GB, above the Metal recommended working set of 12.71 GB, and system free memory fell to 2%. Classified CONDITIONAL PASS (completed, valid output, but an OOM event and near-exhausted memory).

**Backend effect (512²).** The Metal tensor API speeds Qwen denoising **1.72×** (147.6 s → 254.6 s when disabled). Output is correct on both paths.

**Note on the pressure metric.** The kernel's pressure level was noisy between runs (512²: 129/137 samples at warn; 768²: 2/353), even though min-free and swap got worse at the larger sizes. Swap Δ, min free %, wired max and the kernel peak footprint are the more consistent indicators.

**Residual swap drift.** Swap used before each run rose from ~0.8 GB to ~2.4 GB across the session. macOS doesn't reclaim swap without memory pressure relief or a reboot. Deltas are reported per run.
