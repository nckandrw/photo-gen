# Phase 9 compositing falsification (CMPF): results

**Registered result (PROTOCOL.md §9, primary arm C2, applied mechanically): SUPPORTED FOR FURTHER DEVELOPMENT (3 of
4).** It is fragile and promising, not established:
- **At the floor of both thresholds.** n = 4 is the minimum before INCONCLUSIVE, and V = 3 is exactly ⌈0.75 n⌉. One
  case flipping gives MIXED; one more exclusion gives INCONCLUSIVE.
- **Dependent on two blind self-revisions.** n = 4 because R15 and R09 were excluded as EDITOR FAILURE: the rater
  scored their G2 edits' adherence PARTIAL. It did so **in revision 2**, folding each instruction's preservation clause
  into adherence ("keep all lettering exactly"; "do not change anything else"). In its first pass it had scored both
  PASS.
- **Under the alternative readings, MIXED.** With revision 1, or counting all six cases, C2 is **4/6 (MIXED)**.
  Counting the two exclusions as failures, it is **3/6 (MIXED)**.
- **A protocol design flaw, recorded rather than fixed** (§9 below). The editor-failure rule should have keyed on the
  *requested change* only. As written, it excluded exactly the cases whose edit failure is the preservation failure
  compositing exists to fix. The registered class stands.

This is a development-set engineering result (G2 has been examined since Phase 5). It is not production validation,
and no generalisation beyond these cases is claimed. Status unchanged: G2 REJECTED, Q-Q AGAINST, Q-V MIXED, Q-VR
RUNTIME-MATCHED; Qwen research-only.

## 1. What was done (commits)
- **Pre-registration** `c6eff32`: protocol, case selection, holdout specification.
- **Annotation workspace and prompt:** `f52a15e`, `c82f107`.
- **Tools, config and D0 gates:** `cd58c6f`. D0 was recomputed with Phase 7's preprocessing; it is bit-identical to
  Phase 7 for R02/R12/R15, and every size equals the G2 output's.
- **Masks frozen** `04a1b23`, before any composite. An isolated source-only annotator drew them; its audit is clean.
- **Runs** `9aa98f8` / `cmp_run`: all gates and invariants pass, and 7/7 cases are deterministic.
- **Review:** prepared (`5b53ac9`), frozen `f87aba8` (`b80dfc52…`), unblinded and analysed `bf721d0`.

## 2. Cases and masks
Primary cases: R01, R05, R09, R11, R12 and R15 (G2, 1024, primary seed); R02 is a non-counted demonstration. The
inclusion rationale for all 16 tasks is in `CASE-SELECTION.md`.

| case | edit | mask area (D0) | annotator difficulty and note |
|---|---|---:|---|
| R01 | white top → dark green | 14.4 % | AMBIGUOUS: print/strap motif counted as garment; hair strands over the top included |
| R05 | add a sleeping grey cat | 5.9 % | AMBIGUOUS: placement unknown; seat cushions + backrest gap |
| R09 | dragon fruit → green apples | 1.6 % | AMBIGUOUS: one pile found; pink netted fruit excluded; a narrow lobe left in partial alpha |
| R11 | red wine → white wine | 11.7 % | AMBIGUOUS: the glossy foot's reflection of the wine excluded (must-not-change) |
| R12 | remove the man (night) | 5.6 % | STRAIGHTFORWARD; no text box touched |
| R15 | paint the wall white | 37.8 % | STRAIGHTFORWARD; its boxes touch t1/t2 (generous metric rectangles) |
| R02 (demo) | remove the van | 13.4 % | AMBIGUOUS: bicycles in front included; roof load covered with an ~18 px margin |

**Hashes and identities:**
- per case: `MASK-MANIFEST.json` (polygons, rasters at both canvases, sources);
- the G2 output and D0 hashes: `config.json`;
- outputs: `runs/<case>-{a,b}/record.json`.

## 3. Per case and arm (blind rater; latest revision; V = viable by PROTOCOL.md §8)
| case | C0 (G2 edit) | C1 (hard, D0 canvas) | C2 (feathered, D0) = primary | C3 (feathered, source resolution) |
|---|---|---|---|---|
| R01 | **V**: A PASS, unintended MINOR | **V**: seam MINOR | ✗ **compositing**: seam MAJOR (white halo along neckline/hair) | ✗ **compositing**: seam MAJOR (same halo) |
| R05 | **V**: unintended MINOR | **V** | **V** | **V**: resolution-mismatch MINOR |
| R09 *(excluded: editor failure)* | ✗: A PARTIAL (rev 2), unintended MAJOR (apples spread to mango, netted and red piles) | **V**: seam/realism MINOR | ✗ **compositing**: A PARTIAL, ghosting (semi-transparent dragon fruit at the edge) | ✗ **compositing**: same ghosting |
| R11 | ✗: unintended MAJOR (red stem turned clear) | ✗ **alignment**: seam MAJOR, geometry MINOR | **V**: seam MINOR | **V**: seam MINOR |
| R12 | ✗: unintended MAJOR, text: 1 GARBLED, 3 DEGRADED | **V**: text 5/5 PRESERVED | **V**: text 5/5 | **V**: text 5/5; resolution-mismatch MINOR |
| R15 *(excluded: editor failure)* | ✗: A PARTIAL (rev 2), unintended MAJOR, text: 3 GARBLED, 1 DEGRADED | **V**: text 5/5 | **V**: text 5/5; seam MINOR (pinkish strip at the pillar edge) | **V**: text 5/5 |
| R02 (demo) | ✗: both signs GARBLED | **V**: geometry MINOR | **V**: ghosting MINOR (faint roof-rack pipe) | **V** |

**Descriptive counts over all six primary cases** (not the registered statistic): C0 **2/6**, C1 **5/6**, C2 **4/6**,
C3 **4/6**. C1's 5/6 is a secondary observation; promoting the non-primary arm after the fact would be a forking path.

**Attention check:** the D0 (unedited) panel was scored adherence FAIL on 7/7 sheets.

## 4. Answers to the directive's questions (§22)
**1. Incidental text.**
- Every composite kept every text element: R12 5/5, R15 5/5 and R02 2/2, all PRESERVED.
- The G2 edits garbled or degraded them: R12 1 G + 3 D; R15 3 G + 1 D; R02 2 G.
- Outside the mask this is **guaranteed by construction** (pixel-identical canvas). The rater's calls add evidence only
  where a box touches the mask: R15 t1/t2, both PRESERVED.
- On C1/C2 the text is the *scaled input's*. C3 keeps the original's.

**2. Unrelated content.**
- Composites: unintended NONE on **17 of 18** counted composite scorings; MINOR on one (R15 C1). *(Corrected 2026-10-09: an earlier commit of this file said "15 of 18".)*
- G2 edits: MAJOR on 4 of 6 (R09, R11, R12, R15).
- Outside the masks the editor had changed 22–72 % of pixels by more than 8 levels; compositing reverts all of it by
  construction.

**3. Requested edit.**
- Composite adherence was PASS everywhere, except R09's feathered arms: PARTIAL, through ghosting of the target at the
  feather band.

**4. Mask errors.**
- The source-only masks had adequate coverage on 6 of 7 cases. That includes R02's roof load, which Phase 8's G2 box
  missed.
- The one margin problem was R09's narrow lobe, which the annotator flagged in advance.
- No composite failure was classed "mask".

**5. Geometry.**
- For R11, the integer-shift search indicates a displacement of **at least 4 px** (best shift (4, −1), on the edge of
  the ±4 window; true size unknown). C1's MAJOR seam corroborates it.
- The hard paste then showed a MAJOR seam. Compositing assumes no global motion; an editor that shifts the frame
  breaks it.

**6. Boundary artifacts.**
- The most serious was the **inner-ramp halo or ghosting on tight masks around high-contrast targets**: R01's white
  halo (white top → green) and R09's ghosted dragon fruit.
- The inner ramp blends the *original target* back in at the mask edge.

**7. Does feathering help?**
- Both ways. It hid R11's misalignment (C2 viable where C1 failed), and it caused R01's and R09's failures (C1 viable
  where C2 failed).
- The failures belong to the **inner-ramp rule** specifically, not to feathering in general.

**8. Source resolution.**
- C3 and C2 had identical viability on every case.
- C3 keeps original detail (and original text) outside the mask, and adds MINOR resolution mismatch at the edit (R12,
  R05).
- There is no viability difference in this study.

**9. Edit categories unsuitable for straightforward compositing:**
- edits that move or reframe the scene (R11);
- recolouring or replacing a high-contrast target with a tight inner-ramp mask (R01, R09).
- Removals (R12, R02), additions (R05) and region repaint (R15) worked.

**10. Beyond R02?** Yes, on these development cases: R12 and R15 behave like R02. This is not a generalisation claim.

**11. Left for a trainable localisation/preservation specialist:**
- producing these masks automatically: a human (or isolated agent) drew them;
- choosing the boundary rule per edit type;
- detecting global motion;
- for additions, predicting the placement before generation.

**12. What a future generator could stop doing:** regenerating content outside the edit region. The editor
re-synthesised 22–72 % of out-of-mask pixels, and compositing throws all of that away.

**13. Compute.** Compositing is **postprocessing**: it costs 6–24 s per case on the CPU (≤ 1.9 GB) and saves no
generation compute, because the editor still generates the full frame. Real savings need localised generation, token
reuse or cropping.

## 5. Determinism, performance, resources
- **Determinism:** every case and arm composited twice in fresh processes, identical hashes (7/7).
- **Cost:** 6.4–24.0 s per case (C3's source-resolution feather dominates), peak footprint 0.8–1.9 GB.
- **No swap growth, no GPU, no model load, no download.**

## 6. Limitations and disclosures
- **Scope:** six cases, one rater, development set; n = 4 after exclusions.
- **Selector knowledge:** the session assistant chose the cases knowing G2's frozen text outcomes. The selection rule
  is mechanical within categories (`CASE-SELECTION.md`).
- **Annotator:** isolated (audit clean). It was interrupted once by a usage limit and resumed in the same context.
  `CLAUDE.md` may describe G2's leakage mode in general terms to subagents.
- **Rater:**
  - five blind self-revisions, preserved in `review/SCORES-DRAFT-HISTORY.csv`:
    - R01 C3 (unintended);
    - R15 C3, R15 C2 (unintended);
    - **R15 C0, R09 C0 (adherence PASS → PARTIAL; these two decide n)**;
  - it used `other:unedited` for the D0 panels;
  - C3's panel size identifies it;
  - audit clean.
- **Alignment search:** it is limited to ±4 px.
- **Text boxes:** generous metric rectangles; "touches the mask" does not mean lettering is inside it.

## 7. Recommendation (one immediate next experiment)
**Automatic edit-region localisation, benchmarked against these frozen human masks.**
- **Why this unknown:** the data separate the parts.
  - Masks drawn from the source alone largely worked: adequate coverage on 6/7 cases.
  - Text and unrelated content were then preserved by construction.
  - The remaining failures came from the boundary rule and from global motion.
  - The masks are the part that does not scale, and the seven frozen masks are now a reference set needing no new
    inference.
- **Cheapest falsification:** compare an automatic localiser's masks with the frozen ones (coverage, overlap, text
  exclusion), then re-composite the existing outputs under the frozen rules.
- **Boundary rule:** an outer-ramp or dilated feather is a **known fix candidate** for R01/R09. It is untested and would
  need its own pre-registered run on a different case set, or the holdout.
- **The protocol fix for next time:** an editor-failure rule keyed on the requested change only.
- **Not chosen now:**
  - FLUX.2 [klein] 4B screening stays in the backlog. It answers a different question (a better editor), and
    compositing is editor-independent.
  - Training feasibility is premature until localisation is shown to be the bottleneck.
