Z-Image: DiT hidden stream runs in float32 despite bf16 model precision (≈1.4× slower denoise on an M5)

### Environment (tested)
- mflux 0.20.0, mlx 0.32.2, mlx-metal 0.32.2, Python 3.12.14
- MacBook Air M5 (8-core GPU), 16 GB, macOS 27.0 (26A428)
- `mflux-community/z-image-turbo-mflux-q4` @ d2d30500, `mflux-generate-z-image-turbo --low-ram`, 1024×1024
- The relevant files are byte-identical on `main` @ 9ca480fd, so the references below point there.

### What happens [verified]
`ModelConfig.precision` is bfloat16, and the latents, caption features and q4 scales are bf16. However, a runtime dtype probe shows the DiT's attention input, SDPA `q` and FeedForward input are **float32** on every step.

An ablation (one patch subset per process, dtypes recorded at runtime) shows **two sources, and both must be fixed** to keep the stream in bf16:

1. **The timestep embedding is float32.**
   - [`transformer.py#L78`](https://github.com/mflux-community/mflux/blob/9ca480fd87fce5623e90878766c751d9140c4aa8/src/mflux/models/z_image/model/z_image_transformer/transformer.py#L78) passes `timestep.astype(mx.float32)` to the embedder.
   - The sinusoidal path in [`timestep_embedder.py#L32-L33`](https://github.com/mflux-community/mflux/blob/9ca480fd87fce5623e90878766c751d9140c4aa8/src/mflux/models/z_image/model/z_image_transformer/timestep_embedder.py#L32-L33) is float32, and the embedder output stays float32.
   - That `t_emb` feeds the adaLN modulation of every block, promoting the block input.
2. **The RoPE tables are float32.** [`rope_embedder.py#L35-L41`](https://github.com/mflux-community/mflux/blob/9ca480fd87fce5623e90878766c751d9140c4aa8/src/mflux/models/z_image/model/z_image_transformer/rope_embedder.py#L35-L41) builds them in float32, and [`_apply_rotary_emb`](https://github.com/mflux-community/mflux/blob/9ca480fd87fce5623e90878766c751d9140c4aa8/src/mflux/models/z_image/model/z_image_transformer/attention.py#L80-L88) returns the promoted dtype. So q/k are float32 at every attention call even when the block input is bf16.

| patched | SDPA q | FFN input |
|---|---|---|
| nothing | float32 | float32 |
| timestep-embedding output cast to bf16 only | float32 | float32 |
| RoPE output cast back to the input dtype only | float32 | float32 |
| **both** | **bfloat16** | **bfloat16** |

Not a source: `x_pad_token` / `cap_pad_token` are created with `mx.zeros` (float32), but they are loaded from the checkpoint as bf16, so they end up bf16.

### Minimal change we tested (as an in-process patch; no mflux files modified)
- cast the TimestepEmbedder output to the model dtype;
- in `_apply_rotary_emb`, return `out.astype(x.dtype)`. The rotation is still computed with the float32 tables; only the result is cast, matching diffusers.
- cast the additive attention mask built at [`attention.py#L71`](https://github.com/mflux-community/mflux/blob/9ca480fd87fce5623e90878766c751d9140c4aa8/src/mflux/models/z_image/model/z_image_transformer/attention.py#L71) to `q.dtype`. With bf16 q, SDPA rejected the float32 mask in our tests.

### Measured effect (1024×1024, 9 steps, q4, same seed) [verified]
- **Controlled A/B, chip cool before each arm:** denoise 78.3 s → **55.6 s (−29.1%)**.
- **Paired A/B, 24 prompt/seed pairs, ABBA order, back to back:** median denoise ratio **0.70**; mean s/step 15.0 → 10.6.
- **Peak memory:** unchanged (7.34 vs 7.34 GB).
- **Determinism:** output is deterministic run to run, but **not** pixel-identical to the float32-stream output (PSNR 20–42 dB depending on the scene; the differences are small content/layout variations).
- **Quality:** blinded pairwise review of those 24 pairs (single rater) found float32 better in 0 pairs, bf16 better in 2 (minor), no meaningful difference in 22, and no text-rendering regression.

### Scope / not claimed
- Single machine (M5, 16 GB). [inference] Since float32 activations double the memory traffic of every activation-side op, other Apple-silicon chips are likely affected too, but the size of the effect there is unmeasured.
- Only Z-Image was checked. [hypothesis] Other models with float32 timestep embeddings or RoPE tables may behave the same way.
- We don't know whether the float32 stream is intentional (e.g. a quality choice). If it is, perhaps it could be an opt-in or documented behaviour.

Related: #__ISSUE2__ (a separate memory issue we found in the same pipeline). Happy to open a PR if a bf16 stream is wanted.
