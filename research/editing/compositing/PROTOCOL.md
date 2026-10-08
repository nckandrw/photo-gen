# Phase 9 compositing falsification (CMPF): pre-registration

**Status.** This file, `CASE-SELECTION.md` and `HOLDOUT-PROTOCOL.md` are committed **before any Phase 9 mask, D0
canvas or composite exists, and before the mask annotator is spawned.** The rules below are fixed now; deviations
become dated amendments at the end, and a method added after results is labelled exploratory and never counted.
Local times: Asia/Manila (UTC+8).

**Scope.** This is an engineering falsification on the G2 **development** set. It is not production validation, not a
quality gate, and not a holdout result (§13). It cannot change G2 (REJECTED), Q-Q (AGAINST), Q-V (MIXED) or Q-VR
(RUNTIME-MATCHED), or Qwen's status (research-only, `validated: false`, non-commercial licence). There is no new model
inference, no download, no GPU workload, and no change to `app/`, `config/` or either venv.

## 1. Question and hypotheses
**Question.** Given an existing generative edit, can a fixed, pre-declared compositing method,
`I_final = (1 − M) ⊙ I_canvas + M ⊙ I_edit`, produce an image that keeps unrelated content (above all incidental text)
while keeping the requested edit, without unacceptable boundary or geometry artifacts?

**Hypotheses, registered as competing; the study can reject the method:**
- **H1, preservation benefit:** compositing removes incidental-text corruption and unintended changes outside the mask.
- **H2, adherence/geometry trade-off:** it fails when the edit's spatial footprint (shadows, reflections, occlusion,
  attachments, revealed background, moved parts) extends beyond the mask.
- **H3, boundary artifacts:** hard compositing shows seams. Feathering reduces seams but may cause ghosting,
  colour contamination or retained fragments of a removed object.
- **H4, canvas resolution:** source-resolution compositing keeps more original detail outside the mask, but may show a
  resolution mismatch at the boundary.
- **H5, no generalisation:** the Phase 8 R02 pilot result does not transfer to other scenes and edit categories.

## 2. Cases (`CASE-SELECTION.md`; mechanical within categories)
- **Primary:** six G2 tasks at the **1024** budget, using the **primary-seed** outputs `research/qwen/runs/G2-1024-<task>/`:
  - **R12:** removal with incidental text;
  - **R15:** text-preserving facade edit with a complex mask;
  - **R09:** replacement among similar objects;
  - **R05:** addition with uncertain placement;
  - **R11:** transparent object;
  - **R01:** simple localized control.
- **R02** is a **non-counted demonstration**. Its Phase 8 masks are not used; R02 gets a fresh mask from the same
  isolated annotator under the same rules, and it never enters the classification.

## 3. Masks (isolated annotator; frozen before any composite)
**Annotator.** A fresh subagent that reads **only** `research/editing/compositing/annotation/`, which contains:
- per case, a source-only view image (the staged source at a long side ≤ 2048, with a normalised coordinate grid);
- the G2 task metadata copied **verbatim**: `instruction`, `must_change`, `must_not_change`, `regions.what`;
- the compositing rule;
- a source-only overlay helper, to check its own polygons.

It never sees a G2 output, a composite, a Phase 8 mask, a review result or this protocol's outcome sections.

**Withheld on purpose:** G2's `regions.change` box. It was drawn for metrics, and in Phase 8 it anchored the coverage
failure.

**Rule given to the annotator:**
- Mark every region the requested edit may legitimately change: the object, its attachments, contact shadows,
  reflections, and background that a removal will reveal.
- Leave out unrelated content and **every text element not targeted by the instruction**.
- Feathering happens **inside** the mask over a band of 16 px at the 1024 canvas (≈ 1.35 % of the long side; it
  scales with the canvas). The outer part of the mask therefore blends source with edit, so a margin is needed for
  content that must be fully replaced.
- No automatic dilation is applied. The margin is the annotator's choice, made once.

**Representation:**
- one or more polygons in **normalised source coordinates** (x right, y down, in [0, 1]), whose union is the editable
  region;
- per case, a rationale, the components included (shadow, reflection, attachment, revealed background), and
  STRAIGHTFORWARD / AMBIGUOUS.

**Freeze:**
- The polygons are rasterised deterministically (PIL `ImageDraw.polygon`, fill 255) at every canvas size.
- `MASK-MANIFEST.json` records the polygon JSON sha256, each rasterised mask's sha256, the source hashes and the
  annotator's audit.
- All of this is committed **before the compositing tool runs on any case.**
- **No primary mask is changed afterwards.** A corrected mask would be a separately labelled exploratory arm.

**Audit.** `research/qwen/qq/rater_audit.py` runs on the annotator's transcript. Any read outside its directory is a
discrepancy and is reported.

## 4. Arms (identical mask in every arm; the only variables are feathering and canvas)
| arm | output | canvas | mask |
|---|---|---|---|
| **C0** | the G2 output, unchanged (RGB; alpha dropped) | — | — |
| **C1** | hard composite | **D0**, the scaled conditioning input, at the G2 output size | binary |
| **C2 (primary)** | feathered composite | D0 | inner linear ramp |
| **C3** | feathered composite at **source resolution** | the staged source photograph | inner linear ramp, at source scale |

**D0.** Recomputed with Phase 7's own function (`research/qwen/qv/qv_roundtrip.py preprocess`: EXIF-oriented, RGBA,
LANCZOS to `dimensions(1024, w/h)`), converted to RGB.

**Feather.** `alpha = Σ_{k=0}^{F−1} erode^k(M) / F`:
- this is a linear ramp in chessboard distance inside the mask, 0 outside;
- `erode` is a 3 × 3 minimum filter, with image borders edge-replicated so mask edges on the frame are not feathered;
- `F = round(16 × L / 1184)`, where L is the canvas long side.

**C3 projection.** The G2 output is resized to the source size with PIL LANCZOS. D0 was a full-frame resize of the
source with no crop, so this is the exact inverse coordinate map, including the per-axis rounding to multiples of 32.
The mask is rasterised at the source size from the same polygons. No manual warping or alignment is applied.

**Composite arithmetic.** float32 `(1 − α)·canvas + α·edit`, rounded half-to-even (NumPy), clipped to uint8, RGB PNG.

## 5. Gates (all must hold; a failed gate makes that case unevaluable)
1. The staged source pixel sha256 equals the G2 sidecar's `input_image.pixel_sha256`.
2. The G2 output pixel sha256 equals its sidecar, checked **before and after** the runs. Files are opened read-only and
   never written.
3. **The D0 recomputation is bit-identical** to Phase 7's `input.png` for R02, R12 and R15, and its size equals the G2
   output size for every case.
4. **Construction invariants:**
   - C1 equals D0 outside the mask, and equals C0 inside it;
   - C2 equals D0 outside the mask;
   - C3 equals the source outside the mask.
   These are verified and reported as invariants, never as quality evidence.
5. **Determinism:** every case and arm is composited twice in fresh processes, with identical output hashes.

## 6. Alignment and geometry checks (mechanical; composites are made regardless)
- **Alignment:** an integer-shift search over [−4, 4]² minimising the grey-level MAE between C0 and D0 on pixels
  outside the mask dilated by F. **Alignment failure** if the best shift is not (0, 0). It is recorded as its own
  failure class, never "fixed".
- **Descriptive:**
  - C0-vs-D0 MAE and the fraction of pixels changed by more than 8 levels, outside the mask (global drift);
  - the mean |C0 − D0| in a boundary ring of width F just outside the mask;
  - mask area fraction, perimeter, feather-band area;
  - text-box intersection with the mask.

## 7. Blind review (fresh rater; `cmp_blind.py`)
**Per sheet (one per case, 7 sheets):**
- `ORIGINAL` (long side ≤ 2048) and `ORIGINAL-FULL` (the staged source at full resolution, for judging C3);
- the instruction;
- the case's TEXT ELEMENTS (`qq_blind.ELEMENTS`; only R02, R12 and R15 have them);
- five versions in random order: **C0, C1, C2, C3 and D0.** D0 is included as canvas-legibility reference and as a
  no-edit attention check: its adherence should be FAIL.

**Per version, scored against ORIGINAL:**
- `adherence` PASS / PARTIAL / FAIL;
- `seam` NONE / MINOR / MAJOR;
- `realism` PASS / MINOR / MAJOR;
- `unintended` NONE / MINOR / MAJOR (semantic and geometric changes outside what the instruction asks);
- `geometry` PASS / MINOR / MAJOR (does the edited region fit the unchanged scene: perspective, contact, scale);
- `primary_defect`: one of `none`, `leftover-of-target`, `truncated-edit`, `orphan-shadow-or-reflection`,
  `seam-or-tone-step`, `ghosting`, `resolution-mismatch`, `collateral-change`, `text-damage`, `other:<word>`;
- `t1..t5`: PRESERVED / DEGRADED / GARBLED / REMOVED / NA, or `-`;
- notes.

**Mechanics:**
- **Revision history:** the draft is append-only with a `revision` column. `check` and `freeze` use the latest revision
  per id and preserve the whole file.
- The rater gets its own scratch directory for crops and helpers.
- The key is sealed before any panel is rendered, and the prompt is committed before the rater is spawned.
- `check` → `freeze` → commit → `unblind`.
- Audit with `rater_audit.py`.
- **The session assistant views no C0, D0 or composite image until the scores are frozen.**

**Disclosed now:**
- C3's panel size identifies it.
- The hypothesis may leak through `CLAUDE.md`.
- The case selector, the session assistant, has read the frozen G2 outcomes and the Phase 7/8 text calls.

## 8. Per-case viability (fixed now)
**A version is VIABLE when all of these hold:**
1. adherence PASS;
2. unintended NONE or MINOR;
3. text: every element legible (PRESERVED or DEGRADED) in the arm's reference canvas stays legible. The canvas is D0
   for C1 and C2, and ORIGINAL for C3, and D0 legibility is taken from the D0 panel's call.
   - A text box that does not intersect the mask is equal to the canvas by construction (§5.4): reported as an
     invariant, and still checked against the rater's call.
4. seam NONE or MINOR;
5. realism PASS or MINOR;
6. geometry not MAJOR.

C0 is scored by the same rule, as the baseline.

**Editor failure:** if the rater scores **C0 adherence ≠ PASS**, compositing cannot rescue that case. It is reported as
EDITOR FAILURE and **excluded from the compositing denominator**. The all-cases count (editor failures counted
non-viable) is reported alongside.

**Failure class of a non-viable composite**, assigned mechanically in this order:
1. **alignment** (§6 mechanical flag);
2. **mask**: `primary_defect` ∈ {leftover-of-target, truncated-edit, orphan-shadow-or-reflection}, or adherence below
   PASS while C0's is PASS;
3. **compositing**: `primary_defect` ∈ {seam-or-tone-step, ghosting, resolution-mismatch}, or seam MAJOR;
4. **other**: anything else, with the rater's note quoted.

## 9. Study classification (primary arm C2 only; applied mechanically)
n = primary cases that are evaluable (gates pass, scored) and not EDITOR FAILURE. V = C2-viable cases among them.
1. **INCONCLUSIVE** if n < 4, or more than one primary case is unevaluable.
2. **SUPPORTED FOR FURTHER DEVELOPMENT** if V ≥ ⌈0.75 n⌉ (n = 6: ≥ 5; n = 5: ≥ 4; n = 4: ≥ 3).
3. **NOT SUPPORTED** if V < n / 2 (n = 6: ≤ 2; n = 5: ≤ 2; n = 4: ≤ 1).
4. **MIXED** otherwise.

The threshold is an exploratory engineering bar, not a statistical standard. With n ≤ 6 the proportions are not
estimates of general performance. Every MAJOR failure is reported individually, whatever the class.

**Secondary, descriptive only:**
- the same rule applied to C1 (the feathering effect is C2 vs C1) and to C3 (the canvas effect is C3 vs C2);
- C0's viability;
- per-case failure classes;
- R02 (demonstration).

## 10. Metrics (supporting; reported in separate categories, never combined into a score)
- **Guaranteed by construction:** outside-mask identity (§5.4).
- **Measured:**
  - PSNR/SSIM of each arm vs its canvas inside the mask;
  - boundary-ring error;
  - text-box PSNR/SSIM vs canvas;
  - modified-pixel area;
  - mask area, perimeter, feather band;
  - timings and peak footprint.
- **Blind human judgments:** §7–§8.
- **Interpretation:** a separate section of `RESULTS.md`.

## 11. Resources
- CPU-only image processing: NumPy, PIL in the Z-Image venv, and the edit venv only for the D0 recomputation (PIL
  operations, no model load).
- No GPU job, no model load, no download.
- Timings and peak footprint per run are recorded.

## 12. Outputs
`research/editing/compositing/`:
- `PROTOCOL.md`, `CASE-SELECTION.md`, `HOLDOUT-PROTOCOL.md`;
- `annotation/` (sources view, instructions, annotator draft);
- `MASK-MANIFEST.json` and `masks/` (polygon JSON committed; rasters gitignored, sha256 in the manifest);
- `config.json`;
- the tools;
- `runs/<case>/` (records committed; PNGs gitignored);
- `review/`;
- `results.json`, `RESULTS.md`.

## 13. Development set versus holdout
G2 has been examined in Phases 5–8, so it is a **development** set for this method. A positive Phase 9 result means
"support for continued development" only. `HOLDOUT-PROTOCOL.md` specifies a future untouched set; it is not
collected or run in Phase 9.

## Amendments
(none)
