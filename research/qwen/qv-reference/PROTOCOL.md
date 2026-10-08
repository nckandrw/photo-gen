# Q-VR: reference-runtime validation of the Qwen-Image-2.1 VAE path (Phase 8 pre-registration)

**Status.** This file is committed **before any Phase 8 tool has run on a G2 photograph, before the weight-identity
check, before any primitive probe, and before any Phase 8 output exists.** The thresholds in §6 and the rules in §7 are
fixed here. Tools follow in a separate commit, smoke-tested on synthetic images only. Nothing below is made stricter
or looser after results are seen; deviations become dated amendments at the end. Local times are Asia/Manila (UTC+8;
`date` prints "PST").

**Scope.** A measurement-instrument check, **not a quality gate.** It cannot change G2 (REJECTED), Q-Q (AGAINST) or
Q-V (MIXED), their frozen scores, or Qwen's status (research-only, `validated: false`, Qwen Research License,
non-commercial). Nothing here changes `app/`, `config/`, either production venv, or any production path.

## 1. Question
Do the same Qwen-Image-2.1 VAE weights, given bit-identical inputs, produce materially different encode/decode results
through **A1, MLX/mflux** (the production path that Phase 7 measured) and **A2, an independent CPU reference** (the
official Diffusers implementation, PyTorch on CPU, fp32)?

**What is already known, stated up front so the result is read correctly:**
- **A catastrophic MPS-style failure is already excluded.** The third-party PyTorch-MPS defect (ComfyUI #16433,
  pytorch #194922) gives round trips of 6.6–10 dB PSNR and mean absolute error ≈ 48/255. Phase 7's MLX round trips are
  29–33 dB from the scaled input, mean absolute error 3.7–5.5/255. **What Phase 8 can still find is a subtle,
  runtime-specific difference.**
- **Our 1024 sizes are in that defect's risk zone.** 896×1184 and 1184×896 appear in the third-party "broken" table,
  and mflux's `qwen21_avg_down.py` performs the same rank-5 temporal front pad, with `mx.pad`. MLX's pad is a different
  implementation from MPSGraph's, so the defect is a hypothesis for MLX, not a fact. §5.2 tests it directly.
- **mflux's VAE says it was adapted from the Diffusers class.** "Independent" here means a different runtime and
  framework running the official reference code, not a different model. RUNTIME-MATCHED therefore means "MLX matches
  the official reference implementation", never "the VAE is good".
- **M5 TF32.** `research/experiments/nax-status.md` verified that MLX's fp32 matmul and attention run at TF32-class
  precision by default (`MLX_ENABLE_TF32=1`); production strips `MLX_*`, so production always runs with it. Whether
  MLX's convolutions use it is unknown. A1 is therefore "fp32 storage, TF32-class math in some ops", not IEEE fp32. The
  A1T arm (§3) isolates this.

## 2. Evidence protected (checked 2026-10-09, before any Phase 8 run)
- **Git:** tree clean; Phase 7 is **9** commits after `56880d2` (`a390bef` … `b213b73`, plus the docs-only resume aid
  `817a7c2`; the directive expected 8 ending at `b213b73`). They were reviewed (no `app/`, `config/` or `bin/` change; no
  image, weight or large file) and pushed as a fast-forward `56880d2..817a7c2`. Tags v3 (`1c097eb` → `401e400`) and v4
  (`1741179` → `33669eb`) are unchanged locally and on the remote.
- **Frozen sheets, untouched since their freeze commits:** G2 `SCORES-FROZEN.csv` `f14deba4…`; Q-Q `bcef9aa3…` /
  `4c8d6f36…`; Q-V `SCORES-FROZEN.csv` `00c1b5e3…` / `PREFERENCE-FROZEN.csv` `43066548…`.
- **Assets** (`research/qwen/assets/qwen-assets-verification-phase8-pre.json`): source checkpoint 87 files, 28/28
  upstream-matched at `d26bb61`; canonical q4 export 18/18 pinned; no q8 export.
- **Checks:** tests 93/93 OK; `bin/photo-gen verify` ok; `verify --edit` ok.
- **Phase 7 count audit** (directive §6, done first): `phase7-transitions.md`. 512: K 6, L 4, one reversal (R15 t3) →
  3 legible; 1024: K 10, L 3, no reversal → 7. Figures correct; the headline prose was clarified in place (`3c0a07f`).

## 3. Arms
Items: the staged G2 inputs **R02, R12, R15** at **512 and 1024** (6 items), exactly as Phase 7.

| arm | what | runtime | rated? |
|---|---|---|---|
| **D0** | the scaled conditioning input: Phase 7's `input.png` (re-derived bit-exactly by A1) | PIL | yes |
| **A1** | the production MLX path, re-captured with tensors (§4.1). Must reproduce Phase 7's `roundtrip` `pixel_sha256` | mflux 0.21.0 / MLX 0.32.2, edit venv, production worker env, GPU | yes |
| **A2** | Diffusers `AutoencoderKLQwenImage21` on CPU, fp32, fed **A1's exact input tensor**; same normalisation, bf16 cast, mflux tiling arithmetic and output conversion (§4.2) | torch 2.14.0 CPU, diffusers 0.41.0, `torch-ref/.venv` | yes |
| **X12** | stage isolation: **A2's decoder on A1's exact decoder input** (MLX encoder → CPU decoder) | CPU | no (numeric) |
| **A1T** | A1 with `MLX_ENABLE_TF32=0` (precision-mode attribution) | MLX GPU | no (numeric) |
| X21 | CPU encoder → MLX decoder | — | conditional: only if any item is MATERIAL (§6) |

**Improvement Clause (declared now).**
1. **Identical inputs, one stage at a time.** A2 receives A1's captured fp32 encode input, not its own preprocessing, and
   X12 receives A1's exact decoder input. Comparing stages on identical inputs localises any difference to the
   encoder or decoder from the start, which makes most of directive §12 unnecessary. The full A2 chain is still run
   for the rated images. *Validity:* stronger (no preprocessing confound). *Cost:* seconds.
2. **A1T arm.** TF32 is the most likely source of any A1–A2 difference, and it is a documented precision mode, not a
   defect. *Cost:* seconds per item; production untouched (a separate launcher sets the variable).
3. **Primitive probes (§5.2).** The MPS defect is tested at the operation level in MLX, with a PyTorch-MPS positive
   control. *Cost:* seconds, no weights.
4. **Short-circuit for the text review (§7).** If A1 and A2 differ by less than the bf16 cast that production already
   applies, a blind rater cannot be informative about the runtime: flips at 3–5 px glyphs would be rater noise. The
   review still runs (directive §14; it also carries the conditional arms and records the §13 per-element table), but
   then A1/A2 call differences are reported as rater test–retest disagreement, not runtime evidence.
5. **No untiled-vs-untiled arm.** Every G2 size exceeds mflux's 32-latent decode tile, so production decodes tiled at
   both budgets; each tile decode is itself an untiled decode, so the decoder is compared untiled per tile anyway.
   Phase 7's untiled MLX variant at 1024 reached 12.5 GB with critical memory samples, and an untiled CPU decode at
   1024 would need an ≈ 11 GB im2col buffer (torch CPU here has no oneDNN; batch-1 convolutions use im2col + BLAS).

## 4. The two paths
### 4.1 A1 (MLX, `mlx_side.py capture`, edit venv, production worker environment via `mlx_run.py`)
Phase 7's own functions, imported from `research/qwen/qv/qv_roundtrip.py` (unchanged): `load_vae` (vae-only
`Qwen21Initializer.load_components`, canonical q4 export, `vae/0.safetensors` `248d52c5…`), `preprocess`
(`open_oriented().convert("RGBA")` → LANCZOS to `dimensions(budget, w/h)` → `/127.5 − 1`, NCHW), `vae.encode`
(untiled; latent mean, normalised by the checkpoint `latents_mean`/`latents_std`), `pack_unpack(…, bf16)`, `decode` with
`TilingConfig()` (512 px tiles, 8-latent overlap, cosine ramp), `to_pil`. MLX cache limit 1 GB. Saved (`.npy`, fp32):
`x_in` (1,4,H,W), `moments` (the 128-channel `quant_conv` output, before the mean is taken), `z_norm` (normalised mean),
`z_dec_in` (after pack → bf16 → unpack → fp32; the decoder's actual input), `dec` (tiled decoder output in [−1, 1],
before conversion). Also `roundtrip.png` (RGBA) and the in-memory parameter check (§5.1).

### 4.2 A2 (CPU reference, `ref_side.py`, `torch-ref/.venv`)
- **Model:** `AutoencoderKLQwenImage21.from_config(<dense vae/config.json>)`, then `load_state_dict(<dense
  vae/diffusion_pytorch_model.safetensors>, strict=True)` directly: no `from_pretrained`, no hub (`HF_HUB_OFFLINE=1`).
  fp32, `eval()`, `torch.inference_mode()`. Every parameter and every input is asserted to be on CPU; nothing is ever
  moved to MPS. The thread count is recorded.
- **Encode:** `vae.encode(x_in[:, :, None])` with tiling off (Diffusers default), posterior `mode()` (= mean);
  the 128-channel `posterior.parameters` is saved as `moments`.
- **Latent handling:** `(mean − latents_mean) / latents_std` (fp32, the checkpoint config), then fp32 → bf16 → fp32
  (`torch.Tensor.to`). `pack`/`unpack` are pure permutations, so they are not re-implemented; §5.1 proves the cast
  commutes with them on A1's data.
- **Decode:** a verbatim NumPy port of mflux's `VAETiler.decode_image_tiled` (`tiler_port.py`), calling
  `vae.decode(z · latents_std + latents_mean)` per tile (Diffusers clamps to [−1, 1], as mflux clips).
- **Output conversion, both arms:** `tiler_port.to_uint8`: `clip(x/2 + 0.5, 0, 1)·255 → round → uint8`, mflux's
  `ImageUtil` arithmetic in NumPy. A1 and A2 are compared as float arrays **and** after this conversion.
- **Independent preprocessing check:** A2 recomputes the input from the staged PNG with its own PIL calls
  (`ImageOps.exif_transpose`, RGBA, the same dimension formula, LANCZOS, `/127.5 − 1`) and must equal A1's `x_in` bit
  for bit. Diffusers' own `VaeImageProcessor.preprocess` (`/255`, then `2x − 1`) is computed as a **separately labelled
  variable** and only reported (max difference, elements differing); it is never fed to the VAE.

## 5. Gates (all must pass; otherwise INCONCLUSIVE for the affected budget)
### 5.1 Identity and transcription gates
1. **Weight identity** (`weight_identity.py`): all 238 tensors of the export's `vae/0.safetensors` equal the dense
   `diffusion_pytorch_model.safetensors` tensors **bit for bit** after a layout transform that is defined per tensor by
   inspection and recorded (expected: identical, 4-D conv `transpose(0,2,3,1)`, or a reshape that only drops size-1
   axes). Any other transform, any missing tensor, or any non-zero difference fails the gate.
2. **A1 in-memory parameters** equal the export file tensors bit for bit (what MLX actually computes with).
3. **A1 reproduction:** for 6/6 items, A1's `roundtrip.png` `pixel_sha256` equals Phase 7's run `a` record, and A1's
   `input.png` equals Phase 7's `input.png`.
4. **Preprocessing:** A2's own recomputation equals A1's `x_in` bit for bit (6/6).
5. **Cast:** torch's bf16 cast of A1's `z_norm` equals A1's `z_dec_in` bit for bit (6/6), and A1's `z_dec_in` equals
   MLX's elementwise cast of `z_norm` (the permutation commutes).
6. **Tiler port:** on one 512 and one 1024 item, `tiler_port.decode_image_tiled` with MLX's own per-tile decode
   reproduces mflux's `VAETiler` output bit for bit, and `tiler_port.to_uint8` of A1's `dec` reproduces A1's
   `roundtrip.png` RGBA pixels (any differing pixel count is recorded; required: 0).
7. **A2 determinism:** R12-512 is run twice in fresh processes; the outputs must be bit-identical.

### 5.2 Primitive probes (the MPS-defect hypothesis at operation level)
- **MLX (test):** hooks record the exact shape, pad widths and dtype of every `mx.pad` call during an encode **and** a
  tiled decode at each of the four G2 sizes (576×448, 448×576, 1184×896, 896×1184), using a synthetic image of that
  size (shapes depend only on size). Each distinct call is replayed on the GPU with random data in **fp32** (the
  production dtype) and **bf16**, against `np.pad`; and the full `Qwen21AvgDown` op at each temporal call site is
  replayed against a NumPy transcription of Diffusers' `AvgDown3D`. Pass = every comparison bit-exact (the pad) or
  ≤ 1e-6 max abs (the averaging op, fp32).
- **PyTorch MPS (positive control, never a reference):** the same temporal-pad shapes through `F.pad` on MPS against
  CPU, torch 2.14.0 (before the upstream fix in 2.15). It shows whether the defect class is present on this machine,
  so a clean MLX result is read against a demonstrated failure.
- **Interpretation (fixed now):** if any MLX probe fails, the result is a candidate MLX defect: it is reported with a
  minimal reproduction, and its effect on A1 is assessed through §6; nothing is patched.

## 6. Numerical comparison and thresholds (fixed now)
**Per item i**, B_i is Phase 7's own measured effect of the bf16 latent cast that production applies (the
`fp32-latents` variant of run `QV-<b>-<task>-a`, mean absolute RGBA difference on the 0–255 scale):

| item | 512 R02 | 512 R12 | 512 R15 | 1024 R02 | 1024 R12 | 1024 R15 |
|---|---|---|---|---|---|---|
| B_i | 0.15999 | 0.12229 | 0.14379 | 0.12032 | 0.09151 | 0.12640 |

**Final-image tier for A1 vs A2** (both converted with `to_uint8`; MAE on the 0–255 scale; ΔPSNR = PSNR(A2, D0) −
PSNR(A1, D0), RGB):
- **PIXEL-EQUIVALENT (PE):** MAE_RGBA(A1, A2) ≤ B_i. The runtimes differ by less than a cast production already makes.
- **MATERIAL:** MAE_RGB(A1, A2) ≥ 1.0, or |ΔPSNR| ≥ 0.5 dB, or any non-finite value in any A1/A2 tensor.
- **SMALL:** neither.

**Localisation (descriptive, reported for every item):** shape, dtype, min/max, mean, variance, finite counts, MAE,
max abs, RMS, relative L2 and Pearson correlation for `moments`, `z_norm`, `z_dec_in` (also the fraction of bf16 values
that differ), the decoder output on identical latents (X12 vs A1) and the full round trip (A2 vs A1). Wording fixed now
for `z_norm`: relative L2 ≤ 1e-3 → "agreement at fp32/TF32 rounding level"; ≥ 1e-2 → "material latent mismatch"
(investigated, not interpreted).

**TF32 attribution:** A1T vs A2 is tiered the same way. If A1 vs A2 is not PE but A1T vs A2 is PE, the difference is
attributed to MLX's TF32 default and labelled **"precision-mode difference (documented MLX default), not a defect"**.

## 7. Classification (applied mechanically, in this order)
R_b = elements legible (PRESERVED or DEGRADED) in A2 but not in A1 at budget b; Q_b = legible in A1 but not in A2;
both from the same blind rater.
1. **INCONCLUSIVE** if any §5.1 gate fails, or the reference cannot be run safely at a budget (§9). In the second case
   the other budget is still classified and the failed budget is reported as unresolved.
2. **RUNTIME-MATCHED** if every item is PE. The A1/A2 text calls are then rater test–retest calibration only.
3. **MLX-DEGRADED** if ≥ 2 items are MATERIAL with ΔPSNR ≥ +0.5 dB, or (some item is not PE and) R_b − Q_b ≥ 2 at
   either budget.
4. **REFERENCE-DEGRADED** if ≥ 2 items are MATERIAL with ΔPSNR ≤ −0.5 dB, or (some item is not PE and) Q_b − R_b ≥ 2
   at either budget.
   If both 3 and 4 hold → INCONCLUSIVE.
5. **RUNTIME-MATCHED** if no item is MATERIAL and |R_b − Q_b| ≤ 1 at both budgets.
6. **INCONCLUSIVE** otherwise; the localisation (§6) and, if any item is MATERIAL, the X21 arm are reported.

**Worded in advance:** RUNTIME-MATCHED means "the tested MLX path shows no material runtime-specific difference from
the official CPU reference on these items"; it strengthens the reading that the common VAE/preprocessing path is
responsible for the Q-V losses, and it does not claim every MLX op equals CPU. MLX-DEGRADED means a runtime-specific
cause is plausible; it is localised and reproduced minimally before it is attributed, and production is not patched.

## 8. Conditional arms (each runs only if its gate holds; otherwise it is deferred and the reason recorded)
**Gate for all three:** every §5.1 gate passes and **no item is MATERIAL** (an unresolved runtime difference would
confound them; directive §16).

### 8.1 Texture-Fix decoder (TF)
- **Identity:** `madebyollin/texture-fix-vae-for-qwen-image-2.1` @ `702909b4d408912c7a28fadea06e8b7fdb38ef0c`,
  `diffusion_pytorch_model.safetensors` (fp32, 1,350,989,544 bytes, LFS sha256 `9c4a3e6b…f492a6a8`) and `config.json`.
  Licence: Qwen Research License (non-commercial), the same as the base model; research-only use matches it.
- **Acquisition audit** is written and committed before the download, into `models/research/` (gitignored).
- **Compatibility:** strict load into the same class; `config.json` identical to the original's; a per-tensor diff
  against the original VAE (which tensors differ, encoder vs decoder); encoder equivalence on one 512 and one 1024
  item (relative L2 of `z_norm`, TF encoder vs original). The decoder comparison uses identical latents either way.
- **Arm:** A2's `z_dec_in` → TF decoder through the same tiler and conversion, on CPU. Rated as a panel.
- **Reading (fixed now):** R_TF / Q_TF = elements legible in TF but not A2 / in A2 but not TF, per budget. "TF keeps
  more text" if R_TF − Q_TF ≥ 2 at a budget; "TF loses more text" if Q_TF − R_TF ≥ 2; otherwise "no material text
  difference". Better texture is never read as better text. TF is never made a default.

### 8.2 Identity-edit probe (ID)
- **One run:** R15 at 512 through the production CLI (`run_edit.sh` mode `app`, so `gpu.lock` and the job system apply),
  instruction `Preserve this image exactly. Do not change anything.`, seed 2510715 (G2's R15 seed), 40 steps, the
  production defaults. A no-change instruction is not a DiT bypass; this is an empirical drift probe (n = 1).
- **Why R15-512:** G2's R15-512 edit garbled the large shop sign (Q-Q frozen call) although the Phase 7 round trip
  kept it, so the probe asks whether the DiT garbles it without any nearby edit.
- **Metrics:** PSNR/SSIM against D0 and A1, globally and in the fixed text boxes; text calls as a panel on the R15-512
  sheet; wall time, peak footprint, swap. Determinism is not re-tested (edit determinism was established in Phases 4–6).
- **Reading:** an element legible in A1 (the output-path ceiling) but not in ID, within this rater, is "additional loss
  beyond the output path under a no-change instruction". Cross-rater comparison with the frozen G2 edit (Q-Q's calls)
  is descriptive only.
- **1024:** one R15-1024 identity run only if the 512 run loses no element that A1 keeps (so 512 cannot discriminate)
  **and** a memory preflight leaves ≥ 4 GB headroom. Otherwise not run.

### 8.3 Compositing baseline (CMP; no GPU)
- **Case:** R02 at 1024, the existing G2 output (`G2-1024-R02`, pixel sha256 `13d1e1bb…`); no new edit.
- **Canvas:** D0 for R02-1024 (the exact image the edit was conditioned on, 1184×896). Not the full-resolution source.
- **Mask:** G2's own `regions.change` box for R02, `[0.19, 0.70, 0.63, 1.00]` (task manifest, written before any G2
  output existed), converted to pixels with `round()`. Both R02 text elements lie outside it.
- **Alignment first:** integer phase-correlation shift between the G2 output and D0 on the rows above the box. If the
  shift is not (0, 0), the composite is **not** made and the misalignment is reported.
- **Composites:** hard: `(1 − M)·D0 + M·edit`; feathered: the same with a 16-px linear ramp on the box edges that are
  not on the image border.
- **Rated** on a separate sheet: G2 output, hard and feathered composites in random order, with ORIGINAL and the
  instruction. Rubric: edit adherence PASS/PARTIAL/FAIL; seam NONE/MINOR/MAJOR; realism PASS/MINOR/MAJOR; unintended
  change outside the edit region NONE/MINOR/MAJOR; the two text elements.
- **Reading:** "viable pipeline baseline" only if a composite has adherence PASS, seam ≤ MINOR, realism ≤ MINOR and
  keeps legible every element D0 keeps. Identical pixels outside the mask are never counted as success by themselves.

## 9. Resource feasibility and stop conditions (fixed now)
- **Staging:** synthetic smoke (both sides, before this protocol's tool commit) → R12-512 → R12-1024 → the rest. Each
  stage records wall time, peak footprint (libproc lifetime maximum) and swap.
- **Watchdog for every CPU run (`run_ref.sh`):** kill and stop if swap grows > **2048 MB** over the run's start, or the
  memory-pressure level is critical for **10** consecutive samples, or the reference process's footprint exceeds
  **11 GB**. Swap at the start of Phase 8 was 1.49 GB. The monitor's real cadence is recorded (Phase 7: ≈ 2.5 s, not 1 s).
- **Never in parallel:** no A1 (GPU) and A2 (CPU) process at the same time; one chain at a time; no photo-gen job during
  the chain (the harness bypasses `gpu.lock`, except the ID arm, which uses the app).
- If R12-1024 cannot run safely, 1024 is reported unresolved and 512 is still classified (§7 rule 1).

## 10. Blind review (fresh-subagent rater; `qvr_blind.py`)
- **Item sheets (6):** ORIGINAL (staged source, long side ≤ 2048) plus panels **D0, A1, A2** (and **TF** if run; **ID**
  on R15-512 if run), each a separate file at native size, labelled A, B, C … in an order from `random.Random(seed)`;
  the key is sealed read-only before any panel is written. Per panel: the five Phase 7 text categories per element
  (`qq_blind.ELEMENTS` verbatim) and fidelity PASS/MINOR/MAJOR with a family. No preference question.
- **Composite sheet (1):** §8.3.
- The prompt is committed before the rater is spawned; the rater reads only `review/blind/`; it may crop at native
  resolution into a scratch directory, never enlarging with smoothing. `check` → `freeze` → commit → `unblind` → tally.
  The session assistant views no Phase 8 output before the freeze. Audit with `research/qwen/qq/rater_audit.py`.
- **Disclosed in advance:** the hypothesis may leak through `CLAUDE.md`; panel sizes reveal the budget; if A1 and A2 are
  pixel-equivalent, the rater can see that two panels match (provenance between them stays hidden); Phase 7's rater
  scored D0 and A1 before, so D0/A1 calls here are a **second rater on the same pixels**, reported as inter-rater
  agreement only, and never used to revise Q-V.

## 11. Glyph-height strata (exploratory; measured on the sources before any Phase 8 output)
`glyph-heights.json`: approximate cap or x-height of each element's main line and smallest material line, measured in
source pixels on the full-resolution staged photographs (±20 %), scaled by the output long side / source long side.
Bins: < 10 px, 10–20 px, > 20 px (main line). Descriptive only; not information-theoretic thresholds.

## 12. Not done in Phase 8
No training, fine-tuning, LoRA, distillation, pruning, VAE fine-tuning or architecture work; no MLX patch; no
production change; no q8 export; no change to either pinned venv; the dense source checkpoint is kept. OCR/CER is not
computed: no OCR engine is installed in any project environment, installing one is out of scope, and at 2–6 px glyphs
an OCR failure would mostly measure the OCR engine. Workstream B (Q-A) is desk research only:
`research/editing/QA-ALTERNATIVE-MODELS.md`.

## 13. Outputs
`research/qwen/qv-reference/`: this protocol, the tools, `requirements.lock.txt`, `weight-identity.json`, probe records,
`runs/<arm>-<budget>-<task>/` (JSON records; `.npy` and PNG gitignored with sha256 in the records), `qvr-chain.sh`
and its log, `qvr-summary.json`, `review/`, the report `research/qwen/QWEN-QVR-REFERENCE.md`.

## Amendments
**Amendment 1 (2026-10-09, before any G2 photograph, any weight-identity check or any probe ran; synthetic smoke only).**
*What:* the CPU reference executes large convolutions in bands of output rows (`ref_side.install_banded_conv`, im2col
budget 256 MB per call). *Why:* the synthetic 512 smoke (`synthetic:640x480`, never a G2 item) reached a peak footprint
of 11.2 GB with +1.9 GB swap, just under the §9 limit, because torch 2.14.0 here has no oneDNN and runs batch-1 CPU
convolutions as im2col + GEMM with a full (C_in·k·k) × (H_out·W_out) buffer (≈ 5.4 GB for the decoder's 576-channel
3×3 conv on one 512-px tile). *Validity:* each band is `F.conv2d` on exactly the input rows its outputs need, after the
layer's own zero padding, so every output element is the same dot product with the same weights; a new gate
(`ref_side.py conv-gate`, run in the chain as `GATE-conv`) requires the banded and unbanded results to agree, and a
synthetic pre-check already gave **bit-identical** outputs for six VAE-shaped convolutions and for a full 256-px encode
and decode with the real weights (62 banded calls), and byte-identical `dec`/`dec_x12` arrays for the 512 smoke run with
and without banding. *Cost:* the smoke's peak fell to 6.9 GB with no swap growth and its wall time from 23 s to 13 s.
Diffusers' code, weights and arithmetic are unchanged; only the im2col buffer is smaller. Added to §5.1 as gate 8
("banded convolution bit-identical to unbanded"); a non-bit-identical result with max |Δ| ≤ 1e-5 would be recorded
and accepted, larger fails the gate.
