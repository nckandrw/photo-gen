# MFLUX Z-Image-Turbo: sustained 10-run thermal characterization (MacBook Air M5 16 GB)

**Date:** 2026-09-24, 17:33:08–17:54:33 (PST).
**Raw data:**
- `runs/mf-th10-r1..r10/` (cmd.txt, mflux.log, stderr.log with `/usr/bin/time -l` and tqdm per-step, monitor.csv at 1 Hz, phases.json, pre/post.txt, summary.txt)
- `mflux-sustained-10run.csv` (one row per run; existing mflux-bench schema plus thermal fields)
- `preflight-mflux-10run-20260924-1732.log`
- Outputs: `outputs/mf-th10-r*.png`

## 1. Objective
Characterize the sustained, thermally saturated operating point of the existing MFLUX Z-Image-Turbo production configuration at 1024² over 10 consecutive generations, keeping the cold, transition and sustained regimes separate. This is not a new comparison or an optimization.

## 2. Environment
- MacBook Air, Apple M5 (10-core CPU, 8-core GPU, `applegpu_g17g`), 16 GiB, macOS 27.0 (26A428), Metal 4.
- **AC power.**
- Controlled application state restored before run 1:
  - Safari, Xcode and Numbers had been opened since the last phase.
  - Numbers and Xcode were checked first and had no open documents, so there was no unsaved work.
  - All three were quit gracefully via AppleScript `quit`, with no prompts and no force-quit.
  - Remaining GUI apps: Finder and Terminal (+ Claude Code).
- Pre-run state (17:32:48):
  - memory free 80%; `kern.memorystatus_vm_pressure_level` 1 (normal);
  - pmset: no thermal or performance warnings;
  - **residual swap 911 MB**, higher than the ≈0.5 GB at the start of the earlier MFLUX phase and documented here, not normalized;
  - wired 2.39 GB; compressor 0.69 GB.
- The machine had been idle ≈54 min since the previous GPU workload (16:39), so run 1 started cold.

## 3. Versions (verified in preflight, unchanged)
- CPython 3.12.14 (project-local uv), mflux 0.20.0, mlx 0.32.2, mlx-metal 0.32.2, device `Device(gpu, 0)`.
- `uv pip freeze` identical to `mflux/requirements.lock.txt` (56 packages; no drift).
- No package installed, upgraded or modified.

## 4. Model
`mflux-community/z-image-turbo-mflux-q4` @ d2d30500c4bc0d19770bd952951df3e7c635ae9e. All 6 LFS files re-hashed before the run and matched the sha256 values recorded at download (`mflux-versions.md`).

## 5. Configuration
- Command (every `runs/mf-th10-r*/cmd.txt`):

  `mflux/zi_driver.py --model models/mflux/z-image-turbo-mflux-q4 --base-model z-image-turbo --prompt "a red apple on a wooden table, soft window light" --width 1024 --height 1024 --steps 9 --seed 42 --low-ram --output outputs/mf-th10-rN.png`

  with `HF_HUB_OFFLINE=1`.
- Guidance is forced to 0.0 by the Turbo CLI. Scheduler: mflux default.
- One process per run, launched back to back by the existing harness. The gap between one run's end and the next run's start was 2–3 s: harness teardown/monitor stop, with no deliberate cooling.
- **Harness change (documented, approved):** `research/mrun.sh` gained an optional `LOWRAM_FLAG` override after the earlier 3-run series. `LOWRAM_FLAG` was unset for all 10 runs, so `--low-ram` was present, as confirmed by each `cmd.txt`. The effective command is identical to the prior MFLUX 1024² runs.
- The instrumentation probes in `zi_driver.py` are the same as in the prior 3-run series (timing, MLX active/peak memory, memory-saver probes). No methodology changes were made during execution.

## 6. Run-by-run results

| Run | Start | Wall (s) | ×r1 | Denoise (s) | s/step first → last | TE (s) | VAE (s) | Peak footprint (GB) | Max RSS (GB) | Swap Δ (MB) | Pressure L2/L4 samples | Min free | Wired max (GB) | pmset pre/post | Pixels = r1 |
|---:|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---|---:|---:|---|---|
| 1 | 17:33:08 | **84.62** | 1.000 | 78.59 | 8.63 → 8.86 | 0.67 | 1.97 | 7.26 | 1.55 | 0.0 | 0/0 | 46% | 6.14 | none/none | ✔ |
| 2 | 17:34:37 | 101.32 | 1.197 | 95.29 | 8.90 → 11.61 | 0.64 | 2.55 | 7.33 | 2.84 | 0.0 | 0/0 | 34% | 6.54 | none/none | ✔ |
| 3 | 17:36:24 | 121.20 | 1.432 | 115.05 | 12.24 → 12.82 | 0.64 | 2.63 | 7.36 | 2.84 | 0.0 | 0/0 | 50% | 6.00 | none/none | ✔ |
| 4 | 17:38:30 | 128.44 | 1.518 | 122.25 | 12.89 → 13.65 | 0.64 | 2.73 | 7.35 | 2.84 | 0.0 | 0/0 | 53% | 6.17 | none/none | ✔ |
| 5 | 17:40:43 | 132.19 | 1.562 | 125.80 | 14.74 → 13.83 | 0.65 | 2.80 | 7.35 | 3.79 | 0.0 | 0/0 | 56% | 5.02 | none/none | ✔ |
| 6 | 17:43:01 | 136.27 | 1.610 | 130.04 | 13.72 → 14.13 (peak 15.45) | 0.64 | 2.75 | 7.28 | 3.82 | 0.0 | 0/0 | 40% | 6.04 | none/none | ✔ |
| 7 | 17:45:22 | 130.97 | 1.548 | 124.71 | 13.67 → 13.81 | 0.64 | 2.70 | 7.35 | 2.84 | 0.0 | 0/0 | 53% | 4.94 | none/none | ✔ |
| 8 | 17:47:38 | 132.59 | 1.567 | 126.38 | 13.81 → 14.03 | 0.64 | 2.67 | 7.35 | 2.95 | 0.0 | 0/0 | 55% | 5.06 | none/none | ✔ |
| 9 | 17:49:55 | 134.65 | 1.591 | 128.32 | 13.93 → 14.23 | 0.64 | 2.80 | 7.35 | 3.06 | 0.0 | 0/0 | 47% | 6.08 | none/none | ✔ |
| 10 | 17:52:15 | 135.61 | 1.603 | 129.10 | 13.84 → 14.36 | 0.64 | 2.79 | 7.35 | 2.88 | +1.3 | 0/0 | 39% | 5.97 | none/none | ✔ |

Load/init (lazy weights) was 1.07–1.20 s in every run. MLX allocator peaks were identical in every run: TE 3.61 GB; VAE decode 5.70 GB; active after TE release 0.003 GB; active before VAE 3.47 GB. The full per-step traces are in the CSV (`steps_trace`).

## 7. Thermal analysis

**Summary statistics (wall time, s):**

| Set | Mean | Median | Min | Max | SD | CV |
|---|---:|---:|---:|---:|---:|---:|
| All 10 | 123.79 | 131.58 | 84.62 | 136.27 | 17.26 | 13.9% |
| First half (1–5) | 113.55 | — | — | — | — | — |
| Second half (6–10) | 134.02 | 134.65 | 130.97 | 136.27 | 2.20 | 1.6% |
| Runs 5–10 (plateau, see below) | **133.71** | **133.62** | 130.97 | 136.27 | 2.10 | **1.57%** |
| Runs 4–10 | 132.96 | 132.59 | 128.44 | 136.27 | 2.77 | 2.1% |

Denoise statistics track wall time: runs 5–10 have mean 127.39 s, median 127.35 s, CV 1.63%.

**Empirically supported regimes (from per-step times, not assumptions):**
1. **Cold / burst: run 1.** 8.49–8.86 s/step, flat within the run; 84.6 s wall.
2. **Thermal transition: runs 2–4.**
   - Run 2 starts at the cold rate (8.90 s/step) and rises steadily within the run to 11.61 s/step. **Throttling onset occurs during run 2**, about 1.6–2.5 min into continuous load.
   - Runs 3–4 continue rising: 12.2 → 13.7 s/step.
3. **Sustained throttled: runs 5–10.**
   - 13.7–14.4 s/step, apart from one excursion to 15.45 s/step inside run 6.
   - Wall 131.0–136.3 s, CV 1.57%.
   - A least-squares line over runs 5–10 has a slope of **+0.40 s/run (+0.3%/run)**, smaller than the run-to-run SD (2.1 s). In runs 7→10, per-step times creep from 13.8 to 14.4 s/step.
   - **The data support a near-plateau.** A slow residual upward drift of about 0.3%/run can't be excluded, and behaviour beyond run 10 isn't measured.

## 8. Memory analysis
Every metric that would indicate memory contention stayed flat while throughput fell 1.6×:
- Peak footprint 7.26–7.36 GB.
- MLX peaks identical every run.
- Swap Δ 0 MB in 9 runs and +1.3 MB in run 10.
- Zero warn/critical pressure samples in all 10 runs.
- Min free memory ≥34%; wired ≤6.54 GB.

Max RSS varied (1.55–3.82 GB), but RSS excludes Metal buffers and isn't the operative metric.

**The slowdown isn't attributable to memory.** It shows the signature expected from thermal throttling:
- per-step time rises *within* a run under constant work;
- it plateaus;
- no other process competed (controlled app state);
- the earlier phase showed full recovery after 10 minutes idle.

pmset reported no thermal or performance warnings at any run boundary, but pmset on this Mac doesn't expose GPU clocks, temperatures or throttling, and `powermetrics` needs sudo, which wasn't used. **Thermal throttling is therefore inferred, not directly measured.**

## 9. Determinism analysis
- All 10 outputs have identical decoded-pixel sha256: `fe47d88dfb4bec549060c29c527eeff280d863e8e12176cdc1c28d3d8003a118`.
- That is the same hash as the earlier `mf-1024` and `mf-th3-r1..r3` runs (a different session hours earlier), so the output is invariant across thermal states and sessions.
- PNG files differ only in metadata chunks (eXIf/iTXt/tEXt, which include generation time). Pixel data is identical.

## 10. Sustained-throughput analysis

| Regime | Basis | s/image | Images/hour |
|---|---|---:|---:|
| Cold / burst (single image) | run 1 (measured) | 84.6 | 42.5 (**extrapolation**: holds only for the first image after a cool-down; runs 2+ are slower) |
| Sustained throttled | runs 5–10 mean (measured) | 133.7 | 26.9 generation-only; **26.4 including the measured 2–3 s inter-run harness gap** (**extrapolation** beyond run 10) |
| First 10 images from cold | runs 1–10 total 1237.9 s + 9 gaps (27 s) | 126.5 avg | 28.5 (measured over 21.1 min) |

## 11. Comparison with the existing sd.cpp baseline (not re-run)
The sd.cpp reference is Z-Image-Turbo Q4_K + Qwen3-4B Q4_K_M + Flux VAE, tensor API disabled (#1990), 1024² (`z-image-tests.md`, `FINAL-M5-COMPARISON.md`).

| Dimension | sd.cpp (measured earlier) | MFLUX (this series) | Observation |
|---|---|---|---|
| Burst (first image) | 360.6 s (19-run mean; sd.cpp showed no cold/hot difference) | 84.6 s | MFLUX **0.23×** the time |
| Sustained | 356.8 s mean over the 10-run series (349.1–364.0) ≈ 10.1 img/h | 133.7 s (runs 5–10) ≈ 26.9 img/h | MFLUX **0.37×** the time (**2.7×** throughput) |
| Thermal stability | wall r10/r1 = 1.033; denoise range 314–328 s | wall r10/r1 = 1.603; plateau CV 1.6% after ~7 min | sd.cpp is more stable; MFLUX drops 1.6× then stabilizes |
| Peak memory | 6.84 GB | 7.26–7.36 GB | MFLUX **+0.4–0.5 GB** |
| Swap | Δ 0 (one run +0.27 GB) | Δ 0 (one run +1.3 MB) | equivalent |
| Pressure | L1 (one run with 34 L2 samples) | L1 in all runs | equivalent to marginally better for MFLUX |
| OOM/fallback | VAE-OOM → tiled retry every run | none | MFLUX has none |
| Determinism | byte-identical files | pixel-identical (metadata differs) | both deterministic |

## 12. Comparison with the prior MFLUX 3-run sequence (same configuration)

Actual timeline of the prior sequence (from `runs/*/pre.txt` and `post.txt`):
- The sd.cpp phase ended at 15:01:58, followed by **≈56 min idle**.
- mf-512 / mf-512-probe / mf-768 ran 15:58:17–16:00:48 (≈2 min of load, small images).
- mf-1024: 16:00:49–16:02:35.
- **69 s gap**, then mf-th3-r1: 16:03:44–16:05:22.
- mf-th3-r2 and mf-th3-r3 followed with ~0–1 min gaps, ending at 16:10:37.

| Consecutive 1024² image | Prior sequence | This 10-run series |
|---|---|---|
| #1 | mf-1024: 103.8 s, 9.4 → 11.9 s/step (preceded by ≈2 min of 512/768 load) | r1: 84.6 s, 8.6 → 8.9 s/step (preceded by ≈54 min idle) |
| #2 | mf-th3-r1: 95.3 s, 8.9 → 10.8 s/step (after a 69 s pause) | r2: 101.3 s, 8.9 → 11.6 s/step |
| #3 | mf-th3-r2: 155.6 s, ~16.4 s/step | r3: 121.2 s, 12.2 → 12.8 s/step |
| #4 | mf-th3-r3: 149.6 s, ~15.8 s/step | r4: 128.4 s, 12.9 → 13.7 s/step |
| Throttled level | ≈15.8–16.4 s/step (150–156 s) | ≈13.7–14.4 s/step (131–136 s, runs 5–10) |

- **Discrepancy (reported, unresolved):** the prior throttled level was about **12–15% slower** than this series' plateau.
- The configuration, binary, model, command, AC power and controlled app state were identical.
- Both sequences started from a comparable ≥54 min idle, so **accumulated heat-soak from earlier work that day doesn't explain it**. An earlier draft of this report suggested that; it was corrected after checking the run timestamps.
- Candidates that this data can't distinguish:
  - ambient temperature;
  - the laptop's physical placement or surface, which affects fanless heat dissipation;
  - background system activity not captured by the harness;
  - battery charge state or charging load on AC (pmset reported AC throughout, but charging heat wasn't logged).
- **Practical reading:** the sustained operating point on this Mac spans **≈131–156 s/image across the two measured sessions**. The controlled 10-run measurement here gives 133.7 s (runs 5–10). The between-session spread (~15%) is larger than the within-plateau variation (CV 1.6%), so a single-session plateau shouldn't be quoted to better than about ±10% without controlling those factors.

## 13. NAX / tensor-unit execution (unchanged conclusion)
- MLX 0.32.2 (macOS-26 mlx-metal wheel) contains M5/NAX-capable Metal kernels, e.g. `qmm_t_nax`.
- This Mac (macOS 27.0, `applegpu_g17g`) satisfies MLX's `is_nax_available()` eligibility conditions (macOS ≥26.2, GPU gen ≥17).
- This strongly supports compatibility with the NAX execution path. However, no GPU kernel trace was taken, so per-kernel NAX execution is **not directly proven** by this or any prior experiment in this project.

## 14. Limitations
1. Throttling is inferred from timing; no temperature, clock or power telemetry (would need `powermetrics` with sudo).
2. Only one 10-run series. The ~12–15% level difference from the prior 3-run series (similar idle history) is unexplained, and between-session reproducibility of the plateau isn't established.
3. Behaviour beyond 10 runs (~22 min) is unmeasured. The weak +0.3%/run trend can't be excluded as a slow drift.
4. Ambient temperature wasn't recorded.
5. Residual swap at start (911 MB) differed from the prior phase (~0.5 GB). Swap stayed flat throughout, so no effect is evident.

## 15. Conclusions (answers)
- **A. Cold 1024² generation:** 84.6 s (run 1; 8.5–8.9 s/step). Earlier cool-start runs measured 83.6–103.8 s.
- **B. After thermal saturation:** 131.0–136.3 s per image (runs 5–10), mean 133.7 s.
- **C. Does performance stabilize?** Yes, to a near-plateau from run 5 (≈7 min of continuous load): CV 1.6%, with a weak residual upward trend of +0.4 s/run that isn't statistically separable from noise over 6 runs.
- **D. Sustained throughput:** 133.7 s/image mean (median 133.6), ≈26.9 images/hour generation-only, or ≈26.4 including the measured inter-run gap. The per-hour figure is an extrapolation beyond 10 runs.
- **E. Memory change with throttling?** No. Peak footprint 7.26–7.36 GB and MLX peaks identical in every run.
- **F. Swap?** Effectively zero (0 MB in 9 runs, 1.3 MB in one).
- **G. Pressure?** Normal (level 1) in 100% of samples across all 10 runs.
- **H. Pixel-identical?** Yes, all 10, and identical to the earlier session's 1024² runs.
- **I. vs sd.cpp 10-run:** sustained 133.7 s vs 356.8 s, so MFLUX takes 0.37× the time (≈2.7× throughput). Burst: 84.6 vs 360.6 s (0.23×). sd.cpp holds constant speed (+3.3% r1→r10); MFLUX loses 1.6× before stabilizing, and still stays faster in every regime measured.
- **J. Remaining bottleneck?** Consistent with **thermal** throttling, and not memory: every memory indicator was flat while throughput fell. The thermal attribution is inferred from within-run per-step drift and prior recovery-after-idle evidence, with no direct temperature or clock telemetry. That makes it **strongly suggested but not directly measured**.
- **K. Next highest-value experiment (evidence-driven):** the one open inference in this characterization is *why* throughput falls (J) and *why* the plateau level differs between sessions (§12). Both come down to missing thermal telemetry.
  - **Recommended:** a telemetry-instrumented repeat. Run the same 10-run protocol with `sudo powermetrics --samplers gpu_power,thermal,cpu_power -i 1000` logged alongside. It's read-only, but it needs your sudo authorization. It would directly measure GPU frequency, power and thermal-pressure state against the per-step times, turning "consistent with thermal throttling" into a measured attribution. If run in two sessions, and alongside a record of ambient temperature, placement and battery charge state, it would also show which factor drives the 131 vs 150 s between-session difference.
  - No optimization experiment (duty-cycling, precision changes) is recommended until the throttle mechanism is measured, since its value depends on what that shows.
