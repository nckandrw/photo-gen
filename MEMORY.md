# MEMORY.md — photo-gen work ledger

A lossless-resume ledger. Newest entry first. Each entry: date, what was done, where the evidence lives, current state, what's open. Update at the end of every working session (see CLAUDE.md § Memory ledger).

---

## Current state (snapshot, keep this block up to date)
_Last updated 2026-10-09 (PHASE 9 COMPLETE + lossless-handoff pass). Read `research/editing/compositing/PHASE9-INDEX.md` next; `PHASE9-DIGEST.md` beside it is the one-file compact copy of all Phase 9 docs. Local times are Asia/Manila (UTC+8; `date` prints "PST")._

**Where things stand. Nothing is running.**
- **Production (text-to-image, Z-Image):** unchanged since v3.
- **Image editing (Qwen-Image-2.1): research-only.**
  - Chronology: G0 CAPABLE → G2 REJECTED → Q-Q AGAINST → Q-V MIXED → Q-VR RUNTIME-MATCHED.
- **Phase 9 CMPF** (`research/editing/compositing/RESULTS.md`): compositing existing G2 edits onto the canvas with
  isolated source-only masks.
  - **Registered: SUPPORTED FOR FURTHER DEVELOPMENT (C2 3/4), fragile.** It sits at both thresholds and rests on two
    blind adherence revisions. Counting all six cases, it is 4/6 (MIXED).
  - Descriptive, all six cases: C0 2/6, C1 hard 5/6, C2 feathered 4/6, C3 source resolution 4/6. At the registered
    n = 4: C0 2/4, C1 3/4, C3 3/4 (only C2 is registered).
  - Composites kept 12/12 text elements; the edits garbled them.
  - Failures: inner-ramp halo/ghosting (R01, R09) and global motion (R11).
- **Recommended next (awaiting you):** automatic edit-region localisation, benchmarked against the 7 frozen masks
  (no new inference for the first comparison).
- **Git:**
  - Phase 8 pushed (`817a7c2..d2357f9`, 24 commits). **Phase 9 commits are local, NOT pushed**: `2ba6dd9..cab2910`
    (19) plus the handoff commit, so 20 ahead of `origin/main` at the handoff.
  - Tags: v4 latest (`1741179` → `33669eb`), v3 `401e400`. No v5.
- **Assets:**
  - kept: the dense Qwen checkpoint (33 GB, RETAIN) and the canonical q4 export;
  - Texture-Fix VAE deleted 2026-10-09 05:56 (+1.33 GB);
  - q8 export not recreated;
  - `torch-ref/` (737 MB) kept.
- **Hardware:** macOS **27.0.1** is the current validated environment; 27.0 is the historical baseline
  (`docs/HARDWARE.md`).
- **Open decisions** (each has a "how to start" procedure in `PHASE9-INDEX.md` §4; none is authorised):
  1. Localisation experiment (recommended).
  2. Push Phase 9.
  3. Boundary-rule candidate.
  4. FLUX.2 gate sequence.
  5. Holdout collection.
  6. Tag: none before a holdout pass.
  7. **RELEASE-NOTES macOS wording:** the header says "macOS 27.0", but v3 (2026-10-07) and v4 (2026-10-08) were
     tagged on 27.0.1. Surfaced, not edited.
  8. Dependabot alerts on the edit venv (unchanged).
  9. A 6-step gate at 768² (not Qwen).

### How to resume (read in this order)
1. `CLAUDE.md` (loaded automatically): rules, architecture, commands.
2. This "Current state" block.
3. `research/editing/compositing/PHASE9-INDEX.md`: the latest phase (CMPF), its open decisions with how-to-start
   procedures (§4); then `RESULTS.md`. `PHASE9-DIGEST.md` is the same material compacted into one file.
4. Earlier indexes, newest first:
   - `research/qwen/PHASE8-INDEX.md` (Q-VR, Q-A);
   - `research/qwen/PHASE7-INDEX.md` (Q-V; §7 session mechanics that work);
   - `PHASE6-INDEX.md` (Q-Q, status labels, v4; §7 procedures);
   - `PHASE5-INDEX.md` (G2, P2, identity);
   - `PHASE4-INDEX.md` (the edit backend's design).
5. `research/experiments/STATUS.md` (every experiment's status) and `research/EXPERIMENT-BACKLOG.md` (next frontier).

**Checks, no GPU:**
- `git status -sb` shows `main` ahead of `origin/main` by the unpushed Phase 9 commits, unless pushed since;
- `bin/photo-gen verify` and `verify --edit` must be ok;
- the tests must give 93 OK (command in `CLAUDE.md`);
- nothing should be running: `pgrep -fl "run_edit|qvr-|cmp_run|mlx_side|ref_side|mflux_qwen_edit_worker"`.

### Standing facts (current as of 2026-10-09; older snapshots are preserved in PHASE4/5/6-INDEX.md and their ledger entries)
**Production (text-to-image, Z-Image-Turbo q4 @ `d2d30500`, mflux 0.20.0 / MLX 0.32.2, `--low-ram`)**
- **Validated combinations** (`VALIDATED_COMBINATIONS`):
  - fp32 + 9 (REFERENCE) and bf16 + 8 (FAST) at 512², 768², 1024²;
  - bf16 + 9 at 1024² only;
  - bf16 + 5 (BALANCED) at 1024² only;
  - bf16 + 4 (ULTRA) at 512² only.
  - Everything else needs `--allow-experimental`.
- **Minimum validated compute per size:** 512² → ULTRA; 768² → FAST; 1024² → BALANCED. 768² BALANCED is NOT CONFIRMED (Stage B confirmation 3/1/28; see the 2026-09-29 entry).
- **Regression hashes** (p01 apple, seed 42):
  - 1024²: reference `fe47d88d`, fast `7b45cfbe`, balanced `befe1b3c`, bf16/9 `11b19277`;
  - 768²: reference `94a023d3`, fast `20ff9e2c`;
  - 512²: reference `9ae59f59`, fast `0b9cc20a`, ultra `6aa2b842`.
  - Last re-checked through the CLI on 2026-10-08: REFERENCE 512² and ULTRA 512², exact.

**Editing (research-only):** Qwen-Image-2.1 @ `d26bb61`, q4 export, mflux 0.21.0 in `mflux-qwen/.venv`, policy P2. G0 CAPABLE → G2 REJECTED → Q-Q AGAINST → Q-V MIXED → Q-VR RUNTIME-MATCHED; CMPF compositing SUPPORTED, registered and fragile (see above and `CLAUDE.md`). The app reports `tasks["image-edit"].status = "research-only"` plus a `quality_status` record; `validated: false`; `--allow-experimental` is the opt-in.

**Git:**
- **Tags:** v1 `9ee051c` → `db10040`; v2 `d6c03d1` → `3961404`; v3 `1c097eb` → `401e400`; v4 `1741179` → `33669eb`. All are immutable; never move them.
- **Push:** `git -c credential.helper= -c credential.helper='!gh auth git-credential' push origin main`. SSH isn't authorized on GitHub.
- Stage explicitly; never `git add .`. Never commit PNGs: `git add -f` on a run directory would stage `out.png`.

**Machine:** MacBook Air M5, 16 GB.
- macOS **27.0.1 (26A434)** since 2026-09-29, the current validated environment; 27.0 (26A428) is the historical baseline (`docs/HARDWARE.md`).
- Local time zone Asia/Manila (UTC+8); `date` prints "PST".
- Free disk about 180 GiB at the Phase 9 close (2026-10-09).

**Assets on disk (gitignored):**
- **Qwen:**
  - `models/research/qwen-image-2.1`: 33.1 GB, RETAIN LOCALLY, DELETE trigger in `QWEN-ASSET-PROVENANCE.md` §6;
  - `models/qwen/qwen-image-2.1-edit-mflux-q4`: 10.64 GB, pinned, used by the backend;
  - the duplicate q4 export was deleted in Phase 5; the q8 export was deleted in Phase 6. Their `.export.json` / `merge-q8.json` records are kept.
  - the Texture-Fix VAE (Phase 8) was deleted on 2026-10-09 (provenance §9).
- **CPU reference venv** `torch-ref/` (737 MB; torch 2.14.0 + diffusers 0.41.0; hashed lock in `research/qwen/qv-reference/`): kept for numerical regression testing.
- **Review crops** (from session scratch, gitignored PNGs): `research/qwen/qv/review/{rater-crops,spot-check}/`, `research/qwen/qv-reference/review{,-cmp2}/rater-crops/`, `research/editing/compositing/review/rater-crops/` and `research/review-crops/{g2-rater,qq-rater,qq-spot-check}/`; every file's sha256 is in `research/review-crops/MANIFEST.sha256`. Subagent transcripts, which hold rater tool calls, are session-local under `~/.claude-.claude-nck/projects/-Users-nckandrw-Dev-photo-gen/<session>/subagents/`. The audits extracted from them are committed (`RATER-AUDIT.json`).
- **Session-scratch evidence (Phases 8–9), preserved at the handoff:**
  - `research/qwen/qv-reference/scratch-preserved/`: lock inputs, Phase 8 pre/post checks, the amendment-1 smoke runs,
    glyph crops, the CMP2 grid view. README and SHA256SUMS; tensors and PNGs local only.
  - `research/editing/qa-configs/`: the Q-A config files.
  - `research/qwen/assets/df-*-texturefix-delete.txt`.
  - The session scratch itself (`/private/tmp/claude-501/…`) does not survive the session.
- **Z-Image research:** `models/research/z-image-base-mflux-q4` @ `087eaf40`, plus the LoRA at `models/research/loras/` @ `f9a4db41`; 15/15 files verified.
- **sd.cpp comparator:** `sdcpp/`, `models/diffusion_models`, `models/text_encoders`, `models/vae`; about 15.5 GB of old sd.cpp/Qwen models, plus the uv cache. You deferred their cleanup: don't delete without being asked.
- **`research/experiments/p3b/cap/*.gputrace`** (about 14 GB): summarized in `nax-status.md`; delete only with your OK.

**Still-open, not Qwen:**
- Phase 3 leftover: whether a dedicated 6-step gate at 768² is worth it. Stage C stays deferred.
- Resolution-aware automatic step selection is not to be implemented yet.
- Editing backlog: Q-S on hold; Q-U and Q-C not started; LOC (localisation) recommended; FLUX.2 gate sequence and the holdout are specified (`EXPERIMENT-BACKLOG.md`).

---

## 2026-10-09 — Phase 9 lossless-handoff pass (user: "update the documents/memory/ledger/index so I can start a new session losslessly")
- **Digest:** the user's "cat and compact" digest is now in the repo as
  `research/editing/compositing/PHASE9-DIGEST.md`. The source docs are authoritative.
- **Session-scratch evidence preserved** (93 files, `cmp`-verified):
  - `research/qwen/qv-reference/scratch-preserved/`:
    - the `uv pip compile` inputs named in `requirements.lock.txt`'s header;
    - Phase 8 pre/post checks;
    - the amendment-1 smoke runs (unbanded `ref` 11.2 GB / 23 s → banded `ref2` 6.9 GB / 13 s) and `conv-gate.json`;
    - glyph crops and the CMP2 grid view (local only);
    - `.gitignore` re-includes the smoke `data/record.json`.
  - `research/editing/qa-configs/`: 18 Q-A config JSONs.
  - `research/qwen/assets/df-{before,after}-texturefix-delete.txt`.
  - Rater and annotator scratch were already in the repo; counts match: CMPF rater 484, annotator 106, Q-VR rater 255 (+ its committed helper), CMP2 rater 41.
- **Docs:**
  - PHASE9-INDEX: §4 gives every open decision a how-to-start procedure; §3 records the RELEASE-NOTES discrepancy;
    §1 adds the non-primary n = 4 counts.
  - EXPERIMENT-BACKLOG: the stale Q-P row is marked done (as CMPF).
  - CLAUDE.md: the HARDWARE line now says 27.0.1 is current.
  - This block was updated.
- **Correction to the Phase 9 final report:** it said only v4 was tagged after the 27.0.1 update. **v3 (2026-10-07)
  was too.** v1 and v2 were on 27.0.
- **Still not pushed; no tag.** Nothing is running.

---

## 2026-10-09 — Phase 9 COMPLETE (directive "PHOTO-GEN Phase 9 — Preservation-Aware Compositing Falsification…")
- **Phase 8 reconciled and pushed:** 24 commits `3452c7d..d2357f9`. `357c908` was followed by the order-only fix
  `d2357f9`. Checks passed (93 OK, verify ×2, assets, frozen sheets). Pushed as a fast-forward.
- **Housekeeping:**
  - HARDWARE.md: 27.0.1 current, 27.0 baseline (`2ba6dd9`).
  - Texture-Fix deleted after checks (`f07023e`, provenance §9).
- **CMPF:**
  1. Pre-registration `c6eff32`.
  2. Isolated source-only annotator (`c82f107`): interrupted by a usage limit, resumed, audit clean. Masks frozen
     `04a1b23`.
  3. D0 gates bit-exact against Phase 7.
  4. Runs: deterministic 7/7, gates and invariants pass; R11 alignment failure.
  5. Fresh rater; frozen `f87aba8`; unblinded `bf721d0`; RESULTS `7d92e15` (+ count fix `03ed914`).
  - **Result:** SUPPORTED (registered, fragile).
- **Disclosed:**
  - the editor-failure rule absorbed preservation clauses (post-unblind note);
  - five rater self-revisions;
  - the selector knew G2 outcomes;
  - the alignment search was limited to ±4.
- **Not pushed; no tag.** Nothing is running.

---

## 2026-10-09 — Phase 8 COMPLETE (same directive; resumed after the usage-limit cut-off)
- **Chain:** `qvr-chain.sh` → `QVR_CHAIN_DONE` 01:23:55 (23 steps rc 0, no abort). Analysis `134a618`.
- **Q-VR result: RUNTIME-MATCHED.**
  - All gates pass (weights 238/238; A1 = Phase 7 6/6; preprocessing, cast and tiler ports bit-exact; A2 deterministic).
  - A1–A2 is SMALL on 6/6 (0.14–0.19/255 > B_i), and PE with TF32 off.
  - Blind review (`3294fd2`): A1/A2 24/24 identical.
  - MLX pad/AvgDown probes are bit-exact. The PyTorch-MPS defect does not reproduce on this machine (`b00846d`).
- **Conditional arms:** `qvr-cond-chain-r2.sh` (`819a1c9`; attempt 1 stopped on a tool path bug, kept as `runs/FAILED-*`).
  - Texture-Fix @ `702909b`: audit first, 1.35 GB downloaded and verified. Its encoder is bit-identical, its decoder
    0.3–0.7 dB worse, and the text calls are the same.
  - Identity probe `research/qwen/runs/QVR-ID-512-R15`: 26.0 vs 31.1 dB; 1 clear + 1 borderline loss; 1024 not
    triggered.
  - CMP (G2 box): coverage failure.
  - **Amendment 2** (post-hoc, undeclared-deviation fix), CMP2 with a conservative whole-van mask: the feathered
    composite is viable (`822fa77` + CMP2 freeze).
- **Disclosed:**
  - the rater revised three D0 calls via a helper script outside its permitted directories (no effect on the tallies);
  - one TF step grew swap by 1.9 GB (under the 2 GB limit);
  - the monitor cadence was 1.2–1.7 s;
  - macOS 27.0.1;
  - a second rater on Phase 7's pixels: 20/24 agreement; still MIXED by Q-V's rules (descriptive).
- **Closing checks:** tests 93/93; `verify` and `verify --edit` ok; assets identical to pre-Phase-8
  (`qwen-assets-verification-phase8-post.json`); frozen G2/Q-Q/Q-V sheets intact; no `app/`, `config/` or `bin/` change.
- **Docs:** report `research/qwen/QWEN-QVR-REFERENCE.md`, Q-A doc, STATUS, backlog, PERFORMANCE-MAP,
  QWEN-EDITING-QUALITY, RELEASE-NOTES "Unreleased", CLAUDE.md, ASSET-PROVENANCE §8, HARDWARE note, `PHASE8-INDEX.md`.
  Review crops preserved (`research/review-crops/MANIFEST.sha256`).
- **Not pushed; no tag.** Nothing is running.

---

## 2026-10-09 — Phase 8 IN PROGRESS (directive "PHOTO-GEN Phase 8 — Qwen VAE Runtime Verification, Failure Attribution, and Future Editing Research"); session cut off by usage limit
- **Done:** preflight (93/93 tests, verify + verify --edit ok, assets `research/qwen/assets/qwen-assets-verification-phase8-pre.json`); Phase 7 = **9** commits (8 + docs-only `817a7c2`; the directive said 8), reviewed and **pushed** `56880d2..817a7c2` (no force; tags untouched). §6 count resolved: `research/qwen/qv-reference/phase7-transitions.md` (512: 6 − 4 + 1 reversal R15 t3 = 3); clarified in place `3c0a07f`. ComfyUI #16433 read: a PyTorch-MPS MPSGraph pad bug for rank-5 tensors (pytorch #194922, fixed for torch 2.15); not MLX. Pre-registration `ec5b04f` (`research/qwen/qv-reference/PROTOCOL.md`), tools + amendment 1 (banded CPU conv, bit-identical) `db190f8`. CPU reference venv `torch-ref/.venv` (torch 2.14.0 CPU, diffusers 0.41.0; lock `research/qwen/qv-reference/requirements.lock.txt`).
- **IN FLIGHT at cut-off:** chain `research/qwen/qv-reference/qvr-chain.sh` → log `research/qwen/qv-reference/qvr-chain.log`, marker **`QVR_CHAIN_DONE`** (or `QVR_CHAIN_STOPPED <step>`); started 01:17:08; all steps through A2-1024-R02 rc 0, no abort; remaining were A1/A2-1024-R15 and six A1T runs (≈ 5 min total).
- **Next:** (1) `mflux/.venv/bin/python3.12 research/qwen/qv-reference/analyze_qvr.py research/qwen/qv-reference/qvr-summary.json` → numeric class (PROTOCOL §6–7); commit runs (JSON only; .npy/PNG ignored). (2) If no item MATERIAL: conditional arms §8 (Texture-Fix acquisition audit then download fp32 @ `702909b`; ID R15-512 via `run_edit.sh app`; CMP R02-1024 — `composite.py` not yet written). (3) sheets.json → `qvr_blind.py prepare` → rater prompt commit → fresh-subagent rater → freeze → unblind → `analyze_qvr.py … review`. (4) Report `research/qwen/QWEN-QVR-REFERENCE.md`, Q-A doc `research/editing/QA-ALTERNATIVE-MODELS.md` (desk notes so far: FLUX.2-klein-4B Apache-2.0, VAE 32 ch @ 8×, mflux `mflux-generate-flux2-edit`; LongCat-Image-Edit Apache-2.0, FLUX.1 VAE 16 ch, no MLX runtime; Qwen-Image-Edit-2511/Layered Apache-2.0, 20B, Qwen-Image VAE 16 ch @ 8×; Step1X-Edit v1p2 / OmniGen2 FLUX.1 VAE; Qwen-Image-2.1 is 64 ch @ 16×). (5) Ledger/STATUS/backlog/index; no v5 tag; Phase 8 commits not pushed.
- **Side finding (not filed upstream):** mflux 0.21.0 text-to-image `Qwen21VAE()` uses hard-coded latent mean/std that differ from the checkpoint config at 11/128 values; the edit path uses the config (Q-V gate-proven).

---

## 2026-10-08 — Phase 7 (directive "PHOTO-GEN Phase 7 — Q-V VAE round-trip ceiling test and Qwen decision gate")
- **Step 0, checks:** tree clean; `main` = `56880d2` = origin; v3 `1c097eb`→`401e400`, v4 `1741179`→`33669eb`; Q-Q frozen `bcef9aa3`/`4c8d6f36` and G2 `f14deba4` intact; `assets/qwen-assets-verification-phase7-pre-qv.json`: source 87/87, q4 export 18/18; no q8 export.
- **Pre-registration:** `research/qwen/qv/PROTOCOL.md`.
  - The VAE-only round trip of the staged G2 inputs R02, R12 and R15 at 512 and 1024, using mflux's own edit-path functions; the primary path is a ceiling (bf16 latent cast, tiled decode).
  - The E05 pipeline-equivalence gate runs first.
  - Provenance-blind review: ORIGINAL | scaled input | round trip, with randomised order.
  - Rules INCONCLUSIVE / VAE-IMPLICATED / BUDGET-LIMITED / VAE-CLEARED / MIXED, applied within one rater.
- **Chain:** `research/qwen/qv/qv-chain.sh` → `research/qwen/qv/qv-chain.log`. **DONE** 23:55:48 (`QV_CHAIN_DONE`); all rc 0; all gates passed (`0b2514d`).
  - **Equivalence gate:** a real 3-step E05 production-worker edit; the harness reproduced the encode input/output and decode output bit for bit; bf16 into unpack; tiling identical.
- **Rating:** rater prompt `6e527f0`; fresh-subagent rater; frozen 2026-10-09 00:25:20 (`670642e`); unblinded `f718359`.
- **Result: MIXED.**
  - 512: N 12, S 6, K 6, L 4 → the round trip keeps 3/12 legible.
  - 1024: N 12, S 2, K 10, L 3 (one per photo) → it keeps 7/12.
  - Thresholds: implicated ≥ 5; cleared or budget-limited ≤ 1.
  - Preference: scaled input 6/6.
  - Cross-rater, the 19 edit-garbled units: 7 scaling / 6 VAE / 6 regeneration.
- **Disclosed:**
  - the Improvement Clause items: equivalence gate, scaled-input panel, ceiling framing, a/b repeats, 1 GB cache cap;
  - the hypothesis may have leaked to the rater via CLAUDE.md;
  - panel sizes reveal the budget;
  - the rater's helper scripts in its crop directory;
  - the audit's "git " matches were the word "digit";
  - 3 critical samples, all in the untiled variant only;
  - the start swap was 4.3 GB;
  - the monitor samples about every 2.5 s;
  - regional SSIM doesn't track the text failures.
- **Close** (`a257500`, `6981582`): review crops preserved (`research/review-crops/MANIFEST.sha256`, directive §11); budgets > 1024 labelled untested; report `QWEN-QV-DIAGNOSTIC.md`; docs (STATUS, backlog, QWEN-EDITING-QUALITY, PERFORMANCE-MAP, guide, README, RELEASE-NOTES "Unreleased", CLAUDE.md); `PHASE7-INDEX.md`. Not pushed or tagged.
- **Dependabot:** the 4 alerts are documented in `docs/REPRODUCIBILITY.md` §5.1. The lock is unchanged.

- **Resume aids (2026-10-09, after the close):**
  - The "Current state" block was rebuilt as one current picture: the G0 → G2 → Q-Q → Q-V chronology, git state (8 unpushed commits), and six consolidated open decisions. The stale Phase 6 snapshot was removed from it; it is preserved in `PHASE6-INDEX.md` and the Phase 6 entry below.
  - `PHASE7-INDEX.md` gained §6 (how to start each open decision) and §7 (the session mechanics that work).
  - CLAUDE.md: blind-review tools and the crop-preservation rule; the Qwen source checkpoint in the research-models list.
  - Not pushed.
---

## 2026-10-08 — Phase 6 (directive "PHOTO-GEN Phase 6 — Phase 5 closeout, Q-Q diagnostic, status hardening, and v4 release")
- **Step 0, checks:** working tree clean; `origin/main` = `401e400`; v3 = tag object `1c097eb` → `401e400` (local and remote); **15 Phase 5 commits** `0d15f49` … `63c24a5` (`git rev-list --count 401e400..63c24a5`). *Correction:* the Phase 5 closing chat summary said 13, then 19.
- **Step 1, documentation corrections** (docs only; every correction is marked in place; no score, evidence file or criterion changed; `SCORES-FROZEN.csv` still `f14deba4…`):
  1. `results.md` per-item table: R04 is "guacamole → black olives" (it said "black-bean dip").
  2. `QWEN-EDITING-QUALITY.md` G2 table: criterion S counts FAIL marks: 512 = 3 marks on 2 items (R09 adh + pres, R12 pres); 1024 = 2 marks on 2 items (it said "3 of 4 items" / "2 of 4 items").
  3. Times now from commit timestamps: amendment 1 = `f16e092` 12:11:01 (4 s before the chain's 12:11:05; it said ~12:15); amendment 2 = `cf96d4a` 16:49:21 (it said ~16:55); provenance §6 = `0ccc0b7` 17:23:40 (it said about 17:45); Phase 5 complete = `63c24a5` 17:33:39 (it said ~18:30); sources acquired ~12:00–12:11 (it said ~12:00–12:20).
- **Step 2, labels** (`a4f9d57`): `/capabilities`/`/status` `tasks["image-edit"].status = "research-only"` + `quality_status` (G2 REJECTED); warning, opt-in error, CLI help name G2; manifest, worker (`3094e942`), `validated=false` untouched; `configuration_id` 3cd79615/fffe8df3 unchanged; tests 93/93.
- **Step 3, Q-Q diagnostic** (`research/qwen/qq/PROTOCOL.md`, pre-registered `fea3872`): q8 export built per component (`models/research/qwen-image-2.1-edit-mflux-q8`, 18.46 GB; gates E and V passed; `135decd`); smoke `924bc96`.
  - **(was in flight; DONE 11:04:18, `QQ_CHAIN_DONE`)** chain `research/qwen/qq/qq-chain.sh` → log `research/qwen/qq/qq-chain.log`, marker `QQ_CHAIN_DONE` (started 2026-10-08 08:51:44, 18 runs, ~2.3 h). Then: gate Q (q4 = G2 pixels), `make_pairs.py` → `qq_blind.py prepare` → fresh-subagent rater → freeze → unblind → `analyze_qq.py`.
  - Chain: 18/18 runs rc 0, no abort, 0 critical. Gate Q: 8/8 q4 runs = G2 pixels. Gate D: passed (`f73c16c`).
  - Rater sheets frozen 11:32 (`77f8a35`); unblinded (`f1f353e`). **AGAINST:** G4 19, R 1, W 0; text FAIL 6/6 both arms; preference q8 3 / q4 0 / SAME 3. Report `7fd3edc`.
  - q8 export deleted 11:36:42 (+18.5 GB; `f2ff5a6`).
- **Step 4, close:** Z-Image REFERENCE 512² `9ae59f59` and ULTRA 512² `6aa2b842` exact through the CLI. Docs updated: STATUS, PERFORMANCE-MAP, backlog (Q-Q done; Q-V next), QWEN-EDITING-QUALITY, RELEASE-NOTES v4, README, guide, REPRODUCIBILITY §5.6, THIRD-PARTY-LICENSES, CLAUDE.md. PHASE6-INDEX written. Pushed; v4 tagged on the closing commit.
- **Disclosed:**
  - Amendment 1: the export tool bug (save_model writes every component's config).
  - Added after pre-registration, before any q8 G2 output: `make_pairs.py` and `smoke.sh`.
  - `rater_audit.py` was extended after the rater finished.
  - The rater moved P03–P06 quality from MINOR to PASS for both arms.
  - AGAINST sits at its boundary (R ≤ 1). A post-freeze, unblinded look found one candidate (R15-512 banner); not counted.
  - Local times are UTC+8, not US Pacific.

---

## 2026-10-07 — Phase 5 (directive "PHOTO-GEN PHASE 5: Harden Qwen editing, validate it on real photographs, and determine production readiness" + addendum on source-checkpoint disposition)
- **Done, in order:**
  1. Push and tag: `origin/main` → `401e400`; **v3** tag.
  2. Duplicate q4 export verified byte-identical and deleted (`0d15f49`; `QWEN-ASSET-PROVENANCE.md`).
  3. Backend identity (`51d4d6a`).
  4. Memory lifetime A/B, P2 ADOPTED (`a3a225c`, `973ef7f`; `QWEN-MEMORY-LIFETIME.md`).
  5. G2 pre-registration (`8694119`).
  6. Sources: 16 CC0/PD Commons photos, plus the MPO input fix (`e653122`, `f16e092`; protocol amendment 1).
  7. **G2 chain 12:11:05 → 16:45:07 PST** at git `f16e092`. *Correction:* the earlier current-state block said "started ~12:25"; the chain log's start is 12:11:05.
  8. Blind sheets with seed 20261007, plus amendment 2 (`cf96d4a`).
  9. Fresh-subagent rater; sheet frozen 17:13, `f14deba4…` (`6577b09`); unblind and tally.
  10. Results, Qwen G2 section and source disposition (`0ccc0b7`). Docs in the closing commit.
- **Result: REJECTED at 512 and 1024** (pre-registered §9: preservation FAIL ≥ 3).
  - 4 preservation FAILs per budget: R02, R12, R15 (text-derived; the rater also scored them FAIL directly) and R09.
  - The verdict doesn't depend on R09. The session assistant spot-checked all 6 forcing text FAILs at native resolution after the freeze; this was descriptive, not a re-score.
- **Disclosed deviations:**
  - amendment 2 (procedural only): shuffle seed, zoom crops, incremental rows, extra format checks, anonymization limits (sheet sizes differ per budget, the harness may load CLAUDE.md into the rater);
  - the rater revised 3 of its own preservation scores before hand-back; no tallied count changed (`g2/RATER-AUDIT.json`);
  - G2 wall times come from the monitored harness, which ran slower than unmonitored edits.
- **Evidence:** `research/editing/real-world/` (`results.md`, `benchmark.csv`, `scores.csv`, `results-summary.json`, `g2/`), `research/qwen/runs/G2-*` (incl. sidecars), `QWEN-EDITING-QUALITY.md` § G2, `QWEN-ASSET-PROVENANCE.md` §6.
- **Open:** see the current-state "Open user decisions". Backlog Q-Q and Q-A are in `research/EXPERIMENT-BACKLOG.md`. Nothing is running.

## 2026-10-06 — Phase 4 started (directive "PHOTO-GEN PHASE 4: Qwen editing backend + unified image-task layer")
- **Pending CLI check CLOSED (directive §2).**
  - `bin/photo-gen generate -p "a red apple on a wooden table, soft window light" --seed 42 --profile balanced --json` → job `20261006T143008Z-756b0e`, pixel `befe1b3c8af5424cc5f65868fec96938bfac782238f46c18652244fada3bdd42` (= documented), `validated: true`, bf16/5, 38.98 s wall (cold, battery), denoise 33.26 s, peak 5.84 GB, transformer released.
  - Same with `--width 768 --height 768` → refused, exit 2: "bf16 + 5 steps is validated only at 1024x1024; pass allow_experimental=true…".
  - Tests 42/42 before any Phase 4 change.
- **Upstream news found during research:** our mflux issues #760/#761 were closed 2026-10-01; fixes landed as #802 (transformer release) and #803 (bf16 stream **default**, new `--float32`) in **mflux 0.21.0** (2026-10-03). So 0.21.0 changes Z-Image numerics: the production venv must stay on 0.20.0.
- Phase 4 work in progress: see `research/qwen/`.
- **User decisions (2026-10-06):**
  - Licence: accepted Qwen-Image-2.1 for research use (Qwen Research License, non-commercial; never commit or redistribute weights).
  - Approved: the 33 GB checkpoint @ `d26bb61` (every file hash verified), a separate venv (production 0.20.0 untouched), and the sd.cpp comparator TE + mmproj. The comparator also uses the existing 2.1 DiT GGUF + VAE.
- **Paused 23:00–23:5x for the user's meeting.** Downloads and the venv install were suspended (SIGSTOP) and then resumed. All downloads verified: 30/30 files vs `research/qwen/upstream-file-manifest.json` (`download-verification.json`).
- **2026-10-07 progress (details in `research/qwen/`):**
  - **Venv:** `mflux-qwen/.venv` (mflux 0.21.0 + MLX 0.32.2; the rest per the upstream lock). Lock in `config/qwen-python-requirements.lock.txt`.
  - **q4 export:** `models/qwen/qwen-image-2.1-edit-mflux-q4` (10.64 GB). Byte-identical across 2 runs. Manifest `config/backend-qwen21-edit-mflux.json`.
  - **Incidents:** see `research/qwen/INCIDENTS.md`:
    - the watchdog kill missed the child (export run 1);
    - the harness was edited mid-run (S2).
  - **Smoke results:**
    - probes are passive (app = plain CLI pixels); repeat-deterministic;
    - deferred DiT load is pixel-identical at 512 and 1024 (now the production default);
    - 512 footprint 12.63 → 8.85 GB; 1024 footprint 14.20 → 12.08 GB;
    - 1024 edit ≈ 607 s (40 steps).
- **Commits:**
  - `c6c01a9`: pre-registration (benchmark v1 + audit + smoke evidence);
  - `cf21eaa`: frozen sources 11/11 + regions;
  - `5f89f4f`: task layer + edit backend; 72/72 tests;
  - `7dca169`: golden fixture tracked (a `.gitignore` fix);
  - `a7cc451`: frozen G0 chain.
- **Z-Image real regression through the refactored app:** all exact (fe47d88d, 7b45cfbe, befe1b3c, 6aa2b842, API 9ae59f59). Footprints as documented. Evidence: `research/qwen/zimage-regression/`.
- **G0 done (01:34–04:00, clean conditions):** 512 **CAPABLE**, 1024 **CAPABLE**. Scores frozen before metrics: `research/qwen/g0/` (512 `0a80b2c2`, 1024 `3d52f2ad`).
  - 512: 11/11 adherence; E08 preservation PARTIAL (oranges also replaced); 2 MINOR.
  - 1024: 11/11 adherence and 11/11 preservation; 2 MINOR.
  - Timing: 1024 cold 496.8 s; sustained median 556 s (1024), 103 s (512).
  - Memory: 1024 peak 12.1 GB, 0 critical samples; 512 peak 8.9 GB.
  - Cold Z-Image BALANCED through the refactored app: `befe1b3c` in 35.6 s (recorded 36.1).
- **G1 done (04:01–04:29):**
  - References were pre-resized to 512 for both runtimes; the mflux parity run equals G0-512-E01.
  - Blind 4 pairs: mflux 1 / sd.cpp 1 / 2 ties. Scores frozen `957ef229`, key `bac40ba3`.
  - sd.cpp: ≈ 290 s vs 88.9 s (same-chain mflux control) per 512 edit; 12.8 vs 9.0 GB; critical-pressure samples in 3/5 runs → **mflux kept**.
  - Blinding was weak (the mflux arm had been seen in G0); disclosed.
- **Real API check** (`research/qwen/api-check/`):
  - `POST /edit` through `serve` gave G0-512-E05's exact pixels;
  - a running edit was cancelled cleanly (worker killed, no orphan, no output);
  - a ULTRA generation afterwards was exact.
  - Then `EditRequest` gained `backend_id`/`model`/`model_revision`, and the sidecar gained `model_manifest.sha256` (metadata only; the re-run edit was identical).
- **Speed-claim baselines:** sd.cpp is ≈ 3.3× the same-chain mflux control and ≈ 2.8× the G0 sustained median. "1024 preserves better" was softened to one test, one seed.
- **Reports:**
  - `research/qwen/`: `QWEN-SOURCE-AUDIT`, `QWEN-RUNTIME-COMPARISON`, `QWEN-EDITING-BASELINE`, `QWEN-EDITING-QUALITY`, `INCIDENTS`.
  - `research/editing/`: the benchmark.
  - Docs updated: README, guide, HARDWARE, REPRODUCIBILITY §5, THIRD-PARTY-LICENSES §5, USAGE, RELEASE-NOTES (Unreleased; **no tag created**), CLAUDE.md, STATUS, BACKLOG (Q-G/Q-S/Q-M/Q-U/Q-C), COMPONENT-SOURCES.
- **Disclosed deviations / incidents:**
  1. The export watchdog killed `/usr/bin/time`, not the python child (export run 1 completed regardless; preserved as `ABORTED-*`; run 2 is canonical and byte-identical).
  2. The harness was edited mid-run (S2); no impact.
  3. The `worker_run.py` relative-path bug: the first chain-2 runs failed instantly (kept), rerun as `*r2`.
  4. The `app/tests/data` fixture was initially gitignored (fixed in `7dca169`).
  5. The smoke runs (meeting apps open) are confounded for absolute swap; the clean baseline comes from G0.
  6. G0 rater = the AI assistant, non-blind (single config), primed by the smoke.
  7. The protocol was committed after source generation had started (before any source was viewed or any edit run).
- **Open items for the user (none auto-start):**
  1. Whether a `v3` tag is wanted for this state.
  2. Production adoption of editing needs a blinded G2 on one fixed configuration (backlog Q-G) and, for any commercial use, a licence change.
  3. Disk: `models/research/qwen-image-2.1` (33 GB, the export source) and `models/qwen/ABORTED-20261007T0005-…` (10.6 GB, byte-identical to the canonical export) can be removed only with the user's OK.
  4. Speed lever Q-S (fewer steps); memory lever Q-M (1024 denoise peak); Q-U (one venv for both tasks?).

## 2026-09-29 — BALANCED (bf16 + 5) adopted at 1024²; 768² confirmation NOT CONFIRMED
- **Directive:** "PHOTO-GEN NEXT PASS: promote the clean 1024² 5-step result, run a focused 768² confirmation, defer Stage C".
- **BALANCED:**
  - `PROFILES['balanced']` and `VALIDATED_COMBINATIONS[('bf16',5)] = (1024²,)`; CLI choice added; tests 42/42 (`test_balanced_profile_gated_at_1024_only`). Commit `b59036c`.
  - Docs updated: README, USAGE, HARDWARE, guide, CLAUDE.md, machine profile (hash `befe1b3c`, cold 36.1 s), STATUS, PERFORMANCE-MAP (roles and operating-point table), BACKLOG.
- **Confirmation (768² only):**
  - Pre-registered in `8149bf3` (`protocol-confirm768.md`): 16 prompts (8 text-focused), seeds 3141/9091, 32 pairs. Improvement Clause: faded/doubled text is not minor; pooled under-denoising family; balance +4.
  - 64/64 runs rc = 0, on battery power.
  - Blind 3/1/28. Frozen sha `864c590f`, key `d66b6ab7`.
  - Verdict **NOT CONFIRMED**: criterion 4 failed (the c03 subtitle was 8-better in both seeds); criterion 1a passed only at equality.
  - Sensitivity, both directions: C19 as a tie → CONFIRMED; the C22 decal as incidental → FAILED.
  - Pooled descriptive 6/1/49. Commit `35cee41`.
- **Disclosed:**
  - The CLI end-to-end check of BALANCED was denied by the auto-mode classifier and is pending for the user. The hash comes from the production worker, which matched the CLI for FAST and ULTRA.
  - The rater was primed by Stage B.
- **Production unchanged apart from BALANCED 1024². Stage C / 6-step not started.**

## 2026-09-29 — Step-count gate Stage B (bf16/8 vs bf16/5): VALIDATED at 512², 768² (narrowest pass), 1024²
- **Directive:** "PHOTO-GEN NEXT PASS", Stage B. User: "let stage b finish completely".
- **Runs:** 147, all rc = 0. Blind review of 72 pairs in 3 directories; all sheets frozen before any unblind.
  - Frozen sha256: 512² `2e2ac624`, 768² `6ea6b796`, 1024² `7b34cd41`.
- **Blind results (8-better / 5-better / ties):**
  - 512² 1/0/23 (pen type);
  - 768² 3/0/21 (p03 ghosted text, p07 faded subtitle judged minor, p09 duplicate balloon);
  - 1024² 0/0/24.
- **Speed:** paired sustained denoise 5/8 is 0.629 / 0.630 / 0.625. Cold 5-step vs the same-day Stage A cold 8-step: 11.3/15.6, 20.9/30.4, 36.1/54.4 s wall. Memory is identical.
- **Stage B question:**
  - the 4-step signatures are eliminated at 1024²;
  - at 768² they are not eliminated but shifted;
  - none at 512².
  - 768² came out worse than 1024², against the σ ordering.
- **Evidence:** `results.md` § Stage B, `benchmark-B.csv`, `metrics-summary-B.json`, `scores-B.csv`, `blind-mapping-B.json`, `failure-modes-B.json`, `key-B*-unblinded.json`, `stage_metrics.py`.
  - Commits `b4e2d39` (artifacts), `54d24c6` (sidecars), `d36a545` (results).
- **Disclosed deviations:**
  - grid16 was re-implemented: the Stage A inline code was lost. The best fit to the 144 Stage A values has max |error| 0.46, and Stage A was re-scored with the same code. Criterion 5 is unaffected.
  - The 1024² C01–C08 notes were transcribed after a context break, but before freeze.
- **Docs:** STATUS, PERFORMANCE-MAP, EXPERIMENT-BACKLOG, gate README.
- **Production unchanged. Stage C not started.**

## 2026-09-29 — ULTRA profile (bf16 + 4) promoted at 512² only; Stage B launched
- **ULTRA:** `PROFILES['ultra']` plus `VALIDATED_COMBINATIONS[('bf16',4)] = (512²,)`; tests 41/41 (`test_ultra_profile_gated_at_512_only`). CLI: 512² → `6aa2b842`, validated; 768² refused.
- **Docs:** README, the guide, USAGE, HARDWARE, CLAUDE.md, the machine profile, STATUS, PERFORMANCE-MAP. The step-sweep report has an evidence-chain addendum.
- **Stage B** pre-registered and launched (see Current state).

## 2026-09-29 — Step-count gate Stage A (bf16/8 vs bf16/4): 512² VALIDATED, 768²/1024² REJECTED
- **Pre-registered** (`f49604c`): fresh seeds 2026/7331; 12-prompt suite; 3 resolutions; lexicographic scoring + failure-mode checklist; grid16 guard; per-stage fresh seeds (Improvement Clause).
- **Results:** 150 runs, 0 failures. Blind 512² 1/0/23, 768² 1/0/23, 1024² 3/1/20. Every 4-step loss was an under-denoising signature (ghost duplicate text, malformed glyph, ghost plates). No grid artifact.
- **Reconciliation:** the probe control (2/3/19 at 1024²) did not generalise on the text criterion. Pooled 1024²: 5 / 4 / 39, with 4-step losses concentrated on text.
- **Docs:** STATUS, PERFORMANCE-MAP, step-sweep annotation. Production unchanged.

## 2026-09-29 — 4-step probe COMPLETE: REJECTED; Turbo-4 emerges as the next gate candidate
- **Benchmark:** 72 sustained runs + 3 cold, 0 failures. Paused 22:52 → 08:55 (user), resumed without repeating completed runs.
- **Blind, three pairwise directories** (keys sealed until all were frozen):
  - C vs B: 6–18;
  - C vs A: 8–16;
  - A vs B: 2 / 3 / 19 ties.
  - All C losses were decided on visual quality (grain). On adherence C was 6–5 / 8–5 (not significant).
- **Performance (paired sustained denoise vs A):** B 0.504, C 0.541 (C/B 1.062). Cold wall: A 53.8, B 29.9, C 32.3 s. Memory: C 6.69 GB vs 5.85 GB.
- **LoRA fully applied:** 204 layers, 612/612 keys.
- **Q6 new failure mode:** a 16-px grain; grid16 3.9–11.5 in C vs ≤ 1.62 in A/B.
- **Corrections made before committing:** I had mis-attributed p12 correctness and duplicate artifacts to the wrong arms in the first draft. Fixed from the unblinded keys.
- **Registers updated:** STATUS, EXPERIMENT-BACKLOG (Phase 3 addendum), PAPER-RESEARCH-MAP.

## 2026-09-28 (evening) — 4-step probe started (directive "PHOTO-GEN EXPERIMENT: 4-step Z-Image Base + LoRA vs Turbo")
**Goal:** can a 4-step-distilled model (Z-Image **base** + alibaba-pai 4-step LoRA; NOT Turbo) beat plain Turbo-at-4-steps on speed/quality, and approach FAST? Inference only; production untouched.

**Done**
- **Pre-registered** (commit `052e41d`, before any benchmark image): `4step-probe/README.md`, `experiment-config.json`, `blind-protocol.md`, `asset-manifest.json` (15/15 files verified).
- Candidates at 1024² bf16: **A** Turbo 8 (= FAST), **B** Turbo 4, **C** base + LoRA at 4 steps.
- Fresh seeds 4242/6174 × the 12-prompt suite. The per-condition order rotates through all 6 permutations.
- Worker `4step-probe/probe_worker.py` reuses the production worker's patches; it reproduced FAST `7b45cfbe` exactly.

**Discrepancies found in smoke (all disclosed in `4step-probe/README.md`)**
1. **Scheduler:** mflux's base CLI defaults to `flow_match_euler_discrete` (at 4 steps: σ 1 → 0.967 → 0.908 → 0.767 → 0). C uses `linear` (≈ the official static shift 3.0), the same as A/B.
2. **mflux bakes LoRAs by default** (dequantize → add → requantize q4): peak 10.54 GB, swap +0.97 GB. Now `--no-bake-lora` (runtime adapters): 6.67 GB, no swap, +4% denoise. The baked runs are kept as secondary data.
3. **Base without LoRA** at 4 steps = noise, and 5.84 GB (so the +4.7 GB was purely the bake transient).
4. **New metric (Improvement Clause):** C shows a 16-px periodic grid (FFT peak/background): C 5.6, A 1.0, B 1.1; flow-match 37.8; no-LoRA 41.7. It is not caused by bf16 or baking. This is a candidate new failure mode (Q6).
5. **Corrected my own unverified claim** ("612/612 keys matched"). The key count is still to be checked.

**Smoke numbers** (single runs, not cold-controlled):

| run | wall | denoise |
|---|---:|---:|
| A | 55.7 s | 50.1 s |
| B | 31.4 s | 26.0 s |
| C runtime | 33.2 s | 27.1 s |

## 2026-09-28 — Chain P3B results (profile, NAX, block sensitivity, FFN sweep, quant speed map)
- **NAX VERIFIED:** q4 qmm + SDPA use NAX in bf16 AND fp32. fp32 goes via MLX's `MLX_ENABLE_TF32=1` default. TF32 off → qmm 3.2× slower, SDPA 2.7×, and REFERENCE 512² hash `6d4311fe` ≠ `9ae59f59`. So REFERENCE depends on the TF32 default (the worker strips `MLX_*` env; protected). `nax-status.md`.
- **Kernel profile, FAST 1024²:** q4 matmuls 74% @ ≈10.4 TFLOPS, SDPA 15%, RoPE + elementwise 11%, compile gain 2.7%. Kernel counts NOT MEASURED (the capture text gives an inventory only). `kernel-profile.md`.
- **Harness bug found and fixed:** the op profile's synthetic norms defaulted to fp32, which promoted "bf16" to fp32. Fixed (bf16 norms + the production bf16 patch): bf16/fp32 = 0.68. The faulty outputs are in `p3b/superseded/`.
- **Block sensitivity:** equal-cost main blocks; cr0/cr1 cheap but critical; late L25–L28 least important; no block is free. ρ(512, 1024) = 0.75. `block-sensitivity-map.md`.
- **FFN width:** the identity control is exact. 90% width already breaks text → no training-free point → BLOCKED on recovery training. `ffn-reduction-design.md`.
- **Quant speed map:** nothing beats q4 g64 by ≥ 3%. q5/q6/q8 +8…46%, fp4/fp8 slower → speed search CLOSED. `quantization-map.md` (order confound disclosed).
- **Probe assets verified** (7/7 LFS sha256).

## 2026-09-28 — v2 freeze, license, 4-step acquisition, chain B start (directive "PHOTO-GEN POST-FAST VALIDATION")
- **Discrepancy surfaced, user decided:** bf16+9 WAS gated at 1024² (bf16 gate, 0/2/22), so it stays valid at 1024² only and is experimental at 512²/768². Implemented as an explicit `VALIDATED_COMBINATIONS` table plus a regression test (`test_validated_matrix_is_exact`). One old test that relied on the mislabel was adapted.
- **v2:** commit `3961404`, verified from a clean clone: 40/40 tests; CLI REFERENCE 1024 `fe47d88d`, FAST 512 `0b9cc20a`, 768 `20ff9e2c`, 1024 `7b45cfbe`; API 512 `9ae59f59`; bf16/9 at 512/768 refused. Tag pushed; v1 untouched.
- **License:** MIT (holder "nckandrw", user's choice) for photo-gen code only. `docs/THIRD-PARTY-LICENSES.md` built from package and HF metadata. **Flag:** the production q4 pack (`mflux-community/z-image-turbo-mflux-q4` @ d2d30500) declares NO license (no card, no LICENSE); upstream Z-Image-Turbo is Apache-2.0. We don't redistribute.
- **4-step probe:** audit passed (all Apache-2.0; the LoRA directly targets distilled 4-step quality, but it is for Z-Image *base*). 6.47 GB downloaded, pinned.
- **Chain B smoke tests:** all scripts OK.
  - NAX VERIFIED for bf16 q4 qmm + SDPA (capture). fp32 TF32-off control: 3.2× slower qmm, 2.7× slower SDPA → REFERENCE uses NAX via the TF32 default.
  - FFN identity control is exact. Harness fix: the memory metric is now exact DiT weight bytes.

## 2026-09-25 — Phase 3: FAST resolution gates completed; production matrix updated
- **Direct blinded REFERENCE-vs-FAST gates** (24 pairs each, seeds 1618/8128, `fast-resolution-gates-report.md`):
  - G512 0/0/24;
  - G768 2/0/22 (lean toward REF, within margin);
  - G1024 0/1/23;
  - pooled 72 pairs: REF 2 / FAST 1 / 69 ties. All VALIDATED.
- **Production change** (a separate commit): `GATED_STEPS[("bf16",8)]` now covers 512², 768², 1024². Test updated (39/39). CLI help updated. End-to-end check: FAST 512² → `0b9cc20a` validated, no warnings.
- **Docs updated:** README, HARDWARE, USAGE, the guide, the machine profile, STATUS, CLAUDE.md.
- **Disclosed:** G512 swap episodes in both arms during Safari/`du` activity; the unplanned 16:53 chain stop.

## 2026-09-25 — Git repository created (directive "PHOTO-GEN GIT REPOSITORY SETUP")
- **Repository:** private `github.com/nckandrw/photo-gen`, branch `main`, tag `photo-gen-m5-16gb-v1` (the validated M5 16 GB build). Repo-local identity only.
- **Versioned:** app/, bin/, config/ (incl. new `machine-profile-m5-16gb.json` and clean `python-requirements.lock.txt`), docs/ (guide, new HARDWARE.md, REPRODUCIBILITY.md, USAGE.md = the old README), research text evidence (≈12 MB).
- **Excluded:** model weights, mflux/ toolchain, data/, outputs/, sd.cpp binaries, research PNGs (749 file hashes in `research/EXCLUDED-IMAGES.sha256`), and in-progress fastgate results.
- **Verification from a clean clone** (toolchain + model attached by symlink at the documented paths):
  - 39/39 tests; `verify --full` OK (11 files re-hashed).
  - CLI REFERENCE 1024² `fe47d88d`, CLI FAST 1024² `7b45cfbe`, API REFERENCE 512² `9ae59f59`, all exact.
- **.gitignore fix found by the clone test:** `mflux/.venv/`-style patterns didn't match symlinks; changed to `mflux/.venv` etc.
- **INCIDENT:** chain P3A stopped ~16:53 with no error (the worker for g512-p08-s8128-ref was killed mid-run). Likely a process-group cleanup of the 16:22 relaunch, which was started inside a compound command. G512 is at 39/48. Relaunch as a top-level `nohup … &` (the pattern that survived 2+ h). The p08-s8128 pair's timing is not comparable.
- **Discrepancies:**
  - research harnesses and `mflux/env.sh` hard-code `~/Dev/photo-gen` (documented: clone to that path);
  - `mflux/requirements.lock.txt` contains ANSI codes (a clean copy is in config/);
  - no licence file has been chosen for the project code.

## 2026-09-25 — Phase 3 (in progress): record audit, sigma audit, resolution gates, model/runtime research; documentation build
**Directives:**
- "PHOTO-GEN PHASE 3" (resolution validation, scheduler audit, then model/runtime research).
- Mid-session: "PHOTO-GEN DOCUMENTATION BUILD".

**Done so far**
- **Record audit:** `research/experiments/phase3-record-audit.md`.
  - "Two blinded gates" = a *chain* (fp32/9→bf16/9→bf16/8), never a direct REFERENCE-vs-FAST gate.
  - Quality (24 pairs) and timing (36 pairs) datasets are now separated.
  - NFE wording fixed in PERFORMANCE-MAP, STATUS, README, the arch map and the Z-Image report (a correction header).
- **Sigma audit** (`sigma-schedule-audit.md`): mflux applies the FLUX dynamic shift (base 0.5 / max 1.15) to Z-Image; the official pipeline computes μ but ignores it (static shift 3.0).
  - Plumbing via external scheduler `sigma_sched.py` + `sigma_worker.py`; parity control reproduced 9ae59f59 / 0b9cc20a / 7b45cfbe exactly.
  - **Result: CLOSED.** 512² M 3 / S 0 / 21 ties; 768² M 2 / S 0 / 22 ties; 1024² sanity near-identical (1 S-better text pair). No runtime effect (ratios 0.999 / 1.005 / 1.001). Implementation difference, quality-neutral; production unchanged. Review speed (~1 min per 24 composites, AI rater) disclosed.
- **Desk reports:** `nax-status.md` (static: LIKELY for q4 qmm + SDPA in both precisions via the `MLX_ENABLE_TF32` default), `quantization-map.md`, `distillation-feasibility.md` (new: alibaba-pai Z-Image-Fun-Lora-Distill 2/4/8-step for Z-Image *base*), `ffn-reduction-design.md` (group-aligned, bit-exact kept weights), `block-sensitivity-map.md`, `kernel-profile.md`, `phase3-scorecard.md`, `phase3-plan.md` (Improvement Clause: a direct 1024² gate; 34 blocks, not 32).
- **Chain B prepared** (not run): `phase3-chainB.sh`, `op_profile.py`, `nax_probe.py`, `quant_microbench.py`, `p3_block_probe.py`, `ffn_prune_worker.py`, jobs in `p3b/`.
- **prod_runner.py:** added an optional `PRODRUNNER_WORKER_SCRIPT` / `PRODRUNNER_WORKER_ENV` (defaults unchanged; backup `prod_runner.py.bak-pre-phase3`).
- **Docs:** `docs/photo-gen-guide.html`. The README got a guide link, the full request-field list, and a label on the performance table.

**Discrepancies found (reported, not silently fixed)**
- `normalize()` labels bf16/9 at 512²/768² `validated_configuration: true` (the bf16 gate covered 1024² only). A code fix awaits the user's decision.
- The manifest `measured_1024` is pre-memfix (immutable, left alone).
- `capabilities.memory_profile.source` cites the wrong report.
- Port-in-use gives a raw traceback.

**Disclosed deviations**
- The CLI/API validation commands (verify, status, capabilities, serve + non-generating requests) ran while the sigma 512² block was in its sustained phase: light CPU only, no generation.
- Protocol status lines were corrected ~14:08, before any A/B image existed (hashes in `phase3-plan.md`).

**Open**
- Sigma 768²/1024² review; FAST gates G512/G768/G1024 review; chain B.
- Guide generation-command validation.
- Download approvals (Z-Image base q4 + PAI LoRA; quant packs).

## 2026-09-25 — Pass 3: productionize, 8-step gate, upstream issues, closures
**Directive:** "PHOTO-GEN NEXT RESEARCH PASS — productionize memory fix, validate 8-step, close branches".

**Done**
- **Transformer-release fix merged**, default ON for both precisions.
  - Code: `app/photogen/runtimes/mflux_zimage_worker.py::_install_transformer_release`.
  - Gate: 16 ABBA runs on the production worker (fp32/bf16 × 512/1024); pixel-identical, 1 compile per run, no runtime cost. Also verified end to end through the CLI.
  - Test: `app/tests/test_worker_lifetime.py`.
  - Evidence: `research/experiments/production-memory-fix-report.md`, `memfix/`, `e2e/`.
- **8-step blinded gate PASSED** (bf16/9 vs bf16/8).
  - Primary seeds 7 + 1234: 0 worse / 1 better / 23 ties. Seed 42 was contaminated (seen before), so it's secondary only.
  - Denoise ratio 0.887.
  - Evidence: `research/experiments/8step-quality-gate-report.md`, `gate8/` (frozen scores + manifests).
- **Profiles implemented:** `profile: reference|fast`; `GATED_STEPS` gates bf16/8 at 1024² only; metadata and repro record the profile.
  - Code: `runtimes/mflux_zimage.py`.
  - Docs: README "Configurations".
- **Performance map:** `research/experiments/PERFORMANCE-MAP.md`. Cold runs are clean; the 1024² sustained block was NOT at steady state (disclosed).
- **Upstream issues SUBMITTED** to mflux-community/mflux (the repo moved from filipstrand):
  - #761: fp32 hidden stream. Its title was later corrected to "≈1.4× slower".
  - #760: the compiled predict closure keeps the DiT alive.
  - Record: `upstream-mflux-issue-SUBMITTED.md`.
- **E10 ablation:** only the timestep embedding and RoPE promote the stream to fp32, and **both** must be fixed. Pad tokens load as bf16 and are NOT a source. The earlier docs claiming "three sources" carry correction headers.
- **Scheduler/NFE finding:** in mflux, N steps = N NFE, so the reference runs 9 NFE. The official "9 steps = 8 forwards" was a diffusers artifact (diffusers PR #13730). See `scheduler-nfe-note.md`.
- **Closed branches:**
  - Caching: REJECTED (`cache-audit-report.md`; upstream #753 agrees).
  - heretic-v2 TE: CLOSED. Artifacts deleted; hashes in `tev2/PROVENANCE-heretic-v2.json`; registry emptied.
- **Blind protocol:** `blind_stage.py` (prepare/freeze/unblind with hashes), `BLIND-PROTOCOL.md` (includes the earlier teab key-deletion incident record).
- **Registers:** `research/experiments/STATUS.md` (every experiment's status) and the backlog §Pass 3 frontier.

**Disclosed actions**
- Stopped the chain6 parent process to re-sequence runs.
- Changed the FakeRuntime pattern, which was too sparse at 1024² and tripped the blank-image check.
- Two failed harness attempts preserved (`memfix-console-attempt{1,2}-*`).

## 2026-09-24/25 — Pass 2: bf16 gate, step sweep, cache audit, VAE lifecycle, uncensoring (heretic v2)
- **bf16 gate PASSED:** 24 blinded pairs, 0 / 2 / 22; denoise ratio 0.70. Shipped as opt-in `precision: bf16`, with parity checked.
  - Evidence: `research/experiments/bf16-quality-report.md`, `bf16ab/`.
- **Step sweep 9→4:** `step-sweep-report.md`, `stepsweep/`.
- **VAE lifecycle:** `vae-lifecycle-report.md`.
- **Cache audit:** `cache-audit-report.md`, `audit/`.
- **Micro-opts:** `microopt-report.md` (mask=None: no gain in bf16).
- **E09 pruning proxy:** in `pruning-tmp-assessment.md`.
- **heretic-v2 TE (Tier 1):** converted to q4 with bit-exact validation; zero cost; no behavioural difference on borderline prompts (stock already renders them).
  - Evidence: `te-heretic-v2-report.md`, `tev2/`, `teab/`.
  - Later closed in Pass 3.
- **Upstream draft written:** `upstream-mflux-issue-DRAFT.md`, preserved with a correction header.
- **Content boundary agreed with the user:** no explicit content is authored or reviewed by Claude; minors are hard-blocked. `te_userfile_ab.py` + selftest exist, but the test was CLOSED, not run.

## 2026-09-24 — Pass 1: research, runtime bake-off, app build
- **Qwen-Image 2.1 on sd.cpp** researched and measured.
  - M5 Metal tensor bug #1990 → `GGML_METAL_TENSOR_DISABLE=1`.
  - Evidence: `research/REPORT.md`, `QWEN-BASELINE-20260924.md`.
- **Z-Image-Turbo** researched and compared: `Z-IMAGE-TURBO-REPORT.md`, `FINAL-M5-COMPARISON.md`.
- **MFLUX chosen as the production runtime:** `MFLUX-ZIMAGE-RESULTS.md`, `MFLUX-ZIMAGE-SUSTAINED-10RUN-RESULTS.md` (sustained fp32 ≈133.7 s wall; fanless Air throttles from ≈8.5 to ≈14 s/step).
- **photo-gen app built:** CLI, API, queue, SQLite, pixel hashing, integrity checks. Parity passed (`PHOTO-GEN-PARITY-20260924.md`).
- **Architecture addendum** ("own the chassis, OEM parts"): `COMPONENT-SOURCES.md`.
- **Paper research:** `research/papers/index.md` (27 papers), `PAPER-RESEARCH-MAP.md`, `z-image-architecture-map.md`, `EXPERIMENT-BACKLOG.md`.
- **Key early finding (E01/E02):** mflux runs the DiT stream in fp32; a bf16 stream is ≈1.41× faster.
