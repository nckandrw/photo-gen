# Q-VR (Phase 8): does the MLX runtime explain the Qwen VAE path's text loss? Reference-runtime validation

**Pre-registered class: RUNTIME-MATCHED** (`research/qwen/qv-reference/PROTOCOL.md` §7 rule 5), applied mechanically.
- **Gates:** all §5.1 gates pass.
- **Numbers:** the MLX production path (A1) differs from the official Diffusers implementation on CPU in fp32 (A2) by
  0.14–0.19/255 on every item. That is "SMALL": above Phase 7's own bf16-cast perturbation, and below its
  tiled-vs-untiled perturbation of 0.21–0.54/255. The PSNR between the arms is 50–55 dB.
- **TF32:** with `MLX_ENABLE_TF32=0` the two become pixel-equivalent on 6/6 items (0.002–0.004/255). The residual is
  MLX's documented TF32 default, **a precision mode, not a defect**.
- **Blind text review:** all 24 element calls are identical for A1 and A2 (R = Q = 0 at 512 and 1024).

**What this settles:** the Phase 7 Q-V losses are **not** an MLX/mflux runtime artefact. The same weights run through
the official reference implementation lose the same text. **Q-V's MIXED stands, unchanged.**

**What it does not settle:**
- This tests the VAE path only. The DiT and text-encoder runtimes are not tested.
- RUNTIME-MATCHED means "matches the official implementation", not "the VAE is adequate".

**Status unchanged:** G2 REJECTED, Q-Q AGAINST, Q-V MIXED (all frozen); Qwen editing research-only,
`validated: false`, Qwen Research License (non-commercial).

## 1. The external lead: ComfyUI #16433, the PyTorch-MPS VAE defect
- **What it is** (read at the implementation level, with the linked upstream fix):
  - MPSGraph's `padTensor` corrupts rank > 4 tensors once the inner extent reaches 2^16 elements (pytorch #194922,
    fixed by #195147 for torch 2.15).
  - The Wan/Qwen VAE's `AvgDown3D` front temporal pad hits it, giving round trips of 6.6–10 dB PSNR.
  - It is an operation in **PyTorch's MPS backend**. MLX implements `pad` independently.
- **mflux's own validation notes** (`mflux/models/qwen21/reference/VALIDATION.md`, a secondary source for us) found
  the same defect in PyTorch 2.13 MPS. They report MLX matching NumPy, and fp32 MLX-vs-Torch VAE errors of about 1e-4.
- **Our test (M):** hooks recorded every `mx.pad` call during encode and tiled decode at all four G2 sizes: 28
  distinct calls and 12 temporal AvgDown sites.
  - Each pad call was replayed on the GPU in fp32 and bf16 against `np.pad`, and each AvgDown site against a NumPy
    transcription of Diffusers' `AvgDown3D`.
  - **All bit-exact** (`runs/PROBE-mlx`). **The MPS defect class is absent from MLX.**
- **The positive control was negative.**
  - The same shapes through torch 2.14.0 `F.pad` on MPS were bit-exact against CPU (`runs/PROBE-mps`).
  - So were the upstream reports' own minimal reproductions: pytorch #194922, the ComfyUI comment's cases and mflux's
    all-ones case (`runs/PROBE-mps-upstream`, post-hoc and descriptive).
  - The reports came from macOS 15.8 and 26.x; this machine runs **macOS 27.0.1**, and MPSGraph ships with the OS.
    An OS-level fix is a **hypothesis**, not verified.
  - So §5.2's "read against a demonstrated failure" did not apply. The MLX probe stands on its own bit-exact NumPy
    comparison.

## 2. Gates (all passed; `qvr-summary.json`)
1. **Weights** (`runs/GATE-weights`): all **238/238** tensors of the canonical export's `vae/0.safetensors`
   (`248d52c5…`) are bit-identical to the dense source checkpoint's VAE, after the transforms derived per tensor:
   88 identical, 88 conv transposes (0, 2, 3, 1), 62 squeezes. MLX's in-memory parameters equal the file (238/238).
2. **A1 reproduces Phase 7:** for 6/6 items, the round-trip and input `pixel_sha256` equal Phase 7's run `a` records.
3. **Preprocessing:** the CPU side recomputed the input from the staged PNG with its own PIL calls, bit-identical
   (6/6).
   - *Labelled variable:* Diffusers' `VaeImageProcessor.preprocess` also gives an identical tensor (max |Δ| = 0), and
     `calculate_dimensions` gives the same sizes.
4. **bf16 cast:** torch's cast of A1's normalised latent equals A1's decoder input bit for bit (6/6), and it commutes
   with pack/unpack.
5. **Tiler port:** a NumPy port of mflux's `VAETiler` with MLX's per-tile decode reproduced mflux bit for bit (R12 at
   512 and 1024). The uint8 conversion port equals mflux's `to_pil` exactly (6/6).
6. **A2 determinism:** two fresh processes on R12-512 give byte-identical arrays.
7. **Banded CPU convolution** (amendment 1; `runs/GATE-conv`): bit-identical to the unbanded call.
   - Without banding, torch here has no oneDNN and runs batch-1 CPU convolutions as a full im2col. The synthetic 512
     smoke reached 11.2 GB.
   - An untiled 1024 CPU decode would need an ≈ 11 GB im2col buffer. That is an estimate; it was not run.

## 3. Numbers (A1 = MLX production path, A2 = CPU reference; descriptive except the tier)
| item | B_i (bf16-cast effect) | A1–A2 MAE (RGBA, /255) | tier | PSNR(A1, A2) dB | ΔPSNR vs D0 (A2 − A1) | z_norm rel. L2 A1/A2 | bf16 values flipped | decoder-only (X12) MAE | **A1T**–A2 MAE (TF32 off) |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|
| R02-512 | 0.160 | 0.195 | SMALL | 50.4 | −0.004 | 4.8e-3 | 34 % | 0.040 | **0.003 (PE)** |
| R12-512 | 0.122 | 0.144 | SMALL | 54.6 | −0.001 | 4.0e-3 | 37 % | 0.032 | **0.002 (PE)** |
| R15-512 | 0.144 | 0.163 | SMALL | 53.7 | +0.001 | 3.1e-3 | 33 % | 0.037 | **0.002 (PE)** |
| R02-1024 | 0.120 | 0.185 | SMALL | 52.7 | +0.001 | 5.5e-3 | 49 % | 0.039 | **0.004 (PE)** |
| R12-1024 | 0.092 | 0.137 | SMALL | 54.6 | +0.005 | 5.6e-3 | 51 % | 0.030 | **0.003 (PE)** |
| R15-1024 | 0.126 | 0.194 | SMALL | 52.4 | −0.002 | 5.3e-3 | 50 % | 0.040 | **0.004 (PE)** |

- **Where the difference comes from:**
  - The latent difference (relative L2 3–6e-3) falls **between** the pre-registered wordings (≤ 1e-3 "rounding
    level", ≥ 1e-2 "material"). With TF32 off it drops to about 5e-6, fp32 agreement.
  - The decoder alone, on identical latents, contributes 0.03–0.04/255. The rest comes from the encoder's TF32
    arithmetic, amplified by bf16 rounding flips: 33–51 % of latent values round to a different bf16 neighbour.
- **No arm or tensor holds a non-finite value.**
- **The largest single-pixel differences** (99 levels on R02-512, 76 on R12-1024) lie **outside** the text boxes.
  - Inside the boxes the maximum is 5–18 levels.
  - Pixels differing by more than 10 levels are 0.002–0.05 % of each image, and 0–7 of them per image are in boxes.

## 4. Blind review (fresh-subagent rater; frozen `review/SCORES-FROZEN.csv` `9bb5918e…`; 7 sheets / 28 versions)
**A1 vs A2:** 24/24 element calls are identical. With 50–55 dB between the arms, R = Q = 0 is expected; the review was
decisive only because the numbers fell outside the pixel-equivalence bound.

**Per element and glyph-height strata** (directive §13): `qv-reference/glyph-strata.md`.
- Round-trip losses concentrate below 10 px main-line height: 9 of the 10 losses.
- Elements at 10–20 px kept 3/3 at 1024.
- The one loss above 20 px (R12-1024 t5) is a composite element whose smallest lettering is about 3 px.
- Heights are approximate (±20 %) and exploratory.

**Second rater on Phase 7's exact pixels** (D0 and A1; descriptive only, never used to revise Q-V):
- Legibility agreement with Phase 7's frozen calls: 20/24 for D0 and 20/24 for A1, all at borderline elements.
- The round-trip legible totals are identical: **3/12 at 512, 7/12 at 1024**.
- This rater reads more in the scaled input (K = 8 and 12, against 6 and 10), so attributes more loss to the VAE
  (L = 5 at each budget, against 4 and 3).
- Put through Q-V's rules, that would still be **MIXED** (L₁₀₂₄ = 5 < 6).
- Three self-revised calls, all on D0 panels (§7), feed the K counts.
- The rater also called one unprocessed D0 panel's fidelity MINOR: a fidelity-noise datum.

## 5. Conditional arms (gate held: all gates pass, no item MATERIAL)
### 5.1 Texture-Fix decoder (`madebyollin/texture-fix-vae-for-qwen-image-2.1` @ `702909b`)
- **Hypothesis:** a decoder fine-tuned for cleaner textures might also keep small text better.
- **Controlled variable:** the decoder only. Latents were identical (A2's), as were runtime (CPU fp32), tiling and
  conversion.
- **Results:**
  - Weights (`runs/TF-weights`): all 132 decoder tensors were fine-tuned. 52 encoder tensors differ only by a
    constant ratio, the card's power-of-two rescale, and 50 are identical.
  - The **TF encoder output is bit-identical** to the original's (6/6), which verifies the card's "same function"
    claim exactly.
  - The TF decoder reconstructs **0.31–0.71 dB further** from D0 than the original decoder, on 6/6 items (MAE vs A2
    1.9–2.8/255). This agrees with the card's own slightly lower PSNR.
  - Text: the 24/24 TF calls equal A2's (R_TF = Q_TF = 0), so **no text difference was detected**.
- **Limitation:** the rater's helper shows it wrote shared notes for the three round-trip panels, treating TF as one
  of three near-identical panels, although TF differs visibly more than A1–A2 does. "TF does not rescue the text"
  stands; "TF has no effect on text" does not.
- **Conclusion:** a decoder swap of this kind is **not** a path to text preservation. It is not adopted.

### 5.2 Identity-edit probe (R15 at 512, production app path)
- **Run:** instruction "Preserve this image exactly. Do not change anything.", seed 2510715, 40 steps, `run_edit.sh app`.
- **Cost:** 88 s; peak footprint 8.16 GB.
- **Results:**
  - PSNR vs D0 **26.0 dB, against 31.1 dB for the output-path ceiling** (A1). SSIM 0.835 vs 0.910, and lower in all
    five text boxes.
  - Fidelity **MAJOR**: the mascots were recoloured, under a no-change instruction.
  - Of the three elements the ceiling keeps legible:
    - t3 (door number) is a **clear** loss: PRESERVED in A1 for both raters, GARBLED in ID;
    - t2 (window banner) is a **borderline** loss: this rater called A1 DEGRADED, Phase 7's rater GARBLED;
    - t1 (shop sign) is kept, DEGRADED.
  - Cross-rater, descriptive: G2's actual R15-512 edit (Q-Q frozen calls) garbled t1 too, while the identity edit
    kept it.
- **Conclusion (n = 1, one seed):** the full pipeline adds text loss and global drift beyond the output-path ceiling
  even when asked to change nothing. This is evidence for directive Scenario C, and it does not identify a single DiT
  operation.
- **1024 not run:** the pre-registered rule runs it only if 512 loses nothing.

### 5.3 Compositing baseline (R02 at 1024, the existing G2 output; no new edit)
- **Pre-registered arm (CMP, G2's `regions.change` box)** (`runs/CMP-1024-R02`):
  - The alignment shift was (0, 0). But the G2 edit had regenerated the whole frame: outside the box it differs from
    D0 by 10.3/255, with 56 % of pixels changed by more than 8 levels.
  - Rated:
    - the **G2 edit** removes the van cleanly (adherence PASS) but rewrites both signs into wrong letters (GARBLED;
      unintended change MAJOR);
    - the **hard and feathered composites** keep both signs PRESERVED and leave nothing unintended, but adherence is
      PARTIAL and realism MAJOR, with seams MAJOR (hard) and MINOR (feathered). G2's box cuts through the van's roof
      load, which is left floating.
  - Not viable by the pre-registered bar. **This tests G2's box, not compositing.**
- **Deviation and amendment 2:** using G2's box was an undeclared deviation from directive §18's "conservative manual
  mask". **CMP2** (post-hoc, disclosed) uses a whole-van mask drawn on D0 only (x 205–775, y 590–896), with a new
  fresh rater (`review-cmp2/`, frozen `1f60d2a4…`; audit clean):

  | version | adherence | seam | realism | unintended | t1 / t2 |
  |---|---|---|---|---|---|
  | G2 edit | PASS | NONE | MINOR | **MAJOR** (both signs rewritten; texture softened everywhere) | GARBLED / GARBLED |
  | hard composite | PASS | **MAJOR** (tone step at the box edge) | MINOR | NONE | PRESERVED / PRESERVED |
  | **feathered composite** | **PASS** | **MINOR** | **MINOR** | **NONE** | **PRESERVED / PRESERVED** |

  - The **feathered composite meets the "viable" bar** (§8.3), on this one case. Its remaining flaw is a small
    fragment of the van's shadow that the mask did not cover, cut by the box's right edge.
  - **Limits:** n = 1; the mask was chosen post-hoc, by hand, after the coverage failure was known; the rater differs
    from the main review's.
- **Conclusion:** keeping the original pixels outside a mask that covers the object (and its shadow), with a feathered
  edge, can keep the incidental text **and** carry the edit in a valid image, where the edit alone garbled both signs.
  - The hard problem is the mask: G2's box failed. An automatic, conservative and shadow-aware edit-region mask is the
    open question.
  - Identical pixels outside the mask were never counted as success by themselves; the rater judged the whole image.

## 6. Memory and time (descriptive; this Mac; monitor cadence 1.2–1.7 s per sample, not 1 s)
| step | wall time | peak footprint |
|---|---|---|
| A1 (MLX) round trip with captures | 512: 4–6 s; 1024: 12–21 s | 6.8–7.5 / 7.9–8.1 GB |
| A2 (CPU reference, banded; A2 + X12 decodes) | 512: 14–16 s; 1024: 62–63 s | 6.9 / 8.9–9.2 GB |
| TF decode + encoder check (CPU) | 512: ≈ 10 s; 1024: ≈ 35 s | 6.0–6.6 / 8.7–8.8 GB |
| identity edit, R15-512 (GPU, app) | 88 s | 8.16 GB |

- **Swap:** no step aborted, and no step had a critical-pressure sample. One step, TF-1024-R02, grew swap by 1.9 GB,
  just under the 2048 MB limit; all others grew it by less than 0.7 GB.
- **CPU reference without banding:** 11.2 GB at 512 on the synthetic smoke.

## 7. Limitations and disclosures
- **Scope:** 3 photographs × 2 budgets, one rater per review. VAE path only. The CPU reference shares the model
  definition lineage with mflux (mflux's VAE was adapted from Diffusers'), so this is a runtime/implementation check,
  not an independent re-derivation of the model.
- **Amendments:**
  - 1 (pre-run): banded convolution;
  - 2 (post-hoc): the conservative composite mask.
- **Incidents (tool bugs, not results):** a relative-path `ValueError` in `ref_side.py` and in `composite.py`. Both
  were fixed; the failed run directories are kept as `runs/FAILED-*`.
- **Rater audit** (`review/RATER-AUDIT.json`):
  - no key or run-record access;
  - it used nearest-neighbour (non-smoothing) enlargements;
  - **deviation:** it wrote a helper script in the session scratchpad, outside its permitted directories, to revise
    its own draft. It changed notes and three calls, all on D0 panels, so the A1/A2, TF and ID tallies are
    unaffected. The helper is preserved.
- **Leaked hypothesis** (via `CLAUDE.md`): pixel-equivalent panels were visibly alike, and panel sizes reveal the
  budget.
- **macOS:** the machine has run 27.0.1 since 2026-09-29, while `docs/HARDWARE.md` says 27.0. A note was added there.
- **No OCR or CER:** no OCR engine is installed in any project environment (protocol §12).

## 8. What this means (directive §26)
- **Scenario B holds:** CPU and MLX agree, and the reconstruction loss is real at the tested budgets.
  - The loss is concentrated in glyphs under about 10 px.
  - A texture-oriented decoder fine-tune does not help.
- **Scenario C also holds** (n = 1): even a no-change edit loses text beyond that ceiling and drifts globally.
- **Compositing** (n = 1): pasting the original back keeps the text by construction.
  - With G2's box it failed on mask coverage.
  - With a covering, feathered mask (post-hoc) it was **viable**: the edit carried, both signs kept, seam and realism
    MINOR.
  - The cheapest path to text preservation is therefore *not* inside the Qwen model: it is a preservation-aware
    pipeline, whose open problem is automatic masking.
- **Together:** for this model on this machine, no remaining runtime, precision or decoder experiment is likely to
  change the G2 outcome. The constraints are the representation and the regenerating editor.
- **Recommendation:** stop Qwen-Image-2.1-focused work and redirect to `research/editing/QA-ALTERNATIVE-MODELS.md`,
  starting with the FLUX.2 [klein] 4B VAE entry screen.

## 9. Storage
- **Kept:**
  - the dense source checkpoint (RETAIN LOCALLY; its VAE was read as the reference);
  - the canonical q4 export (its VAE only was read);
  - the Texture-Fix VAE (1.35 GB, `models/research/`). Its deletion trigger is met at Phase 8 close; it is **kept
    pending your decision**.
- **Not done:**
  - the q8 export was not recreated;
  - no production, `app/`, `config/` or pinned-venv change.
- **New:** a research-only venv `torch-ref/` (675 MB, gitignored), installed from a hashed lock.
