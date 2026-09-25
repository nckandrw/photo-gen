# Validation test log — Qwen-Image-2.1 on MacBook Air M5 16 GB

Each run's raw evidence lives in `research/runs/<run-id>/` (cmd.txt, sd-cli.log, stderr.log incl. `/usr/bin/time -l`, monitor.csv at 1 Hz, pre/post.txt, summary.txt). Machine-readable rows: `bench.csv`. Peak memory = kernel "peak memory footprint" from `time -l` (includes Metal shared buffers) unless stated.

## Directive improvements applied
1. TE gate is run as the first stage of a minimal sd-cli run (no encode-only mode exists in `sd-cli -h`).
2. Scheduler: sd.cpp model-specific default (resolution-dependent flow schedule per sd.cpp docs) instead of forcing `simple`; actual scheduler recorded from logs.
3. mmproj (`--llm_vision`) validated in a separate run; t2i runs omit it (documented as edit-only), so t2i memory isn't inflated by an unused 1.16 GB tower.

## Phase 0 — machine state (2026-09-24 10:30)
Matches REPORT.md on every hardware/toolchain point. Log: `preflight-20260924-1030.log`. Memory free 72%, swap 0, no thermal warnings, **on battery (74%)**, lowpowermode 0.

## Phase 1–2 — sd.cpp acquisition + Metal
PASS. See versions.md. Minor discrepancy (logged, resolved): `SD_METAL` CMake option defaults OFF and CI doesn't pass it, but the binary links Metal.framework, exports 214 ggml_metal symbols and `--list-devices` shows `MTL0 Apple M5` → ggml's own Apple default enables Metal.

## Phase 3–5 — TE gate + DiT gate, 512², 8 steps, cfg 1, euler, seed 42 (run `p5-512-s8-seed42`, 10:36)
Command: `runs/p5-512-s8-seed42/cmd.txt` (no optional flags; auto-fit default; no --llm_vision). Power: battery. Other apps open (Safari/WebKit, Office) — auto-fit reported only 4885 MiB RAM free at start.

**Functional result: PASS.** Output `outputs/p5-512-s8-seed42.png` — coherent red apple on wooden table, window light; no NaN/noise/blocking.
- TE chain verified from log: GGUF parsed (`q4_K: 217, q6_K: 37, f32: 145`) → `llm: num_layers = 36, vocab_size = 151936, hidden_size = 4096, intermediate_size = 12288` → Qwen2 tokenizer (merges 151387, vocab 151674) → `get_learned_condition completed, taking 7.64s` (includes 6.80 s lazy weight load). WARN `no vision weights detected, vision disabled` — expected without --llm_vision.
- Model detected as `Version: Qwen Image 2.1`; DiT `q4_K: 192, bf16: 73`; VAE bf16 238 tensors, Wan-VAE graph.
- Scheduler actually used: **"get_sigmas with Flux scheduler"** (model default), sampler Euler.
- Timings: TE 7.64 s (6.80 load) · DiT load 6.51 s · sampling 50.79 s for 8 steps (first step 12.95 s/it incl. warmup) · VAE decode **23.59 s** at 512² · generate_image 82.02 s · wall 86.33 s.

**Memory result: significant pressure even at 512².**
- auto-fit plan placed **all three models on MTL0 at once**: DiT 4003 MiB + TE 4789 MiB (reported 4302 MB loaded) + VAE 644 MiB = **8949.76 MB params, all "VRAM"**, each with a compute reserve (2048/2048/1024 MiB). TE weights stay resident after encoding (no release).
- Peak footprint (time -l) **9.7 GB**; max RSS 9.6 GB; wired memory rose 2.85 → 13.8 GB (Metal residency sets).
- `kern.memorystatus_vm_pressure_level` = 2 (warn/yellow) for essentially the entire run, peak **4 (critical)** at/after VAE decode; min free 7%.
- Swap 0 → ~2.6 GB during sampling → **peak 6.55 GB** around VAE decode; compressed peak 8.23 GB.
- Interpretation: the report's key assumption (TE must be freed before DiT on 16 GB) is confirmed as the dominant factor; sd.cpp's default auto-fit budgets against the 12.1 GB Metal working set, not against the ~4.9 GB of truly free RAM.
