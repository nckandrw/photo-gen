# Qwen-Image-2.1 editing: runtime comparison (Phase 4, directive §13)

**Question:** which implementation gives PHOTO-GEN the best practical Qwen editing backend on this MacBook Air M5 (16 GB)?

**Candidates considered:** `QWEN-SOURCE-AUDIT.md` §5. Only the two serious, editing-capable, Apple-Silicon-native candidates were measured. The rest were excluded on documented evidence:
- **Diffusers MPS:** 33 GB bf16, plus a PyTorch MPS padding bug.
- **ComfyUI:** MPS VAE-encode corruption, #16433.
- **The two MLX q4 packs:** no vision tower, so they can't edit.
- **Edit-2511:** a 20B DiT; it doesn't fit.

| | **A: mflux 0.21.0 `QwenImage21Edit`** (selected) | **B: stable-diffusion.cpp `master-908`** (comparator) |
|---|---|---|
| backend | MLX 0.32.2 (Metal + NAX), the same MLX as production Z-Image | ggml Metal (tensor API on) |
| weights | local q4 export of the official checkpoint @ d26bb61. DiT + Qwen3-VL text/vision encoder at q4 (MLX affine, g64); VAE fp32. 10.64 GB, byte-reproducible export | `leejet/Qwen-Image-2.1-GGUF` Q4_K DiT @ cc11433 (the 2026-09-24 baseline file); official `Qwen3VL-8B-Instruct-Q4_K_M.gguf` + `mmproj-…-F16.gguf` @ f982a07; Comfy-Org bf16 VAE @ 9a44dbd |
| parity with the reference | mflux ships 35 component-level parity tests against Diffusers `80c7ed2` (fp32). Its validation reproduces its 1024² failures with the official pipeline | sd.cpp's own implementation; no published parity numbers. Its docs' example uses cfg 6.0, against the official 1.0 (D4) |
| edit features used | single reference, instruction, prefix KV cache, 40 steps, guidance 1.0 | `-r` reference + `--llm_vision`, prefix cache (default `auto`), 40 steps, cfg 1.0, euler |
| memory lifecycle | sequential under `--low-ram`, plus PHOTO-GEN's deferred DiT load (pixel-identical) | auto-fit; graph splitting; automatic VAE OOM fallback (observed 2026-09-24) |
| dependencies | separate venv: mflux, MLX, torch 2.13 and transformers 5.15 (processor/tokenizer); Python 3.12 | one native binary + dylib; no Python |
| maintainability | Python; same patch and probe pattern as production Z-Image; 3-day-old release with 1 open edit-API bug (#831, not on our path) | C++ binary; fast-moving master builds; Qwen-2.1 edit support is about 2 weeks old |
| determinism (measured) | repeat-identical (RGB and RGBA), and identical to the plain mflux CLI (`QWEN-EDITING-BASELINE.md`) | see §2 |

## 1. Measured: mflux (A)
`QWEN-EDITING-BASELINE.md`:
- **512:** 83–112 s per edit (median 103 s; ≈ 2.3 s/step), peak footprint 8.7–9.0 GB, no swap growth, no critical pressure.
- **1024:** 497 s cold and 556 s sustained median, 12.1 GB, warn-level episodes only.
- **Determinism:** repeat-deterministic and identical to the plain mflux CLI.
- **Quality:** G0 CAPABLE at both budgets.

## 2. Measured: sd.cpp (B), G1 chain (`g1-chain.sh`, 2026-10-07 04:01–04:29, AC, apps closed)
All runs at the 512 budget, 40 steps, cfg 1, euler, the same pre-resized 512² references as mflux. The configuration is the 2026-09-24 baseline's (auto-fit, no memory flags), plus `-r` and `--llm_vision`.

| run | wall (`/usr/bin/time`) | text+vision cond. | VAE encode | sampling | VAE decode | peak footprint | wired max | swap growth | warn / critical samples | min free |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|
| SMOKE (apple) | 287.1 s | 11.1 s | 1.5 s | 268.1 s (6.75 s/it) | 5.5 s | 12.77 GB | 12.53 GB | +3.91 GB | 233 / 0 | 9% |
| E01 | 289.3 s | 11.2 s | 1.4 s | 270.9 s | 5.4 s | 12.78 GB | 12.60 GB | +4.13 GB | 83 / 0 | 9% |
| E05 | 293.1 s | 12.3 s | 1.3 s | 273.7 s | 5.4 s | 12.79 GB | **13.39 GB** | +4.96 GB | 65 / **1** | 7% |
| E07 | 293.7 s | 10.9 s | 1.4 s | 275.8 s | 5.3 s | 12.78 GB | 12.51 GB | +4.81 GB | 100 / **1** | 7% |
| E11 | 293.4 s | 12.0 s | 1.4 s | 274.2 s | 5.4 s | 12.42 GB | 12.57 GB | +4.17 GB | 239 / **2** | 9% |

- No VAE OOM fallback at 512, and no run tripped the watchdog. But 3 of 5 runs had critical-pressure samples, and wired memory exceeded the 12.71 GB Metal recommended working set (E05).
- **Like-for-like mflux control** in the same chain: `G1-mflux-E01-parity`, 88.9 s, 8.97 GB, no swap growth, no warn samples. Its pixels are identical to G0-512-E01.
- **Implementation differences observed** (sd.cpp vs mflux/Diffusers), recorded rather than resolved:
  - sd.cpp uses its own "Flux scheduler" shift (μ = 0.630 at 1024 image tokens);
  - its own conditioning system prompt ("Comprehend and analyze the provided prompt.");
  - a bf16 Comfy-Org VAE.
  The Diffusers pipeline is the authority (D4); sd.cpp has no published parity tests for Qwen-2.1 editing.

## 3. Verdict
| criterion | mflux 0.21.0 (A) | sd.cpp master-908 (B) |
|---|---|---|
| correctness / parity | 35 reference tests vs Diffusers; parameters equal the official defaults | no published parity; scheduler and prompt template differ from the reference |
| edit quality (G1, 4 blind pairs) | 1 win | 1 win (2 ties); one sd.cpp **adherence failure** (E01 hybrid) |
| wall per 512 edit | **83–112 s (median 103 s)** | ≈ 287–294 s (**≈ 2.9× slower**) |
| peak footprint at 512 | **≈ 9.0 GB** | ≈ 12.8 GB |
| memory safety at 512 | **normal pressure, no swap growth** | swap +3.9–5.0 GB, critical samples in 3/5 runs, wired > Metal working set |
| 1024 | measured: 497 s cold, 12.1 GB, never critical | **not run** (bounded): at 512 it already reaches the 1024 memory level of mflux, and its 2026-09-24 t2i at 1024² needed a VAE OOM fallback with 2% free |
| determinism | repeat-identical; identical to the plain CLI | not measured |
| dependencies | separate Python venv (torch/transformers) | one native binary |
| maintainability | same worker/probe pattern as production; MLX shared with Z-Image | separate C++ toolchain; different numerics stack |

**Decision: mflux 0.21.0 (A) is the Qwen editing backend.**
- On this M5 it is ≈ 2.9× faster per edit and uses ≈ 3.8 GB less peak memory.
- It stays out of critical pressure; sd.cpp does not, even at 512.
- It is the implementation with demonstrated parity to the authoritative pipeline.
- **On quality the bounded A/B shows no separation.** The choice rests on performance, memory safety and correctness evidence, not on a quality win.
- sd.cpp remains a valid **comparator**: it uses no Python and keeps one binary for both Qwen families. It is not adopted.