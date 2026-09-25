# Upstream mflux issues — SUBMITTED (auditable record)

- **Submitted:** 2026-09-25 00:42–00:43 UTC (08:42–08:43 PST), by the user's GitHub account via `gh`, under the directive "PHOTO-GEN NEXT RESEARCH PASS" §11.
- **Repository:** `mflux-community/mflux` (the former `filipstrand/mflux` redirects here).
- **Tested:** mflux 0.20.0 / MLX 0.32.2 / mlx-metal 0.32.2 on a MacBook Air M5 16 GB, macOS 27.0 (26A428), model `mflux-community/z-image-turbo-mflux-q4` @ d2d30500.
- **Line references:** pinned to upstream `main` @ 9ca480fd87fce5623e90878766c751d9140c4aa8. The relevant files are byte-identical to the installed 0.20.0.
- **Duplicate search:** before submission, the tracker was searched (float32/bf16/dtype/low-ram/keep_transformer/pad_token/rotary). No duplicate; related, not duplicate: #714/#715 (RoPE lazy eval), #718 (slicing), #753 (FBCache).
- **Changes vs the DRAFT** (`upstream-mflux-issue-DRAFT.md`, preserved unedited apart from its correction header):
  - split into two issues;
  - pad-token claim removed after the E10 ablation disproved it;
  - "each source sufficient" replaced by the measured "both required";
  - `del predict` offered as an untested alternative.
- **Maintainer responses:** none yet. Append below with dates; never edit the evidence above to match a response.

## Issue #761 — Z-Image: DiT hidden stream runs in float32 despite bf16 model precision (≈1.4× slower denoise on an M5)  [title as corrected; originally "≈30% slower"]
URL: https://github.com/mflux-community/mflux/issues/761

````markdown
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

Related: #760 (a separate memory issue we found in the same pipeline). Happy to open a PR if a bf16 stream is wanted.
````

## Issue #760 — Z-Image: `--low-ram` drops `model.transformer`, but the compiled `predict` closure keeps the DiT alive through VAE decode
URL: https://github.com/mflux-community/mflux/issues/760
(Body edited once, 00:43 UTC, only to append the cross-link to #761.)

````markdown
### Environment (tested)
- mflux 0.20.0, mlx 0.32.2, mlx-metal 0.32.2, Python 3.12.14
- MacBook Air M5 (8-core GPU), 16 GB, macOS 27.0 (26A428)
- `mflux-community/z-image-turbo-mflux-q4` @ d2d30500, `mflux-generate-z-image-turbo --low-ram`
- The relevant files are byte-identical on `main` @ 9ca480fd, so the references below point there.

### What happens
1. [`generate_image`](https://github.com/mflux-community/mflux/blob/9ca480fd87fce5623e90878766c751d9140c4aa8/src/mflux/models/z_image/variants/z_image.py#L106) creates `predict = self._predict(self.transformer)`.
2. [`_predict`](https://github.com/mflux-community/mflux/blob/9ca480fd87fce5623e90878766c751d9140c4aa8/src/mflux/models/z_image/variants/z_image.py#L213-L240) returns `mx.compile(predict)` (except on M1/M2), and the inner function closes over `transformer`.
3. With `--low-ram`, [`MemorySaver.call_after_loop`](https://github.com/mflux-community/mflux/blob/9ca480fd87fce5623e90878766c751d9140c4aa8/src/mflux/callbacks/instances/memory_saver.py#L61-L75) → [`_delete_transformer`](https://github.com/mflux-community/mflux/blob/9ca480fd87fce5623e90878766c751d9140c4aa8/src/mflux/callbacks/instances/memory_saver.py#L100) sets `self.model.transformer = None`, then runs `gc.collect()` and `mx.clear_cache()`.
4. The local `predict` is still alive in `generate_image` during `_decode_latents`, and its closure (and the compiled function) still references the transformer. **The q4 DiT (≈3.47 GB) stays resident through VAE decode.** [verified]

### Evidence [verified on the environment above]
- **Reproducer (no weights needed):** run `ZImage._predict(t)` on a stand-in object `t`, drop every other reference, and call `MemorySaver(keep_transformer=False).call_after_loop(...)`. A `weakref` to `t` is still alive afterwards. We keep this as a unit test.
- **Real run (1024×1024, 9 steps, `--low-ram`):** MLX active memory entering `_decode_latents` = **3.47 GB**, and the VAE-phase MLX peak = **5.70 GB**.

### Fix we tested
`predict` reads the transformer from a small holder dict. After the loop, the holder is cleared (both the transformer and the compiled function), followed by `gc.collect()` and `mx.clear_cache()`. We did this as an in-process patch in our app; no mflux files were modified. The `predict` body and the compile decision are unchanged.

Sketch:
```python
@staticmethod
def _predict(transformer):
    holder = {"t": transformer}
    def predict(latents, timestep, sigmas, text_encodings, negative_encodings, guidance):
        tr = holder["t"]
        ...  # unchanged body, using tr
    holder["fn"] = predict if AppleSiliconUtil.is_m1_or_m2() else mx.compile(predict)
    def call(*a, **k): return holder["fn"](*a, **k)
    call.release = lambda: holder.clear()   # invoked where MemorySaver drops the transformer
    return call
```
Upstream this could be done more simply, e.g. `del predict` in `generate_image` right after `ctx.after_loop(latents)`. We have **not** tested that variant; it would need the same checks (the compiled function must not be cached elsewhere).

### Measured effect of the holder fix (ABBA, 2 reps per config, production settings, seed 42)
| config | peak process footprint before → after | VAE-phase MLX peak before → after | output |
|---|---|---|---|
| fp32 activations, 1024² | 7.26–7.35 → **6.56 GB** | 5.70 → **2.23 GB** | pixel-identical |
| fp32 activations, 512² | 6.88–7.26 → **5.93 GB** | 5.63 → **2.16 GB** | pixel-identical |
| bf16 activations*, 1024² | 7.26–7.33 → **5.84 GB** | 5.70 → **2.23 GB** | pixel-identical |
| bf16 activations*, 512² | 7.00–7.25 → **5.41 GB** | 5.63 → **2.16 GB** | pixel-identical |

- Runtime: no measurable change. `mx.compile` is called once per run in both arms (no recompilation), load and text-encode times are unchanged, and VAE time is unchanged within noise.
- Swap growth was 0 MB in all 16 runs.
- \*The bf16-activation rows come from a separate local patch; see the related dtype issue (linked below). They are included only to show the fix is independent of activation dtype.

### Scope / not claimed
- Only Z-Image was checked. Other model families use different predict/closure structures, so we don't claim they are affected. [hypothesis: any variant that compiles a closure over the transformer and relies on `_delete_transformer` has the same issue]
- Tested on a single machine and memory size.

Happy to open a PR if that's useful.


Related: #761 (float32 hidden stream in the same pipeline; source of the bf16 rows above).
````

## Edits after submission
- 2026-09-25 00:45 UTC: #761 **title** corrected from "(≈30% slower denoise on an M5)" to "(≈1.4× slower denoise on an M5)". The original was a baseline error: fp32 is ≈1.41× slower; equivalently, bf16 takes ≈29% less denoise time. Body unchanged.

## Maintainer responses
(none as of 2026-09-25 08:45 PST)

## Tracking log
- 2026-09-25 ~14:20 local (Phase 3 §18): checked via `gh api`.
  - #760: open, 0 comments, last updated 2026-09-25T00:43Z.
  - #761: open, 0 comments, last updated 00:45Z.
  - #753 (FBCache, third-party): open, 0 comments.
  - No maintainer response and no related merged PR. The latest PRs are #758/#756/#749/#747/#741, none touching Z-Image precision or `--low-ram` lifetime.
  - Upstream main is 9ca480fd (2026-09-23), unchanged since the issues were filed.
  - Upstream fix policy (directive §18): inspect → reproduce locally → compare with our patch → benchmark on M5 → decide. The pinned environment is not changed because upstream changes.
- Related upstream finding, not yet filed: mflux applies the FLUX dynamic sigma shift to Z-Image-Turbo, while the official pipeline uses a static shift of 3.0 (`sigma-schedule-audit.md`). This is held back until the audit's A/B shows whether it matters.
