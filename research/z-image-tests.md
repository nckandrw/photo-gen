# Z-Image-Turbo vs Qwen-Image-2.1 — controlled validation log

Raw evidence per run: `research/runs/<TEST ID>/` (cmd.txt, sd-cli.log, stderr.log with `/usr/bin/time -l`, monitor.csv at 1 Hz, pre/post.txt, summary.txt). Monitor logs are also copied to `research/z-image-monitor-<TEST ID>.log`. Peak memory = kernel "peak memory footprint" (`time -l`) unless stated. Pressure levels: 1 normal, 2 warn, 4 critical (`kern.memorystatus_vm_pressure_level`).

## Environment (Phase 0, 2026-09-24 10:59)
Preflight: `preflight-zimage-20260924-1059.log`. POWER=AC (charging). macOS 27.0 (26A428), M5, 8-core GPU, Metal 4, 16 GiB. Safari quit via AppleScript (graceful); Office was already closed. Remaining GUI apps: Finder, Terminal. Memory free 77%; **residual swap 0.83 GB carried over from the earlier Qwen run** (macOS does not reclaim swap without reboot; runs report swap *delta*). No thermal warnings.

## Directive improvement 1 (applied)
Directive's "cfg = 0" → sd.cpp `--cfg-scale 1`. In sd.cpp @88411ef (`src/pipeline/request.cpp` L311–314) cfg-scale 0 triggers "unconditioned mode, images won't follow the prompt (use cfg-scale=1 for distilled models)"; cfg-scale 1 is the no-CFG path equivalent to diffusers `guidance_scale=0`. Recorded as guidance=0 / cfg=1.

---
TEST ID: zi-t1-512
DATE: 2026-09-24 11:05
POWER: AC
OS: macOS 27.0 (26A428)
RUNTIME: stable-diffusion.cpp sd-cli (Metal, auto-fit default)
RUNTIME VERSION: master-908-88411ef
MODEL: DiT z_image_turbo-Q4_K.gguf · TE Qwen3-4B-Q4_K_M.gguf · VAE ae.safetensors
MODEL REVISION: leejet c61c0e4 · Qwen bc64014 · Comfy-Org 6fc90a3
SHA256: 14b375ab… · 7485fe6f… · afc8e282… (full in z-image-versions.md)
RESOLUTION: 512×512
STEPS: 9
GUIDANCE: 0 (official semantics)
CFG: 1 (sd.cpp flag)
SEED: 42
PROMPT: a red apple on a wooden table, soft window light
RESULT: **FAIL — output corruption.** Process rc=0, no warnings/errors, but PNG is uniformly white (all pixel bytes 255).
LOAD TIME: TE 3.28 s + DiT 5.27 s + VAE 0.41 s (lazy loads)
DENOISING TIME: 45.08 s (9 steps)
VAE TIME: 3.22 s
TOTAL TIME: 52.14 s wall (generate_image 51.91 s)
PEAK MEMORY: 7.21 GB footprint; max RSS 7.14 GB
PEAK SWAP: 0 MB growth (824.5 MB residual → 824.5)
THERMAL RESULT: no warnings; pressure level 1 throughout; min free 25%
OUTPUT: outputs/zi-t1-512.png
FAILURE/NOTES: Load test passed: `Version: Z-Image`; TE `llm: num_layers = 36, vocab_size = 151936, hidden_size = 2560, intermediate_size = 9728`; Qwen2 tokenizer (vocab 151674); chat-template prompt; auto-fit put DiT 3685 + TE 2375 + VAE 160 MiB = **6221 MB params on MTL0** (vs 8950 MB for Qwen-2.1). Scheduler logged: "discrete". Weight stats DiT f32 251 / q8_0 22 / q4_K 180. Corruption matches open upstream bug **sd.cpp #1990** (2026-09-18, Apple M5 Max, same leejet GGUFs Q4_K/Q8_0): "tensor-API path silently outputs blank white PNGs (exit 0) — GGML_METAL_TENSOR_DISABLE=1 restores correct output".

---
TEST ID: zi-t1-512-diag-tensoroff (DIAGNOSTIC, not primary)
DATE: 2026-09-24 11:08
POWER: AC
OS / RUNTIME / MODELS / SHA256 / RESOLUTION / STEPS / GUIDANCE / CFG / SEED / PROMPT: identical to zi-t1-512
ENV: GGML_METAL_TENSOR_DISABLE=1 (process-scoped; recorded in runs/zi-t1-512-diag-tensoroff/env.txt). ggml log confirms `has tensor = false`.
RESULT: **Correct image** — photoreal red apple on wooden table, window light background; no artifacts.
LOAD TIME: TE 3.24 s + DiT 5.28 s + VAE 0.41 s
DENOISING TIME: 69.30 s (9 steps; +54% vs tensor-API path)
VAE TIME: 3.84 s
TOTAL TIME: 83.08 s wall (generate_image 76.62 s)
PEAK MEMORY: 7.27 GB footprint; max RSS 6.87 GB
PEAK SWAP: 0 MB growth
THERMAL RESULT: no warnings; pressure level 1; min free 23%
OUTPUT: outputs/zi-t1-512-diag-tensoroff.png
FAILURE/NOTES: Confirms sd.cpp #1990 reproduces on base M5 (8-core GPU). Classification of root cause: **Backend failure** (ggml Metal tensor-API kernels, M5-specific), not model/format/memory.

## Category labels (per decision 2026-09-24, Option A)
- **Z-Image default sd.cpp** → FAIL — M5 Metal tensor backend bug (#1990): `zi-t1-512`
- **Z-Image tensor-disabled** → PASS — workaround (`GGML_METAL_TENSOR_DISABLE=1`, Metal tensor API = disabled): `zi-t1-512-diag-tensoroff`, `zi-p-*`
- **Qwen tensor-enabled** → Primary control: `qw-p-*`
- **Qwen tensor-disabled** → Backend diagnostic: `qw-diag-*`
Tooling added: `zrun.sh` (Z-Image wrapper, sets env + writes env.txt), `record.py` (log→CSV extraction), `imgcheck.py` (PNG uniformity check). Bench rows are machine-extracted from logs.

---
TEST ID: zi-p-512 — Z-Image tensor-disabled (PRIMARY + #1990 WORKAROUND)
DATE: 2026-09-24 11:14 · POWER: AC · OS: macOS 27.0 (26A428) · RUNTIME: sd.cpp master-908-88411ef, Metal, auto-fit default, Metal tensor API = disabled
MODEL / REVISION / SHA256: as z-image-versions.md (DiT c61c0e4 14b375ab…, TE bc64014 7485fe6f…, VAE 6fc90a3 afc8e282…)
RESOLUTION: 512×512 · STEPS: 9 · GUIDANCE: 0 · CFG: 1 · SEED: 42 · PROMPT: apple
RESULT: PASS — correct image, **byte-identical** to the diagnostic run (determinism confirmed)
LOAD TIME: 8.77 s (TE 3.27 + DiT 5.09 + VAE 0.41, lazy) · TEXT ENCODE: 3.49 s (incl. TE load)
DENOISING TIME: 69.03 s (7.7 s/step) · VAE TIME: 3.80 s · TOTAL TIME: 76.58 s wall
PEAK MEMORY: 7.26 GB footprint · PEAK SWAP: +0.00 GB · PRESSURE: level 1 for 66/66 samples; min free 17%
THERMAL RESULT: no warnings · OUTPUT: outputs/zi-p-512.png

---
TEST ID: zi-p-768 — Z-Image tensor-disabled (PRIMARY + #1990 WORKAROUND)
DATE: 2026-09-24 11:16 · POWER: AC · same runtime/models
RESOLUTION: 768×768 · STEPS: 9 · GUIDANCE: 0 · CFG: 1 · SEED: 42 · PROMPT: apple
RESULT: PASS — correct photoreal image (apple with water droplets, window, wooden table); no artifacts
LOAD TIME: 9.77 s · TEXT ENCODE: 3.41 s · DENOISING TIME: 156.37 s (17.4 s/step) · VAE TIME: 8.30 s · TOTAL TIME: 168.38 s wall
PEAK MEMORY: 7.10 GB footprint · PEAK SWAP: +0.18 GB · PRESSURE: level 1 for 135/142 samples; **level 2 (warn) for 7 samples, all at the end (VAE decode)**; wired peaked 12.78 GB (≈ Metal working set 12.71 GB); min free 8%
THERMAL RESULT: no warnings · OUTPUT: outputs/zi-p-768.png

---
TEST ID: zi-p-1024 — Z-Image tensor-disabled (PRIMARY + #1990 WORKAROUND) — **1024² PRIMARY GATE**
DATE: 2026-09-24 11:19 · POWER: AC · same runtime/models · natural baseline (no memory flags)
RESOLUTION: 1024×1024 · STEPS: 9 · GUIDANCE: 0 · CFG: 1 · SEED: 42 · PROMPT: apple
RESULT: **PASS** — valid, correct, detailed image; no OOM; pressure level 1 for 305/305 samples; swap +0.00 GB; no numerical corruption
LOAD TIME: 8.36 s · TEXT ENCODE: 3.22 s · DENOISING TIME: 326.51 s (36.3 s/step) · VAE TIME: 32.23 s · TOTAL TIME: 362.30 s wall (6.0 min)
PEAK MEMORY: 6.88 GB footprint · PEAK SWAP: +0.00 GB · compressed ≤ 2.31 GB · wired ≤ 11.57 GB · min free 16%
THERMAL RESULT: no warnings recorded (pmset) · OUTPUT: outputs/zi-p-1024.png
FAILURE/NOTES: Minor discrepancy (logged, not material): Z-IMAGE-TURBO-REPORT §12 modeled 3.2–3.9 min DiT (±2×); measured 5.44 min with tensor API disabled (the ~35% tensor-off penalty measured at 512² explains most of the gap). Scaling 768→1024: 2.09× denoise for 1.78× tokens.

---
TEST ID: zi-th3-r1..r3 — Z-Image tensor-disabled, 3 consecutive 1024² (no cooldown)
DATE: 2026-09-24 11:33–11:52 · POWER: AC · config identical to zi-p-1024
| Run | Start | Denoise (s) | VAE (s) | Wall (s) | Peak footprint (GB) | Swap Δ (GB) | Pressure | Thermal |
|---|---|---:|---:|---:|---:|---:|---|---|
| zi-p-1024 (reference) | 11:27:09 | 326.51 | 32.23 | 362.30 | 6.88 | 0.00 | L1 only | no warnings |
| r1 | 11:33:44 | 324.73 | 33.15 | 361.46 | 6.87 | 0.00 | L1 only | no warnings |
| r2 | 11:39:49 | 338.74 | 30.41 | 372.75 | 6.75 | +0.27 | L2 for 34/312 samples (11:41:26–31 and 11:43:30–11:44:07, mid-denoise) | no warnings |
| r3 | 11:46:05 | 336.55 | 31.17 | 371.50 | 6.83 | 0.00 | L1 only | no warnings |
RESULT: **STABLE.** Denoise drift r1→r3 +3.6% (max +4.3% at r2); no thermal warnings from pmset; no memory growth in sd-cli (footprint 6.75–6.88 GB). All four 1024² outputs **byte-identical**.
NOTES: The r2 warn window coincides with a ~2 GB rise in system wired memory while sd-cli's own footprint stayed flat at 6.02 GB (monitor proc_mem_gb) → attributed to transient system-wide activity, not the generator (cause not identified). pmset exposes no CPU_Speed_Limit on this machine, so throttling is inferred from timing only.

---
## CORRECTION (2026-09-24, after quality runs) — zi-p-1024 reclassified PASS → CONDITIONAL PASS
Evidence missed in the original zi-p-1024 entry: every Z-Image 1024² run (zi-p-1024, zi-th3-r1..3, zi-q-*) logged
`WARN model_manager.cpp:1831 - model manager cannot make enough memory available on MTL0: need 7263.57 MB device / 6751.57 MB budget, available 6123.25 MB device / 5611.57 MB budget`
followed by `WARN backend_fit.cpp:506 - VAE decode ran out of memory; retrying with spatial tiling` (VAE tile 64×64 latent, 3×3 tiles).
Nature: sd.cpp's model manager refused the *untiled* VAE decode allocation before attempting it (DiT 3.7 GB + TE 2.4 GB still resident) and fell back automatically; no Metal allocation failed, system pressure stayed level 1, swap Δ 0, output valid. The directive's PASS definition requires "no OOM", so the label becomes **CONDITIONAL PASS (VAE-OOM-fallback)**. 512² and 768² Z-Image runs did NOT log this warning.
Same mechanism on Qwen: qw-p-768, qw-p-1024 and all qw-q-* (need 8771.81 MB, available 3817.62 MB at 1024²). Shortfall at 1024²: Z-Image ≈1.1 GB vs Qwen ≈5.0 GB.
Original rows retained; result column rewritten as "CONDITIONAL PASS (was: PASS)" with a CORRECTION note.

---
TEST ID: zi-th10-r1..r10 — Z-Image tensor-disabled, 10 consecutive 1024² (no cooldown)
DATE: 2026-09-24 14:01–15:02 · POWER: AC · config identical to zi-p-1024 · preceded by ~3.5 h of near-continuous GPU load (quality benchmark)
| Run | Denoise (s) | VAE (s) | Wall (s) | Footprint (GB) | Swap Δ | Pressure |
|---|---:|---:|---:|---:|---:|---|
| r1 | 313.99 | 31.48 | 349.05 | 6.83 | 0 | L1 |
| r2 | 327.86 | 31.32 | 362.72 | 6.87 | 0 | L1 |
| r3 | 328.40 | 32.05 | 363.99 | 6.83 | 0 | L1 |
| r4 | 322.93 | 30.93 | 357.57 | 6.86 | 0 | L1 |
| r5 | 322.21 | 30.96 | 356.77 | 6.82 | 0 | L1 |
| r6 | 319.99 | 30.78 | 354.34 | 6.87 | 0 | L1 |
| r7 | 319.68 | 30.70 | 353.92 | 6.83 | 0 | L1 |
| r8 | 320.45 | 30.93 | 354.94 | 6.83 | 0 | L1 |
| r9 | 319.88 | 31.10 | 354.53 | 6.87 | 0 | L1 |
| r10 | 325.61 | 31.33 | 360.51 | 6.82 | 0 | L1 |
RESULT: **STABLE.** Denoise range 314.0–328.4 s (±2.3% of mean); r10/r1 = 1.037; r3/r1 = 1.046; no monotonic degradation. All 10 outputs **byte-identical** to zi-p-1024. Footprint flat (no leak). Swap Δ 0 every run. pmset: no thermal/performance warnings at any run boundary. Every run logged the VAE-OOM-fallback (expected; see CORRECTION) → CONDITIONAL PASS per definition, stable.
