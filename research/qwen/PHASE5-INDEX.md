# Phase 5 index: lossless resume point (Qwen hardening + real-world G2)

**Directive:** "PHOTO-GEN PHASE 5: Harden Qwen editing, validate it on real photographs, and determine production readiness", pasted by the user on 2026-10-07 together with the addendum "QWEN SOURCE CHECKPOINT AND SPARE EXPORT DISPOSITION".

**User decisions (2026-10-07):**
- G2 sources: **CC0/PD only**, from Wikimedia Commons;
- G2 rater: a **fresh subagent** (provenance-blind);
- GPU blocks: **clean conditions** (heavy apps closed, AC).

**Outcome: Phase 5 COMPLETE (2026-10-07; last Phase 5 commit `63c24a5` at 17:33:39 PST. *Correction (2026-10-08):* this line previously said "~18:30"). Qwen editing: G2 REJECTED at 512 and 1024; not promoted; research opt-in only. Source checkpoint: RETAIN LOCALLY. Nothing is running. Phase 5 commits are NOT pushed.**

## 0. Start here (new session)
1. Read `CLAUDE.md`, then `MEMORY.md` ("Current state" plus the 2026-10-07 Phase 5 entry), then this file.
2. Check what is running: `pgrep -fl "run_edit|mem-chain|g2-chain|mflux_qwen_edit_worker"`. Then the chain logs and markers (§3).
3. Verify the machine (no GPU):
   - `bin/photo-gen verify` and `bin/photo-gen verify --edit` must both be ok;
   - the tests (`cd app/tests && PHOTOGEN_ROOT=../.. PYTHONPATH=..:. ../../mflux/.venv/bin/python3.12 -m unittest`) must report **92 OK**.

## 1. Directive §31 success conditions
| # | condition | status | evidence |
|---|---|---|---|
| 1 | Phase 4 pushed; v3 immutable | ✅ | `origin/main` = `401e400`; annotated tag `photo-gen-m5-16gb-v3` (tag object `1c097eb`) → `401e400`, pushed |
| 2 | backend identity explicit | ✅ | `jobs.backend_id` column + migration (`app/photogen/store.py`); commit `51d4d6a` |
| 3 | authoritative identity stamped by the backend | ✅ | manifest-stamped identity; execute-time identity check; worker version check (`51d4d6a`) |
| 4 | Qwen memory lifetime investigated; exact safe improvement adopted | ✅ | `QWEN-MEMORY-LIFETIME.md`: P2 ADOPTED (5/5 criteria; 1024 peak −1.35 GB; exact parity); `a3a225c`, `973ef7f` |
| 5 | duplicate q4 storage cleaned | ✅ | `QWEN-ASSET-PROVENANCE.md` (deleted 10:20; +10.67 GB) |
| 6 | real-photograph benchmark exists | ✅ | `research/editing/real-world/` (16 sources, 16 tasks) |
| 7 | source provenance and licences recorded | ✅ | `source-manifest.json` (14 CC0, 2 PD; Commons SHA-1 verified) |
| 8 | G2 pre-registered | ✅ (committed before any source fetch) | `research/editing/real-world/protocol.md`, `task-manifest.json`, `selection.json` |
| 9 | evaluated at 512 and 1024 | ✅ | 45 edits, 12:11:05–16:45:07, 45/45 rc 0 (`benchmark.csv`, `research/qwen/runs/G2-*`) |
| 10 | provenance-blind review | ✅ | fresh-subagent rater; frozen `f14deba4…` before unblinding (`g2/`, `RATER-AUDIT.json`) |
| 11 | VALIDATED / EXPERIMENTAL / REJECTED | ✅ **REJECTED** (512 and 1024) | `results.md`, `results-summary.json` |
| 12 | 1024 limitations documented | ✅ MARGINAL (wall 592 s; 10.87 GB; swap ≤ 1.19 GB; 0 critical) | `results.md` §4, `docs/HARDWARE.md`, `PERFORMANCE-MAP.md` |
| 13 | docs match reality | ✅ | README, guide, HARDWARE, REPRODUCIBILITY, THIRD-PARTY-LICENSES, USAGE, RELEASE-NOTES, STATUS, PERFORMANCE-MAP, EXPERIMENT-BACKLOG, CLAUDE.md |

## 2. Live status
- **10:33–11:48:** memory A/B chain (done; `MEMCHAIN_DONE`).
  - Preflight: Z-Image 5/5 exact; production edit `bd548f1b` exact.
  - Verdict **ADOPT** (`memory/ab-summary.json`); runtime switched in `973ef7f`.
  - Production-path re-check (`memory/postadopt/`): `bd548f1b` / `bdc03c36`, same `configuration_id` and `edit_id`, peak 8.91 → 8.17 GB at 512.
- **~12:00–12:11:** G2 sources acquired (16 CC0/PD, `source-manifest.json`); committed with amendment 1 and the frozen chain in `f16e092` at 12:11:01. *Correction (2026-10-08):* this line previously said "~12:00–12:20", which would overlap the chain start.
  - Two Panasonic/Sony MPO camera JPEGs were rejected by photo-gen; the input fix is `e653122` (amendment 1 in `protocol.md`).
  - Regions and orientation were checked on the staged images.
- **12:11:05–16:45:07:** G2 chain at git `f16e092` (`G2_CHAIN_DONE`). 45/45 rc 0, no abort, 0 critical samples, all 5 repeats bit-identical. *Correction:* earlier versions of this file said "~12:25".
- **16:46:** `make_items.py` → 40 items; `g2_blind.py prepare`, seed 20261007, key `652bfa45…` sealed; amendment 2 committed (`cf96d4a`) before any output was viewed.
- **16:50:** `verify_assets.py` post-G2: source checkpoint and canonical export unchanged.
- **~16:50–17:12:** fresh-subagent rater. The audit shows it read only `g2/blind/` and its crops. Format checks passed; frozen 17:13 (`6577b09`).
- **17:13:** unblind → `analyze_g2.py` → **REJECTED at 512 and 1024**. Spot check after the freeze (descriptive): all 6 forcing text FAILs confirmed at native resolution.
- **17:23–17:34 (commit times):** `results.md`, `QWEN-EDITING-QUALITY.md` § G2, `QWEN-ASSET-PROVENANCE.md` §6 (`0ccc0b7`, 17:23:40); docs (`2007271`, 17:30:11); docs corrections (`d1dc2b7`, 17:33:30); this index (`63c24a5`, 17:33:39). *Correction (2026-10-08):* this line previously said "~17:30–18:30".
- **Open user decisions:**
  1. keep or remove the rejected edit task;
  2. Q-Q diagnostic (dense-weight export, `EXPERIMENT-BACKLOG.md`) or trigger the source-checkpoint DELETE;
  3. push the Phase 5 commits.

## 3. Chains (script → log, marker)
| chain | script | log | marker |
|---|---|---|---|
| memory A/B | `research/qwen/memory/mem-chain.sh` | `research/qwen/memory/mem-chain.log` | `MEMCHAIN_DONE` |
| G2 | `research/editing/real-world/g2-chain.sh` (from `make_g2_chain.py`) | `research/editing/real-world/g2-chain.log` | `G2_CHAIN_DONE` |

## 4. Commits (Phase 5)
- `0d15f49`: asset provenance + full verification (before deletion)
- `904b0c2`: duplicate export deleted; canonical export re-verified in full
- `51d4d6a`: backend identity, authoritative identity, configuration identity (tests 90/90)
- `6d95ada`: memory A/B pre-registration (worker patches default off, probes, frozen chain)
- `a3a225c`: memory A/B results (P2 passes 5/5)
- `973ef7f`: P2 adopted as the production default (tests 91/91)
- `8694119`: G2 pre-registration + post-adoption confirmation
- `e653122`: MPO camera-JPEG input fix (tests 92/92)
- `f16e092`: G2 sources + amendment 1 + frozen chain (the chain ran at this commit)
- `cf96d4a`: G2 run records + blind sheets + amendment 2 (before any output was scored)
- `6577b09`: rater scores frozen (before unblinding)
- `0ccc0b7`: G2 results (REJECTED), rater audit, sidecars, Qwen G2 section, source disposition RETAIN LOCALLY
- `2007271`: Phase 5 docs + ledger + this index
- `d1dc2b7`: docs corrections (adherence qualified to primary items; PARTIAL attribution; sustained-chain timing baseline; status wording)
- `63c24a5`: this index's final commit list and the open app-label item
- **Total: 15 Phase 5 commits after `401e400`** (`0d15f49` … `63c24a5`). *Correction (2026-10-08):* a chat summary at the close of Phase 5 said 13 and then 19; `git rev-list --count 401e400..63c24a5` is 15.
- **Open in the app (not changed; user decision):** `/capabilities` reports the edit task as `status: experimental`, and the job warning says "no edit configuration has passed a quality gate". Both are accurate, but neither names G2 REJECTED.
