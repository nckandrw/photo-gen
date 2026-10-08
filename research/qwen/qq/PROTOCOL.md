# Q-Q diagnostic: does higher weight precision reduce incidental-text garbling? (Phase 6 pre-registration)

**Status.** This file, the export tool (`export_q8_split.py`, `export-q8.sh`, `merge_q8.py`), the run harness (`qq_run.py`, `run_edit.sh` mode `qq:`), the chain generator (`make_qq_chain.py`), the review tool (`qq_blind.py`) and the tally (`analyze_qq.py`) were committed **before the q8 export existed, before any q8 edit ran and before anyone viewed a Q-Q output.** Nothing below is made stricter or looser after results are seen; any deviation is a dated amendment with its reason.

**Scope.** This is a diagnostic, not a gate. It cannot change the G2 verdict (REJECTED at 512 and 1024, `research/editing/real-world/results.md`), the frozen G2 scores, or Qwen's status. Whatever the outcome, no precision becomes a production default here (directive §12).

## 1. Question and hypotheses
G2 rejected the q4 configuration mainly on failure mode (a). Small incidental text elsewhere in the photo is re-synthesized and garbled: R02, R12 and R15 failed text on all 8 text-preservation items (`results.md` §3). Phase 5 listed four candidate causes (`QWEN-ASSET-PROVENANCE.md` §6):
1. q4 quantization of the DiT and/or the Qwen3-VL encoder;
2. the fp32 VAE round trip;
3. the output budget;
4. another interaction in the editing pipeline.

**This diagnostic tests only candidate 1:** does raising the weight precision, with everything else fixed, materially improve the preservation of incidental text?
- **H1 (q4 implicated):** with q8 weights, text that q4 garbles is preserved legibly, repeatably across tasks and budgets.
- **H0 (q4 not the primary cause):** q8 garbles essentially the same text.

**Not separable here.** We cannot isolate DiT precision from text-encoder precision. mflux 0.21.0 refuses checkpoints whose components use different bit widths: `Qwen21Initializer.load_components` raises "Conflicting component quantization levels". Mixing them would need patching mflux's loader. That is out of scope, and it would add a second change.

## 2. Arms (the only intended variable is the weight representation)
| arm | export | weights |
|---|---|---|
| **q4** | `models/qwen/qwen-image-2.1-edit-mflux-q4`: canonical, manifest-pinned (`config/backend-qwen21-edit-mflux.json`); re-verified 18/18 on 2026-10-08 | MLX affine 4-bit, group size 64, on the DiT and on the Qwen3-VL text/vision encoder including `lm_head`; VAE fp32 |
| **q8** | `models/research/qwen-image-2.1-edit-mflux-q8`: research only, gitignored, built in this phase (§3) | MLX affine **8-bit**, group size 64 (the mflux default), on the same layers; VAE fp32 |

- **Same source for both arms:** `models/research/qwen-image-2.1`, `Qwen/Qwen-Image-2.1` @ `d26bb61`. Re-verified on 2026-10-08 before any Q-Q step: 87/87 files have the same sha256, size and inode as the post-G2 record, and 28/28 match the upstream manifest (`research/qwen/assets/qwen-assets-verification-phase6-pre-qq.json`).
- **Same tools for both arms:** the mflux 0.21.0 API, the edit venv and its lock.
- **Expected q8 sizes,** from the q4 export's tensor headers (q8 doubles the packed weight bytes; scales and biases are unchanged): DiT 7.66 GB, text encoder 9.44 GB (its `lm_head` stays lazy at load), VAE 1.35 GB; about 18.4 GB in total.
- **Fixed for both arms:**
  - the staged G2 input photographs (by pixel sha256), instructions, seeds and `output_resolution` (and therefore the output dimensions);
  - mflux 0.21.0 and MLX 0.32.2 in `mflux-qwen/.venv`, entry point `mflux-generate-qwen-2.1-edit` `main()` unmodified;
  - 40 steps, guidance 1.0, prefix KV cache, linear schedule, `--low-ram`;
  - the production worker `app/photogen/runtimes/mflux_qwen_edit_worker.py` (sha256 `3094e942…`) with the adopted memory policy P2;
  - **the same VAE:** its tensors must be identical between the two exports (gate V);
  - output handling: the worker's PNG, RGB `pixel_sha256` and RGBA sha256.
- **Harness:** both arms run through `research/qwen/qq/qq_run.py` under `research/qwen/run_edit.sh` mode `qq:<arm>` (1 Hz monitor; same abort thresholds as G2).
  - This is the production worker run directly, as the Phase 5 memory A/B did with `mem_run.py`, whose P2 outputs reproduced the production path's pixels exactly. The only difference between arms is `model_path`.
  - It is **not** `bin/photo-gen edit`: the production runtime pins the q4 export by manifest and correctly refuses any other model. Gate Q (§5) checks equivalence with G2 instead.

## 3. Building the q8 export (`export-q8.sh`)
Why per component: mflux's documented export, `QwenImage21Edit(quantize=N, model_path=src).save_model(dst)`, materializes all three components before writing. At q8 that is about 18.4 GB, more than this machine holds.

`export_q8_split.py` narrows `QwenImage21WeightDefinition.get_components` in-process to a subset. The **same** mflux code then (`QwenImage21Initializer` → `Qwen21Initializer.load_components` → `ModelSaver.save_model`) loads, quantizes and writes only that subset. The components left out are set to `None`, so their lazily initialized random weights are never evaluated or written.

**Steps, in order.** Each runs in its own process under the monitor and watchdog, and the chain stops at the first failure.
1. `qerr` on the transformer and on the text encoder, sampling every 8th quantizable 2-D weight. This is the relative RMS error of 4-bit and 8-bit affine quantization against the dense bf16 weights. It shows how far q8 is from q4 (directive §4.2: "materially different").
2. **Gate E (procedure equivalence), on q4:** the subset loader at `quantize=4`, run once for vae + transformer and once for text_encoder, must reproduce **every** tensor of the canonical q4 export (dtype, shape, `mx.array_equal`).
   - It is compared in memory, shard by shard. **No q4 file is written,** so the deleted duplicate is not recreated.
   - If any tensor differs, stop. This is a Discrepancy, and no q8 edit runs.
3. Export at 8 bits: vae + transformer into one staging part, text_encoder into the other.
4. `merge_q8.py` assembles the export:
   - shared files (processor, scheduler, `model_index.json`, configs) must be byte-identical between the two parts, and are compared with q4's;
   - the directories are renamed into the final export (no copies);
   - it records sha256 and size for every file, plus every shard's metadata;
   - **Gate V:** the q8 VAE tensors must be byte-identical to the q4 VAE tensors. The file bytes differ only through the `quantization_level` metadata.
   - Leftover part files are removed only after each one is shown identical to the file that was kept.
5. Re-run `verify_assets.py`: the source checkpoint and the canonical q4 export must be unchanged.

## 4. Items, runs and order
- **Core, 6 pairs:** R02, R12 and R15 with their G2 primary seeds (2510702, 2510712, 2510715), at 512 and 1024. These are the six text FAILs that by themselves establish the G2 rejection.
- **Supplementary, 2 pairs:** R12's second seed 2520712, at 512 and 1024. G2 also failed text there; it tests whether an effect repeats across seeds.
- **Determinism:** one q8 repeat of R12 primary per budget.
- **Order** (`make_qq_chain.py`; identical in both blocks, arms balanced over positions):
  1. R02 q4, R02 q8
  2. R12 q8, R12 q4
  3. R15 q4, R15 q8
  4. R12-s2 q8, R12-s2 q4
  5. R12 q8 repeat
- **Timing of the chain:** 20 s between runs; the 512 block, then a 120 s cooldown, then the 1024 block. That is 18 runs in one chain, in clean conditions (heavy apps closed, AC; the user confirmed on 2026-10-08).
- **Feasibility smoke before the chain is frozen.** It uses the G0 source E05, not a G2 item, and is not evidence. It runs as `QQSMOKE-*`:
  - q8 at 512 with 40 steps;
  - q8 at 1024 with 3 steps (denoise is the binding phase at 1024, and its peak comes at step 0, when the DiT is read).
  - **Rule fixed now:** if the 1024 smoke aborts, fails to allocate or records any critical-pressure sample, q8 at 1024 is **not executable on this machine**. The chain then runs the 512 block only and the report says so. The same rule at 512 means the diagnostic is not executable at all.
  - **Nothing is changed to make it fit:** no wired-limit change, no other memory policy, no fewer steps.
  - A chain run that aborts is recorded as aborted, and its pair is reported as unavailable.

## 5. Mechanical gates (before any rating)
- **E:** see §3, step 2.
- **V:** see §3, step 4.
- **Q (q4 arm = G2):** every q4 run's RGB `pixel_sha256` and RGBA sha256 must equal its G2 run's. Any difference is a Discrepancy: stop, surface it, and do no rating.
- **D (q8 determinism):** each q8 repeat must equal its original (RGB and RGBA). If one doesn't, the result is reported as it is.

## 6. Review (arm-blind, paired; `qq_blind.py`)
**Sheets:**
- One sheet per pair: 8, or 4 if 1024 is not executable.
- Each sheet has three panels: the original resized to the output size (what the model was conditioned on), result A and result B, all scaled to a long side of 1024 px.
- Sheet order and the **A/B side** per sheet come from `random.Random(seed)`; the key is sealed read-only before any sheet is rendered.
- A q8 repeat never becomes a sheet; determinism is reported mechanically.

**This is a genuine arm-blind comparison.** Both arms appear on every sheet, sides are randomized, and the rater is not told what differs between "two configurations".

**Rater:**
- A fresh subagent (as in G2), reading only `research/qwen/qq/review/blind/`. It may crop at native resolution into a scratch directory outside the repository, and appends rows as it goes.
- The session assistant views no Q-Q output before the freeze.
- Format checks (`qq_blind.py check`) return format-only corrections.
- **Disclosed:** the rater's harness may load `CLAUDE.md`, which describes the G2 text failure mode. That primes attention to text equally for both arms.
- `CLAUDE.md` gets no Q-Q content until the scores are frozen.

## 7. Scoring
- **Per result (A and B separately), in the G2 hierarchy and with G2's definitions** (`research/editing/real-world/protocol.md` §6):
  1. adherence;
  2. preservation;
  3. composition;
  4. quality (with artifact family);
  5. text (PASS/PARTIAL/FAIL).
- **Per text element and result, one category:**
  - **PRESERVED:** the same wording is readable and looks like the original's;
  - **DEGRADED:** the same wording is still correctly readable, but the glyphs are deformed, smeared or partly missing;
  - **GARBLED:** it can no longer be read as the original's (wrong, invented or duplicated letters, gibberish, or unreadable where the original panel is readable);
  - **REMOVED:** gone, or replaced by something else;
  - **NA:** not readable in the original panel either. NA is set for both results together.
  - **"Legible"** means PRESERVED or DEGRADED.
- **Per sheet:** a paired `text_preference` of A, B or SAME, judged on the listed text elements only.

**Text elements.** These were defined from the **sources'** lettering, before any q8 output existed (`qq_blind.ELEMENTS`). The rater sees locations only and reads the wording off the original panel. Elements that q4 kept legible in G2 are included, so that worsening can be counted.

| task | elements |
|---|---|
| R02 | t1 the blue street-name sign; t2 the white plate under the no-entry sign |
| R12 | t1 the banner across the street; t2 the pink half-disc hanging sign; t3 the small green sign; t4 the purple fascia lettering at the left edge and the pink round letter sign; t5 the signs at the right edge |
| R15 | t1 the large shop sign; t2 the white banner on the right-hand window; t3 the number decal on the door glass; t4 the poster on the lower door panel; t5 the small red sticker on the door glass |

## 8. Classification (directive §9; computed by `analyze_qq.py` from the frozen sheets)
**Counting.** A unit is one (element, core pair) that is not NA. Over the core pairs (N = 6, or 3 if 1024 is not executable):
- **G4** = units where q4 is GARBLED or REMOVED;
- **R** (rescued) = of those, units where q8 is legible;
- **W** (worsened) = units where q4 is legible and q8 is not;
- **preference** = core sheets whose text preference is the q8 result, or the q4 result;
- **text FAIL** = the G2-style text dimension per arm, over the N core results.

| class | rule (all conditions must hold) |
|---|---|
| **STRONG evidence that q4 is implicated** | R ≥ 3 (≥ 2 when N = 3) and R ≥ G4/2; W ≤ 1; rescues in at least 2 of the 3 tasks and at every gated budget; q8 preferred on ≥ ⌈2N/3⌉ core sheets and q4 on ≤ ⌊N/6⌋ |
| **AGAINST q4 as the primary explanation** | R ≤ 1 **and** q8 text FAIL on ≥ N − 1 core results ("q8 still garbles the same text") |
| **INCONCLUSIVE (weak or mixed)** | anything else |

**Reporting rules:**
- The supplementary pairs are reported alongside the class and qualify the "repeatable" wording. They are not counted in the thresholds.
- The non-text dimensions (adherence, preservation including leakage, composition, quality) are reported per arm, descriptively. Any q8 regression is stated.
- **Inter-rater check (descriptive):** the q4 results are bit-identical to G2's outputs (gate Q), so this rater's q4 text and preservation scores are compared with the frozen G2 scores of the same pixels.
- **Wording of conclusions:**
  - STRONG → "supports q4 quantization as a contributing factor in the tested cases";
  - AGAINST → "does not support q4 quantization as the primary cause in the tested cases";
  - neither ever claims more than these 3 tasks, 2 budgets, this model, this runtime and these exports.
- No item is added, removed or re-scored after unblinding.

## 9. Memory and time (descriptive; never a gate)
- **Per run:** wall time (`qq_run` subprocess wall), peak footprint (libproc lifetime max), MLX peak and denoise MLX peak, phases, swap growth, warn and critical samples, minimum free percentage.
- q8 is compared **with the q4 runs of the same chain** (sustained, monitored, interleaved), not with G2's numbers.
- No speed claim beyond these medians and ranges.

## 10. Storage disposition (directive §10)
- **Source checkpoint:** RETAIN LOCALLY, untouched.
- **Canonical q4 export:** kept; the backend depends on it.
- **Deleted duplicate:** not recreated (§3, step 2 writes no q4 files).
- **The q8 export:** **deleted by default** after its identity (every file's sha256, the export and merge records, `qerr`), its results and the report are committed. It is re-creatable deterministically from the retained source (gate E shows the procedure is exact).
  - It is retained only if the report names a concrete follow-up experiment that needs it.
  - Deletion follows the Phase 5 procedure: record, commit, `rm`, `df` before and after, then log it.

## 11. Outputs
`research/qwen/qq/`:
- this protocol;
- `export/` (records, logs, monitors, `merge-q8.json`);
- the chain script and log;
- `review/` (`MANIFEST.json`, sealed key, `blind/` with ITEMS, instructions, templates and drafts; composites gitignored, `SCORES-FROZEN.csv`, `PREFERENCE-FROZEN.csv`, `key-unblinded.json`);
- `qq-summary.json`.

Elsewhere:
- run records in `research/qwen/runs/QQ-*` and `QQSMOKE-*`;
- the report `research/qwen/QWEN-QQ-DIAGNOSTIC.md`.

## Amendment 1 (2026-10-08, 08:4x PST; before any q8 edit; tooling only, nothing in §1–§10 changes)
**What happened.** The export chain (`export-chain-attempt1.log`, started 08:40:43 at `fea3872`) passed `qerr` and gate E. Gate E held for both component groups, with 0 mismatches: vae 238/238 tensors, transformer 753/753, text_encoder 1440/1440.

Then `export-q8-vae-transformer` failed with rc 1 after writing every vae and transformer shard. `QwenImage21Edit.save_model` writes `<dst>/<name>/config.json` for **all three** components (`_component_configs`), but `ModelSaver` creates only the directories of the components it saves. So the write of `text_encoder/config.json` raised `FileNotFoundError`. No watchdog abort occurred (peak footprint 10.74 GB, swap +0.79 GB).

**Fix:**
- `export_q8_split.py export` now pre-creates the three component directories before `save_model`.
- `export-q8.sh` now skips a step whose record JSON already exists, and refuses to run a step whose logs exist.

**Kept:**
- the attempt's logs, renamed `*-attempt1*`;
- the partial part directory, as `models/research/qq-staging/ATTEMPT1-q8-part-vae-transformer`. It is compared file by file (sha256) with the re-run's vae and transformer shards, which is an export-determinism check. It is removed only after that comparison is recorded.
