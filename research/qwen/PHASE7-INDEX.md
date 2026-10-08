# Phase 7 index: lossless resume point (Q-V VAE round-trip ceiling test)

**Directive:** "PHOTO-GEN Phase 7 — Q-V VAE round-trip ceiling test and Qwen decision gate", pasted by the user on 2026-10-08.

**Times:** local, Asia/Manila (UTC+8). `date` prints "PST".

**Outcome: Phase 7 COMPLETE (2026-10-09). Q-V: MIXED** (pre-registered).
- Even a perfect copy of the reference latents, decoded exactly as the edit decodes, loses incidental text.
- At 512 it keeps **3/12** lettering elements legible: scaling alone loses 6, the VAE 4 of the remaining 6.
- At 1024 it keeps **7/12:** the VAE loses 3 of 10 legible-input elements, one per photo.
- **Recommendation (not implemented): stop Qwen-Image-2.1 editing work.** Run Q-A only if editing remains a goal, with a VAE round-trip entry screen.
- **Status unchanged:** G2 REJECTED, Q-Q AGAINST, research-only, `validated: false`.
- **Git:** commits are local, **not pushed, not tagged** (the directive did not authorise it). Nothing is running.

## 0. Start here (new session)
1. Read `CLAUDE.md`, then `MEMORY.md` ("Current state" and the 2026-10-08 Phase 7 entry), then this file. Earlier indexes: `PHASE6-INDEX.md`, `PHASE5-INDEX.md`, `PHASE4-INDEX.md`.
2. Check that nothing is running: `pgrep -fl "run_edit|chain|qv_run|qq_run|mflux_qwen_edit_worker"`.
3. Verify, without the GPU: `bin/photo-gen verify` and `verify --edit` must be ok; the tests must give **93 OK**.

## 1. The chronology (kept separate)
| step | phase | result | report |
|---|---|---|---|
| G0 | 4 | capability: CAPABLE at 512 and 1024 (synthetic sources) | `QWEN-EDITING-QUALITY.md` |
| G2 | 5 | real-photograph quality: **REJECTED** at 512 and 1024 (incidental text garbled; edit leakage) | `research/editing/real-world/results.md` |
| Q-Q | 6 | q8 against q4: **AGAINST**, so q4 is not supported as the primary cause | `QWEN-QQ-DIAGNOSTIC.md` |
| Q-V | 7 | VAE-only round trip: **MIXED**; the output path itself loses text (severely at 512, partly at 1024) | `QWEN-QV-DIAGNOSTIC.md` |

## 2. What was done (commit times)
1. **Checks** (before anything): tree clean; `main` = `56880d2` = origin; v3 `1c097eb` → `401e400`; v4 `1741179` → `33669eb`.
   - Frozen Q-Q (`bcef9aa3`, `4c8d6f36`) and G2 (`f14deba4`) sheets intact.
   - `assets/qwen-assets-verification-phase7-pre-qv.json`: source 87/87, q4 export 18/18.
   - No q8 export exists.
2. **Pre-registration** `a390bef` (2026-10-08 23:50:11): `research/qwen/qv/PROTOCOL.md`, with these tools:
   - `qv_roundtrip.py` (harness and equivalence gate);
   - `qv_run.py` (production worker environment);
   - `run_edit.sh` mode `qv:`;
   - `make_qv_chain.py` → `qv-chain.sh`;
   - `qv_blind.py`, `analyze_qv.py`;
   - `text-boxes.json` (drawn from the sources only).

   The Dependabot note went into `docs/REPRODUCIBILITY.md` §5.1.
3. **Chain** 23:50:16–23:55:48: the equivalence gate (`QVGATE-512-E05`), then 12 round trips (`QV-<budget>-<task>-<a|b>`). All rc 0; all gates passed (`0b2514d`).
4. **Rating:** rater prompt `6e527f0`; fresh-subagent rater; sheets frozen 2026-10-09 00:25:20 (`670642e`); unblinded and tallied (`f718359`); report and docs (closing commit).

## 3. Key evidence
- **Equivalence gate** (`runs/QVGATE-512-E05/worker/gate.json`): a real 3-step E05 edit at 512 through the production worker, with capture hooks.
  - The harness reproduced the edit's VAE encode input and output, and its decode output, bit for bit.
  - The latents going into `unpack` were bf16, and the tiling was identical.
- **Path:** RGBA → LANCZOS to `dimensions(budget, aspect)` → `/127.5 − 1` → `vae.encode` (mean; untiled) → pack → bf16 → unpack → fp32 → tiled `VAEUtil.decode` (`TilingConfig()`) → `to_pil`.
- **VAE:** `vae/0.safetensors` `248d52c5…` (the manifest pin), loaded with mflux's vae-only loader.
- **Gates:** source pixels = G2 (6/6); sizes = G2 outputs (6/6); VAE identity; a/b determinism, bit-identical (6/6).
- **Counts** (scaled input → round trip, 12 elements per budget):

  | budget | input P / D / G | round trip P / D / G |
  |---|---|---|
  | 512 | 4 / 2 / 6 | 2 / 1 / 9 |
  | 1024 | 9 / 1 / 2 | 4 / 3 / 5 |

  REMOVED and NA were 0 throughout. L₁₀₂₄ = 3 against the thresholds (≥ 5 implicated; ≤ 1 cleared or budget-limited), so the class is MIXED.
- **Blind preference:** the scaled input over the round trip on 6/6 sheets.
- **Cross-rater** (Q-Q's 19 edit-garbled units): 7 scaling, 6 VAE, 6 regeneration. At 512: 5 / 4 / 2; at 1024: 2 / 2 / 4.
- **Cost:** 512 takes 3.1 s at 5.2–6.0 GB; 1024 takes 12.7 s at 6.1–6.9 GB. The primary path had no critical sample.
- **Crops kept** (directive §11): `research/qwen/qv/review/rater-crops/` and `review/spot-check/` (PNGs gitignored; sha256 in `research/review-crops/MANIFEST.sha256`, which also preserves the G2 and Q-Q rater crops under `research/review-crops/`).
- **Budgets above 1024 were never tested.** Their impracticality is an extrapolation, and the stop recommendation does not rest on it: at 1024 a perfect copy already loses at least one legible element on every item.

## 4. Git
- **Phase 7 commits** after `56880d2`:
  - `a390bef` pre-registration;
  - `0b2514d` chain, gates and sheets;
  - `6e527f0` rater prompt;
  - `670642e` frozen sheets;
  - `f718359` unblinded tally;
  - `a257500` report, docs, this index, ledger;
  - `6981582` review crops preserved, and budgets > 1024 labelled as untested;
  - plus this commit-list update.
- **Not pushed, not tagged.** `origin/main` is still `56880d2`; v4 stays at `33669eb`.

## 5. Open decisions for the user
1. **Qwen-Image-2.1 editing:** stop the work, as recommended. Then choose whether to keep the task as a research opt-in or remove it (removal steps in `PHASE6-INDEX.md` §7).
2. **Q-A** (only if image editing is still a goal): a desk survey of alternative editing models that fit 16 GB.
   - Proposed entry screen: a candidate's VAE/conditioning round trip keeps the G2 text elements legible at a feasible budget, before any editing gate.
   - The Q-V harness and `qq_blind.ELEMENTS` generalise to that screen.
3. **The 33 GB source checkpoint:** Q-V didn't need it, and stopping Qwen work meets the DELETE trigger in `QWEN-ASSET-PROVENANCE.md` §6. Delete it, or keep it on your word.
4. **Push** the Phase 7 commits; decide on any tag.
5. **Dependabot** alerts on the edit venv: they are documented, and the lock is unchanged.
