# Phase 5 index: lossless resume point (Qwen hardening + real-world G2)

**Directive:** "PHOTO-GEN PHASE 5: Harden Qwen editing, validate it on real photographs, and determine production readiness", pasted by the user on 2026-10-07 together with the addendum "QWEN SOURCE CHECKPOINT AND SPARE EXPORT DISPOSITION".

**User decisions (2026-10-07):**
- G2 sources: **CC0/PD only**, from Wikimedia Commons;
- G2 rater: a **fresh subagent** (provenance-blind);
- GPU blocks: **clean conditions** (heavy apps closed, AC).

_This file is updated as Phase 5 progresses; the live status is in §2._

## 0. Start here (new session)
1. Read `CLAUDE.md`, then `MEMORY.md` ("Current state" plus the 2026-10-07 Phase 5 entry), then this file.
2. Check what is running: `pgrep -fl "run_edit|mem-chain|g2-chain|mflux_qwen_edit_worker"`. Then the chain logs and markers (§3).
3. Verify the machine (no GPU):
   - `bin/photo-gen verify` and `bin/photo-gen verify --edit` must both be ok;
   - the tests (`cd app/tests && PHOTOGEN_ROOT=../.. PYTHONPATH=..:. ../../mflux/.venv/bin/python3.12 -m unittest`) must report **91 OK**.

## 1. Directive §31 success conditions
| # | condition | status | evidence |
|---|---|---|---|
| 1 | Phase 4 pushed; v3 immutable | ✅ | `origin/main` = `401e400`; annotated tag `photo-gen-m5-16gb-v3` (tag object `1c097eb`) → `401e400`, pushed |
| 2 | backend identity explicit | ✅ | `jobs.backend_id` column + migration (`app/photogen/store.py`); commit `51d4d6a` |
| 3 | authoritative identity stamped by the backend | ✅ | manifest-stamped identity; execute-time identity check; worker version check (`51d4d6a`) |
| 4 | Qwen memory lifetime investigated; exact safe improvement adopted | ✅ | `QWEN-MEMORY-LIFETIME.md`: P2 ADOPTED (5/5 criteria; 1024 peak −1.35 GB; exact parity); `a3a225c`, `973ef7f` |
| 5 | duplicate q4 storage cleaned | ✅ | `QWEN-ASSET-PROVENANCE.md` (deleted 10:20; +10.67 GB) |
| 6 | real-photograph benchmark exists | in progress | `research/editing/real-world/` |
| 7 | source provenance and licences recorded | in progress | `source-manifest.json` |
| 8 | G2 pre-registered | ✅ (committed before any source fetch) | `research/editing/real-world/protocol.md`, `task-manifest.json`, `selection.json` |
| 9 | evaluated at 512 and 1024 | pending | G2 chain |
| 10 | provenance-blind review | pending | `g2/` |
| 11 | VALIDATED / EXPERIMENTAL / REJECTED | pending | `results.md` |
| 12 | 1024 limitations documented | pending | `results.md` §memory class |
| 13 | docs match reality | pending | — |

## 2. Live status
- **10:33–11:48:** memory A/B chain (done; `MEMCHAIN_DONE`).
  - Preflight: Z-Image 5/5 exact; production edit `bd548f1b` exact.
  - Verdict **ADOPT** (`memory/ab-summary.json`); runtime switched in `973ef7f`.
  - Production-path re-check (`memory/postadopt/`): `bd548f1b` / `bdc03c36`, same `configuration_id` and `edit_id`, peak 8.91 → 8.17 GB at 512.
- **Next:**
  1. fetch the G2 sources (`fetch_sources.py`);
  2. check licences, regions and orientation; commit `source-manifest.json`;
  3. freeze the chain (`make_g2_chain.py > g2-chain.sh`, commit);
  4. run G2 (~4.5 h);
  5. score blind;
  6. analyze;
  7. docs.

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
