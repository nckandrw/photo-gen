# Phase 8 index: lossless resume point (Q-VR reference-runtime validation + Q-A desk survey)

**Directive:** "PHOTO-GEN Phase 8 — Qwen VAE Runtime Verification, Failure Attribution, and Future Editing Research",
pasted by the user on 2026-10-09.

**Times:** local, Asia/Manila (UTC+8). `date` prints "PST".

**Outcome: Phase 8 COMPLETE (2026-10-09).**
- **Q-VR: RUNTIME-MATCHED** (pre-registered): the MLX VAE path matches the official Diffusers CPU reference.
  - The residual 0.14–0.19/255 is MLX's TF32 default; it is pixel-equivalent with TF32 off.
  - In the blind review, 24/24 text calls are identical.
  - **Q-V's MIXED stands, and is now runtime-independent.**
- **Texture-Fix decoder:** no text rescue; 0.3–0.7 dB further from the scaled input.
- **Identity edit (R15-512, n = 1):** extra loss beyond the output-path ceiling (1 clear + 1 borderline element),
  fidelity MAJOR.
- **Compositing (n = 1):** with G2's box, it keeps the text but fails on mask coverage. With a conservative,
  feathered whole-van mask (CMP2, post-hoc) it is **viable**: edit PASS, both signs PRESERVED, seam and realism MINOR.
- **Q-A:** desk survey done. Shortlist: FLUX.2 [klein] 4B first, via a VAE round-trip entry screen.
- **Recommendation:** stop Qwen-Image-2.1-focused work and redirect to the FLUX.2 [klein] 4B VAE entry screen.
- **Status unchanged:** G2 REJECTED, Q-Q AGAINST, Q-V MIXED, research-only, `validated: false`.
- **Git:** the Phase 7 commits were pushed (`56880d2..817a7c2`). **The Phase 8 commits are local, not pushed; there
  is no v5 tag.**

## 0. Start here (new session)
1. Read `CLAUDE.md`, then `MEMORY.md` ("Current state" and the Phase 8 entry), then this file. Earlier indexes:
   `PHASE7-INDEX.md` … `PHASE4-INDEX.md`.
2. Check that nothing is running: `pgrep -fl "run_edit|qvr-|mlx_side|ref_side|mflux_qwen_edit_worker"`.
3. Verify without the GPU:
   - `bin/photo-gen verify` and `verify --edit` must be ok;
   - the tests must give **93 OK**;
   - `research/qwen/assets/qwen-assets-verification-phase8-post.json` is the latest asset record.

## 1. Chronology (kept separate)
| step | phase | result | report |
|---|---|---|---|
| G0 | 4 | CAPABLE (synthetic) | `QWEN-EDITING-QUALITY.md` |
| G2 | 5 | **REJECTED** at 512 and 1024 | `research/editing/real-world/results.md` |
| Q-Q | 6 | **AGAINST** (q4 not the primary cause) | `QWEN-QQ-DIAGNOSTIC.md` |
| Q-V | 7 | **MIXED** (the output path itself loses text) | `QWEN-QV-DIAGNOSTIC.md` |
| Q-VR | 8 | **RUNTIME-MATCHED** (the loss is not an MLX artefact) | `QWEN-QVR-REFERENCE.md` |
| Q-A | 8 | desk survey; FLUX.2 [klein] 4B first | `research/editing/QA-ALTERNATIVE-MODELS.md` |

## 2. What was done (commits, in order)
1. **Preflight and push.** Checks passed. The Phase 7 commits were **9**, not the directive's 8: `817a7c2` is a
   docs-only resume aid. They were pushed as a fast-forward with no force.
   - Asset record: `qwen-assets-verification-phase8-pre.json`.
   - §6 count audit: `qv-reference/phase7-transitions.md`. 512: 6 − 4 + 1 reversal = 3. Clarified in place
     (`3c0a07f`).
2. **Pre-registration** `ec5b04f`: `qv-reference/PROTOCOL.md` and `glyph-heights.json`.
3. **Tools, lock and amendment 1** (banded CPU convolution) `db190f8`. Chain `qvr-chain.sh` → `qvr-chain.log`:
   23 steps rc 0, no abort, at `134a618`.
4. **Post-hoc MPS diagnostic and Texture-Fix acquisition audit:** `b00846d`.
5. **Conditional arms:** `qvr-cond-chain.sh` stopped on a tool bug; `qvr-cond-chain-r2.sh` succeeded (`819a1c9`).
6. **Review:** prepared and prompt committed (`cd2f8a6`); fresh rater; frozen `bd94220`; unblinded and tallied
   (`3294fd2`).
7. **Amendment 2 (CMP2):** `822fa77`, with its own one-sheet review. Closing checks: `dd423b2`. Report, docs, this
   index: the closing commit.

## 3. Key evidence
- `qv-reference/qvr-summary.json`: gates, tiers, A1T attribution, review tallies, TF/ID/CMP numerics, probes.
- `qv-reference/runs/`:
  - `GATE-weights` (238/238);
  - `PROBE-mlx` (28 pad calls and 12 AvgDown sites, bit-exact);
  - `PROBE-mps` and `PROBE-mps-upstream` (the defect does not reproduce on torch 2.14.0 / macOS 27.0.1);
  - `GATE-conv`;
  - `A1/A2/A1T-<b>-<t>`, `A2b-512-R12`;
  - `TF-*`, `TF-weights`;
  - `CMP-1024-R02`, `CMP2-1024-R02`;
  - `FAILED-*` (tool-bug incidents, kept).
- `research/qwen/runs/QVR-ID-512-R15/`: the identity probe (app path).
- `qv-reference/review/` and `review-cmp2/`: sealed keys, frozen sheets, rater prompts, audits.
  - The crops are under `review/rater-crops/` (PNGs gitignored; sha256 in `research/review-crops/MANIFEST.sha256`).
- `qv-reference/glyph-strata.md`: per-element calls with glyph-height bins.
- CPU reference venv: `torch-ref/` (gitignored). Lock: `qv-reference/requirements.lock.txt`.

## 4. Discrepancies surfaced (not silently reconciled)
- Phase 7 had 9 commits, not 8.
- The Q-V 512 headline prose omitted one reversal; the figures were correct. Clarified in place.
- mflux 0.21.0's text-to-image `Qwen21VAE()` uses hard-coded latent mean/std that differ from the checkpoint config
  at 11/128 values. The edit path uses the config (gate-proven). Not filed upstream.
- The PyTorch-MPS defect does **not** reproduce on this machine; the third-party reports were on macOS 15.8/26.x.
- The machine runs **macOS 27.0.1** (since 2026-09-29) while `docs/HARDWARE.md` said 27.0. A note was added there,
  and the validated-target statement is unchanged.
- The §8.3 composite used G2's box instead of a conservative manual mask: an undeclared deviation, corrected by
  amendment 2 (post-hoc).
- The rater revised its own draft via a helper script outside its permitted directories (three D0 calls; no effect
  on the A1/A2, TF or ID tallies).

## 5. Open decisions for the user
1. **Stop Qwen-Image-2.1-focused work** (recommended). Then decide whether to keep the research-only edit task or
   remove it (`PHASE6-INDEX.md` §7).
2. **Q-A step 1:** the FLUX.2 [klein] 4B VAE round-trip entry screen. It needs an acquisition audit and the VAE file
   only (~160 MB).
3. **Assets:**
   - Texture-Fix VAE (1.35 GB): its deletion trigger is met; it is kept pending your word.
   - The 33 GB Qwen source checkpoint: RETAIN LOCALLY. Its DELETE trigger fires if Qwen work stops.
4. **Push the Phase 8 commits** (not authorised by the directive) and **v5:** not recommended; no production or
   validated change.
5. **`docs/HARDWARE.md`:** restate the validated target as 27.0.1, or keep 27.0 with the note.
6. Dependabot alerts on the edit-venv lock: unchanged. The new `torch-ref` venv uses the patched fsspec 2026.9.0 and
   urllib3 2.8.0.

## 6. How to start the recommended next step (not started)
**FLUX.2 [klein] 4B VAE entry screen.**
1. Write an acquisition audit for `black-forest-labs/FLUX.2-klein-4B` @ `e7b7dc27f9`, covering the VAE files only
   (licence Apache-2.0).
2. Pre-register:
   - the round trip of the staged G2 sources R02/R12/R15, at the budgets the editor would use;
   - D0, against a round trip through mflux 0.21.0's `flux2_vae`, in the existing edit venv (the installed mflux
     already supports FLUX.2);
   - an equivalence gate against the real `Flux2KleinEdit` path, on a non-G2 input;
   - the pass bar, fixed in advance. For example, the round trip keeps legible every element D0 keeps at 1024.
3. Reuse `qv-reference/qvr_blind.py`, the fresh-rater mechanics and `analyze`-style mechanical tallies.
4. Only if it passes: a G2-style editing gate (`research/editing/real-world/`).
