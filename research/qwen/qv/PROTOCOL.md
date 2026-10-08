# Q-V diagnostic: does the Qwen VAE round trip itself garble incidental text? (Phase 7 pre-registration)

**Status.** This file was committed **before the pipeline-equivalence gate ran, before any Q-V round trip existed, and before anyone viewed a Q-V output.** So were the tools (`qv_roundtrip.py`, `qv_run.py`, `run_edit.sh` mode `qv:`, `make_qv_chain.py`, `qv_blind.py`, `analyze_qv.py`) and the metric boxes (`text-boxes.json`, drawn on the source photographs only). Before the commit, the harness was smoke-tested on a synthetic image only (no G2 item, no E05).

Nothing below is made stricter or looser after results are seen. Any deviation is a dated amendment with its reason. Local times are Asia/Manila (UTC+8; `date` prints "PST").

**Scope.** This is a causal diagnostic, **not a quality gate.** It cannot change:
- the G2 verdict (REJECTED at 512 and 1024) or its frozen scores;
- the Q-Q verdict (AGAINST) or its frozen scores;
- Qwen's status: research-only, `validated: false`, `--allow-experimental`, Qwen Research License non-commercial.

Nothing here creates a profile, a validated configuration or a production path.

## 1. Question and pre-registered interpretation
**Question.** Does the Qwen-Image-2.1 VAE round trip itself, at the edit pipeline's output budgets, materially degrade or garble incidental text in the real photographs that established the G2 rejection?

Q-Q weakened candidate 1 (q4 quantization). Q-V addresses candidates 2 (the VAE round trip) and 3 (the output budget/resolution); candidate 4 is "another pipeline interaction". The core path contains no DiT, no text encoder and no prompt.

**What the round trip is.**
- It is a **ceiling of the output path:** the image a DiT would produce if it copied the reference latents perfectly (§3).
- It is **not** an imitation of an edit: in a real edit the decoder sees regenerated latents.
- Therefore outcome A is worded "the output path imposes a ceiling", never "the edit's VAE garbles the text".

| outcome | meaning, worded in advance |
|---|---|
| **A: VAE-IMPLICATED** | The VAE/output path imposes a preservation ceiling. Raising DiT precision cannot by itself restore information the round trip already destroys. This does not prove which internal component (encoder, latent, decoder, tiling) is responsible. |
| **B: VAE-CLEARED** | The VAE round trip keeps the relevant text legible, so it does not explain the failure. The failure arises mainly when the editing model regenerates the image, or in another part of the pipeline. |
| **C: BUDGET-LIMITED** | At 1024 the VAE is acceptable, but at 512 the output path loses the relevant text. The report splits that loss into scaling loss (the text is already unreadable in the scaled input) and VAE loss. |
| **C: MIXED** | Some text survives and some doesn't, without meeting any rule above, or the result differs strongly by image. What remains unresolved is stated. |
| **INCONCLUSIVE** | A gate fails, the pipeline cannot be reproduced faithfully, or too little text is readable even in the scaled input at 1024 to judge the VAE. |

## 2. Evidence protected (checked 2026-10-08, before any Q-V step)
- **Git:** working tree clean; `main` = `56880d2` = `origin/main`; v3 = tag object `1c097eb` → `401e400`; v4 = tag object `1741179` → `33669eb` (local and remote).
- **Frozen hashes:** Q-Q `review/SCORES-FROZEN.csv` `bcef9aa3…` and `PREFERENCE-FROZEN.csv` `4c8d6f36…`; G2 `SCORES-FROZEN.csv` `f14deba4…`. All three match their manifests.
- **Assets** (`research/qwen/assets/qwen-assets-verification-phase7-pre-qv.json`): source checkpoint 87/87 files with the same sha256, size and inode as after Q-Q, and 28/28 match upstream; canonical q4 export 18/18.
- **No q8 export exists,** and none is created. The q4 export's VAE is the VAE Q-Q showed to be tensor-identical in q8.

## 3. What the edit pipeline does, and the harness path
The edit pipeline is mflux 0.21.0, `mflux/models/qwen21/variants/edit/qwen_image_21_edit.py` `generate_image` and `cli/qwen21_edit_generate.py`, run by the production worker with `--low-ram` and policy P2.
- **Reference image:**
  1. `open_oriented(path).convert("RGBA")`;
  2. resize to `QwenImage21LatentCreator.dimensions(output_resolution, w/h)` with LANCZOS. This is the same size as the output, a multiple of 32;
  3. `pixels = float32 / 127.5 − 1`, NCHW;
  4. `vae.encode(pixels)`: direct and untiled. It returns the latent **mean** (no sampling), normalised by `latents_mean`/`latents_std`;
  5. `pack_latents(…).astype(prompt_embeds.dtype)`, which is bf16 according to `ModelConfig.precision`. The equivalence gate confirms this empirically.
- **Output:**
  1. the DiT's output latents go through `unpack_latents(…).astype(float32)`;
  2. `VAEUtil.decode(vae, latents, tiling_config)`. Under `--low-ram`, MemorySaver sets `TilingConfig()`: 512-px decode tiles, overlap 8 latents × 16 px. The Qwen VAE does not opt out of implicit tiling;
  3. `ImageUtil.to_pil` gives RGBA.
  - MemorySaver also sets the MLX cache limit to 1 GB.
- **Harness, `qv_roundtrip.py roundtrip`:** the same functions in the same order, run on the staged G2 input at the given budget:
  1. preprocess;
  2. `vae.encode`;
  3. `pack_latents`, then `astype(bf16)`;
  4. `unpack_latents`, then `astype(fp32)`;
  5. tiled `VAEUtil.decode` with `TilingConfig()`;
  6. `to_pil`, giving `roundtrip.png` (RGBA).

  It also saves the scaled conditioning image as `input.png` (RGB; its alpha was 255 everywhere).
- **Variants**, computed in the same process from the same latent and reported **only as pixel differences, never rated:** fp32 latents (no bf16 cast), and untiled decode.
- **VAE:**
  - loaded alone from the canonical q4 export `models/qwen/qwen-image-2.1-edit-mflux-q4/vae/`, through mflux's own `Qwen21Initializer.load_components` with a vae-only weight definition. Production P2 reloads the decode VAE for every edit in exactly this way;
  - shard `vae/0.safetensors` sha256 `248d52c5…` (pinned in `config/backend-qwen21-edit-mflux.json`); fp32 weights;
  - `Qwen/Qwen-Image-2.1` @ `d26bb61`.
- **Software:** mflux 0.21.0, MLX / mlx-metal 0.32.2.
- **Environment:** the production worker's, built by `_worker_env`: `MLX_*`, `HF_*` and `PYTHON*` stripped, HF offline. The launcher is `qv_run.py`, and `run_edit.sh` mode `qv:` adds the 1 Hz monitor and the watchdog. The MLX cache limit is 1 GB, as under `--low-ram`.

## 4. Pipeline-equivalence gate (before any G2 item)
- **The run:** one real 3-step edit of the G0 source E05 (not a G2 item) at 512, seed 42, through the **production worker** (`photogen.runtimes.mflux_qwen_edit_worker.main`; q4 export; policy P2). Read-only hooks record:
  - `vae.encode`'s input pixels and output latent;
  - the dtype going into `unpack_latents`;
  - `VAEUtil.decode`'s input latent, its tiling config and its output.
- **Then, in the same process, the harness must:**
  1. reproduce the captured encode input from the staged E05 image, **bit for bit**;
  2. reproduce the captured encode output from that input, **bit for bit**;
  3. decode the captured decode-input latent to the captured decode output, **bit for bit**, with the harness's own tiling config;
  - the dtype going into `unpack_latents` must be `mlx.core.bfloat16`;
  - the tiling configs must be equal.
- **If any check fails,** the chain stops (`QV_CHAIN_STOPPED_GATE_FAILED`). A Discrepancy is recorded, no G2 item is run, and Q-V is INCONCLUSIVE until the cause is understood.

## 5. Items, runs, mechanical gates
- **Items:** the staged G2 inputs of **R02, R12 and R15** (`input_image.staged_path` in `research/qwen/runs/G2-<budget>-<task>/sidecar.json`), at **512 and 1024**. That makes 6 items.
- **Runs:** each item runs twice, in two fresh processes (`a` and `b`), giving 12 round trips: `research/qwen/runs/QV-<budget>-<task>-<a|b>/`. The order is the gate, then 512 (R02, R12, R15), then 1024; `make_qv_chain.py` generates it.
- **Mechanical gates** (`analyze_qv.py`; all must hold, otherwise the result is INCONCLUSIVE):
  - **source:** the staged pixel sha256 equals the G2 sidecar's `input_image.pixel_sha256`;
  - **geometry:** the round-trip size equals the G2 output size (sidecar width and height) for every item;
  - **VAE identity:** every run's `vae/0.safetensors` sha256 equals the manifest pin;
  - **determinism:** runs `a` and `b` are bit-identical in input, round trip (RGB `pixel_sha256` and RGBA identity) and both variants;
  - **equivalence:** §4 passed.
- **Conditions are recorded, not imposed.** Each run takes seconds and the verdict doesn't depend on swap, so there is no clean-conditions request. `conditions.txt` records the machine state.

## 6. Review (provenance-blind; panel order randomised)
**Sheets** (`qv_blind.py`): one per item, from run `a`; 6 in total. Three panels:
- **ORIGINAL:** the full-resolution staged source, downscaled to a long side of at most 2048 px and never upscaled. It is the ground truth for what the lettering says.
- **A and B:** the **scaled conditioning input** and the **VAE round trip**, both at their **native output pixel size** with no resampling. Their order per sheet comes from `random.Random(seed)`, and the key is sealed read-only before any sheet is rendered.
- **Improvement Clause:** the scaled-input panel is added beyond the directive's source-vs-round-trip pair. A source-vs-round-trip pair cannot tell scaling loss (the output budget) from VAE loss, which §3C of the directive asks for.
- This is **not an A/B model comparison,** and it is not called A/B blind.

**Rater:**
- A fresh subagent that reads only `research/qwen/qv/review/blind/`, with a neutral prompt ("two processed versions"; no mention of VAE, budget, hypothesis or Q-Q).
- It may crop at native resolution into a scratch directory outside the repository, and must not enlarge crops with smoothing. It appends rows as it goes.
- Format checks (`qv_blind.py check`) send back format-only corrections. The session assistant views no Q-V output before the freeze.
- The prompt is committed as `review/RATER-PROMPT.md`; the audit is done with `research/qwen/qq/rater_audit.py`.

**Disclosed limits:**
1. **The hypothesis has leaked.** The rater's harness may load `CLAUDE.md`, which already names "VAE round-trip ceiling test" as the next candidate. It isn't edited to hide that, and it gets no Q-V content until the freeze. The randomised panel order is what keeps the rater from knowing which panel is the round trip.
2. **Panel sizes reveal the budget.** Native-resolution inspection requires showing the real sizes.
3. **The wording is visible.** The text elements are `research/qwen/qq/qq_blind.py` `ELEMENTS` verbatim, by location only, and the rater reads the wording off ORIGINAL.

## 7. Scoring (per processed version, then per sheet)
- **Per text element**, against ORIGINAL:
  - **PRESERVED:** same wording, readable, the lettering looks like the original's;
  - **DEGRADED:** same wording, still correctly readable, but glyphs softened, deformed or partly missing;
  - **GARBLED:** no longer readable as the original's (wrong, invented or duplicated letters, gibberish, or unreadable where ORIGINAL is readable);
  - **REMOVED:** gone or replaced;
  - **NA:** unreadable in ORIGINAL too; set for both versions together.
  - **Decided now:** DEGRADED counts as **legible**. Material loss means GARBLED or REMOVED. DEGRADED is reported separately as softening.
- **`fidelity`**, for everything apart from the lettering: PASS / MINOR / MAJOR, with a family.
- **`text_preference`** per sheet: A, B or SAME.

## 8. Primary classification (within one rater; `analyze_qv.py`)
**Counts.** A unit is one (task, element, budget): R02 has 2 elements, R12 5, R15 5, so there are 12 units per budget. For budget b:
- **N_b:** units whose ORIGINAL is readable (not NA);
- **K_b:** units whose **scaled input** is legible;
- **L_b:** units in K_b whose **round trip** is GARBLED or REMOVED (VAE loss);
- **S_b:** units in N_b whose scaled input is not legible (scaling loss).

**Rules, applied in this order:**
1. **INCONCLUSIVE** if any gate (§4, §5) fails, or **K_1024 < 3**.
2. **VAE-IMPLICATED** if **L_1024 ≥ max(2, ⌈K_1024 / 2⌉)**: the round trip destroys at least half of the legible input text even at 1024.
3. **BUDGET-LIMITED** if **L_1024 ≤ 1**, and at 512 **S_512 + L_512 ≥ ⌈N_512 / 2⌉**: the 512 output path, scaling plus VAE, loses at least half of the readable original text. The split between S_512 and L_512 is reported.
4. **VAE-CLEARED** if **L_1024 ≤ 1 and L_512 ≤ 1**, and rule 3 does not apply.
5. **MIXED** otherwise.

**Reported with the class:**
- per-task L, so it shows whether the loss is concentrated in one image;
- softening counts (PRESERVED → DEGRADED);
- fidelity, and the paired preference.

## 9. Secondary cross-reference (cross-rater, descriptive)
- **The set E:** Q-Q's 19 core units that the **q4 edit** garbled, from the frozen `research/qwen/qq/qq-summary.json`. Each is followed through Q-V:
  - **scaling:** the Q-V scaled input is not legible;
  - **vae:** the input is legible but the round trip is not;
  - **regeneration:** the round trip is legible, so neither scaling nor the VAE explains the edit's garbling;
  - **na_in_qv:** the Q-V ORIGINAL is unreadable.
- **Caveats:**
  - This crosses raters.
  - Q-Q's "original" panel was already the scaled input. So E units were legible in the scaled input according to the Q-Q rater, and a "scaling" result here mostly reflects disagreement between the raters on borderline text.
  - It interprets, and never changes, the §8 class.

## 10. Descriptive metrics (computed only after the freeze; never override the visual verdict)
- **Whole image:** SSIM (7×7 box, grey), PSNR and MAE between `input.png` and `roundtrip.png`.
- **Per text box:** SSIM and MAE, using boxes fixed before any output existed (`text-boxes.json`).
- **Tracking check:** the median box SSIM is compared for units whose round trip is legible against those whose round trip was lost. That tests whether the metric follows the visual result; G2 showed that it may not.
- No automated metric gate is created.

## 11. Memory and time (descriptive)
- **Per run:**
  - from `identity.json`: VAE load, encode, decode and primary-total seconds, plus the total with variants;
  - the peak footprint (libproc lifetime max) and MLX peak, both after the primary round trip and at the end;
  - from `monitor.csv`: swap growth, warn-level and critical samples.
- **Gate run:** recorded the same way.
- This is not optimisation work.

## 12. Recommendation mapping (fixed now; nothing is implemented in Phase 7)
| class | report | smallest next step to recommend |
|---|---|---|
| VAE-IMPLICATED | the output path is a plausible preservation ceiling; further DiT precision work is unlikely to fix it by itself | a narrow check of whether a larger output budget (memory permitting) or a different decode setting (untiled) lifts the ceiling on the same items; else stop Qwen |
| VAE-CLEARED | the round trip does not explain the failure; it arises during regeneration/editing or elsewhere in the pipeline | the Q-A desk survey (alternative models that preserve real-photo text and fit 16 GB) becomes worthwhile; else stop Qwen editing work |
| BUDGET-LIMITED | at 1024 regeneration is the main problem, at 512 the budget path already loses the text | the same as VAE-CLEARED for ≥ 1024; state that 512 has a hard ceiling |
| MIXED / INCONCLUSIVE | state exactly what is unresolved | at most one targeted follow-up; no model replacement without a reason |

## 13. Storage, dependencies and what is not touched
- **Kept:**
  - the dense source checkpoint (RETAIN LOCALLY), which is not used by Q-V;
  - the canonical q4 export: only its VAE is read.
- **Not done:**
  - **no export is created, and the q8 export is not recreated;**
  - no change to G2 or Q-Q evidence, to `app/`, to `config/`, or to any production path.
- Q-V output PNGs are gitignored; their hashes are in the run records.
- **Dependabot:** the 4 open alerts on `config/qwen-python-requirements.lock.txt` (fsspec high; urllib3 one medium and two high) are documented in `docs/REPRODUCIBILITY.md` §5. The lock is **not** changed in Phase 7.

## 14. Outputs
- **`research/qwen/qv/`:**
  - this protocol and the tools;
  - `text-boxes.json`;
  - `qv-chain.sh` and its log;
  - `items.json`;
  - `review/`: `MANIFEST.json`, the sealed key, `blind/` (composites gitignored), the frozen sheets, `key-unblinded.json`, `RATER-PROMPT.md`, `RATER-REPORT.md`, `RATER-AUDIT.json`;
  - `qv-summary.json`.
- **Run records:** `research/qwen/runs/QVGATE-512-E05/` and `QV-*`.
- **Report:** `research/qwen/QWEN-QV-DIAGNOSTIC.md`.
- **Chronology kept distinct:**
  - G0: capability shown;
  - G2: real-world quality REJECTED;
  - Q-Q: q4 not supported as the primary cause;
  - Q-V: the VAE/output-budget investigation.
