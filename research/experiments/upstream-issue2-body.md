Z-Image: `--low-ram` drops `model.transformer`, but the compiled `predict` closure keeps the DiT alive through VAE decode

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
- \*The bf16-activation rows come from a separate local patch; see the linked dtype issue. They are included only to show the fix is independent of activation dtype.

### Scope / not claimed
- Only Z-Image was checked. Other model families use different predict/closure structures, so we don't claim they are affected. [hypothesis: any variant that compiles a closure over the transformer and relies on `_delete_transformer` has the same issue]
- Tested on a single machine and memory size.

Happy to open a PR if that's useful.
