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
1. `CLAUDE.md`, `MEMORY.md` (current state and the Phase 9 entries), then this file and `RESULTS.md`.
   - `PHASE9-DIGEST.md` is a one-file compact copy of all Phase 9 docs: every rule, table, hash and metric.
2. Nothing runs in the background. Checks: tests 93 OK, `verify`, `verify --edit`.
   - `git status -sb` should show `main` ahead of `origin/main` by the unpushed Phase 9 commits: 20 at the handoff,
     `2ba6dd9..` through the handoff commit.

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
  - `results.json` `per_arm` also gives the n = 4 counts for the non-primary arms: C0 2/4 (MIXED), C1 3/4, C3 3/4.
    These are descriptive; only C2 is registered.
- **Digest:** `PHASE9-DIGEST.md`.

## 2. Also done in Phase 9
- **Phase 8 git reconciled:** 24 commits `3452c7d..d2357f9`. The 23rd, `357c908`, was followed by the order-only fix
  `d2357f9`; nothing later. Integrity checks passed, and it was pushed as a fast-forward.
- **`docs/HARDWARE.md`:** macOS 27.0.1 (26A434) is current; 27.0 (26A428) is the historical baseline. The
  machine-profile JSON stays the dated 2026-09-25 read-out.
- **Texture-Fix VAE deleted** after all checks (+1.33 GB). Recorded in `research/qwen/QWEN-ASSET-PROVENANCE.md` §9.
  - Retained: the dense checkpoint and the q4 export.
  - The q8 export was not recreated.
  - `torch-ref/` (737 MB) is kept.
- **Handoff (2026-10-09):** files that committed docs cite but that lived only in session scratch were copied into the
  repo, byte-verified:
  - `research/qwen/qv-reference/scratch-preserved/`: lock inputs, Phase 8 pre/post checks, the amendment-1 smoke runs,
    glyph crops, the CMP2 grid view. See its README.
  - `research/editing/qa-configs/`: the Q-A config files.
  - `research/qwen/assets/df-{before,after}-texturefix-delete.txt`.
  - The stale Q-P backlog row was marked done (as CMPF).

## 3. Discrepancies and disclosures
- **The registered classification hinges on a rubric/rule interaction.** Adherence absorbed the instructions'
  preservation clauses, so R15 and R09 became EDITOR FAILURE in blind revision 2. Recorded as a design defect; the class
  is unchanged.
- **Annotator:** interrupted by a usage limit and resumed in the same isolated context. Its audit is clean.
- **R11 alignment:** the best shift sits at the ±4 search edge, so the true displacement is unknown.
- **The case selector knew G2's frozen outcomes.** The selection rule is mechanical within categories.
- **RESULTS:** one count was corrected after its first commit (unintended NONE 17/18, not 15/18).
- **RELEASE-NOTES macOS wording (surfaced, not edited):**
  - The header says tags are validated on "macOS 27.0". The machine has run 27.0.1 since 2026-09-29 22:50
    (`docs/HARDWARE.md`).
  - v1 (2026-09-25) and v2 (2026-09-28) were tagged on 27.0. **v3 (2026-10-07) and v4 (2026-10-08) were tagged on
    27.0.1.**
  - The Phase 9 final report named only v4.
  - `config/machine-profile-m5-16gb.json` saying 27.0 is intentional: it is the dated 2026-09-25 read-out.

## 4. Open decisions for the user, with how to start each
Nothing below is authorised yet. Each needs your go-ahead.

1. **Localisation experiment (LOC; recommended next).**
   - Start: pre-register `research/editing/localisation/PROTOCOL.md` **before** running any localiser. It covers:
     - the candidate localisers;
     - the inputs, the same as the annotator's: source-only view and verbatim task text, with no G2 output;
     - metrics against `masks/masks-frozen.json`, rasterised at the D0 canvas with `cmp_run.rasterise`: coverage of
       the frozen mask, spill outside it, IoU, and text-box exclusion (`research/qwen/qv/text-boxes.json`);
     - the pass bar.
   - Then re-composite the existing G2 outputs under the frozen Phase 9 rules, followed by a fresh blind review
     (`cmp_blind.py`).
     - `cmp_run.py` reads its polygons from `masks/masks-frozen.json` and rasterises them itself.
     - A localiser's masks need a sibling tool or a parameterised copy. Never overwrite the frozen file.
   - No new editor inference is needed.
   - If a localiser needs model weights: acquisition audit first (licence, revision, sha256), then your OK before any
     download.
   - Phase 9's directive forbade implementing segmentation; a new directive must allow it.
2. **Push Phase 9.**
   - Re-run the checks: tests 93 OK, `verify`, `verify --edit`, `git status` clean.
   - Then push as a fast-forward: `git -c credential.helper= -c credential.helper='!gh auth git-credential' push origin
     main`.
   - No force-push, no tag.
3. **Boundary rule (outer ramp or dilation).**
   - Pre-register it as a new arm, with its parameters fixed in advance.
   - On the G2 cases it can only be exploratory, since they are now development data. Confirmation needs fresh cases
     or the holdout.
   - Also fix the editor-failure rule: key it on the requested change only, with preservation clauses scored under
     unintended/text.
4. **FLUX.2 [klein] 4B** (`research/EXPERIMENT-BACKLOG.md`; `research/editing/QA-ALTERNATIVE-MODELS.md` §2).
   - Start with an acquisition audit of the VAE file only (~160 MB) at the pinned revision `e7b7dc27f9`: licence
     Apache-2.0, re-check at acquisition, sha256.
   - Then a VAE round-trip entry screen on R02/R12/R15 with the Q-V harness (`research/qwen/qv/`).
   - Only then M5 feasibility, then a quality gate.
   - Compare its configs against `research/editing/qa-configs/`.
5. **Holdout collection** (`HOLDOUT-PROTOCOL.md`).
   - First freeze the method under test (code, parameters, mask rule, rubric, pass bar).
   - Then acquire 16–24 CC0/PD photos, with an acquisition record per image.
   - The edits cost ≈ 10 min each at 1024 (GPU), so they need separate authorisation and clean benchmark conditions.
6. **Tag:** none recommended. A tag should mark an independently validated preservation capability, e.g. a holdout
   pass.
7. **RELEASE-NOTES macOS wording** (§3).
   - Options: add a dated note per tag recording its OS (v1/v2 on 27.0, v3/v4 on 27.0.1), or leave it as is.
   - The tags themselves never move.
8. **Carried over, not Phase 9:**
   - SEC: 4 Dependabot alerts on the edit venv lock. An upgrade needs the E05 parity re-check (`research/qwen/PHASE6-INDEX.md` §7).
   - A 6-step gate at 768² for Z-Image.
