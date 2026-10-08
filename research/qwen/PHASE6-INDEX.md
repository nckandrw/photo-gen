# Phase 6 index: lossless resume point (Phase 5 closeout, status hardening, Q-Q diagnostic, v4)

**Directive:** "PHOTO-GEN Phase 6 — Phase 5 closeout, Q-Q diagnostic, status hardening, and v4 release", pasted by the user on 2026-10-08.

**User decision (2026-10-08):** clean conditions for the GPU work (heavy apps closed, AC).

**Times:** all local, Asia/Manila (UTC+8). `date` prints "PST", meaning Philippine Standard Time; this applies to the Phase 5 records too.

**Outcome: Phase 6 COMPLETE (2026-10-08).**
- **Qwen editing:** still G2 REJECTED and research-only. The app now says so explicitly.
- **Q-Q diagnostic: AGAINST.** q8 weights don't fix the incidental-text failure, so q4 is not supported as the primary cause.
- **q8 export:** deleted after its identity was recorded.
- **Source checkpoint:** RETAIN LOCALLY, unchanged.
- **Git:** Phase 5 and Phase 6 are pushed, and v4 is tagged on the closing commit. Nothing is running.

## 0. Start here (new session)
1. Read `CLAUDE.md`, then `MEMORY.md` (the "Current state" block and the 2026-10-08 entry), then this file. `PHASE5-INDEX.md` is the one before it.
2. Check that nothing is running: `pgrep -fl "run_edit|qq-chain|qq_run|mflux_qwen_edit_worker"`.
3. Verify, without the GPU:
   - `bin/photo-gen verify` and `bin/photo-gen verify --edit` must both be ok;
   - the tests must report **93 OK**: `cd app/tests && PHOTOGEN_ROOT=../.. PYTHONPATH=..:. ../../mflux/.venv/bin/python3.12 -m unittest`.

## 1. Directive success conditions (§Success Conditions 1–15)
| # | condition | status | evidence |
|---|---|---|---|
| 1 | Phase 5 evidence unchanged | ✅ | `git diff 63c24a5..HEAD -- research/editing/real-world research/qwen/runs/G2-*` touches only the marked `.md` corrections; `SCORES-FROZEN.csv` still `f14deba4…` |
| 2 | three Phase 5 discrepancies corrected in a new commit | ✅ | `e7e0b61` (docs only, corrections marked in place) |
| 3 | the app says G2 REJECTED / research-only | ✅ | `a4f9d57`; §3 below |
| 4 | `validated: false` intact | ✅ | runtime unchanged in that respect; tests |
| 5 | Q-Q run as a narrow precision diagnostic | ✅ | `research/qwen/qq/PROTOCOL.md`; only the export changes |
| 6 | provenance, hashes, fixed variables, limitations | ✅ | `QWEN-QQ-DIAGNOSTIC.md` §1, §2, §5; `qq/export/merge-q8.json` |
| 7 | cautious conclusion | ✅ | "does not support q4 quantization as the primary cause in the tested cases" |
| 8 | dense source checkpoint intact | ✅ | re-verified 87/87 three times (`assets/qwen-assets-verification-phase6-*.json`) |
| 9 | no duplicate q4 export recreated | ✅ | gate E compared tensors in memory; no q4 file written |
| 10 | full tests pass | ✅ | 93/93 |
| 11 | history not rewritten | ✅ | fast-forward push; the Phase 5 range `401e400..63c24a5` is unchanged (15 commits) |
| 12 | Phase 5 and Phase 6 pushed normally | ✅ | §5 |
| 13 | v3 immutable at `401e400` | ✅ | `ls-remote`: v3 tag object `1c097eb` → `401e400` |
| 14 | v4 created and pushed at the final clean state | ✅ | annotated `photo-gen-m5-16gb-v4` → the closing commit |
| 15 | docs separate integration, capability, quality, production, licensing and research findings | ✅ | `/capabilities` `quality_status`; README; results.md §7; QWEN-QQ-DIAGNOSTIC.md §7 |

## 2. What was done, in order
1. **Checks** (before any change): clean tree; `origin/main` = `401e400`; v3 = tag object `1c097eb` → `401e400` (local and remote); 15 Phase 5 commits `0d15f49` … `63c24a5`.
2. **Corrections** (`e7e0b61`):
   - `results.md` R04 label "black olives";
   - criterion S counted as FAIL marks in `QWEN-EDITING-QUALITY.md`;
   - commit times instead of approximate times: amendment 1 12:11:01, amendment 2 16:49:21, provenance §6 17:23:40, Phase 5 close 17:33:39;
   - the PHASE5-INDEX commit list completed.
3. **Status labels** (`a4f9d57`): §3. `configuration_id` re-derived through the runtime for G2 R12 is unchanged (`3cd79615…`, `fffe8df3…`), and the worker is still `3094e942…`.
4. **Q-Q diagnostic** (08:40–11:36). The report is `research/qwen/QWEN-QQ-DIAGNOSTIC.md`.
   - **Pre-registration** `fea3872`; amendment 1 (export tool bug) `95b99ce`.
   - **Export:** gate E passed (the per-component loader reproduces every canonical q4 tensor); q8 export of 22 files, 18,460,980,668 bytes; gate V passed (VAE identical); export deterministic (`135decd`).
   - **Smoke** on E05: q8 runs at 1024 (13.6 GB peak, paging, 0 critical), so 1024 stayed in scope by the pre-registered rule. Chain frozen in `924bc96`.
   - **Chain** 08:51:44–11:04:18: 18/18 runs rc 0, no abort, 0 critical. Gate Q: 8/8 q4 runs bit-identical to G2. Gate D: q8 repeats identical (`f73c16c`).
   - **Review:** arm-blind paired review by a fresh subagent; sheets frozen 11:32 (`77f8a35`); unblinded and tallied (`f1f353e`); report `7fd3edc`.
   - **q8 export deleted** 11:36:42 (+18.5 GB; `f2ff5a6`).
5. **Z-Image check** before tagging, through the real CLI: REFERENCE 512² → `9ae59f59`, ULTRA 512² → `6aa2b842`, both exact (`research/qwen/qq/zimage-regression/`).
6. **Closing commit:** docs (STATUS, PERFORMANCE-MAP, EXPERIMENT-BACKLOG, QWEN-EDITING-QUALITY, RELEASE-NOTES v4, README, guide, REPRODUCIBILITY, THIRD-PARTY-LICENSES, CLAUDE.md), this index and the ledger. Then the push and the v4 tag.

## 3. Application status (what a user sees)
- **`/capabilities` and `/status`:** `tasks["image-edit"].status = "research-only"` (it was `"experimental"`), plus `tasks["image-edit"].quality_status`:
  - integration: validated;
  - capability: validated (G0 CAPABLE at 512 and 1024);
  - quality: G2 REJECTED at 512 and 1024 (small text elsewhere in the photo gets garbled; edits spread to similar or attached objects);
  - local_production: REJECTED;
  - availability: research/testing opt-in only (`allow_experimental=true` / `--allow-experimental`);
  - license: Qwen Research License, non-commercial research/evaluation only;
  - evidence: `research/editing/real-world/results.md`.
  - `text-to-image` stays `"production"`.
- **Job warning** (sidecar `warnings`; the CLI prints it to stderr): "image-edit (Qwen-Image-2.1) is RESEARCH-ONLY: REJECTED by the real-photograph quality gate G2 at 512 and 1024 (small text elsewhere in the photo gets garbled; edits spread to similar objects); not a production feature; Qwen Research License, non-commercial research/evaluation only".
- **Without the opt-in:** `invalid_request` with "image-edit is RESEARCH-ONLY: Qwen-Image-2.1 editing was REJECTED by the real-photograph quality gate G2 (research/editing/real-world/results.md); pass allow_experimental=true to run it for research/testing".
- **CLI:** the `edit` help and the `--allow-experimental` help name G2, and `photo-gen status` prints an `image-edit:` line.
- **Unchanged:**
  - `validated: false`;
  - no profile;
  - the immutable manifest (`status: experimental`; its sha256 feeds `configuration_id`);
  - `memory_profile.status` and the sidecar `backend_status`, which are registration fields.

## 4. Q-Q result (one paragraph)
**Core items:** R02, R12 and R15 at G2's primary seeds, at 512 and 1024; 23 assessable text elements.
- **Rescue:** q4 garbled 19 of them. q8 rescued **1** (the small word on R15's shop sign at 512) and worsened 0.
- **Text FAIL:** 6/6 in both arms. Adherence, preservation, composition and quality are identical between arms.
- **Blind paired preference:** q8 3, q4 0, SAME 3 on the core sheets. On the supplementary R12 second seed: q8 2/2, 0 rescued.
- **Class: AGAINST** (pre-registered). It rests on R ≤ 1. A post-freeze, unblinded look found one more candidate (R15-512 window banner, first line). That is not counted, and no G2 outcome changes either way.
- **Cost of q8** (same chain):
  - 512: 133 s against 104 s, 12.0 GB against 8.2 GB, swap +1.9 GB;
  - 1024: 810 s against 570 s, 13.8 GB against 10.9 GB, swap +3.1 GB, pressure at warn level in 76% of samples, 0 critical.
- **Inter-rater:** the new rater agreed with G2 on all 8 q4 items, whose pixels are identical.
- **Next question (not started):** a VAE round-trip ceiling test (backlog Q-V), or Q-A (an alternative model).

## 5. Git
- **Phase 5:** 15 commits, `0d15f49` … `63c24a5`, unchanged.
- **Phase 6:** 13 commits, `e7e0b61` … the closing commit:
  - `e7e0b61` Phase 5 corrections;
  - `a4f9d57` status labels;
  - `fea3872` Q-Q pre-registration and tools;
  - `95b99ce` amendment 1 and gate E;
  - `135decd` q8 export recorded;
  - `924bc96` smoke and frozen chain;
  - `881c318` ledger (chain in flight);
  - `f73c16c` chain, gates and sheets;
  - `77f8a35` sheets frozen;
  - `f1f353e` unblinded tally;
  - `7fd3edc` report;
  - `f2ff5a6` q8 deleted;
  - the closing commit, tagged v4.
- **Push:** fast-forward of `main` from `401e400`, no force.
- **Tags:** v3 unchanged (`1c097eb` → `401e400`); v4 annotated on the closing commit.

## 6. Open decisions for the user
1. **Source checkpoint (33.1 GB):** Q-Q, the reason given for retaining it, has now been run. Keep it (bf16 and dense-weight research stay possible) or trigger DELETE. The model can be re-acquired exactly (`QWEN-ASSET-PROVENANCE.md` §6–§7).
2. **Phase 7:** the VAE round-trip ceiling test (Q-V), and/or a desk survey of alternative editing models (Q-A). Or stop investing in editing.
3. **The edit task:** it stays as research-only. Removing it remains your call.
