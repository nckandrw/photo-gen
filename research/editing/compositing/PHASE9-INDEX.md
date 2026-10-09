# Phase 9 index: lossless resume point (CMPF preservation-aware compositing falsification)

**Directive:** "PHOTO-GEN Phase 9 — Preservation-Aware Compositing Falsification, Independent Validation, and Research
Direction", pasted by the user on 2026-10-09. **Times:** Asia/Manila (UTC+8).

**Outcome: Phase 9 COMPLETE.**
- **CMPF:** SUPPORTED FOR FURTHER DEVELOPMENT (registered, primary arm C2: 3/4). Fragile: it sits at both thresholds and
  depends on two blind adherence revisions. Counting all six cases, it is 4/6 (MIXED).
- **Report:** `RESULTS.md`.
- **Recommended next:** automatic edit-region localisation, benchmarked against the frozen masks.
- **Git:**
  - Phase 8 pushed: `817a7c2..d2357f9`, 24 commits.
  - **Phase 9 commits: local, not pushed.**
  - No v5 tag.

## 0. Start here
1. `CLAUDE.md`, `MEMORY.md` (current state and the Phase 9 entry), then this file and `RESULTS.md`.
2. Nothing runs in the background. Checks: tests 93 OK, `verify`, `verify --edit`.

## 1. Files
- **Pre-registration:** `PROTOCOL.md` (with a post-unblind note), `CASE-SELECTION.md`, `HOLDOUT-PROTOCOL.md`
  (specification only).
- **Annotation** (`annotation/`): the isolated annotator's workspace; prompt; `masks-draft.json`; `audit/` (transcript
  audit, scratch helpers).
- **Masks:** `masks/masks-frozen.json` (read-only) and `MASK-MANIFEST.json` (hashes; rasters gitignored).
- **Tools:** `make_d0.py`, `cmp_run.py`, `freeze_masks.py`, `cmp_blind.py`, `analyze_cmpf.py`; `config.json`,
  `sheets.json`.
- **Runs:** `runs/D0/` (D0 gates), `runs/<case>-{a,b}/` (composites; determinism). PNGs are gitignored; their hashes
  are in the records.
- **Review:** `review/`: sealed key, `SCORES-FROZEN.csv` (`b80dfc52…`), `SCORES-DRAFT-HISTORY.csv` (all revisions),
  `key-unblinded.json`, `RATER-PROMPT.md`, `RATER-AUDIT.json`, `rater-crops/` (sha256 in
  `research/review-crops/MANIFEST.sha256`).
- **Results:** `results.json`, `RESULTS.md`.

## 2. Also done in Phase 9
- **Phase 8 git reconciled:** 24 commits `3452c7d..d2357f9`. The 23rd, `357c908`, was followed by the order-only fix
  `d2357f9`; nothing later. Integrity checks passed, and it was pushed as a fast-forward.
- **`docs/HARDWARE.md`:** macOS 27.0.1 (26A434) is current; 27.0 (26A428) is the historical baseline. The
  machine-profile JSON stays the dated 2026-09-25 read-out.
- **Texture-Fix VAE deleted** after all checks (+1.33 GB). Recorded in `research/qwen/QWEN-ASSET-PROVENANCE.md` §9.
  - Retained: the dense checkpoint and the q4 export.
  - The q8 export was not recreated.
  - `torch-ref/` (737 MB) is kept.

## 3. Discrepancies and disclosures
- **The registered classification hinges on a rubric/rule interaction.** Adherence absorbed the instructions'
  preservation clauses, so R15 and R09 became EDITOR FAILURE in blind revision 2. Recorded as a design defect; the class
  is unchanged.
- **Annotator:** interrupted by a usage limit and resumed in the same isolated context. Its audit is clean.
- **R11 alignment:** the best shift sits at the ±4 search edge, so the true displacement is unknown.
- **The case selector knew G2's frozen outcomes.** The selection rule is mechanical within categories.
- **RESULTS:** one count was corrected after its first commit (unintended NONE 17/18, not 15/18).

## 4. Open decisions for the user
1. Run the **localisation experiment** next (recommended).
2. **Push Phase 9** (not authorised by the directive).
3. **Boundary rule:** an outer ramp or dilation is a future pre-registered candidate.
4. **FLUX.2 [klein] 4B** gate sequence (backlog).
5. **Holdout collection** (specified; needs editor runs).
6. **Tag:** none recommended. A tag should mark an independently validated preservation capability, e.g. a holdout
   pass.
