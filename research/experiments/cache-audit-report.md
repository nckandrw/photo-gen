# Cross-step redundancy audit (E05) — is block/step caching viable for 9-step Z-Image-Turbo?

> **CROSS-STEP CACHING — Status: REJECTED (closed 2026-09-25).**
> - **Reason:** insufficient temporal redundancy under the tested Z-Image-Turbo execution (mflux 9 steps = 9 NFE; see scheduler-nfe-note.md).
> - **Not to be implemented:** FastCache, TokenCache, FBCache, TeaCache or equivalents on the strength of papers alone.
> - **Reopen only for** a materially different method.
> - **External corroboration (2026-09-25):** mflux-community/mflux issue #753 (FBCache proposal, open) states that "FBCache is not suitable for turbo models. With Turbos models the change between steps is significant, so no skipping will occur." That is consistent with the measurements below.

**Method.**
- `exp_zimage.py --audit` hooks all 32 single-stream blocks (2 noise refiners + 30 main layers). Between consecutive denoise steps it records, for each block:
  - `block_resid`: the block's residual contribution (out − in);
  - `attn_out`: the attention branch output;
  - `ffn_out`: the FFN branch output.
- Two measures per quantity:
  - **whole-tensor relative change** `rel = ‖Δ‖/‖cur‖`;
  - **per-token relative change**, reported at p10/p50/p90/p99 over the 4096 image + caption tokens.
- Runs: p01 (apple) and p05 (neon text), seed 42, 1024², fp32, 9 steps → 8 step transitions × 32 blocks × 3 quantities = 768 rows per prompt (`audit/audit-p0*.json`).
- `MLX_DISABLE_COMPILE=1` is required so the Python hooks run every step.

**Instrumentation side effects (recorded, not hidden):**
- Output is **not** pixel-identical to production (p01 812b09f8… vs fe47d88d…), because the uncompiled graph uses different kernel fusion. Deltas are therefore representative, not bit-exact.
- Footprint rises to 10.2 GB because of the stored previous-step tensors.
- ≈16.7 s/step vs ≈15 s/step.

## Results (p01; p05 is within ±0.05 on every aggregate)
| transition | block_resid rel, median / min | blocks with rel < 0.05 / < 0.10 | ffn_out rel, median | ffn_out blocks < 0.05 | ffn_out per-token p10, median over blocks |
|---|---|---|---:|---:|---:|
| 0→1 | 0.455 / 0.103 | 0 / 0 | 0.168 | 5 | 0.532 |
| 1→2 | 0.302 / 0.061 | 0 / 7 | 0.116 | 12 | 0.229 |
| 2→3 | 0.206 / 0.038 | 1 / 8 | 0.065 | 14 | 0.145 |
| 3→4 | 0.192 / 0.038 | 3 / 12 | 0.064 | 15 | 0.126 |
| 4→5 | 0.237 / 0.043 | 3 / 13 | 0.073 | 15 | 0.130 |
| 5→6 | 0.260 / 0.051 | 0 / 10 | 0.075 | 14 | 0.186 |
| 6→7 | 0.286 / 0.068 | 0 / 2 | 0.098 | 12 | 0.239 |
| 7→8 | 0.324 / 0.101 | 0 / 0 | 0.084 | 8 | 0.317 |

- **Attention output** changes 20–56% (median) per step. It is the least redundant part: 0 of 32 blocks fall below 0.05 at any step, on either prompt.
- The lowest whole-block residual changes are in blocks 8, 11 and 13 during mid-trajectory transitions 2→5: 0.038–0.06.

## Interpretation
1. **At the level caching methods act on (a block's output reused at the next step), there is little redundancy.**
   - The median block contribution changes 19–46% per step.
   - At most 3 of 32 blocks fall below a 5% change, and only in 3 of the 8 transitions.
   - With only 8 transitions, even a cache that always hit those blocks would skip ≈9 of 256 block evaluations (≈3.5%), at a non-zero error in each one.
   - This is the expected profile for a distilled few-step model: each step makes a large, different update. Contrast 50-step models, where DeepCache/FasterCache-style reuse relies on per-step changes of a few percent.
2. **The FFN-output whole-tensor numbers look more cacheable (12–15 blocks below 5% mid-trajectory), but that is misleading.**
   - The per-token p10 is 0.13–0.53, so even the 10% most stable tokens change by ≥13%.
   - The low whole-tensor figure is dominated by a few very-high-norm (outlier) tokens that barely change.
   - Reusing the FFN output would therefore carry a ≥13% error on ~90% of tokens. Token-level caching (TokenCache/FastCache-style) has no stable token population to exploit.
3. **Best case, if FFN caching were error-free anyway:** 15 blocks × 3 mid transitions × 56% FFN share ≈ 45/256 × 0.56 ≈ **≈10% of denoise**. That saving is FLOPs only and would come with a measurable approximation.

## Decision
**Redundancy is NOT substantial. No caching prototype** (per directive: "only prototype caching if redundancy is substantial; reject FLOP-only wins").
- **Rejected:** block-output caching (≤3.5% ceiling) and token caching (no stable tokens).
- **Deferred:** FFN-branch reuse in mid-trajectory blocks 8–13. The ≈10% ceiling is a FLOP-only estimate and the approximation error is large; it would only be revisited with an E08-grade quality harness and a stronger motivation than the bf16 path already provides.
- **Step reduction (E03) is the more direct lever** for the same "less compute across steps" goal, and is being measured in `step-sweep-report.md`.
