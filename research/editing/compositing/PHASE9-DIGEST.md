# Phase 9 digest: CMPF (compact copy of the Phase 9 docs)

This is a condensed, copy-pasteable digest of `PHASE9-INDEX.md`, `RESULTS.md`, `PROTOCOL.md`, `CASE-SELECTION.md`,
`HOLDOUT-PROTOCOL.md` and `results.json`. It was written at the user's request ("cat and compact…") on 2026-10-09.
**The source documents are authoritative**; if they disagree with this file, they win.

Labels: [REG] pre-registered · [DESC] descriptive · [CONSTR] guaranteed by construction · [EXPL] exploratory idea.
Times: Asia/Manila (UTC+8).

## 0. Status
- **Result [REG]:** SUPPORTED FOR FURTHER DEVELOPMENT. The primary arm C2 was viable on 3 of 4 counted cases. Fragile:
  counting all six cases it is 4/6, which is MIXED.
- **Unchanged:** G2 REJECTED · Q-Q AGAINST · Q-V MIXED · Q-VR RUNTIME-MATCHED. Qwen stays research-only and
  non-commercial.
- **Git:**
  - Phase 8: 24 commits `3452c7d..d2357f9`, pushed as a fast-forward `817a7c2..d2357f9`.
  - Phase 9: 19 commits `2ba6dd9..cab2910`, plus the handoff commit that adds this file. **Local, not pushed.**
  - Tags v3 → `401e400` and v4 → `33669eb` unchanged; no v5.
- **Checks:** tests 93 OK; `verify` and `verify --edit` ok; tree clean; nothing running.
- **Frozen sheets:** G2 f14deba4 · Q-Q bcef9aa3 · Q-V 00c1b5e3 · Q-VR 9bb5918e · CMP2 1f60d2a4 · CMPF b80dfc52.
- **Commits:**
  - pre-registration c6eff32;
  - annotation workspace f52a15e and c82f107;
  - tools and D0 gates cd58c6f;
  - masks frozen 04a1b23;
  - runs 9aa98f8;
  - review prepared 5b53ac9, frozen f87aba8, unblinded bf721d0;
  - RESULTS 7d92e15, corrected 03ed914;
  - close docs a9f9f4e; asset record 774b7af; MEMORY cab2910.

## 1. Question, scope, hypotheses (PROTOCOL §1, §13)
- **Question:** given an existing generative edit, can a fixed compositing rule `I = (1−α)·canvas + α·edit` keep
  unrelated content (above all incidental text) and the requested edit, without bad seam or geometry artifacts?
- **Scope:** an engineering falsification on the G2 **development** set. It is not production validation, not a gate
  and not a holdout result. No model inference, GPU work or download, and no change to `app/`, `config/` or either venv.
- **Hypotheses** (competing; the study could reject the method):
  - H1: compositing removes text corruption and unintended changes outside the mask.
  - H2: it fails when the edit's footprint (shadows, reflections, occlusion, revealed background, moved parts) extends
    beyond the mask.
  - H3: a hard paste shows seams; feathering reduces seams but risks ghosting or leftovers of the target.
  - H4: compositing at source resolution keeps more detail, but may show a resolution mismatch at the boundary.
  - H5: the Phase 8 R02 pilot does not generalise.

## 2. Cases (CASE-SELECTION.md; mechanical within categories, 1024 budget, primary seed)
**Rule:**
1. Exclude by category.
2. Take the coverage categories the directive requires.
3. Within a category, take the lowest-numbered task.

The selector (the session assistant) had read G2's frozen outcomes. They were used only to name the
"collateral change" category.

| task | frozen G2 1024 A/P/C/Q/T | decision |
|---|---|---|
| R01 colour (portrait clothing) | PASS/PASS/PASS/PASS/– | **SELECTED: simple control** (eligible: R01, R03, R04, R07, R10) |
| R02 removal (van) | PASS/FAIL/PASS/PASS/FAIL | **demonstration, not counted** (Phase 8 pilot) |
| R03 material, R04 replacement, R07 vehicle colour, R10 fine texture | – | not selected: control slot filled by R01 |
| R05 addition (interior) | **PARTIAL**/PASS/PASS/PASS/– | **SELECTED: addition, uncertain placement**; kept despite PARTIAL |
| R06 season, R14 style | – | excluded: global edits |
| R08 sign text replacement | – | excluded: the target is the text itself |
| R09 replacement, busy scene | PASS/**FAIL**/PASS/PASS/– | **SELECTED: collateral change to similar objects** |
| R11 wine colour (transparent) | PASS/PARTIAL/PASS/PASS/– | **SELECTED: transparent/refractive** |
| R12 person removal, night, text | PASS/**FAIL**/PASS/PASS/**FAIL** | **SELECTED: removal with incidental text** (required) |
| R13 sky | – | excluded: background edit |
| R15 facade paint, text | PASS/**FAIL**/PASS/PASS/**FAIL** | **SELECTED: complex non-convex mask with text** |
| R16 addition (simple scene) | – | not selected: addition slot filled by R05 |

## 3. Masks (PROTOCOL §3; frozen at 04a1b23, before any composite existed)
- **Annotator:** a fresh subagent that read only `annotation/`.
  - It saw: source-only views (long side ≤ 2048, with a coordinate grid); the verbatim instruction, `must_change`,
    `must_not_change` and `regions.what`; the rule; and an overlay helper.
  - It never saw G2 outputs, composites, Phase 8 masks or results. G2's `regions.change` box was **deliberately
    withheld**, because it anchored Phase 8's coverage failure.
  - Its audit is clean. It was interrupted by a usage limit and resumed in the same isolated context.
- **Rule:**
  - Mark everything the edit may legitimately change: the object, attachments, contact shadows, reflections, and
    background a removal will reveal.
  - Exclude unrelated content and every text element the instruction does not target.
  - The feather lies **inside** the mask, so leave a margin around content that must be fully replaced.
  - No automatic dilation.
- **Representation:** polygons in normalised source coordinates [0,1], plus a rationale, the components included, and
  STRAIGHTFORWARD or AMBIGUOUS.
- **Freeze:**
  - rasterised with PIL `ImageDraw.polygon`, fill 255, at each canvas size;
  - `MASK-MANIFEST.json` holds the polygon, raster and source hashes and the audit;
  - `masks-frozen.json` is read-only;
  - no primary mask may change afterwards.

| case | edit | mask area (D0) | difficulty and note |
|---|---|---:|---|
| R01 | white top → dark green | 14.4 % | AMBIGUOUS: print/strap counted as garment; hair over the top included |
| R05 | add a sleeping grey cat | 5.9 % | AMBIGUOUS: placement unknown; cushions + backrest gap |
| R09 | dragon fruit → green apples | 1.6 % | AMBIGUOUS: one pile; pink netted fruit excluded; a narrow lobe partly in the feather |
| R11 | red wine → white wine | 11.7 % | AMBIGUOUS: the glossy foot's reflection excluded (must-not-change) |
| R12 | remove the man (night) | 5.6 % | STRAIGHTFORWARD; touches no text box |
| R15 | paint the wall white | 37.8 % | STRAIGHTFORWARD; touches text boxes t1/t2 (generous rectangles) |
| R02 (demo) | remove the van | 13.4 % | AMBIGUOUS: bicycles in front included; ~18 px margin over the roof load |

## 4. Arms and arithmetic (PROTOCOL §4; the same mask in every arm)
- **Arms:**
  - **C0:** the G2 output as is (RGB, alpha dropped).
  - **C1:** hard paste onto D0.
  - **C2 (primary):** feathered paste onto D0.
  - **C3:** feathered paste onto the staged source at full resolution.
- **D0:** Phase 7's `qv_roundtrip.preprocess` (EXIF orientation, RGBA, LANCZOS to `dimensions(1024, w/h)`), converted
  to RGB.
- **Feather:** `alpha = Σ_{k=0}^{F−1} erode^k(M) / F`.
  - This is an inner linear ramp in chessboard distance.
  - `erode` is a 3×3 MinFilter with edge-replicated borders, so mask edges on the frame are not feathered.
  - `F = round(16·L/1184)`, where L is the canvas long side.
- **C3 projection:** the G2 output is LANCZOS-resized to the source size. This is the exact inverse of D0, which is a
  full-frame resize with no crop. The mask is rasterised at source size from the same polygons. No warping.
- **Arithmetic:** float32, round half-to-even, clip to uint8, RGB PNG.

## 5. Gates and checks (PROTOCOL §5–§6), all passed
1. The staged source pixel sha256 equals the G2 sidecar's, 7/7.
2. The G2 output sha256 equals its sidecar, before and after the runs (read-only).
3. The recomputed D0 is **bit-identical to Phase 7** for R02, R12 and R15; every D0 size equals the G2 output size.
4. **Invariants [CONSTR]:**
   - C1 equals D0 outside the mask and C0 inside it;
   - C2 equals D0 outside the mask;
   - C3 equals the source outside the mask.
5. **Determinism:** two fresh-process runs per case gave identical hashes, 7/7.

**Alignment:** an integer-shift search over [−4, 4]² minimises the grey MAE between C0 and D0 outside the mask
dilated by F. Any best shift other than (0, 0) is an alignment failure.

## 6. Blind review (PROTOCOL §7)
- **Sheets:** 7, one per case. Each shows ORIGINAL (long side ≤ 2048), ORIGINAL-FULL, the instruction, the text
  elements, and 5 panels in random order: C0, C1, C2, C3 and D0. D0 is the canvas reference and a no-edit attention
  check.
- **Scores per panel:**
  - adherence PASS / PARTIAL / FAIL;
  - seam, realism, unintended and geometry, each NONE-or-PASS / MINOR / MAJOR;
  - `primary_defect`: none, leftover-of-target, truncated-edit, orphan-shadow-or-reflection, seam-or-tone-step,
    ghosting, resolution-mismatch, collateral-change, text-damage or `other:`;
  - t1..t5: PRESERVED / DEGRADED / GARBLED / REMOVED / NA;
  - notes.
- **Mechanics:**
  - append-only drafts with a revision column;
  - the key is sealed before rendering, and the prompt committed before the rater was spawned;
  - check → freeze (`b80dfc52`) → commit → unblind;
  - the rater's audit is clean;
  - the assistant viewed no panel before the freeze.
- **Disclosed leaks:**
  - C3's panel size identifies it;
  - the hypothesis may leak through `CLAUDE.md`;
  - the selector knew G2's outcomes.

## 7. Decision rules (PROTOCOL §8–§9, fixed before the runs)
**VIABLE** requires all of:
- adherence PASS;
- unintended NONE or MINOR;
- every text element legible in the arm's canvas stays legible (the canvas is D0 for C1/C2 and ORIGINAL for C3);
- seam NONE or MINOR;
- realism PASS or MINOR;
- geometry not MAJOR.

C0 is judged by the same rule as the baseline.

**EDITOR FAILURE:** C0 adherence ≠ PASS. The case is excluded from the denominator, and the all-cases count is
reported alongside.

**Failure class** of a non-viable composite, in this order:
1. alignment;
2. mask: a leftover, truncated or orphan defect, or adherence below PASS while C0's is PASS;
3. compositing: seam/tone, ghosting or resolution-mismatch defect, or seam MAJOR;
4. other.

**Classification**, on C2 only: n = evaluable, non-editor-failure primary cases; V = the viable ones among them.
- **INCONCLUSIVE:** n < 4, or more than one case unevaluable.
- **SUPPORTED:** V ≥ ⌈0.75 n⌉.
- **NOT SUPPORTED:** V < n/2.
- **MIXED:** otherwise.

The threshold is an engineering bar, not a statistic.

## 8. Results per case and arm (blind rater, latest revision; V = viable)
| case | C0 G2 edit | C1 hard | C2 feathered (primary) | C3 full resolution |
|---|---|---|---|---|
| R01 | V (unintended MINOR) | V (seam MINOR) | ✗ compositing: seam MAJOR, white halo at neckline/hair | ✗ compositing: same halo |
| R05 | V (unintended MINOR) | V | V | V (resolution mismatch MINOR) |
| R09 *(editor failure)* | ✗ A PARTIAL (rev 2), unintended MAJOR: apples spread to mango, netted and red piles | V (seam/realism MINOR) | ✗ compositing: A PARTIAL, ghosted dragon fruit at the edge | ✗ same ghosting |
| R11 | ✗ unintended MAJOR: red stem turned clear | ✗ alignment: seam MAJOR, geometry MINOR | V (seam MINOR) | V (seam MINOR) |
| R12 | ✗ unintended MAJOR; text 1 GARBLED, 3 DEGRADED | V, text 5/5 PRESERVED | V, text 5/5 | V, text 5/5 (resolution mismatch MINOR) |
| R15 *(editor failure)* | ✗ A PARTIAL (rev 2), unintended MAJOR; text 3 GARBLED, 1 DEGRADED | V, text 5/5 | V, text 5/5 (seam MINOR: pinkish strip at the pillar) | V, text 5/5 |
| R02 (demo) | ✗ both signs GARBLED | V (geometry MINOR) | V (ghosting MINOR: faint roof-rack pipe) | V |

- **Attention check:** D0 adherence FAIL on 7/7 sheets.
- **Text [DESC]:** composites 12/12 PRESERVED (R12 5/5, R15 5/5, R02 2/2). The edits garbled or degraded them: R12
  1G + 3D, R15 3G + 1D, R02 2G.
  - Outside the mask this is [CONSTR]. The rater's calls add evidence only where a box touches the mask (R15 t1/t2,
    both PRESERVED).
  - C1 and C2 keep the scaled input's text; C3 keeps the original's.
- **Unintended [DESC]:** composites NONE on 17/18 scorings (MINOR on R15 C1); corrected from "15/18" in 03ed914. Edits
  MAJOR on 4/6 (R09, R11, R12, R15).

## 9. Classification and sensitivity
- **[REG] C2 = SUPPORTED, n = 4, V = 3.** Editor failures excluded: R15, R09. Unevaluable: 0.
- **Why it is fragile:**
  - n = 4 is the floor, and V = 3 equals ⌈0.75·4⌉ exactly. One case flipping gives MIXED; one more exclusion gives
    INCONCLUSIVE.
  - n depends on two blind revisions. In revision 2 the rater moved R15 C0 and R09 C0 adherence from PASS to PARTIAL,
    folding the instructions' "keep all lettering exactly" and "do not change anything else" clauses into adherence.
  - With revision 1, or counting all six cases, C2 is **4/6 MIXED**. Counting the two exclusions as failed, it is
    **3/6 MIXED**.
- **Design defect (post-unblind note; class unchanged):** the editor-failure rule should key on the *requested change*
  only. Preservation clauses belong under unintended/text. As written, the rule excluded exactly the cases compositing
  exists to fix. The fix is for the next protocol, not applied retroactively.
- **Per arm, n = 4 [DESC]:** C0 2/4 MIXED · C1 3/4 · C2 3/4 · C3 3/4 (only C2 is registered; `results.json`
  `per_arm`).
- **All six cases, each arm on its own scores [DESC]:** C0 2/6 · C1 5/6 · C2 4/6 · C3 4/6. C1's 5/6 is secondary;
  promoting it after the fact would be a forking-paths error.

## 10. Mechanical metrics (results.json; C0 vs D0, outside the mask unless noted)
| case | D0 / source (w×h) | F d0/src | best shift (dy,dx) | MAE | px changed >8 | ring MAE | SSIM | time s | peak GB |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| R01 | 1216×864 / 3413×2411 | 16/46 | (0,0) | 5.33 | 29.5 % | 6.31 | 0.858 | 6.5 | 0.81 |
| R05 | 1248×832 / 3897×2588 | 17/53 | (0,0) | 4.67 | 22.2 % | 9.70 | 0.900 | 8.6 | 0.86 |
| R09 | 1248×832 / 5760×3840 | 17/78 | (0,0) | 15.56 | 71.8 % | 23.62 | 0.741 | 24.1 | 1.86 |
| R11 | 768×1376 / 2250×4000 | 19/54 | **(4,−1) ✗** (MAE 14.77 → 11.77) | 14.74 | 60.4 % | 18.16 | 0.546 | 8.0 | 0.84 |
| R12 | 896×1184 / 3024×4032 | 16/54 | (0,0) | 6.12 | 55.2 % | 9.43 | 0.849 | 10.3 | 1.03 |
| R15 | 896×1184 / 3024×4032 | 16/54 | (0,0) | 10.82 | 47.9 % | 49.68 | 0.777 | 10.4 | 1.11 |
| R02 | 1184×896 / 4592×3448 | 16/62 | (0,0) | 8.84 | 56.1 % | 6.70 | 0.787 | 14.6 | 1.37 |

- The R11 shift is at the ±4 edge, so the true displacement is ≥ 4 px and unknown.
- No GPU, no model load, no download, no swap growth.

**Identities** (sha256 prefixes: source / G2 output / D0 / polygons / D0 mask):
- R01: e91528e8 / 1fbd012e / c1721308 / c98d1178 / 969a64ec
- R05: f7f23ad5 / 04650dff / 14bf91b1 / 31d2bcf7 / c742b809
- R09: 6798a5d5 / a46af4ce / 29fc59b8 / ffbc3372 / 1e4c40a4
- R11: c3b816de / 502c4f55 / 79108c9f / e08e59d2 / 509df0e5
- R12: 6766f960 / 85c0235a / ed934500 / f9a19a68 / 19fe511c
- R15: d3c22ffa / bd8e3f1b / 4d991dc4 / e724c65b / fbf0feb9
- R02: 73670d26 / 13d1e1bb / f940ba52 / f37023a8 / d350bf06

## 11. Findings (answers to the directive's §22)
- **Masks:** source-only masks had adequate coverage on 6/7 cases, including R02's roof load, which Phase 8's G2 box
  missed. The only margin problem was R09's narrow lobe, flagged in advance. No failure was classed "mask".
- **Boundary:** the inner ramp blends the *original target* back in at the mask edge. On tight masks around
  high-contrast targets this produced R01's white halo and R09's ghosted dragon fruit.
- **Feathering cut both ways:** it hid R11's shift (C2 viable where C1 failed) and caused R01 and R09 (C1 viable where
  C2 failed). The fault is the inner-ramp rule, not feathering in general.
- **Geometry:** compositing assumes no global motion. R11's ≥ 4 px frame shift breaks a hard paste.
- **Source resolution:** C3 matched C2 on every case. It keeps original detail and text, at the cost of a MINOR blur
  mismatch inside the mask (R12, R05).
- **Edit types:**
  - unsuitable: scene shifts (R11); high-contrast recolour or replace with a tight inner-ramp mask (R01, R09);
  - worked: removals (R12, R02), addition (R05), region repaint (R15).
  - R12 and R15 behave like R02 on these cases; no generalisation is claimed.
- **Left for a specialist:** automatic masks; a per-type boundary rule; global-motion detection; placement prediction
  for additions.
- **Wasted work:** the editor re-synthesised 22–72 % of out-of-mask pixels, and compositing discards all of it.
- **Compute:** compositing is postprocessing only (6–24 s on CPU, ≤ 1.9 GB) and saves no generation compute. Real
  savings need localised generation, token reuse or cropping.

## 12. Limitations and disclosures
- Development set, one rater, n ≤ 6 (n = 4 after exclusions). The selector knew G2's outcomes.
- Annotator: one usage-limit interruption; audit clean. `CLAUDE.md` may describe G2's leakage mode to subagents.
- Rater: 5 blind self-revisions, kept in `SCORES-DRAFT-HISTORY.csv`:
  - R01 C3 (unintended);
  - R15 C3, R15 C2 (unintended);
  - **R15 C0 and R09 C0 (adherence PASS → PARTIAL; these two decide n).**
- The rater used `other:unedited` for the D0 panels.
- The alignment search covers only ±4 px. Text boxes are generous rectangles: "touches the mask" does not mean the
  lettering is inside it.

## 13. Recommendation [EXPL]
- **Next experiment:** automatic edit-region localisation, benchmarked against the 7 frozen masks.
  1. Compare coverage, overlap and text exclusion with the frozen masks.
  2. Re-composite the existing outputs under the frozen rules.
  - No new inference is needed for this first step.
- **Boundary fix:** an outer ramp or dilated feather is a known candidate for R01/R09. It is untested and needs its
  own pre-registered run on fresh cases or the holdout.
- **Protocol fix:** key editor failure on the requested change only.
- **Not now:**
  - FLUX.2 [klein] 4B stays in the backlog (VAE screen → M5 feasibility → quality gate). It answers "a better editor",
    and compositing is editor-independent.
  - Training is premature.
- **No tag** until a holdout pass.

## 14. Holdout specification (HOLDOUT-PROTOCOL.md; not collected or run)
- **Purpose:** a one-shot confirmation of a method frozen on the development set. Never used for tuning.
- **Sources:**
  - 16–24 new real photos, CC0/PD, each with URL, licence, author, sha256 and EXIF summary;
  - none reused from G0, G2 or any report.
- **Coverage, ≥ 3 images each:**
  - incidental text, including 5–20 px glyphs at the 1024 budget;
  - similar neighbouring objects;
  - occlusion and thin structures;
  - shadows and reflections on wet or glossy surfaces;
  - complex boundaries;
  - portrait and landscape, about 2–24 MP;
  - daylight, night and indoor.
- **Tasks and masks:** written from the source only, by someone who has seen no output. Masks are drawn under the
  frozen rule, then hashed and committed before any edit.
- **One-shot rule:**
  1. Freeze the code, parameters, mask rule, rubric and pass bar before acquisition.
  2. Commit the images, tasks and masks before any edit.
  3. Run once, at a pre-registered budget and seed.
  - Any change after seeing an output turns the set into a development set and requires a new holdout.
- **Review:**
  - a provenance-blind fresh rater with the Phase 9 rubric;
  - append-only drafts, freeze, audit;
  - suggested bar: ≥ 80 % viable and no recurring MAJOR failure class.
- **Cost:** ≈ 10 min per edit for Qwen-2.1 at 1024, so the run needs separate authorisation.

## 15. Other Phase 9 work
- **Phase 8 git reconciled:** the reported 23 commits ending at 357c908, plus the order-only fix d2357f9. Nothing came
  after; pushed as a fast-forward.
- **`docs/HARDWARE.md`:** macOS 27.0.1 (26A434) is current; 27.0 (26A428) is the historical baseline. The
  machine-profile JSON stays the dated 2026-09-25 read-out.
- **Texture-Fix VAE deleted** 2026-10-09 05:56:36 (+1.33 GB), after the identity, hash, no-open-handle and
  not-a-protected-VAE checks. Recorded in `QWEN-ASSET-PROVENANCE.md` §9.
  - Kept: the dense checkpoint and the q4 export (hash-verified unchanged) and `torch-ref/` (737 MB).
  - The q8 export was not recreated.
- **Asset records:** `qwen-assets-verification-phase9-pre.json` and `-post.json` are identical.
- **Updated:** STATUS, EXPERIMENT-BACKLOG (CMPF done, LOC recommended, FLUX.2 sequence, HOLDOUT), PERFORMANCE-MAP,
  RELEASE-NOTES "Unreleased", CLAUDE.md, MEMORY.md (resume order PHASE9 → 8 → 7…), `review-crops/MANIFEST.sha256`.
- **Handoff:** session-scratch evidence was preserved in the repo (`research/qwen/qv-reference/scratch-preserved/`,
  `research/editing/qa-configs/`, `research/qwen/assets/df-*-texturefix-delete.txt`).

## 16. Discrepancy surfaced, not edited
- The `docs/RELEASE-NOTES.md` header says tags are validated on "macOS 27.0". The machine has been on 27.0.1 since
  2026-09-29 22:50.
  - v1 (2026-09-25) and v2 (2026-09-28) were tagged on 27.0.
  - **v3 (2026-10-07) and v4 (2026-10-08) were tagged on 27.0.1.**
  - An earlier chat summary named only v4.
- This needs your decision. One option is a dated note per tag; the tags themselves never move.

## 17. Open decisions
The "how to start" procedures are in `PHASE9-INDEX.md` §4.
1. Run the localisation experiment (recommended).
2. Push Phase 9 (not authorised yet).
3. Pre-register the boundary-rule fix.
4. The FLUX.2 [klein] 4B gate sequence.
5. Collect the holdout (needs editor runs).
6. Tag: none recommended before a holdout pass.
7. The RELEASE-NOTES macOS wording (§16).

## 18. Where things are (`research/editing/compositing/`)
- **Pre-registration:** PROTOCOL.md (with the post-unblind note), CASE-SELECTION.md, HOLDOUT-PROTOCOL.md.
- **Annotation:** `annotation/` (instructions, prompt, cases.json, overlay.py, masks-draft.json, views.sha256,
  `audit/`).
- **Masks:** `masks/masks-frozen.json` (read-only), MASK-MANIFEST.json.
- **Tools:** make_d0.py (edit venv, PIL only), cmp_run.py, freeze_masks.py, cmp_blind.py, analyze_cmpf.py;
  config.json, sheets.json.
- **Runs:** `runs/D0/`, `runs/<case>-{a,b}/record.json` (PNGs gitignored, hashes in the records).
- **Review:** `review/` (SCORES-FROZEN.csv b80dfc52, SCORES-DRAFT-HISTORY.csv, key-unblinded.json, RATER-PROMPT.md,
  RATER-AUDIT.json, `rater-crops/`).
- **Results:** results.json, RESULTS.md. Resume index: PHASE9-INDEX.md.
