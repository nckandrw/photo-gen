# Phase 3 research scorecard (directive §17)

Measurable dimensions only; this is not a "best optimization" ranking. Speed is end-to-end at 1024² unless stated, and the baseline is named in every row. "Confidence" is measurement confidence, not how much we like the idea.

Updated as results land. Draft 2026-09-25 ~15:00: rows marked *(pending)* are waiting on chain P3A or P3B.

| experiment | hypothesis | mechanism | expected speed impact | expected memory impact | quality risk | implementation complexity | hardware specificity | measurement confidence | status |
|---|---|---|---|---|---|---|---|---|---|
| FAST at 512² (direct gate) | bf16/8 ≈ fp32/9 in quality at 512² | precision + one fewer NFE | measured cold: wall 1.41×, denoise 1.53× vs REFERENCE | −0.52 GB (5.41 vs 5.93) | low (1024² chained gates passed) | none (code exists; `GATED_STEPS` entry) | none | *(pending gate)* | PENDING |
| FAST at 768² (direct gate) | same, at 768² | same | measured cold: wall 1.46×, denoise 1.55× | −0.41 GB (5.93 vs 6.33) | low | none | none | *(pending gate)* | PENDING |
| FAST at 1024² (direct gate, Improvement Clause) | the chain holds when tested directly | — | measured cold: wall 1.54×, denoise 1.61× | −0.72 GB | low | none | none | *(pending gate)* | PENDING |
| Official static-3.0 sigma schedule | mflux's FLUX-style dynamic shift costs quality at low resolution | a different sigma trajectory; same NFE | **none** (measured 512²: denoise ratio 0.999) | none | no advantage shown: 512² M 3 / S 0 / 21 ties; 768² M 2 / S 0 / 22 ties; 1024² near-identical | trivial (external scheduler class) | none | medium (24 pairs per resolution, single AI rater) | **CLOSED**: implementation difference, quality-neutral; production unchanged |
| Block-sensitivity map | a subset of the 30 equal-cost blocks contributes little | measurement only | — | — | — | low (probe harness) | none | *(pending P3B)* | DESIGNED |
| Group-aligned FFN width reduction (no recovery training) | a useful width exists at ≥ 10% denoise reduction | fewer FFN hidden channels (whole q4 groups; kept weights bit-exact) | proxy: −26% block time at −37.5% width (bf16, synthetic) | −0.21 GB per −10% width | **high** without recovery training | medium (in-memory slicing) | none | *(pending P3B curve)* | DESIGNED |
| Quantization formats (q3/q5/q6, g32/g128, mxfp4/nvfp4/mxfp8) | some format is ≥ 3% faster than q4 g64 | weight bytes vs unpack cost in NAX qmm | predicted single-digit % at best | ± 0.8 GB (q3 … q6) | format-dependent; untested on real weights | low (speed); a download for quality | MLX/M5-specific kernels | *(pending microbench)* | MAPPED |
| NAX dispatch | the q4 matmuls and SDPA run on NAX in both precisions | M5 neural accelerators via MLX `*_nax` kernels | explains the 7–10 TFLOPS already measured | — | — | none (verification) | M5-specific | static: LIKELY; runtime *(pending capture)* | IN PROGRESS |
| Kernel profile | the FFN/attention matmuls dominate; elementwise ops are minor | — | identifies targets only | — | — | — | M5 | *(pending P3B)* | DESIGNED |
| Custom Metal/MLX kernels | a material non-matmul hotspot exists | fusion/layout | unknown until the profile shows a target | — | none if exact | high | M5/MLX | — | NOT STARTED (gated on the profile) |
| Zero-training few-step probe (PAI 4/2-step LoRA on Z-Image base) | first-party 4-step quality is within the FAST gate | 4 or 2 NFE instead of 8 | ≈ −50% denoise (4 NFE) incl. ≈ 5% LoRA overhead | +0.57 GB LoRA | medium–high (card says "slightly reduces quality") | low (mflux LoRA path; key format LIKELY compatible) | none | — | PROPOSED (needs download approval) |
| Few-step distillation training | a 4-step student of Turbo keeps quality | distillation | ≈ −50% denoise | none | high | very high (cloud GPUs) | none | GPU-hours UNKNOWN | DEFERRED |
