# MEMORY.md — photo-gen work ledger

A lossless-resume ledger. Newest entry first. Each entry: date, what was done, where the evidence lives, current state, what's open. Update at the end of every working session (see CLAUDE.md § Memory ledger).

---

## Current state (snapshot, keep this block up to date)
_Last updated 2026-09-29 10:10 (step-count gate Stage A running)._

**Production (unchanged since v2)**
- **Production = tag `photo-gen-m5-16gb-v2`** (commit `3961404`, verified from a clean clone 2026-09-28). mflux 0.20.0 / MLX 0.32.2, Z-Image-Turbo q4 @ d2d30500, `--low-ram`.
  - **Validated combinations** (`VALIDATED_COMBINATIONS` in `app/photogen/runtimes/mflux_zimage.py`): fp32+9 (REFERENCE) and bf16+8 (FAST) at 512², 768², 1024²; bf16+9 at 1024² only. Everything else needs `--allow-experimental`.
  - 40/40 tests. Transformer-release fix ON. MIT for photo-gen code (`LICENSE`); third-party licences in `docs/THIRD-PARTY-LICENSES.md`; `docs/RELEASE-NOTES.md` (v1 → v2).
- **Regression hashes** (p01 apple, seed 42):
  - 1024²: reference `fe47d88d`, fast `7b45cfbe`, bf16/9 `11b19277`.
  - 768²: reference `94a023d3`, fast `20ff9e2c`.
  - 512²: reference `9ae59f59`, fast `0b9cc20a`.

**Git**
- Private `nckandrw/photo-gen`, branch `main`. Tags v1 (`db10040`) and v2 (`3961404`) are immutable; never move them.
- Push over HTTPS: `git -c credential.helper= -c credential.helper='!gh auth git-credential' push origin main` (the SSH key isn't authorized on GitHub).
- Stage explicitly, never `git add .`.

**RUNNING (started 2026-09-29 10:09): step-count quality gate, Stage A (bf16/8 vs bf16/4)**
- Script `research/experiments/step-count-quality-gate/run-stageA.sh`; console `step-count-quality-gate/stageA-console.log`; marker **`STAGE_A_GEN_DONE`**.
- Stages: 6 cold runs (each after 600 s idle; done tags are skipped without re-idling), then sustained blocks 512 → 768 → 1024 (48 runs each).
- Results: `results-A-{cold,512,768,1024}.jsonl`. Expected ≈ 2.5 h.
- Resume: rerun the script as a top-level `nohup … & disown`. Done tags are skipped.
- Pre-registered: `step-count-quality-gate/protocol.md` (commit `f49604c`).
  - Seeds: A 2026/7331, B 6502/1729, C 8086/5150; confirmatory seed 4096 + `confirm-prompts.json`.
  - Blind dirs `blind-A512/768/1024` (rng 2909291/2/3); **keys sealed until all three are frozen**.
- The 4-step probe (REJECTED) is complete: `4step-probe/results.md`.

**Next steps (in order)**
1. After `STAGE_A_GEN_DONE`: integrity check; blinded review of the three resolutions, scoring each per `protocol.md` (lexicographic priority + failure-mode checklist); freeze all; unblind.
2. Metrics: paired denoise/wall ratios, cold pairs, memory, grid16, Laplacian. Verdict per resolution (VALIDATED / PROMISING / REJECTED / INCONCLUSIVE). Write `benchmark.csv`, `blind-mapping.json`, `scores.csv`, `results.md`.
3. Then Stage B (N = 5, seeds 6502/1729), then Stage C (N = 6, seeds 8086/5150). Create jobs mirroring Stage A.
4. If N = 4 passes at all three sizes: the confirmatory run (`confirm-prompts.json` × seed 4096 at 1024²).
5. Only after the gates: update STATUS, README, the guide and PERFORMANCE-MAP. **No production change inside the experiment.**

**Research assets (gitignored)**
- `models/research/z-image-base-mflux-q4` @ 087eaf40 and `models/research/loras/Z-Image-Fun-Lora-Distill-4-Steps-2603-ComfyUI.safetensors` @ f9a4db41.
- 15/15 files verified against HF digests (`4step-probe/asset-manifest.json`).
- `research/experiments/p3b/cap/*.gputrace` (≈16 GB) are summarized in `nax-status.md`. Delete them only with the user's OK.
- The user deferred any cleanup of old sd.cpp/Qwen models (≈15.5 GB) and the uv cache. Don't delete without being asked.

---

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
