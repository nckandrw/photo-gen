# TMP pruning (arXiv 2606.27089) — assessment for Z-Image-Turbo on this M5 (documentation only; no pruning performed)

## What the paper claims (verified from abstract + paper body, 2026-09-24)
- TMP = Tree-structured Mixed-policy Pruning: prune, then recover quality by hierarchically merging adjacent layer intervals in a binary tree while alternating **off-policy** distillation (teacher outputs supervise student) and **on-policy** distillation (student rollouts guide targets); followed by velocity-prediction alignment. Intended as the *last stage* after step distillation.
- Z-Image-Turbo: "We reduce the expansion rate of the MLP by 37.5% and achieve an overall 33% of parameter count reduction. This results in a 4B pruned model", "with negligible degradation" — evaluated on OneIG-EN/ZH and LongText-Bench (Tables 1–3).
- HunyuanImage-3.0: 80B → 20B, inference on a single 24 GB RTX 4090; weights/scripts "integrated into the existing HunyuanImage3.0 open-source github and huggingface repository".

## What is missing
| Needed to reproduce | Status |
|---|---|
| Pruned Z-Image-Turbo weights | **Not found** (HF model search "Z-Image-Turbo pruned/4B/TMP" 2026-09-24: only 4-bit quantizations and the 4B text encoder) |
| TMP pruning/recovery code | **Not found** in Tencent-Hunyuan/HunyuanImage-3.0 (README/tree checked; only an unrelated "Instruct-Distil" checkpoint); no standalone repo |
| Which MLP channels are removed (selection criterion), per-layer widths | not specified for Z-Image in the paper text available to us |
| Recovery data, steps, compute (GPU-hours) | not reported for Z-Image |
| Latency / memory of the 4B model | not reported (no hardware numbers for Z-Image) |
| Quantization behaviour after pruning | not reported |

## What reproduction would require
1. A channel-selection procedure for the 30+2 blocks' SwiGLU (w1/w3: 10240→6400 outputs, w2: 6400→3840 inputs at −37.5%).
2. A teacher (the bf16 6B Turbo, 24.6 GB fp32 / 12.3 GB bf16 checkpoint) and student forward/backward passes at 1024² — **training-scale GPU memory; not feasible on a 16 GB laptop** (the student alone in bf16 ≈ 8 GB of weights before optimizer state and activations).
3. Prompt/image data for on- and off-policy rollouts; evaluation on OneIG/LongText to confirm "negligible degradation".
4. Re-quantization to MLX q4 (group 64) and re-validation on this Mac.

## Theoretical expected benefit on this M5 (derived from measurements, not from the paper)
- Measured block split (E00, production fp32 activations, q4): FFN = 56% of block time. A 37.5% FFN width cut removes ≈0.375 × 56% ≈ **21% of block time** ⇒ ≈19–20% of denoise at 1024² if the q4 matmul time scales linearly with width (to be checked by the E09 proxy benchmark).
- With the bf16 stream (E02) the FFN share and absolute times change; the bound must be re-derived for the precision actually adopted.
- Memory: DiT weights 3.46 GB (q4) → ≈2.4 GB (≈−1 GB); process footprint correspondingly lower.
- Quality: unknown for us — the paper's "negligible" claim is on its benchmarks after recovery training; an un-recovered width cut would severely damage outputs.

## E09 timing proxy (measured 2026-09-24 21:15; `e09_pruning_proxy.json`)
Setup: synthetic q4 block at L=4128 tokens, FFN 10240 vs 6400, median of 8 reps.
| activations | full block (ms) | FFN −37.5% (ms) | block speed-up |
|---|---:|---:|---:|
| fp32 (production default) | 327.95 | 308.14 | 6.0% |
| bf16 (opt-in) | 288.65 | 213.74 | **26.0%** |

- In bf16, the speed-up is close to the linear estimate above (0.375 × FFN share); the relevant ceiling is **≈26% of block time**.
- The fp32 result (6%) is anomalous against E00's FFN share. The run was single, not interleaved (fp32 measured first), on a chip heat-soaked by 20 minutes of prior runs. **Treat the fp32 figure as unreliable**; re-run interleaved and cool if it ever matters.
- Since bf16 is now the fast path, the payoff bound for a pruned model is ≈25% of denoise.
- None of this changes the blocked status: there are still no weights or code to prune with.

## Decision
**Blocked; no local pruning experiment.** Unblock conditions: (a) published pruned Z-Image-Turbo weights (then: convert → q4 → run the standard A/B + quality gate), or (b) explicit authorization and budget for cloud recovery training with a reproducible procedure. Before (b), run E09 (timing proxy) so the payoff bound is measured, not estimated.
