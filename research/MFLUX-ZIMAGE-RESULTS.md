# MFLUX / MLX Z-Image-Turbo on a MacBook Air M5 16 GB: measured results

**Date:** 2026-09-24 (15:50–17:30). Everything below was measured on this machine unless labelled.
**Evidence:**
- `runs/mf-*/` (cmd.txt, mflux.log, stderr.log with `/usr/bin/time -l` and tqdm per-step, monitor.csv at 1 Hz, phases.json from the instrumentation driver, summary.txt)
- `mflux-bench.csv` (incl. decoded-pixel sha256), `mflux-versions.md`, `outputs/mf-*.png`
- The comparator is the validated sd.cpp configuration in `FINAL-M5-COMPARISON.md` and `z-image-tests.md`.

## Environment
- MacBook Air M5 (10-core CPU, 8-core GPU, `applegpu_g17g`), 16 GiB, macOS 27.0 (26A428).
- **POWER=AC** throughout. Only Finder, Terminal and Claude Code running (same as the sd.cpp phase).
- Residual swap at start ≈0.5 GB (lower than during the sd.cpp phase); per-run Δ reported.
- MLX reports `max_recommended_working_set_size` 12.71 GB and `max_buffer_length` 9.53 GB, identical to the Metal query.

## Exact versions
- Python 3.12.14 (uv-managed, project-local), uv 0.12.18.
- mflux 0.20.0: installed tree byte-identical to the audited sdist (sha256 8fec3407…).
- mlx / mlx-metal 0.32.2 (macOS-26 wheel).
- torch 2.14.0, transformers 5.17.0 (mandatory deps, decision A).
- Full lock: `mflux/requirements.lock.txt`. All versions match the research; no discrepancy.

## Exact model
`mflux-community/z-image-turbo-mflux-q4` @ d2d30500c4bc0d19770bd952951df3e7c635ae9e: 11 files, 5,902,985,542 B. Every file hash-verified (LFS sha256 / git-sha1), listed in `mflux-versions.md`.

## Configuration
- `mflux-generate-z-image-turbo` (unmodified CLI `main()`, run through the timing driver `mflux/zi_driver.py`).
- Flags: `--model <local q4 pack> --base-model z-image-turbo --steps 9 --seed 42 --low-ram`, `HF_HUB_OFFLINE=1`.
- Guidance is forced to 0.0 by the Turbo CLI (official semantics). The scheduler is mflux's default for Turbo (linear sigmas + resolution-dependent shift). The directive specified no scheduler; this is the known minor divergence from the official static shift 3.0, which is close at 1024².
- **No workaround or environment override is needed.**

## Verified `--low-ram` semantics (installed source + runtime probes)
| Claim | Source check | Runtime probe (1024²) |
|---|---|---|
| Components built at init | `ZImageInitializer` builds VAE, transformer and TE | Weights are **lazy**: MLX active memory 0.0 GB after init (1.1 s); they load on first use |
| TE freed before denoising | `MemorySaver.call_before_loop` → `text_encoder=None`, `gc.collect()`, `mx.clear_cache()` | Active 2.21 GB after encode → **0.003 GB** before denoise ✔ |
| Cache limit reduced | `mx.set_cache_limit(1 GB)` under `--low-ram` | cache ≤1.06 GB during VAE ✔ (11.2 GB without `--low-ram`) |
| VAE tiling enabled | `TilingConfig()` implied (8 tiles/dim, 512 px); Z-Image VAE doesn't opt out | VAE MLX peak 5.70 GB tiled vs **10.70 GB** untiled ✔ |
| Transformer freed before VAE | `call_after_loop` → `_delete_transformer()` sets `model.transformer=None` | **✘ Not effective:** active stays **3.47 GB** into VAE decode. The compiled `predict` closure in `ZImage.generate_image` still references the transformer until the function returns. (Harmless here; noted for accuracy.) |
| TE freed without `--low-ram` too | non-low-ram branch also builds a `MemorySaver` | ✔ Also freed (0.003 GB) for single-seed runs, so the TE isn't the difference between modes |

**Memory by phase at 1024² (MLX allocator, `--low-ram`):**

| Phase | Peak |
|---|---:|
| init | 0.001 GB |
| text encode | 3.61 GB |
| denoise (DiT resident) | ≈3.47 GB active + activations |
| VAE decode (DiT still resident + tiled VAE) | 5.70 GB |

Process kernel peak footprint: **7.23 GB**, which includes Python, the imported torch/transformers (≈0.17 GB measured separately) and non-MLX buffers. Max RSS is only 2.6 GB because RSS excludes Metal buffers; footprint is the correct metric.

## Results

| Run | Res | State | TE (s) | Denoise (s) | s/step (first→last) | VAE (s) | Wall (s) | Peak footprint (GB) | Swap Δ | Pressure | Min free | Result |
|---|---|---|---:|---:|---|---:|---:|---:|---:|---|---:|---|
| mf-512 | 512² | cold file cache | 1.84 | 21.28 | – | 1.12 | 30.37 | 6.54 | 0 | L1 all | 39% | PASS |
| mf-512-probe | 512² | warm | 0.66 | 18.14 | – | 0.39 | 22.02 | 7.02 | 0 | L1 all | – | PASS, pixel-identical to mf-512 |
| mf-768 | 768² | | 0.65 | 42.03 | – | 1.43 | 46.91 | 7.22 | 0 | L1 all | 32% | PASS |
| mf-1024 | 1024² | after 2 short runs | 0.65 | 97.15 | 9.4 → 11.9 | 2.86 | 103.84 | 7.23 | 0 | L1 all | 36% | **PASS** |
| mf-th3-r1 | 1024² | consecutive | 0.65 | 88.72 | 8.9 → 10.8 | 2.79 | 95.25 | 7.24 | 0 | L1 all | – | PASS |
| mf-th3-r2 | 1024² | consecutive | 0.65 | 148.38 | 16.4 → 16.1 (**throttled**) | 3.23 | 155.56 | 7.23 | 0 | L1 all | – | PASS |
| mf-th3-r3 | 1024² | consecutive | 0.65 | 142.76 | 15.2 → 16.0 (**throttled**) | 2.92 | 149.57 | 7.22 | 0 | L1 all | – | PASS |
| mf-q-desk | 1024² | **after 10-min cooldown** | 0.66 | 81.35 | 8.7 → 9.2 | 2.00 | 87.20 | 7.25 | 0 | L1 all | – | PASS |
| mf-q-neon | 1024² | right after desk | 0.67 | 119.99 | 10.4 → 14.4 | 2.89 | 126.50 | 7.35 | 0 | L1 all | – | PASS |
| mf-diag-1024-nolowram | 1024² | after 10-min cooldown; **no `--low-ram`** (diagnostic) | 0.64 | 78.14 | 8.6 → 8.8 | 2.12 | 83.55 | **12.81** | **+2.12 GB** | **L4 (critical) ×2, L2 ×2** | 13% | PASS (memory unsafe) |

No run logged a warning, OOM or fallback. All images are valid, non-uniform and visually coherent.

## Peak memory
- `--low-ram`: **7.22–7.35 GB** footprint at every resolution. That's 5.70 GB of MLX peak (VAE decode with the DiT still resident) plus about 1.5 GB of runtime overhead.
- sd.cpp at 1024² measured 6.84 GB, so MFLUX uses **≈0.4 GB more** peak footprint. Despite that, system min-free stayed ≥32% (vs ≥8% for sd.cpp), pressure stayed L1, and there was no graph segmentation or OOM fallback.
- Without `--low-ram`: 12.81 GB footprint, critical pressure, +2.1 GB swap. **Unsafe on 16 GB.**

## Swap
Δ 0 in every `--low-ram` run (9 runs). +2.12 GB without `--low-ram`.

## Thermal results
- **Clear, repeatable thermal throttling under MFLUX:**
  - After a cooldown the chip starts at about 8.5–9 s/step.
  - It ramps within 1–2 images to a plateau of about **15.8–16.4 s/step** (≈1.8×). Wall time: 87–104 s cool → 150–156 s throttled.
  - 10 minutes idle restores the cool rate (desk 8.7 s/step).
  - pmset reported no thermal or performance warnings at any point; it doesn't expose GPU throttling on this Mac, so throttling is inferred from the per-step timing profile. Memory stayed flat and no other process was consuming significant CPU (top: WindowServer 38% max).
- **sd.cpp comparison:** its 10-run series stayed within 314–328 s (≤4.6% drift). Its tensor-off kernels ran at 36 s/step, apparently below the throttling threshold.
- **The 10-run MFLUX series was not run.** The 3-run series was not stable (r2 +67% vs r1), which the directive treats as a condition to stop and report. The throttled plateau from r2/r3 (≈150 s) is the best available estimate of sustained throughput, but it's **UNVERIFIED over 10 runs**.

## Determinism
- Decoded pixels are identical across **all four 1024² apple runs** (pixel sha256 `fe47d88dfb4bec549060c29c527eeff280d863e8e12176cdc1c28d3d8003a118`) and both 512² runs (`9ae59f59…`). That holds regardless of thermal state and of the instrumentation probes.
- PNG *files* differ between runs only in metadata chunks (eXIf/iTXt/tEXt, which include generation time). Pixel hashes are therefore the correct determinism check for MFLUX.
- Tiled vs untiled VAE: pixels differ (max |Δ| 39/255), with no visible difference at viewing scale.

## sd.cpp comparison (same Mac, AC, same prompts/seed/steps/resolutions)
| Metric | sd.cpp (tensor API disabled, #1990 workaround) | MFLUX `--low-ram` | Ratio MFLUX / sd.cpp |
|---|---:|---:|---:|
| 512² wall | 76.6 s | 22.0–30.4 s | 0.29–0.40 |
| 512² denoise | 69.0 s | 18.1–21.3 s | 0.26–0.31 |
| 768² wall | 168.4 s | 46.9 s | 0.28 |
| 768² VAE | 8.30 s | 1.43 s | 0.17 |
| **1024² wall, cool chip** | 360.6 s (n=19 mean; sd.cpp showed no throttling) | 87.2–103.8 s | **0.24–0.29** |
| **1024² wall, throttled plateau** | 360.6 s | 149.6–155.6 s | **0.41–0.43** |
| 1024² denoise, cool / throttled | 325.5 s | 81.4–97.2 / 142.8–148.4 s | 0.25–0.30 / 0.44–0.46 |
| 1024² VAE | 31.5 s | 2.0–3.2 s (tiled) | 0.06–0.10 |
| 1024² text encode | 3.3 s | 0.65 s | 0.20 |
| 1024² peak footprint | 6.84 GB | 7.23 GB | 1.06 |
| 1024² swap Δ / pressure | ~0 / L1 (1 run with L2) | 0 / L1 | – |
| OOM / fallback events at 1024² | VAE-OOM → tiled retry, every run | none | – |
| Correct with default settings | **No** (white images; needs env override) | **Yes** | – |
| Sustained drift | ≤4.6% (10 runs) | ≈+80% plateau after 1–2 images | – |
| Determinism | byte-identical files | pixel-identical (metadata differs) | – |

## Quality sanity check (apple, desk, neon at 1024² vs sd.cpp Z-Image outputs)
- **apple:** same subject, framing and lighting class (dewy pink-red apple on light oak by a window). MFLUX places the apple right of centre; sd.cpp centred it.
- **desk:** near-identical layout: notebook left, fountain pen centre, mug centre-back, brass twin-bell clock right, plant behind the clock. The same prompt-adherence weaknesses as sd.cpp (mug not clearly behind the notebook; plant not far background). Minor clock-numeral glitches in both.
- **neon:** `QWEN IMAGE 2.1` rendered exactly, on the same three-line layout. Colour differs (white-blue vs pink-red with a cyan frame), and the alley context is weak in both.
- **Conclusion:** no significant runtime-induced visual difference in structure, text or artifacts. Differences are those expected from different quantization formats (MLX affine q4 vs GGUF Q4_K), noise generation and the scheduler shift. **A full re-benchmark isn't warranted.**

## Whether MLX avoids the sd.cpp M5 tensor issue
- **Correctness: yes.** Every MFLUX output is correct with no workaround (9/9 runs + diagnostic).
- **M5 Neural Accelerator (NAX) use: STRONGLY SUPPORTED, not VERIFIED.**
  - The installed mlx-metal 0.32.2 macOS-26 wheel's `mlx.metallib` contains NAX kernels, including `qmm_t_nax`/`qmm_n_nax` for quantized matmul.
  - MLX's `is_nax_available()` (v0.32.2 `mlx/backend/metal/device.cpp` L947–966) requires macOS ≥ 26.2 and GPU architecture gen ≥ 17 for non-'p' parts; this device is `applegpu_g17g` on macOS 27.0, so the condition is true.
  - Kernel dispatch wasn't observed directly. MLX has no runtime switch to disable NAX, so an A/B test wasn't possible.
  - The speed result is consistent with NAX use but isn't treated as proof.

## Answers
- **Q1 Correct output on this M5?** Yes, at 512/768/1024², in 10 of 10 runs.
- **Q2 Avoids the sd.cpp tensor-path corruption?** Yes, with no environment override. NAX kernels are very likely active (strongly supported).
- **Q3 Actual memory?** 7.2–7.35 GB peak footprint (MLX peak 5.70 GB) with `--low-ram`; 12.81 GB without.
- **Q4 Speed at 1024²?**
  - 87–104 s per image on a cool chip.
  - ≈150–156 s at the throttled plateau reached after 1–2 consecutive images.
- **Q5 vs sd.cpp's 360.6 s?** 0.24–0.29× cool and 0.41–0.43× throttled, so 2.3–4.1× faster in every measured thermal state.
- **Q6 Does `--low-ram` help materially?** Yes. It cuts peak footprint by 5.6 GB (12.81 → 7.23 GB) and turns critical pressure plus 2.1 GB swap into L1 with no swap, at a VAE cost of about +0.7 s. Denoise speed is unaffected. It's required for safe 1024² on 16 GB.
- **Q7 Thermal sustain?** Worse *stability*, better *throughput*. MFLUX throttles ≈1.8× within 1–2 images, while sd.cpp is flat. Even throttled, MFLUX is 2.3× faster. The 10-run sustain wasn't executed (stop rule).
- **Q8 Deterministic?** Yes at the pixel level (identical pixel sha256 across runs and thermal states). File bytes differ only in metadata.
- **Q9 Visible quality change vs sd.cpp?** No significant runtime-induced difference on 3 prompts.
- **Q10 Production runtime: sd.cpp or MFLUX?** **On the measured evidence, MFLUX for Z-Image-Turbo text-to-image.**
  - It's correct without a workaround (sd.cpp fails silently without one).
  - It's 2.3–4.1× faster per image in every thermal state measured.
  - It has no OOM fallbacks, better system headroom (min free ≥32%), zero swap, and pixel-level determinism.
  - Trade-offs: ≈0.4 GB higher process footprint; a larger dependency surface (Python + torch + transformers, ≈0.17 GB imported); and throttling-driven variability in sustained batches.
  - sd.cpp remains the validated runtime for Qwen-Image-2.1 and a zero-Python fallback for Z-Image.

## Known limitations
1. The 10-run MFLUX sustain wasn't executed (the 3-run series was unstable). Long-batch throughput beyond 3 consecutive images is unmeasured.
2. NAX use is inferred from source plus wheel contents, not observed via GPU capture.
3. Thermal state was inferred from per-step timing; pmset exposes no GPU throttle data here.
4. n=1 seed per prompt for the quality sanity check. Scheduler differs from official static shift 3.0 (mflux default).
5. The sd.cpp comparison mixes quantization formats (GGUF Q4_K vs MLX affine q4), which is inherent to comparing the runtimes.
6. `--low-ram`'s transformer release before the VAE is ineffective in mflux 0.20.0 (closure reference). An upstream fix would lower the VAE-phase peak by about 3.5 GB, which is untested.
7. Residual swap before the MFLUX phase (≈0.5 GB) differed from the sd.cpp phase (0.8–2.4 GB). Deltas are reported.
