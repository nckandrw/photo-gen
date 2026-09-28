# Structured FFN-width reduction: experimental design (Phase 3 §10)

Status: **DESIGNED 2026-09-25.** A first measurement pass is queued in chain P3B. This is research only: no production change, no weight file is written, no tensor is edited on disk.

## Why FFN width
- The SwiGLU FFN (w1, w3: 3840→10240; w2: 10240→3840) is ≈ 56% of a block's matmul time (E00).
- The E09 proxy (synthetic weights) showed −37.5% width → −26% bf16 block time. That is a proxy only, not evidence a reduced model keeps quality.

## Structurally valid method: group-aligned hidden-channel removal
**Mathematical validity.** SwiGLU output is a sum over hidden channels:

`FFN(z) = Σ_j w2[:, j] · silu(w1[j] · z) · (w3[j] · z)`

Removing hidden channel j removes exactly one summand. The consistent operation is: drop row j of w1 and w3 **and** column j of w2. Any other slicing is not a valid structured reduction.

**q4 layout constraint.** MLX affine q4 groups 64 consecutive values along each weight's *input* dimension.
- w1/w3 rows are output channels, so each row carries its own groups. Row removal is exact.
- w2's input dimension *is* the hidden dimension, and 8 uint32 words hold one 64-channel group. Removing arbitrary channels would split groups and force re-quantization, which changes the kept weights.
- **Group-aligned removal** (drop whole original 64-channel groups: w2's 8 packed columns + 1 scale column + 1 bias column per group) keeps every retained weight, scale and bias **bit-identical** to the pack.

The result is still a valid q4 layer. Hidden width stays a multiple of 64, so the NAX `K % 64 == 0` condition for w2 still holds (`nax-status.md`).

**Importance score (calibration, no evaluation data).** Per block b and hidden channel j:

`s_bj = E_{calib prompts, steps, tokens}[ |silu(w1_j z) · (w3_j z)| ] · ||w2[:, j]||₂`

This is the expected magnitude of the channel's contribution to the FFN output: an activation-aware, FLAP/Wanda-style criterion. Group score = Σ_j∈group s_bj. The calibration prompts (`p3b/calib-prompts.json`, 8 prompts) are **disjoint** from the 12-prompt evaluation suite.

**Allocation.** Pass 1 keeps the fraction k of groups per block uniformly (main + noise-refiner blocks; the context refiner runs on 32 caption tokens and is negligible). Pass 2 (only if pass 1 shows a usable point): non-uniform allocation guided by `block-sensitivity-map.md`.

## Implementation (`ffn_prune_worker.py`)
- Wraps the unmodified production worker. After model load it slices the q4 arrays in memory by the kept group indices.
- `mx.compile` stays **on**, so timings are production-like, unlike the instrumented probes.
- Control: k = 1.0 leaves the arrays untouched and **must reproduce the production FAST hash** for the same prompt/seed/resolution. For 512² p01 seed 42 bf16/8 that is `0b9cc20a…`.

## Pass 1 measurement (chain P3B)
- **Curve:** k ∈ {1.0, 0.9, 0.8, 0.7, 0.6} (hidden 10240 → 9216 / 8192 / 7168 / 6144).
- **Quality (automated):** 512², bf16/8, 12 suite prompts, seed 42. PSNR/SSIM vs k = 1.0 per prompt. These are *descriptive* only; low PSNR can mean benign content drift.
- **Quality (visual):** contact sheets per k, reviewed for gross failure (structure collapse, texture loss, text breakage).
  - This is not a blinded gate. A blinded gate is required before *any* operating point could be proposed.
- **Runtime:** production-like compiled runs. 512² for all 60 runs (sustained, sequential); 1024² p01 at each k (5 runs, sequential).
  - Paired comparison vs k = 1.0 in the same block. Cold-state figures are not claimed.
- **Memory:** peak footprint per run. Expected saving ≈ 3 × 3840 × 64 × 0.5625 B ≈ 0.41 MB per group removed per block.
  - At k = 0.6: 64 groups × 32 blocks ≈ **0.85 GB**, i.e. 40% of the 2.12 GB of q4 FFN weights. Runtime activations shrink too (the `[L, hidden]` intermediates).

## Decision rule
A "useful operating point" requires all three of:
- (a) ≥ 10% end-to-end denoise reduction at 1024² vs k = 1.0;
- (b) no gross failure on the contact sheet in any of the 12 prompts;
- (c) a subsequent blinded gate vs FAST passing the FAST-gate criteria.

Without recovery training, **(b) is expected to fail below k ≈ 0.9**. The TMP paper needed distillation recovery at −37.5%. If it does fail, the result is recorded as "no training-free operating point". Recovery training joins the distillation plan as a costed option (`distillation-feasibility.md`).

## Results
(appended after chain P3B)

## Smoke test (2026-09-28, 512², bf16/8, p01 s42; `p3b/smoke/`; the scores are from a 2-step smoke calibration, NOT the real calibration)
- **Identity control PASSED:** keep = 1.0 reproduces the production FAST hash `0b9cc20a…` exactly (compiled path, `compile_calls` = 1).
- **Widths as designed:** 10240 / 8192 / 6144. **Exact resident DiT weights:** 3.464 / 3.039 / 2.614 GB, matching the design estimate (−0.85 GB at k = 0.6).
- **Harness fixes forced by the smoke test** (disclosed):
  1. The lifetime peak footprint is confounded by a load-time transient: the full and sliced arrays briefly coexist. k = 0.8 showed 5.86 GB vs 5.41 GB. A cache clear after slicing does not remove the transient, so memory is now reported as **exact DiT weight bytes** (`dit_weight_bytes`), not lifetime footprint.
  2. The phase MLX peaks cannot isolate denoise (the `vae_decode` phase resets the peak inside `generate_total`). They are not used for this sweep.
- The smoke timings (single runs) are not evidence.
