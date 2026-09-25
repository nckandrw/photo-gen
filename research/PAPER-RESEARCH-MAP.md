# photo-gen paper research map (initial pass, 2026-09-24)

This map covers the first pass over the 27 papers in the research addendum. Detail per paper is in `papers/index.md`. The architecture grounding is in `z-image-architecture-map.md`. The ranked experiments are in `EXPERIMENT-BACKLOG.md`.

**Depth of review (honest):**
- **Audited against source and measurements:** Z-Image (2511.22699), TMP (2606.27089, body read for the Z-Image section), FlashAttention (principle checked against MLX's fused SDPA, measured).
- **Abstract only so far:** the other 24. Mechanism statements for those are provisional until each reaches AUDIT.
- **No paper result is presented as a photo-gen result.**

## 1. The measured frame every paper was judged against
Measured on this M5 (E00–E02):
- At 1024², **denoise is ≈94% of wall time**.
- Within a DiT block (production state): **FFN 56%, QKV 19%, SDPA 18%, out-proj 6%**.
- Production mflux 0.20.0 **runs the DiT hidden stream in float32**, an unreported upstream behaviour (E01). A bf16 stream is measurably faster (E02).
- **q4 is the fastest weight format** on this GPU.
- **VAE ≈3% and text encoder <1%** of wall time.

That frame decides transferability more than any paper's headline number: attention-only ideas have a ceiling of ≈18% of denoise, VAE ideas ≈3%, and anything that reduces steps, precision cost, or FFN work acts on most of the runtime.

## 2. Papers, mechanisms and transferability

| Paper | Key mechanism | → Z-Image-Turbo | → MFLUX | → MLX | Apple Silicon limitation | Class |
|---|---|---|---|---|---|---|
| Z-Image 2511.22699 | S3-DiT single stream; Qwen3-4B TE; Flux VAE; 8-NFE Turbo | is the model | implemented (map verified) | bf16 reference semantics vs mflux fp32 promotion | none | DIRECTLY TRANSFERABLE |
| TMP 2606.27089 | MLP-width pruning (−37.5%) + tree-structured mixed-policy distillation recovery | yes (paper applies it) | would load if shapes are re-declared (UNVERIFIED) | yes | recovery training needs datacenter GPUs; **no Z-Image artifact released** | PARTIALLY TRANSFERABLE — blocked |
| Decoupled-DMD 2511.22677 | CFG-augmentation drives few-step distillation; DM regularizes | produced Turbo's 8-NFE recipe | n/a (training) | n/a | training infeasible locally | CONCEPTUALLY USEFUL; inference step sweep directly testable (E03) |
| FastCache 2505.20353 / TokenCache 2409.18523 / DeepCache 2312.00858 / 6Bit-Diffusion 2603.18742 | reuse hidden states/tokens/blocks across steps when change is small; block I/O difference predicts sensitivity | unknown redundancy at 8 NFE | needs hooks in the compiled predict | gather/scatter overhead unmeasured | bookkeeping cost on MLX | **Measured (E05): NOT TRANSFERABLE at 8 NFE** — per-step block changes 19–46% (median); token-level stability absent (per-token p10 ≥13%); ≤3.5% block-skip ceiling. See experiments/cache-audit-report.md |
| ToMA 2509.10918 | GPU-friendly token merging | attention ceiling ≈18% | — | — | merging ops' overhead | CONCEPTUALLY USEFUL (FLOPs ≠ wall-clock lesson) |
| PTQ4DiT 2405.16005 / Q-DiT 2406.17343 / Timestep-Aware Correction 2407.03917 | activation-aware, timestep-aware, granularity-aware PTQ | our q4 is weight-only | MLX affine q4, group 64 | no W4A8 GEMM path in use | integer-activation kernels not in our stack | CONCEPTUALLY / PARTIALLY (granularity, sensitivity → E07) |
| FlashAttention 2205.14135 | IO-aware tiled exact attention | — | — | **already embodied** in `mx.fast.scaled_dot_product_attention` (fused, NAX paths) | — | CONCEPTUALLY USEFUL (realized) |
| SageAttention 2410.02367 | 8-bit attention | ceiling ≈18% | — | custom kernel needed | CUDA INT8-specific | NOT TRANSFERABLE as-is |
| SANA / MobileDiffusion / SnapGen | architecture co-design (32× AE, linear attention, small nets) + distillation | would be a different model | — | — | training | CONCEPTUALLY USEFUL (long-term) |
| Lightweight decoders 2503.04871 | distilled small VAE decoders | VAE ≈3% of wall | — | — | training | CONCEPTUALLY USEFUL — low value measured |
| Consistency / LCM / Moment matching | few-step distillation theory | future re-distillation | — | — | training | CONCEPTUALLY USEFUL (long-term) |
| SaRA / IntLoRA | PEFT, incl. integer LoRA on quantized weights | customization of the q4 base | mflux has LoRA support | yes | training memory on 16 GB unverified | PARTIALLY TRANSFERABLE (Tier C) |
| GenEval / GenEval 2 / T2I-CompBench++ / OneIG / ImageReward | evaluation | applies | — | judges may need separate env | offline policy for VLM judges | DIRECTLY TRANSFERABLE as tools (E08) |

## 3. Experiments worth running (see backlog for ranking)
- E02: bf16 stream.
- E03: step sweep.
- E04: exact micro-optimizations.
- E06: VAE-phase memory fix.
- E05: redundancy instrumentation.
- E09: pruning payoff bound.
- E08: evaluation harness.
- E07: quantization sensitivity.
- E10: attention share at high resolution.

## 4. Not worth running now (measured reasons)
- Fused QKV and fused SwiGLU: no gain with q4 (E00).
- Switching to q8 or bf16 weights for speed: q4 is fastest (E00).
- Qwen-style prefix KV cache: not exact for Z-Image.
- SageAttention-style kernels: ≈18% ceiling plus a custom kernel.
- Lightweight VAE: ≈3% ceiling.
- Local TMP reproduction: no artifact, needs training.

## 5. Expected performance impact, quality risk, complexity (current view)
| Direction | Expected impact on 1024² denoise | Quality risk | Complexity |
|---|---|---|---|
| bf16 hidden stream (E02) | **measured −29.1% denoise (1.41×)** | low–medium (not bit-exact; PSNR 34.6–42.3 dB) | low |
| Step reduction (E03) | ≈11%/step | high below 8 NFE | trivial to run, costly to evaluate |
| Exact micro-opts (E04) | ≈1–2% | none | low |
| Caching (E05→) | unknown; few-step models typically offer little | medium | medium–high |
| FFN pruning (TMP) | ≈26% of block time in bf16 (E09 proxy, measured) | depends on recovery training | very high |
| Attention-side | ≤≈18% ceiling | medium | high |

## 6. Current recommendation and evidence (updated 2026-09-25, pass 3)
**Done**
- E02 (bf16) passed its blinded gate and is an opt-in mode.
- E06 (transformer release) is in production.
- E04 micro-opts: rejected/deferred.
- E05 caching: rejected. Measured low redundancy at 9 NFE, corroborated by upstream #753's note that FBCache doesn't fit turbo models.
- E09 proxy: bounded the pruning payoff (≈26% block time in bf16).
- E03 8 steps: under a blinded gate.

**Paper-driven ideas that remain relevant**, now ordered by the model/runtime frontier in EXPERIMENT-BACKLOG.md §Pass 3:
1. **Structured reduction** (TMP, block importance). Only via measured block-skip probes and a credible recovery-training path; no arbitrary weight deletion.
2. **Quantization** (PTQ4DiT, Q-DiT, timestep-aware). Start with the formats MLX 0.32.2 already runs on the M5 (affine q4/q8, mxfp4, nvfp4, mxfp8), measured per block before any conversion.
3. **Kernels** (FlashAttention principle). Profile first; attention is ≤18% of block time, so GEMM efficiency and the non-matmul remainder come first.
4. **Few-step distillation** (Decoupled-DMD, LCM). A feasibility study only. Note: mflux 8 steps already ≈ the official 8-NFE recipe (scheduler-nfe-note.md), so "<8" means below the distilled recipe.
5. **VAE** (lightweight decoders). Low priority: ≈3% of wall time.

**No longer pursued:** caching families (FastCache, TokenCache, DeepCache, FBCache, TeaCache) and TE substitution.
