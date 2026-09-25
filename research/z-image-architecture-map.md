# Z-Image-Turbo architecture map: paper → mflux 0.20.0 implementation → tensors → MLX ops → optimization

**Date:** 2026-09-24.
**Sources:**
- paper arXiv 2511.22699 (Z-Image);
- source `mflux/models/z_image/model/z_image_transformer/*.py` at mflux v.0.20.0 (installed tree, byte-identical to the audited sdist);
- the q4 pack's safetensors headers (`transformer/0.safetensors`);
- measurements E00/E01/E02 in `research/experiments/`.

**Shapes are for 1024×1024:** VAE latent 16×128×128 → patch 2 → **4096 image tokens**. A short prompt gives caption tokens padded to a multiple of 32, e.g. **32**, for a unified sequence of **L ≈ 4128**.

| Paper concept | Actual implementation (mflux 0.20.0) | Tensor shapes @1024² | MLX operation | Measured / derived cost | Potential optimization |
|---|---|---|---|---|---|
| Qwen3-4B text encoder, penultimate hidden state | `ZImageTextEncoder`, 36 layers, hidden 2560; the official pipeline uses `hidden_states[-2]`; chat template; max 512 tokens | caption `[T, 2560]` | q4 matmuls + SDPA (LM) | 0.65 s per image (measured), 3.6 GB MLX peak; freed before denoise under `--low-ram` | None worthwhile for speed (<1% of wall). Memory is already handled by MemorySaver. |
| Flux VAE latent (16 ch, 8×) | `ZImageLatentCreator` / `Qwen21VAE`-style 2D VAE (Flux ae) | latents `[16, 1, 128, 128]` | conv2d stack | decode 2.0–3.2 s (tiled, `--low-ram`); 5.70 GB MLX peak during decode, with the DiT still resident | Time is small (≈3%). Memory: fix mflux's ineffective transformer release (closure in `ZImage.generate_image` keeps the ~3.5 GB DiT alive during decode). |
| Patchify (2×2 spatial patches) | `_patchify`: reshape/transpose to `[4096, 64]`, pad to a multiple of 32 | `[4096, 64]` → `x_embedder` Linear(64→3840) | reshape, transpose, Linear | negligible | — |
| Timestep conditioning (adaLN) | `TimestepEmbedder` (sinusoid → MLP 256); per-block `adaLN_modulation` Linear(256→4·3840) giving scale_msa, gate_msa, scale_mlp, gate_mlp (tanh gates) | `t_emb [1, 256]` | q4 Linear (quantized too) | tiny per block | **Produces float32** (timestep cast to fp32). This is one of the three sources of the fp32 hidden-stream promotion (E01). |
| S3-DiT "noise refiner" (image-only pre-blocks) | `noise_refiner`: 2 × `ZImageTransformerBlock` on image tokens only (t-conditioned) | `[1, 4096, 3840]` | same as a main block | 2/34 of block compute | — |
| S3-DiT "context refiner" (text-only pre-blocks) | `context_refiner`: 2 × `ZImageContextBlock` on caption tokens, **no timestep input** | `[1, 32, 3840]` | Linear + SDPA | tiny at short prompts | **Exact caching:** output is step-invariant, so compute once per image instead of 9×. Saves <1% at short prompts, more for long (up to 512-token) prompts. |
| Single-stream unified sequence | `unified = concat(image, caption)`; 30 `ZImageTransformerBlock`s over L≈4128 | `[1, 4128, 3840]` | — | 30/34 of block compute | — |
| Joint 3-axis RoPE | `RopeEmbedder` (axes dims 32/48/48, θ=256); `_apply_rotary_emb` elementwise real/imag with **fp32 tables** | freqs `[4128, 64, 2]` fp32 | elementwise mul/stack | small elementwise | **fp32 tables re-promote q/k to fp32 every attention.** Diffusers casts the RoPE output back to the input dtype. That's the second, decisive fp32 source (E02b). A fused RoPE kernel could also cut elementwise traffic. |
| Attention (30 heads × 128, QK-RMSNorm) | separate `to_q/to_k/to_v/to_out` (q4, group 64); `norm_q/norm_k` RMSNorm(128); `mx.fast.scaled_dot_product_attention` with an **all-zeros additive mask** (float32) | q,k,v `[1, 30, 4128, 128]` | 4 q4 matmuls + fused SDPA | E00 (fp32 act, as production): QKV 46.8 ms, SDPA 43.7 ms, out 15.7 ms per block. **Attention core ≈18% of the block.** | `mask=None` is exactly equivalent (max diff 0.0) and 5% faster on SDPA (≈1% of step). Fused QKV: no gain with q4 (E00), rejected. |
| SwiGLU FFN (hidden = 8/3·d = 10240) | `w1, w3: 3840→10240`, `w2: 10240→3840`, all q4 group 64 | `[1, 4128, 10240]` intermediate | 3 q4 matmuls + silu·mul | **FFN ≈56% of the block** (w1/w3 88.8 ms + w2 47.7 ms, fp32 act) | Biggest single cost. Candidates: width pruning (TMP: −37.5% FFN width, needs recovery training), activation precision (bf16), step reduction. Fused w1/w3: no gain (E00), rejected. |
| Sandwich norms (pre + post RMSNorm per sub-layer) | 4 RMSNorm per block (`attention_norm1/2`, `ffn_norm1/2`) | `[1, 4128, 3840]` | `mx.fast.rms_norm` | small | — |
| Final layer | LayerNorm (no affine) × adaLN scale → Linear(3840→64), unpatchify, **output negated** | `[4096, 64]` → `[16, 1, 128, 128]` | Linear | negligible | — |
| Weights: q4 | MLX affine quantization, **group 64**, bf16 scales + biases, uint32-packed (e.g. `to_q.weight [3840, 480] U32`, `scales [3840, 60]`) | 3.46 GB DiT | `quantized_matmul` (NAX kernels `qmm_t_nax` present) | E00: q4 is the **fastest** weight format here (q8 +8%, bf16 +22% per block at fp32 act) | Keep q4. Its quality effect relative to bf16 is not measured by us. |
| Activations | Inputs bf16 (`ModelConfig.precision = bfloat16`), **promoted to float32 inside the DiT** — CORRECTED by E10: only (2) and (3) below promote, and both must be fixed; pad tokens load as bf16 from the checkpoint. Original text: (1) `x_pad_token`/`cap_pad_token = mx.zeros(...)` (float32) via `mx.where`; (2) float32 timestep embedding in the adaLN math; (3) float32 RoPE tables | hidden stream fp32 | — | E00: fp32 activations cost 1.34–1.61× per op. E02b (bf16 stream incl. RoPE cast): denoise 72.1 s on a warm-ish chip vs 78.6–81.5 s cool production; PSNR 42.3 dB vs fp32 output | **Top Tier-A candidate. Controlled A/B: denoise 78.33 → 55.55 s (−29.1%, 1.41×), memory unchanged, deterministic; not pixel-identical (PSNR 34.6–42.3 dB) — see experiments/E02-RESULTS.md. Quality gate PASSED on 24 blinded pairs (experiments/bf16-quality-report.md); shipped in photo-gen as opt-in `precision: bf16`, parity-verified.** |
| Scheduler (mflux: N steps = N NFE; reference 9 steps = **9 NFE**; official recipe = 8 NFE, static shift 3.0) | `LinearScheduler`: linspace(1, 1/N, N) + resolution-dependent exponential shift (e^μ = 3.16 at 1024² ≈ official 3.0; **1.88 at 512²**) — see experiments/scheduler-nfe-note.md | N sigmas + terminal 0 | — | per-step cost × 9 | Step reduction (Decoupled-DMD analysis): 9→8→…→4 sweep (backlog). |
| Compiled predict | `mx.compile(predict)` on M3+ (disabled on M1/M2) | — | graph compile | first step +~1 s | — |

## Where time goes (1024², production, cool chip, measured)
- Total ≈86.6 s wall = worker start + imports ≈1.4 s + weight load (lazy) ≈1.1 s + TE 0.65 s + **denoise 81.5 s (94%)** + VAE 2.0 s.
- Denoise ≈9.0 s/step × 9.
  - The E00 synthetic block model accounts for ≈7.8 s/step (32 full blocks × 242.7 ms).
  - The remainder (≈1.2 s/step) is norms, RoPE, modulation, residual elementwise ops, context refiner, patchify, scheduler and compile overhead.
- Within a block (production fp32 act, q4): FFN 56%, QKV 19%, SDPA 18%, out-proj 6%.
- **Implication:** at 1024² the work is **linear-layer-bound, not attention-bound**. Attention-only techniques (token merging, low-bit attention, attention kernels) have a ceiling of ≈18% of denoise. Precision of the hidden stream, step count, cross-step reuse of whole blocks, and FFN width act on 80–100% of it.

## Exactness notes
- **Qwen-2.1-style prefix KV cache does not transfer exactly.** In Z-Image's 30 main blocks the caption tokens are adaLN-modulated by the timestep (the same `t_emb` as the image tokens), so their K/V change every step. Only the 2 context-refiner blocks are step-invariant.
- `mask=None` vs the all-ones boolean mask converted to an all-zeros additive mask: bit-identical SDPA output measured (E00).

## Cross-step behaviour and memory lifecycle (measured 2026-09-24, pass 2)
- **Cross-step redundancy is low at 9 NFE** [corrected 2026-09-25: originally "8 NFE"; the cache audit ran mflux 9 steps = 9 NFE, see scheduler-nfe-note.md] **(E05, `experiments/cache-audit-report.md`).**
  - The median per-block residual contribution changes 19–46% between consecutive steps; attention outputs change 20–56%.
  - FFN outputs look stable as whole tensors (median 6–10% mid-trajectory), but that stability comes from a few high-norm outlier tokens. Per-token p10 change is ≥13%.
  - Block and token caching are rejected; FFN reuse is deferred.
- **Transformer lifetime (E06; production since 2026-09-25, `experiments/production-memory-fix-report.md`).** The `mx.compile` closure in `ZImage._predict` keeps the q4 DiT (≈3.47 GB) alive through VAE decode even with `--low-ram`. Making the release effective is exact (pixel-identical):
  - VAE-phase MLX peak 5.70 → 2.23 GB;
  - peak footprint 7.35 → 6.56 GB at 1024².
- **FFN-width payoff (E09 proxy).** With bf16 activations, a −37.5% FFN width cuts block time by 26%. The fp32 measurement (6%) is unreliable: single, non-interleaved run on a hot chip.
