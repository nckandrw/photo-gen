# MEMORY.md — photo-gen work ledger

A lossless-resume ledger. Newest entry first. Each entry: date, what was done, where the evidence lives, current state, what's open. Update at the end of every working session (see CLAUDE.md § Memory ledger).

---

## Current state (snapshot, keep this block up to date)
- **Production:** unchanged by Phase 3 so far. photo-gen (`app/`), mflux 0.20.0 / MLX 0.32.2, Z-Image-Turbo q4 @ d2d30500, `--low-ram`.
  - Profiles: **reference** = fp32/9 (default, canonical); **fast** = bf16/8 (validated at 1024² via a *chain* of two gates; 512²/768² pending).
  - Transformer-release fix is ON. 39/39 tests pass (re-run 2026-09-25 14:40).
- **Regression hashes** (p01 apple, seed 42): 1024² reference `fe47d88d…`, fast `7b45cfbe…`, bf16/9 `11b19277…`; 512² reference `9ae59f59…`, bf16/9 `c70c38b0…`, bf16/8 `0b9cc20a…`; **768² reference `94a023d3…`, bf16/8 `20ff9e2c…`** (new).
- **Cold:** 1024² reference 83.4 s wall / fast 54.2 s; **768² reference 44.7 s / fast 30.6 s** (new); 512² reference 21.2 s / fast 15.0 s.
- **Docs:** `docs/photo-gen-guide.html` (self-contained guide); README links to it.
- **NOTHING RUNNING (stopped 2026-09-25 ~16:52 at user request, "stop all services").** Chain P3A was killed (SIGTERM to process group 16727) partway through G512: 39/48 jobs in `fastgate/results-512.jsonl`. The in-flight job `g512-p08-s8128-ref` has no result (partial `.mon.csv`/`.request.json` left in `work-512/`, not deleted). The API server was not running. `data/gpu.lock` is free. **To resume:** rerun `phase3-chainA.sh` (finished tags are skipped). The details below describe the state before the stop.
- **Previously RUNNING (background):**
  - **Chain P3A:** `research/experiments/phase3-chainA.sh`, console `phase3-chainA-console.log`, pid in `phase3-chainA.pid`, completion marker `PHASE3A_DONE` (intermediate `SIGMA_AB_DONE`, `GATE_<res>_GEN_DONE`). Resumable by rerunning the script (tags are skipped).
  - Sigma A/B is DONE and reviewed. The chain was paused 16:19–16:22 for guide validation (docval/, all 3 hashes exact), then relaunched; it is now generating gates G512 → G768 → G1024.
  - **Next:** review each gate (blind_stage) as its `GATE_<res>_GEN_DONE` appears; after `PHASE3A_DONE`, run `phase3-chainB.sh` (smoke-test the new scripts first). To stop the chain use `pkill -f phase3-chainA.sh` (the pid file may hold a wrapper).
- **Open items:** see the 2026-09-25 Phase 3 entry below.

---

## 2026-09-25 ~16:52: all photo-gen processes stopped (user directive)
- **Directive:** "close, end, stop all services or anything photo-gen wise that's consuming resources."
- **What was stopped:** the process group of `phase3-chainA.sh` (pid 16731): `prod_runner.py`, the worker, `monitor.sh` and the resource tracker. No API server was running.
- **Where it stopped:** G512 had 39/48 results. Last completed job: `g512-p08-s8128-fast` (16:52:06). The interrupted job `g512-p08-s8128-ref` is incomplete and its partial files were kept. G768, G1024 and Chain B have not run.
- **Open item:** rerun `phase3-chainA.sh` to resume.

---

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
