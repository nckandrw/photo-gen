# Micro-optimizations — separately attributed (bf16 stream, 1024², seed 42)

| # | change | exact? | measured effect | verdict |
|---|---|---|---|---|
| M1 | SDPA `mask=None` instead of the model's all-zeros additive mask | **yes**: pixel-identical (p01 11b19277…, p05 7bfd59ca…, 4/4 runs per arm) | ABBA, 2 prompts × 2 reps (`microopt/results.jsonl`): base 90.6 s mean denoise vs mask-none 92.8 s. Excluding the first (cooler) pair: 91.4 vs 92.0 s. **No speed-up in bf16.** (Earlier fp32 measurement: ≈1% faster.) | **Rejected**: no measurable benefit on the adopted fast path |
| M2 | Effective transformer release before VAE decode | **yes** (pixel-identical) | −0.8 GB peak footprint at 1024² (fp32); no time change (`vae-lifecycle-report.md`) | **Recommended**: memory, not speed; awaiting sign-off |
| M3 | Context refiner once per image (step-invariant) | yes (by construction) | not measured; the bound is <1% at typical prompt lengths (2 small blocks on ≤~60 caption tokens) | **Deferred**: below measurement noise |
| — | Fused QKV / fused SwiGLU with q4 | — | ≤1.4% / 0% (E00) | rejected earlier |

**Conclusion:** after the bf16 stream (−30%) and the step count (≈11% per step), no remaining exact micro-optimization gives a measurable speed-up on this pipeline. The only exact win left is memory (M2).
