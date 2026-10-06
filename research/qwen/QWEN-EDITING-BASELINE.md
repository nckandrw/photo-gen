# Qwen-Image-2.1 editing baseline on the MacBook Air M5 16 GB (Phase 4, directive §11–§12)

## Configuration
| | |
|---|---|
| model | Qwen-Image-2.1 @ `d26bb61` (Qwen Research License, non-commercial), local q4 export `models/qwen/qwen-image-2.1-edit-mflux-q4` (18 files pinned in `config/backend-qwen21-edit-mflux.json`) |
| precision | DiT and Qwen3-VL text/vision encoder q4 (MLX affine, g64); bf16 activations; VAE fp32 |
| runtime | mflux 0.21.0 + MLX 0.32.2 in `mflux-qwen/.venv` (CPython 3.12.14); `mflux-generate-qwen-2.1-edit` `main()` unmodified, in a fresh worker process per job |
| sampling | upstream defaults: 40 steps, guidance 1.0 (no CFG, no negative pass), prefix KV cache on, linear flow-match Euler with resolution-dependent shift, seed 42 |
| memory flags | `--low-ram` (MemorySaver: MLX cache limit 1 GB, text encoder released before denoising, transformer released before decode, tiled VAE encode and decode 512 px) + PHOTO-GEN's deferred DiT load (§3) |
| machine | MacBook Air M5 16 GB, macOS 27.0 (26A428), AC power |

## 1. Correctness, passivity, determinism (smoke, 512 budget)
Input: the BALANCED p01 apple (`befe1b3c…`, 1024²). Instruction: the official model-card example "Change the background to a sunset beach".

| run | path | pixel sha256 (RGB) | RGBA sha256 |
|---|---|---|---|
| S1 | production (`bin/photo-gen edit`, probes) | `f7aa22f650100d78…` | `49a202cbec738122…` |
| S2 | plain mflux CLI, same args, no PHOTO-GEN code | `f7aa22f650100d78…` | `49a202cbec738122…` |
| S3 | S1 repeated | `f7aa22f650100d78…` | `49a202cbec738122…` |
| A0r2 / A1r2 | production worker, stock lifecycle / deferred DiT load | `f7aa22f650100d78…` (both) | `49a202cbec738122…` (both) |
| B0r2 / B1r2 | the same at the 1024 budget | `10296d4bfd392bf0…` (both) | `76f60a786ba8…` (both) |

- **The PHOTO-GEN probes are passive.** Production and the plain CLI produce identical pixels.
- **Edits are repeat-deterministic** on this machine and software.
- **The deferred DiT load is exact** at both budgets.
- **Output alpha.** mflux writes RGBA. For these non-RGBA prompts, alpha ranges 253–255, so it is not exactly opaque. The canonical `pixel_sha256` (RGB, the project-wide definition) is complemented by the recorded `rgba_sha256`.
- Determinism is only claimed for the same input pixels, instruction, seed, steps, budget, export and software. MLX and PyTorch RNGs differ, so seeds do not transfer to Diffusers.

## 2. Where the memory goes: mflux 0.21.0's lifecycle (stock)
The passive per-phase probes (MLX active and peak allocator memory) show the stock edit lifecycle at 512:

| point | MLX active / peak |
|---|---:|
| after load (TE + DiT + VAE all materialized) | 10.29 GB active |
| text + vision encode | 11.53 GB peak |
| reference VAE encode | **12.00 GB peak** |
| before the denoise loop (TE released by MemorySaver) | 5.52 GB active |
| denoise | 7.28 GB peak |
| VAE decode | 6.09 GB peak |

- The peak sits **before** denoising.
- mflux's initializer materializes all three components at load, so the ~4.1 GB q4 DiT is resident through text/vision encoding and the reference VAE encode, where it is never used.
- At 1024 the stock pre-loop peak is 13.92 GB MLX (VAE encode), with a 14.20 GB process footprint and a critical-pressure episode.

## 3. Lifetime fix: deferred DiT load (Improvement Clause record)
| | |
|---|---|
| **Original approach** | mflux 0.21.0's lifecycle unchanged: every component materialized at load. |
| **Proposed approach** | In the edit worker, skip `Qwen21Initializer._materialize` for the transformer only. Its pre-quantized weights stay lazy MLX loads and are read from the export at denoising step 0, after MemorySaver has released the text encoder. Same weights, same graph, same kernels; only when the bytes are read changes. |
| **Evidence** | Pixel parity, RGB **and** RGBA, at 512 (A0r2 = A1r2 = S1 = S2 = S3) and 1024 (B0r2 = B1r2). Memory table below. |
| **Why it is superior** | The stock lifecycle put the 16 GB machine into **critical** memory pressure at both budgets (1 sample each) and grew swap by 3.4–4.5 GB. Directive §12 makes memory safety a hard requirement and calls for "controlled model lifetime / explicit model loading". |
| **Expected benefit** | Peak footprint −3.78 GB at 512 and −2.12 GB at 1024. At 1024 the residual peak is now denoising itself (11.0 GB MLX). |
| **Compatibility impact** | None on outputs (pixel-identical). The `load` phase no longer includes reading the DiT, and step 0 absorbs it (≈ 1.5 s), so compare stock and deferred phase tables accordingly. Recorded per job as `effective_parameters.defer_transformer_load`. |
| **What it replaces** | The stock materialize-all-at-load lifecycle (still selectable in research via `worker_run.py … 0`). |

| run (1 each, sustained, AC) | budget | lifecycle | footprint peak | MLX peak (phase) | denoise MLX peak | swap growth | warn / critical samples | min free |
|---|---:|---|---:|---|---:|---:|---|---:|
| A0r2 | 512 | stock | 12.63 GB | 12.00 (VAE encode) | 7.28 | +3.44 GB | 0 / **1** | 14% |
| A1r2 | 512 | deferred | **8.85 GB** | 7.85 (VAE encode) | 7.23 | 0 | 0 / 0 | 36% |
| B0r2 | 1024 | stock | 14.20 GB | 13.92 (VAE encode) | 11.13 | +4.53 GB | 35 / **1** | 14% |
| B1r2 | 1024 | deferred | **12.08 GB** | 11.01 (denoise) | 11.01 | +2.87 GB | 38 / 0 | 25% |

These smoke runs had the user's meeting apps (Teams, Brave, Slack) open and 4–5 GB of residual swap, so the absolute swap and free figures are **confounded**. The lifecycle comparison is internally paired (same conditions, back to back). The clean baseline is §4.

## 4. Clean baseline (G0 chain: apps closed, AC, git `a7cc451`, production path with the deferred DiT load)
### 4.1 Cold 1024² (directive §11): `G0-1024-E05-cold`, after 600 s idle, 2026-10-07 02:09
Source E05 (1024² Z-Image REFERENCE); instruction "Change the background to a sunset beach"; seed 42; 40 steps.

| metric | value |
|---|---:|
| load (DiT deferred; TE + VAE materialized) | 1.61 s |
| text + vision encode | 3.57 s |
| reference VAE encode (tiled) | 1.64 s |
| **denoise, 40 steps** | **474.1 s** (step 0 16.9 s incl. the DiT read and prefix KV; median 12.77 s/step) |
| VAE decode (tiled) | 12.80 s |
| **total wall** (job generation_seconds; worker process incl. Python start) | **496.8 s** |
| peak footprint (libproc lifetime max) | 12.08 GB |
| MLX peak: VAE encode / denoise / decode | 9.77 / 11.01 / 6.12 GB |
| MLX active after load / before denoise | 6.14 / 1.39 GB |
| swap: start → max (growth) | 1.00 → 2.89 GB (+1.89 GB) |
| kernel memory pressure (1 Hz) | 10 of 351 samples warn, **0 critical**; min free 24% |

### 4.2 Sustained suites (11 benchmark tests + 1 repeat per budget, back to back with 20 s gaps)
| | **512 budget** (12 runs, 01:34–01:59) | **1024 budget** (11 runs after the cold one, 02:18–04:00) |
|---|---:|---:|
| wall per edit: median (min–max) | **103.3 s** (83.0–112.2) | **556.4 s** (477.9–601.0) |
| denoise: median | 96.2 s (2.31 s/step) | 532.1 s (13.16 s/step) |
| text + vision encode / VAE encode / VAE decode | 1.1 / 0.5 / 1.6 s | 4.2 / 2.0 / 12.4 s |
| load | 1.5 s | 1.5 s |
| peak footprint | 8.69–8.98 GB | 12.08–12.31 GB |
| MLX peak (phase) | 7.85 GB (VAE encode) | 11.01 GB (denoise) |
| swap growth per run | 0–0.36 GB | 1.30–2.12 GB |
| warn / critical samples per run | 0–1 / **0** | 4–11 / **0** |
| min free | 24–47% | 25–29% |

- **Denoising dominates:** 93% of an edit at 512 and 96% at 1024.
- **1024 costs about 5.4× the 512 time** for 4× the pixels. Target and reference tokens both grow 4×, and attention grows faster.
- **Sustained 1024 timing is not monotone in heat.** The second half of the suite (E08–E11, 478–494 s) ran faster than the first (E01–E07, 556–601 s). These figures are observations, not a thermal model.
- **Determinism:** E05 repeated at the end of each suite reproduced its pixels exactly (512 `bd548f1b…`, 1024 `792fdaa9…`).

### 4.3 Memory safety verdict (directive §12)
**Safe at both budgets, with margin at 512 and a tight margin at 1024.**
- No run in either suite produced a critical-pressure sample or tripped the watchdog.
- **1024** costs 1.3–2.1 GB of swap growth per edit and spends a few seconds at warn level. Its 11.0 GB denoise peak is now the binding phase: DiT 4.1 GB + VAE 1.35 GB + prefix KV cache (estimated ≈ 2.2 GB: bf16, ≈ 4.3k prefix tokens × 32 layers × K,V × 4096) + attention activations. The backlog item Q-M covers reducing it.
- **The stock mflux lifecycle is not memory-safe on this machine** (critical episodes at both budgets, §3). The deferred DiT load is therefore a production requirement, not an optimization.
- **Large apps open** (the smoke runs) add the measured 3–4.5 GB of swap growth at 1024. The user guidance is to close them before 1024 edits.

## 4.4 End-to-end through the HTTP API (`research/qwen/api-check/`, 2026-10-07 04:35)
A real `bin/photo-gen serve`, on the same code as the G0 chain.
- **`POST /edit`:** E05 at 512 with seed 42, through the server's background worker thread. Completed in 79.4 s with pixels `bd548f1b…`, **identical to G0-512-E05** (the CLI path); `GET /outputs/{id}` served the same pixels.
- **`POST /jobs/{id}/cancel` on a running edit** (E01, about 20 s into denoising):
  - the edit worker (pid 36900, edit venv) was killed;
  - the job became `cancelled` ("cancelled while running") with no output file;
  - `pgrep` found no edit worker afterwards;
  - `/status` showed pressure normal, 82% free, 1.98 GB wired.
- **Queue afterwards:** a ULTRA 512 generation gave `6aa2b842…`, as pinned.

After this check, `EditRequest` gained `backend_id`/`model`/`model_revision` (so queued and failed jobs name their model) and the edit sidecar gained `model_manifest.sha256`. Both are metadata only. A real CLI edit afterwards gave the identical `bd548f1b…` (`api-check/cli-edit-after-metadata-fix.json`).

## 5. Performance target (directive §25)
| criterion | 512 | 1024 |
|---|---|---|
| safe enough memory behaviour | **yes** (no swap growth, normal pressure) | **yes, tight** (warn-level episodes, +1.3–2.1 GB swap, never critical) |
| usable latency | **yes** (≈ 1.5–2 min) | **marginal** (≈ 8.3 min cold, 9–10 min sustained); usable for one-off edits, not interactive iteration |
| repeatable operation | **yes** (24/24 G0 runs rc 0; repeats pixel-identical) | **yes** |
| acceptable edit quality | G0 **CAPABLE** (`QWEN-EDITING-QUALITY.md`) | G0 **CAPABLE**; the one 512 preservation failure (E08) did not recur (one seed per test) |

No speed optimization was attempted in this phase (directive §26). The first speed lever is fewer denoising steps (backlog Q-S), because denoising is ≥ 93% of every edit.
