# Phase 4 index: lossless resume point (Qwen editing + image-task layer)

**Written 2026-10-07, after Phase 4 closed.** Git HEAD before this file: `aa6d8aa`, branch `main`, **9 commits ahead of `origin/main`, NOT pushed**. Tags v1/v2 untouched; no v3. **Nothing is running.**
Directive: "PHOTO-GEN PHASE 4: Add Qwen as the editing-capable backend and establish the unified image-task layer" (pasted by the user on 2026-10-06; §1–§33).

## 0. Start here (new session)
1. Read `CLAUDE.md` (project rules), then `MEMORY.md` (ledger: "Current state" block, then the 2026-10-06/07 entry), then this file.
2. Verify the machine state (about 1 min, no GPU):
   - `bin/photo-gen verify`: Z-Image; must be `"ok": true` with `hashed_now` 0.
   - `bin/photo-gen verify --edit`: edit backend; must be `"ok": true` (Python 3.12.14, mflux 0.21.0, MLX 0.32.2, 18 files).
   - Tests: `cd app/tests && PHOTOGEN_ROOT=../.. PYTHONPATH=..:. ../../mflux/.venv/bin/python3.12 -m unittest` must give **72 tests OK**.
3. Optional GPU spot checks:
   - Z-Image: `bin/photo-gen generate -p "a red apple on a wooden table, soft window light" --seed 42 --profile ultra --width 512 --height 512` → `6aa2b842…`.
   - Edit: `bin/photo-gen edit --image <E05 source path from research/editing/sources.json> -p "Change the background to a sunset beach" --seed 42 --output-resolution 512 --allow-experimental` → `bd548f1b…` (≈ 80–100 s).
4. Detailed reports:
   - `research/qwen/QWEN-SOURCE-AUDIT.md`: why this model/runtime; 10 discrepancies; licence.
   - `QWEN-EDITING-BASELINE.md`: memory/timing.
   - `QWEN-EDITING-QUALITY.md`: G0/G1 scores.
   - `QWEN-RUNTIME-COMPARISON.md`: mflux vs sd.cpp.
   - `INCIDENTS.md`.
   - `research/editing/README.md`: the benchmark protocol.

## 1. State snapshot
| area | state |
|---|---|
| **Z-Image production** | unchanged. REFERENCE fp32/9 and FAST bf16/8 (512/768/1024), BALANCED bf16/5 (1024 only), ULTRA bf16/4 (512 only); mflux 0.20.0 in `mflux/.venv`. Real regression through the refactored app all exact (§8). Cold BALANCED 35.6 s (recorded 36.1 s). |
| **Edit task** | **EXPERIMENTAL.** Qwen-Image-2.1 @ `d26bb61`, local q4 export, mflux 0.21.0 in `mflux-qwen/.venv`. Every edit `validated=false`; requests need `allow_experimental`. |
| **Gates** | G0 (capability/reliability): **CAPABLE at 512 and 1024**. G1 (runtime A/B vs sd.cpp): no quality separation; **mflux kept** on speed, memory and parity. No G2 (quality-equivalence) yet. |
| **Licence** | Qwen-Image-2.1 = **Qwen Research License, non-commercial** (research/evaluation only). The user accepted it for research use on 2026-10-06. Never commit or redistribute the weights. |
| **Pending from Phase 3** | BALANCED CLI check **closed** 2026-10-06: 1024² `befe1b3c` validated; 768² refused. |

## 2. Directive §33 success conditions
| # | condition | status | evidence |
|---|---|---|---|
| 1 | current Qwen editing implementations researched | ✅ | QWEN-SOURCE-AUDIT §3–§6 |
| 2 | checkpoint/runtime justified + documented | ✅ | audit §4, §7; RUNTIME-COMPARISON §3 |
| 3 | real local edit workflow | ✅ | 24 G0 edits + smoke + API check |
| 4 | runs safely on M5 16 GB | ✅ (tight at 1024) | BASELINE §4.3: 0 critical samples with the deferred DiT load; stock mflux was NOT safe |
| 5 | uses existing job infrastructure | ✅ | one JobManager, queue, store, GPU lock; API cancel verified (BASELINE §4.4) |
| 6 | unified task abstraction, not over-architected | ✅ | `app/photogen/tasks.py` (a 2-entry router) |
| 7 | Z-Image fully regression-tested | ✅ | 5 real hashes exact; golden sidecar test; cold timing equal |
| 8 | editing benchmark belongs to PHOTO-GEN | ✅ | `research/editing/` (model-independent) |
| 9 | Qwen limitations documented | ✅ | BASELINE §5, QUALITY, audit D5/D6/D8 |
| 10 | production vs experimental explicit | ✅ | `validated=false`, `allow_experimental`, docs badges, STATUS |

## 3. Decisions log
**User decisions:**
- **2026-10-06, licence:** accept Qwen-Image-2.1 for research use. The alternatives offered were "require Apache-2.0 only" and "try Edit-2511 anyway".
- **2026-10-06, acquisitions approved:**
  - the 33 GB checkpoint at the exact revision, with every hash verified;
  - a separate Qwen venv, keeping production mflux 0.20.0 untouched and choosing the version by actual compatibility;
  - the sd.cpp comparator TE + mmproj, which is the encoder only; the comparator also uses the existing 2.1 DiT GGUF + VAE.
- **2026-10-06 ~23:00, pause for a meeting:** background jobs were suspended with SIGSTOP and resumed later.
- **2026-10-07, benchmark conditions:** clean conditions (Teams, Brave, Slack closed; AC) for the GPU block.
- **2026-10-07 ~03:15:** the user asked "how much longer"; the full G1 plan was kept (no reply to the offer of a shorter G1).

**Engineering decisions (Improvement Clause):**
- MLX pinned to 0.32.2 (production's M5-verified build) instead of mflux 0.21.0's lock (0.32.0); everything else per mflux's own `uv.lock`.
- **Deferred DiT load** made the edit default: pixel-identical; the stock lifecycle hit critical pressure. Full record in BASELINE §3.
- G0 run at 512 first (memory safety), then 1024 with a cold baseline (directive §11).
- G1 bounded: 512 only, 4 tests, like-for-like 512 references. sd.cpp 1024 was not run (no memory headroom).
- Edit requests reject width/height, CFG, scheduler, masks, strength, multi-reference, LoRA, profile and precision (upstream defaults only).
- Inputs accepted as an absolute path (CLI resolves relative paths). No base64 upload.
- Every edit `validated=false`. No edit profiles.

## 4. Environments and assets (all gitignored except configs)
| item | path | identity | size | notes |
|---|---|---|---:|---|
| production venv | `mflux/.venv` | mflux 0.20.0, MLX 0.32.2, Py 3.12.14 | — | **never install 0.21.0 here** (it changes Z-Image hashes: #802/#803) |
| edit venv | `mflux-qwen/.venv` | mflux 0.21.0 (wheel sha256 `b2e38fd3…`), MLX/mlx-metal 0.32.2, torch 2.13.0, transformers 5.15.0 | 1.1 GB | lock `config/qwen-python-requirements.lock.txt`; constraints `config/qwen-venv-constraints.txt`; rebuild: `docs/REPRODUCIBILITY.md` §5 |
| edit export (canonical) | `models/qwen/qwen-image-2.1-edit-mflux-q4` | 18 files pinned in `config/backend-qwen21-edit-mflux.json` (manifest sha256 `536fba17e382b799…`) | 9.9 GiB (10.64 GB) | byte-identical across 2 exports |
| aborted export copy | `models/qwen/ABORTED-20261007T0005-…` | byte-identical to canonical | 9.9 GiB | **deletable with the user's OK** (incident 1) |
| official checkpoint | `models/research/qwen-image-2.1` | Qwen/Qwen-Image-2.1 @ d26bb61; 28 files vs `research/qwen/upstream-file-manifest.json` | 31 GiB | only needed to re-export; **deletable with the user's OK** |
| sd.cpp comparator TE | `models/text_encoders/Qwen3VL-8B-Instruct-Q4_K_M.gguf` + `mmproj-Qwen3VL-8B-Instruct-F16.gguf` | Qwen/Qwen3-VL-8B-Instruct-GGUF @ f982a07 (Apache-2.0); sha256 `67d1659b…`, `ca524100…` | 4.7 + 1.1 GiB | research only |
| sd.cpp | `sdcpp/master-908-88411ef/sd-cli` | as in the 09-24 baseline | — | comparator only |
| staged inputs | `data/inputs/<pixel_sha256>.png` | canonical RGB PNG | small | created by the app |
| disk | — | 177 GiB free (2026-10-07) | — | — |

## 5. Code map (`app/photogen`)
| file | role (Phase 4) |
|---|---|
| `tasks.py` | **new.** `TEXT_TO_IMAGE`/`IMAGE_EDIT` constants; `TaskRouter` (explicit table; `task_of()` defaults to text-to-image for old rows) |
| `inputs.py` | **new.** `stage_input_image()`: PNG/JPEG/WebP, ≤ 50 MB, 64–8192 px/side, ≤ 40 MP header check, EXIF transpose, opaque only (transparent rejected, opaque alpha dropped), ICC warn-only, canonical RGB PNG named by pixel sha256. `verify_staged()` re-checks before every run |
| `models.py` | `EditRequest` (task, prompt, width/height, steps, seed, seed_source, output_format, validated, input_image, output_resolution, warnings, output_name, profile, backend_id, model, model_revision); `GenerationRequest.from_dict` defaults the task |
| `runtimes/base.py` | `ImageRuntime` gains `task`, `name`, `request_from_dict()`, abstract `sidecar()` |
| `runtimes/mflux_zimage.py` | `task = text-to-image`; `sidecar()` and `_repro_cli` moved here **verbatim** from `jobs.py`; worker untouched |
| `runtimes/mflux_qwen_edit.py` | **new.** `MFluxQwenImageEditRuntime`: manifest loader, health (subprocess version probe of the edit venv + file hashes), `normalize()`, `generate()`, `sidecar()` (`photogen.edit/1`). Key constants: `ACCEPTED`/`REJECTED`, `DEFER_TRANSFORMER_LOAD = True`, `WORKER_TIMEOUT_SECONDS = 5400`, `output_dimensions()` (== mflux, tested), `_alpha_identity()`, `_worker_env()` |
| `runtimes/mflux_qwen_edit_worker.py` | **new.** Runs in the edit venv: probes (phases, step times, MLX peaks, active memory, libproc footprint), `_defer_transformer_load()`, calls mflux's edit CLI `main()` |
| `jobs.py` | `JobManager` takes a runtime **or** a `TaskRouter`; routes submit/execute by task; `runtime.sidecar()` |
| `service.py` | `edit_runtime`, `router`, `verify_edit()`, `require_edit_healthy(cached=)`, `tasks()`, `capabilities()`; `health()` gains `backends` (additive) |
| `api.py` | `POST /edit` (503 if edit unhealthy; task enforced); `/generate` is text-to-image only; `task` on jobs; `/capabilities` gains `tasks`; `serve` runs `verify_edit()` at startup |
| `cli.py` | `edit` subcommand; `verify --edit`; `_run_and_report()` shared by generate and edit; `jobs` tags non-t2i rows |
| `config.py` | `AppConfig.inputs_dir` (+ `ensure_dirs`) |
| tests | `app/tests/test_edit.py` (30 tests: Z-Image golden regression, router, staging, edit contract, mflux 0.21.0 dimension cross-check, jobs/queue/cancel, service/API, CLI, manifest pins, production-venv pin); `helpers.py` gains `FakeEditRuntime`, `edit_manifest()`, `make_image()`; fixture `app/tests/data/zimage-sidecar-golden.json` |
| config | `config/backend-qwen21-edit-mflux.json` (immutable manifest: runtime, model, 18 files, defaults, empty validated list, limits 384–1024 res, 2–60 steps); lock + constraints |

**Known code gap:** the SQLite `runtime` column is `mflux` for both tasks; the task lives in `request_json` (no schema migration).

## 6. Research map
**Benchmark (model-independent): `research/editing/`**
- `README.md`: protocol, rubric (adherence → preservation → composition → quality + text), gates G0/G1, storage policy.
- `suite-v1.json`: 11 tests (source prompt + seed, instruction + `instruction_source`, expected change and preserved elements, scope); `edit_parameters` seed 42, 40 steps.
- `sources.json`: 11/11 accepted at the first seed; `source-attempts.jsonl`, `gen-sources-1.log`.
- `regions.json`: change and preserve boxes, frozen before any edit.
- Scripts:
  - `gen_sources.py`: sources via `bin/photo-gen generate --profile reference`;
  - `edit_metrics.py`: outside-region MAE/PSNR/SSIM, inside MAE, Sobel structure corr; numpy + PIL;
  - `review_sheet.py`: source | output sheets.

**Qwen backend evidence: `research/qwen/`**
- **Reports:** the 4 `QWEN-*.md`, `INCIDENTS.md`, this file.
- **Acquisition:** `qwen-download.sh` (+ log), `upstream-file-manifest.json`, `verify_downloads.py`, `download-verification.json` (30/30 OK).
- **Export:** `export_q4.py`, `export-q4.sh` (abort thresholds: swap growth > 6144 MB or 20 s critical streak), `export/run1-aborted/`, `export/run2/`.
- **Harness: `run_edit.sh <run_id> <mode> <image> <res> <seed> <instruction> [steps]`.**
  - Modes:
    - `app`: `bin/photo-gen edit`;
    - `plain`: unmodified mflux CLI;
    - `worker0`/`worker1`: production worker via `worker_run.py`, defer off/on;
    - `sdcpp`: comparator.
  - 1 Hz monitor (`research/monitor.sh`), the same abort thresholds, git HEAD + dirty paths recorded.
  - Refuses to overwrite a run dir. The body is one function ending in `exit`.
- **Chains** (script → log, marker):

  | chain | script | log | marker |
  |---|---|---|---|
  | smoke 1 | `smoke-chain1.sh` | `smoke-chain1.log` | `SMOKE1_DONE` |
  | smoke 2 | `smoke-chain2.sh` / `smoke-chain2r2.sh` | `smoke-chain2.log` / `smoke-chain2r2.log` | `SMOKE2_DONE` |
  | G0 | `g0-launch.sh` (cooldown + cold BALANCED + `g0-chain.sh`, generated by `make_g0_chain.py`) | `g0-launch.log` | `G0_CHAIN_DONE` |
  | G1 | `g1-chain.sh` (generated by `g1_prepare.py`; refs in `g1/refs/`, `g1/refs.json`) | `g1-chain.log` | `G1_CHAIN_DONE` |
  | Z-Image regression | `zimage-regression.sh` | `zimage-regression.log` | `ZREG_DONE` |
  | API check | `api-check.sh` | `api-check.log` | `APICHECK_DONE` |

- **Run dirs:** `runs/<id>/{conditions.txt, monitor.csv, console.log, result.json | worker/…}`.
  - IDs: `S1-3`, `A0/A1/B0/B1` (failed r1) and `*r2`, `G0-512-E01…E11(+E05-repeat)`, `G0-1024-E01…E11(+E05-cold, E05-repeat)`, `G1-sdcpp-{SMOKE,E01,E05,E07,E11}`, `G1-mflux-E01-parity`.
  - Summaries: `summarize_runs.py <prefix>` → `g0-512-runs.json`, `g0-1024-runs.json`.
- **G0:** `g0/scores-{512,1024}.json` (frozen sha256 `0a80b2c2…`, `3d52f2ad…`), `g0/metrics-*.json`, `g0/review-*/` (PNG, gitignored).
- **G1:** `g1/pairs.json`, `g1/blind/` (MANIFEST, SCORES-FROZEN `957ef229…`, key `bac40ba3…`, now unblinded), `g1/scores-draft.txt`.
- **Z-Image regression:** `zimage-regression/`. **API check:** `api-check/`.

**Registers updated:** `research/experiments/STATUS.md` (Phase 4 table), `research/EXPERIMENT-BACKLOG.md` (Phase 4 addendum Q-G/Q-S/Q-M/Q-U/Q-C), `research/COMPONENT-SOURCES.md` (Phase 4 table).
**Docs updated:** README, `docs/photo-gen-guide.html` (Image editing section, CLI/API/arch/storage/limits/audit), HARDWARE, REPRODUCIBILITY §5, THIRD-PARTY-LICENSES §5, USAGE, RELEASE-NOTES (Unreleased), CLAUDE.md.

## 7. Key results (numbers to carry forward)
- **Memory (deferred DiT load, production):**
  - 512: peak 8.7–9.0 GB, MLX 7.85 GB, no swap growth.
  - 1024: peak 12.1–12.3 GB, MLX 11.0 GB (denoise), +1.3–2.1 GB swap per edit, warn episodes, **0 critical**.
  - Stock mflux (for comparison): 12.63 GB / 14.20 GB with critical episodes.
- **Timing:**
  - 1024 cold: **496.8 s** (encode 3.6 s + VAE enc 1.6 s + denoise 474.1 s + decode 12.8 s; 12.8 s/step median).
  - 1024 sustained median: 556 s.
  - 512 sustained median: 103 s (2.31 s/step).
  - Denoise is ≥ 93% of every edit.
- **G0:**
  - 512: 11/11 adherence; preservation 10 PASS + 1 PARTIAL (E08 oranges → pineapples); MINOR E05 (double sun / pasted light), E09 (daylight patches); 0 MAJOR.
  - 1024: 11/11 adherence and preservation; MINOR E05, E09; 0 MAJOR.
- **G1 (512, 4 pairs):** mflux 1 / sd.cpp 1 / 2 ties.
  - sd.cpp lost E01 on adherence (malformed car-motorcycle hybrid); mflux lost E05 on quality (double sun).
  - sd.cpp: 287–294 s per edit (≈ 3.3× the same-chain mflux control of 88.9 s; ≈ 2.8× the G0 median), 12.8 GB, critical samples in 3/5 runs.
- **Quality caveats:** one seed per test; rater = the AI assistant, non-blind in G0; weak blinding in G1 (mflux outputs seen in G0).

## 8. Reference hashes (pixel sha256 of decoded RGB; same machine and software)
**Z-Image (p01 "a red apple on a wooden table, soft window light", seed 42):**
- REFERENCE: 1024 `fe47d88d…`, 768 `94a023d3…`, 512 `9ae59f59…`.
- FAST: 1024 `7b45cfbe…`, 768 `20ff9e2c…`, 512 `0b9cc20a…`.
- bf16/9 1024 `11b19277…`; BALANCED 1024 `befe1b3c…`; ULTRA 512 `6aa2b842…`.

**Edit backend:**
- Smoke (BALANCED apple input `befe1b3c`, "Change the background to a sunset beach", seed 42):
  - 512 `f7aa22f650100d7858c16f6c67c487c81ee7f5b40803d9b7f9e0c105240f106a` (RGBA `49a202cb…`);
  - 1024 `10296d4bfd392bf0ede6720755e067295f948b4403410e8fee0a465baa5acc6d` (RGBA `76f60a78…`).
- G0, seed 42, 40 steps (16-char prefixes):

  | test | 512 | 1024 |
  |---|---|---|
  | E01 | `5c4f1eb61a2b64a1` | `1ec986d42e83feb6` |
  | E02 | `8e0f4c578c83fec5` | `759c2dc6ce4c9b11` |
  | E03 | `770f4b5994b66962` | `175340bf290a0323` |
  | E04 | `6f9ea288ef8b28a9` | `b5d84b56839ff9df` |
  | E05 | `bd548f1bf8cace9b` (also via API) | `792fdaa977a16567` |
  | E06 | `4d3aae5d786e4f5a` | `39bdb7bdc234c5ae` |
  | E07 | `f679c06035d8e979` | `15ac82403b9f2a30` |
  | E08 | `823f57f846568bd2` | `9886aeb1a7f6dc65` |
  | E09 | `bb6212472f9c1733` | `3275187a9f5768d7` |
  | E10 | `58f97b38c1afac9f` | `b224dc9581f75d71` |
  | E11 | `7ef095a2ad472033` | `d55f4c296f093297` |

- **Sources** (Z-Image REFERENCE 1024², seed): E01 1101 `59bb68cf1f04`, E02 1202 `8a762006289d`, E03 1303 `a28cfd672d6b`, E04 1404 `c5585a832690`, E05 1505 `8f55b71b446a`, E06 1606 `4f8c33dbadc4`, E07 1707 `345ea60a6e5b`, E08 1808 `79b0a959f410`, E09 1909 `dc1ba0cc87d4`, E10 2010 `ce3ca6e9f608`, E11 2111 `865373051583`.

## 9. Rules and gotchas learned this phase
- **Never install mflux 0.21.0 into `mflux/.venv`.** Never run Z-Image in `mflux-qwen/.venv`.
- **Never edit a script, `app/` or `config/` while a chain uses them.** `serve` re-reads the worker module for each job, and zsh reads scripts incrementally. Freeze chain scripts in a commit before launching.
- **Research harnesses bypass `data/gpu.lock`.** Run them strictly sequentially, and no photo-gen jobs meanwhile. Launch long chains as top-level `nohup zsh … & disown` with a marker.
- **Watchdogs must signal the real child.** `/usr/bin/time` wraps it: use `pkill -P`.
- **Memory benchmarks need clean conditions** (apps closed, AC). Report residual swap and *growth*, not absolutes. 1024 edits with large apps open add +3–4.5 GB of swap.
- **Speed claims must name their baseline** (same-chain control vs sustained median, cold vs sustained).
- **Score before metrics:** freeze score sheets (sha256 + `chmod a-w`) before computing any metric. Use `blind_stage.py` for A/Bs.
- **mflux Qwen-2.1 edit output is RGBA** (alpha 253–255 for opaque prompts). `pixel_sha256` covers RGB, and `output_alpha.rgba_sha256` is recorded alongside.
- **Edit dimensions:** `output_dimensions(R, ratio)` with multiples of 32 (Python banker's rounding), equal to mflux 0.21.0 (cross-checked in tests).
- **`.gitignore` gotchas:** the `data/` rule also matches `app/tests/data/` (now negated). Gitignore lines can't carry trailing comments. Stage paths explicitly.
- **mflux #831 (open):** `--scheduler` is ignored for edits. Don't build on the scheduler option until #835 ships.

## 10. Open items and next steps (nothing auto-starts)
**User decisions:**
1. **Push** the 9 (+1) commits to `origin/main`, via HTTPS with `-c credential.helper= -c credential.helper='!gh auth git-credential'`.
2. Whether this state gets a **`v3`** tag (it's under "Unreleased" in RELEASE-NOTES).
3. **Disk cleanup:** `models/research/qwen-image-2.1` (31 GiB) and `models/qwen/ABORTED-…` (9.9 GiB). Both need explicit OK. The earlier deferred cleanup of old sd.cpp/Qwen models and the uv cache is still deferred.
4. Whether to pursue production adoption of editing (needs Q-G; commercial use needs a different licence).

**Backlog** (`research/EXPERIMENT-BACKLOG.md`, Phase 4 addendum):

| # | item | first step |
|---|---|---|
| Q-G | production gate | pre-registered **blinded** G2, fresh sources and seeds, one fixed config (e.g. 512 vs 1024, or q4 vs q8 at 512) |
| Q-S | speed | survey few-step options with acquisition audits: Viggle turbo + LoRA, alibaba-pai Qwen-Image-2.1-Fun-Acc-LoRAs, mflux step cache |
| Q-M | 1024 memory | measure the 11.0 GB denoise split; a lifetime-only VAE release during denoise (pixel-parity candidate) |
| Q-U | one venv for both tasks | test whether 0.21.0 `--float32` reproduces REFERENCE `fe47d88d`/`9ae59f59` |
| Q-C | more capability | multi-ref, masks, RGBA; only on request |

**Phase 3 leftovers (from MEMORY):** an optional dedicated 6-step gate at 768²; resolution-aware step selection is not to be implemented yet.

**Small known gaps** (could be fixed cheaply):
- The SQLite `runtime` column doesn't distinguish tasks.
- No base64/multipart upload on `POST /edit` (path only).
- No progress streaming.

## 11. Phase 4 commits (oldest → newest)
- `c6c01a9`: pre-registration (benchmark v1, source audit, export, smoke evidence)
- `cf21eaa`: frozen sources and regions
- `5f89f4f`: task layer + edit backend (Z-Image unchanged; 72/72)
- `7dca169`: golden fixture tracked (gitignore fix)
- `a7cc451`: frozen G0 chain
- `2b55619`: frozen G1 chain
- `5abc42c`: G0/G1 results + reports
- `ac3105c`: docs + ledger
- `aa6d8aa`: closure: real API edit + cancel, edit job identity + manifest hash, baseline-named claims
