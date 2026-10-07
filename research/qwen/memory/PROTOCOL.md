# Phase 5 memory-lifetime A/B: pre-registration (directive §5–§8)

**Written and committed before any A/B run** (the 384²/3-step functional smoke in `smoke/` is not evidence; it only checked that the patches install and run). Chain: `mem-chain.sh`. Results go in `research/qwen/QWEN-MEMORY-LIFETIME.md`.

## 1. Question
Can the Qwen edit lifecycle on mflux 0.21.0 release components that later stages don't need, earlier, so that the binding memory phase shrinks? The binding phase is denoise at 1024 (11.01 GB MLX, 12.1 GB footprint, +1.3–2.1 GB swap per edit); see `QWEN-EDITING-BASELINE.md` §4. The change must leave pixels exactly unchanged and not cost meaningful runtime.

## 2. What the mflux 0.21.0 source shows (read before designing; file references are in the site-packages of `mflux-qwen/.venv`)
- **Load order** (`qwen21/qwen21_initializer.py` `load_components`): VAE, then transformer, then text encoder, each materialized at load. PHOTO-GEN's production patch already defers the transformer (Phase 4).
- **`QwenImage21Edit.generate_image`** (`variants/edit/qwen_image_21_edit.py`) runs:
  1. `_encode_prompt` (Qwen3-VL text + vision);
  2. `mx.eval(prompt_embeds)`;
  3. the reference `self.vae.encode(pixels)`, untiled and direct;
  4. `before_loop` callbacks, where MemorySaver drops the text encoder;
  5. 40 DiT steps with the prefix KV cache;
  6. `after_loop`, where MemorySaver drops the transformer (`--low-ram`);
  7. `VAEUtil.decode(self.vae, …)`, tiled.
- **The text encoder** (q4, ≈ 5.1 GB) is used only in step 1, because the worker never passes guidance, a negative prompt, enhance, verify, auto-mask or more than one seed (the runtime rejects them all). It is nevertheless resident through step 3, the pre-denoise peak.
- **The VAE** (`QwenImage21VAE`, fp32, 1.35 GB: encoder 0.32 GB, decoder 1.04 GB, from the export's `vae/0.safetensors` header) is used only in steps 3 and 7. It is nevertheless resident through all 40 denoise steps, the binding phase at 1024.

## 3. Arms (worker flags; `mem_run.py` policies)
| arm | flags | meaning |
|---|---|---|
| **P0** | `defer_transformer_load` | production at Phase 4 close (baseline) |
| **P2** | P0 + `release_text_encoder_after_encode` + `release_vae_during_denoise` | candidate |
| P1, PV | either patch alone | diagnostics, run **only** if P2 fails parity (to find the culprit) |

The patches are in `app/photogen/runtimes/mflux_qwen_edit_worker.py`, `_install_lifetime_policy`. They are lifetime-only:
- the text encoder is set to `None` after its output is evaluated;
- at `before_loop` the VAE is swapped for a fresh instance loaded through mflux's own `load_components`, with the same export and arguments, and left lazy. Its decoder bytes are re-read at the first decode tile.

No weight, graph or kernel changes. The runtime default stays P0 until this gate passes.

## 4. Runs (fixed order; one chain, apps closed, AC; 20 s gaps; 120 s cooldown before the 1024 block)
- **Preflight on the Phase 5 code** (real CLI, GPU lock honoured), Z-Image regression:
  - REFERENCE 1024 → `fe47d88d`;
  - FAST 1024 → `7b45cfbe`;
  - BALANCED 1024 → `befe1b3c`;
  - ULTRA 512 → `6aa2b842`;
  - REFERENCE 512 → `9ae59f59`.
- **Preflight edit:** `bin/photo-gen edit` on E05 at 512, seed 42 → `bd548f1b` (production policy P0; it also exercises the new identity code).
- **A/B inputs** (`inputs.json`): E05 (G0 source, 1024², "Change the background to a sunset beach") and E08c (a 3:2 crop of the G0 source E08, 1024×683, "Replace the bananas with pineapples. Do not change anything else."). Neither is a G2 source. Seed 42, 40 steps.
- **512:** E05-P0, E05-P2, E08c-P0, E08c-P2.
- **1024:** E05-P0a, E05-P2a, E05-P2b, E05-P0b (ABBA), E08c-P2, E08c-P0.

## 5. Acceptance (all must hold → ADOPT P2 as the production default; otherwise not adopted, and the result is reported as is)
1. **Exact parity.** Every P2 output has the same RGB `pixel_sha256` **and** the same RGBA sha256 as its paired P0 output (same input, budget, seed). P0 E05 must equal the G0 hashes (512 `bd548f1b…`, 1024 `792fdaa9…`), which ties the baseline to the worker that produced G0.
2. **Determinism.** At 1024, E05-P0a = E05-P0b and E05-P2a = E05-P2b.
3. **Material reduction at 1024.** The median peak footprint (libproc lifetime max) over the three 1024 pairs is **≥ 0.75 GB lower** for P2, and the median swap growth is not higher.
4. **No meaningful runtime regression at 1024.** Median wall P2 ≤ 1.03 × median wall P0 over the three pairs, and the P2 VAE-decode phase is no more than **+3 s** above the paired P0 (the lazy decoder re-read).
5. **Operational.** No P2 run aborts or records a critical-pressure sample.

**Disclosed expectations.** The expected saving is set by the component sizes, not by guesswork: up to 1.35 GB (the VAE) on the denoise phase, and up to ≈ 5.1 GB (the text encoder) on the reference-VAE-encode phase. At 512 the binding phase should become text+vision encode, so the 512 saving will be smaller than the VAE-encode drop suggests.

## 6. Reporting
`QWEN-MEMORY-LIFETIME.md` gets:
- the per-stage table: footprint and MLX active/peak at startup, load, text encode, VAE encode, before loop, step 0, loop end, decode and end;
- the object-residency table;
- parity hashes, timing and swap/pressure per run;
- the verdict against §5.

If P2 is adopted, the runtime flags are switched in a separate commit that cites this gate.
