# DRAFT — NOT SUBMITTED. Upstream issue for filipstrand/mflux (user decision required before posting)

> **CORRECTION (2026-09-25, E10 ablation, `experiments/e10/`, `e10_promotion_ablation.py`).**
> - **Pad tokens are NOT a promotion source.** `x_pad_token`/`cap_pad_token` are stored as BF16 in the checkpoint and loaded over the `mx.zeros` init (dtype after load: bfloat16). The pad-token cast in the patch is a harmless no-op.
> - **Promotion comes from two sources that must BOTH be fixed:**
>   1. the float32 TimestepEmbedder output (adaLN modulation);
>   2. the float32 RoPE tables (`_apply_rotary_emb` returns float32).
> - Measured per variant:
>   - none → SDPA q / FFN in = fp32/fp32;
>   - temb only → fp32/fp32 (RoPE re-promotes q/k, and attention output promotes the residual);
>   - rope only → fp32/fp32;
>   - temb+rope → **bf16/bf16**;
>   - pad+temb+rope → bf16/bf16 (identical).
> - The earlier statements "three sources" and "each sufficient on its own" were wrong. The measured speed/quality results are unaffected (the full patch set was used; the SUBMITTED text (upstream-mflux-issue-SUBMITTED.md) reflects the correction throughout).

> Prepared 2026-09-24 under the "prepare, but do not submit" directive.
> - Every claim is tagged **[verified]** (measured or read in source here), **[inference]** (follows from verified facts) or **[hypothesis]** (not tested).
> - Before posting, re-check the line numbers against mflux `main`; they refer to the 0.20.0 wheel.

---

**Title:** Z-Image: DiT hidden stream silently runs in float32 (≈1.4× slower denoise), plus `--low-ram` transformer release is defeated by the `mx.compile` closure

### Environment
- mflux 0.20.0, mlx 0.32.2, mlx-metal 0.32.2, Python 3.12.14.
- MacBook Air M5 (10-core CPU, 8-core GPU), 16 GB, macOS 27.0 (26A428).
- Model: `mflux-community/z-image-turbo-mflux-q4` @ d2d30500. `mflux-generate-z-image-turbo --low-ram`, 1024×1024, 9 steps.

### 1. float32 promotion of the DiT hidden stream

`ModelConfig.precision` is bfloat16 and the q4 weights' scales/biases are bf16, but the transformer's activations end up float32 **[verified: dtype probe on SDPA q and FeedForward input = float32 for every step after the first refiner call]**. Three sources, each sufficient on its own to promote the stream **[verified by patching them one at a time; E02 first attempt without (3) gave no speed-up]**:

1. `model/z_image_transformer/transformer.py:51-52`: `x_pad_token = mx.zeros((1, dim))` and `cap_pad_token = mx.zeros((1, dim))` default to float32. `mx.where` with the bf16 embeddings then promotes the whole sequence.
2. `transformer.py:78` together with `timestep_embedder.py:32-33`: the sinusoidal timestep embedding is computed in float32, and its MLP output stays float32. The adaLN modulation (`scale_msa`, gates) therefore promotes every block's input.
3. `attention.py:80-88` with `rope_embedder.py:35-41`: the RoPE tables are float32 and `_apply_rotary_emb` returns the promoted dtype, so q/k are re-promoted at every attention call even if (1) and (2) are fixed.

**Minimal fix we tested** (runtime monkey-patch; the equivalent source change is 4 lines):
- create the pad tokens in the model dtype;
- cast the TimestepEmbedder output to the model dtype;
- in `_apply_rotary_emb`, return `out.astype(x.dtype)` (rotary math stays in fp32, the result is in the model dtype, which is diffusers' semantics);
- cast the additive attention mask to `q.dtype` (otherwise `scaled_dot_product_attention` rejects a float32 mask with bf16 q).

**Measured effect** (1024², 9 steps, `--low-ram`, same seed):
- **[verified]** Controlled cool A/B: denoise 78.3 s → 55.6 s (**−29.1%**).
- **[verified]** 24-pair ABBA A/B in the sustained/thermally-throttled regime: median per-pair denoise ratio 0.70; mean s/step 15.0 → 10.6.
- **[verified]** Peak memory footprint unchanged (7.34 vs 7.34 GB).
- **[verified]** Output is deterministic run-to-run, but not pixel-identical to fp32 (PSNR 20–42 dB depending on scene; differences are small content/layout variations).
- **[verified, single rater, n=24]** Blinded pairwise review: no quality regression (fp32 better 0, bf16 better 2, ties 22; text rendering is equal). Full protocol and data are available on request.
- **[inference]** The speed-up likely applies to every Apple-silicon machine, since fp32 matmul/attention is roughly 2× the bytes of bf16 regardless of GPU generation. Only one machine was measured.
- **[hypothesis]** Other mflux models with `mx.zeros` pad tokens or fp32 RoPE could have the same promotion. We only checked Z-Image.

Question for maintainers: is the float32 stream intentional (e.g. a quality choice)? If not, would a PR with the 4-line fix be welcome, possibly behind a flag at first?

### 2. `--low-ram` transformer release is ineffective before VAE decode

`MemorySaver.call_after_loop` sets `self.model.transformer = None` when `keep_transformer=False` (`callbacks/instances/memory_saver.py:69,100`). However, `ZImage._predict` (`variants/z_image.py:213-240`) returns `mx.compile(predict)`, and the compiled closure still references the transformer. The weights therefore stay resident during VAE decode **[verified]**.

Test: replace the closure with a holder that is cleared (plus `gc.collect(); mx.clear_cache()`) in `call_after_loop`.
- **[verified]** Output pixel-identical.
- **[verified]** 512²: VAE-phase MLX peak 5.63 → 2.16 GB; process peak footprint 7.26 → 5.93 GB.
- **[verified, 4+4 runs ABBA, 2 prompts]** 1024²: VAE-phase MLX peak 5.70 → 2.23 GB; process peak footprint 7.35 → 6.56 GB (−0.8 GB); pixel-identical; no time change.
- **[inference]** On 16 GB machines this is the difference between comfortable headroom and memory pressure at 1024².

### Not claimed
- No claim about CUDA or other back ends.
- No claim about models other than Z-Image-Turbo.
- No quality claim beyond the 24-pair blinded review described above.
