# G2: real-world editing quality gate, pre-registration (Phase 5, directive §13–§21)

**Status:** this file, `task-manifest.json` and `selection.json` were committed **before any G2 edit ran and before any full-size source was decoded**. The tasks were written from 900-px previews. Every number below was fixed before any G2 output existed. Nothing is made stricter or looser after the results are seen. A deviation is recorded as a dated amendment with its reason, and it is disclosed.

## 1. Question
Can PHOTO-GEN give genuinely useful, reliable image editing on the 16 GB MacBook Air M5, using **real camera photographs**? G2 supersedes G0 as the main quality evidence. G0 used Z-Image-generated sources, which the model may find easier: they are clean and synthetic, with no sensor noise, compression or messy real-world clutter. G0 still stands; where G2 disagrees with it, both are reported, and G2 has the higher evidentiary value for real use.

## 2. Configuration under test (fixed; nothing is tuned during the gate)
- **Model and runtime:**
  - Qwen-Image-2.1 @ `d26bb61`, local q4 export (manifest `config/backend-qwen21-edit-mflux.json`, sha256 `536fba17…`);
  - mflux 0.21.0 + MLX 0.32.2 in `mflux-qwen/.venv`;
  - upstream defaults: 40 steps, guidance 1.0 (no CFG), prefix KV cache, linear flow-match schedule, `--low-ram`.
- **Path:** the production path, `bin/photo-gen edit` (job system, input staging, sidecar). It is launched through `research/qwen/run_edit.sh` mode `app` for the 1 Hz monitor and the watchdog: abort on swap growth > 6 GB or 20 consecutive critical-pressure samples.
- **Output budgets:** `output_resolution` **512** and **1024**. The output size follows the input aspect ratio, in multiples of 32. Each budget is gated separately (§7). Each budget is one `configuration_id` (Phase 5 sidecar), recorded with the results.
- **Memory lifetime policy:** whatever the production default is when the chain is frozen. The candidate memory fix is adopted only if it is pixel-identical (`research/qwen/memory/PROTOCOL.md`), so the policy cannot change quality. It is recorded per run (`execution.memory_policy`, the policy the worker reports it applied).
  - **Outcome before freeze (2026-10-07):** P2 passed its gate and became the production default in commit `973ef7f` (`research/qwen/QWEN-MEMORY-LIFETIME.md`): `defer_transformer_load` + `release_text_encoder_after_encode` + `release_vae_during_denoise`. G2 therefore runs P2. The configuration identity does not include the memory policy, because the policy is pixel-neutral by that gate.

## 3. Sources and tasks
- **Sources:** 16 real camera photographs from Wikimedia Commons, CC0 or public domain only (`selection.json`). Provenance (URL, licence, creator, Commons SHA-1, file SHA-256, pixel SHA-256, EXIF camera, ICC profile, dimensions) goes in `source-manifest.json`. The images are never committed.
- **Composition of the set:** 11 landscape and 5 portrait. Subjects: people, street, product, food, interior, landscape, vehicle, sign/text, a busy market, fine texture, transparent glass, night/neon/rain, architecture, an animal, a text storefront and a simple object scene.
- **Colour.** The photo-gen input pipeline applies no colour management (`inputs.py`): pixel values are used as decoded and treated as sRGB. Each source's embedded ICC profile is recorded. Review sheets are rendered from the staged pixels, so the rater sees what the model saw.
- **Tasks:** one pre-registered task per photo (`task-manifest.json`), each with a **MUST CHANGE** statement and a **MUST NOT CHANGE** list. They cover all 11 edit types of directive §12:
  - colour change: R01, R07, R10, R11;
  - material change: R03;
  - object replacement: R04, R09;
  - object addition: R05, R16;
  - object removal: R02, R12;
  - background change: R13;
  - style transformation: R14;
  - composition-preserving change: R06;
  - localized edit in a busy scene: R09;
  - text replacement: R08;
  - text-preserving edit: R15, plus the preserved text in R02 and R12.

## 4. Runs (fixed order, one chain, clean conditions: heavy apps closed, AC; 20 s gaps)
| block | runs | seeds |
|---|---|---|
| 512 primary | R01…R16 | 2510701…2510716 (task `seed`) |
| 512 second seed (hard cases) | R08, R09, R11, R12 | 2520708, 2520709, 2520711, 2520712 |
| 512 repeats (determinism) | R08, R09, R12: identical request again | primary seed |
| cooldown 120 s | | |
| 1024 primary | R01…R16 | primary seeds |
| 1024 second seed | R08, R09, R11, R12 | second seeds |
| 1024 repeats | R09, R12 | primary seed |

That is 45 edits in total (512: 23; 1024: 22). The seeds are fresh: every earlier Qwen run used seed 42, and neither seed range appears anywhere in the repository or the job database. "Hard cases" were picked before generation: text replacement, a busy localized replacement, a transparent liquid, and person removal at night.

## 5. Provenance-blind scoring (this is **not** an A/B blind; there is one configuration)
- **Rater.** A fresh assistant instance (subagent), chosen by the user on 2026-10-07. It has never seen the run metadata, the protocol drafting, any G0 output or score, or any G2 output before scoring.
  - It receives only the rubric (§6), and for each item an anonymized ID, the instruction, the MUST CHANGE and MUST NOT CHANGE lists, and a composite (left/top = source, right/bottom = output).
  - It is told to read nothing else.
  - The session assistant that designed the tasks does not score.
- **Items.** Every distinct G2 output: 32 primary plus 8 second-seed = 40. A repeat is scored only if its pixels differ from its original; then it is an extra item and the D criterion has already failed.
- **Anonymization:**
  - IDs are random (seeded shuffle across both budgets).
  - The composites are re-rendered PNGs without metadata; raw outputs carry mflux metadata.
  - Both panels are scaled to the same display size (long side 1024 px), so pixel dimensions do not reveal the budget.
  - Sharpness may still hint at the budget. This is disclosed and not claimed away.
- **Procedure:**
  - the mapping key is written atomically and made read-only **before** any composite exists;
  - the rater writes `scores-draft.csv`;
  - the sheet is frozen (sha256 + read-only) **before** any metric is computed or any key is read;
  - unblinding refuses unless the frozen scores and the key both still match their recorded hashes.
- **Tooling and storage:** `g2_blind.py` (prepare, freeze, unblind), a single-image sibling of `research/experiments/blind_stage.py` following `BLIND-PROTOCOL.md`. The composites are gitignored; their hashes are committed.

## 6. Rubric (scored in this order; the definitions extend `research/editing/README.md` §2)
| dimension | PASS | PARTIAL / MINOR | FAIL / MAJOR |
|---|---|---|---|
| 1 **edit adherence** | the MUST CHANGE is fully present and recognizable | present but incomplete or wrong in an attribute (shade, partial removal or recolour, wrong object type, extra leftovers) | absent, or a different change |
| 2 **preservation** | every MUST NOT CHANGE element is recognizably unchanged (small global tone or sharpness shifts allowed) | exactly one listed element materially altered, **or** one unrequested object added or removed | scene regenerated, identity of a person or object lost, or ≥ 2 listed elements materially altered |
| 3 **composition** | layout, viewpoint and framing unchanged | — | layout, viewpoint, crop or zoom changed |
| 4 **visual quality** | natural; no visible artifact | MINOR: visible but not distracting | MAJOR: distracting or unrealistic (seams, halos, grain/grid, malformed objects, smeared texture, implausible lighting, heavy over-sharpening) |
| 5 **text** (items with text in MUST CHANGE or MUST NOT CHANGE) | exact wording; no duplication, dropped letters or ghosting; legible | legible, but a minor glyph or style deviation | wrong or misspelled words, garbled, duplicated or ghosted letters, illegible, or text changed where it had to stay |

- **Artifact family tag.** For every MINOR or MAJOR the rater names the family from a fixed list: `seam/halo`, `grain/grid`, `malformed-object`, `texture-smear`, `lighting-mismatch`, `colour-cast`, `detail-loss/blur`, `ghosting/duplication`, `oversharpening`, `other:<word>`.
- **Text failures count as real errors.** A text FAIL on the requested text (R08) is also an adherence FAIL. A text FAIL on text that had to stay (R02, R12, R15) is also a preservation FAIL. The rater scores text separately; the mapping is applied mechanically at tally time.

## 7. Pass criteria, per output budget (N = 16 primary items; fixed before generation)
| id | criterion | threshold (all must hold) |
|---|---|---|
| **A1** | edit adherence | **0 FAIL** and **≤ 2 PARTIAL** (including text-derived FAILs) |
| **A2** | preservation | **0 FAIL** and **≤ 3 PARTIAL** (including text-derived FAILs) |
| **A3** | composition (no systematic global drift) | **≤ 1 FAIL** |
| **A4** | visual quality | **≤ 1 MAJOR**, and no artifact family tagged (MINOR or MAJOR) on **≥ 6** of the 16 items |
| **A5** | text (no systematic degradation) | **0 text FAIL** over the text items (R02, R08, R12, R15), and **≤ 1** text PARTIAL |
| **O** | operational (all runs at this budget) | every run rc 0 with a valid output; **0 watchdog aborts**; **0 critical-pressure samples** (kernel level 4) in the 1 Hz monitor |
| **D** | determinism | every repeat reproduces its original exactly (RGB `pixel_sha256` **and** RGBA sha256) with identical `configuration_id` and `edit_id`. If not, the actual behaviour is documented and not explained away. |
| **S** | seed robustness (4 second-seed items) | the adherence FAILs plus preservation FAILs (text-derived ones included) number **≤ 1** of 4 |

**G2 PASS at a budget** means A1–A5, O, D and S all hold.

## 8. Memory/UX class per budget (directive §20; computed over all G2 runs at that budget)
| class | conditions (all must hold) |
|---|---|
| **COMFORTABLE** | median wall ≤ 180 s; 0 critical samples; median swap growth ≤ 0.25 GB and max ≤ 0.5 GB; warn-level samples ≤ 5% of each run |
| **USABLE** | median wall ≤ 360 s; 0 critical samples; median swap growth ≤ 1.0 GB and max ≤ 2.0 GB |
| **MARGINAL** | median wall ≤ 900 s; 0 critical samples; no abort; max swap growth ≤ 4 GB |
| **NOT PRACTICAL** | otherwise |

- **How the class is assigned:** the budget gets the highest class whose conditions all hold. Wall time is the job's `generation_seconds`; swap growth is the run's maximum swap minus its starting value.
- **Disclosure.** The time thresholds were chosen knowing the G0 timings (512 ≈ 103 s, 1024 ≈ 556 s sustained). On time alone, 1024 therefore cannot be better than MARGINAL unless something changes.
- **Disclosure (swap thresholds).** The swap thresholds were written while the memory A/B was running, after its 512 results were known:
  - P0 E05 at 512 grew swap by 0.234 GB, just under the 0.25 GB COMFORTABLE line; the adopted P2 grew it by 0.069 GB, and E08c by 0.033 / 0.000 GB.
  - The thresholds are left unchanged.
  - At 1024 this knowledge changes nothing: wall time (≈ 550 s per edit in the A/B) caps 1024 at MARGINAL whatever the swap figures are.
- **Timing context.** G2 wall times come from the monitored harness, and the monitored runs in the memory A/B were slower than unmonitored production edits of the same request (512: about 100–115 s against about 80–86 s; `QWEN-MEMORY-LIFETIME.md` §4). The classes are applied to the monitored G2 times as measured. This is conservative and disclosed.
- **Rationale (a UX judgement, not a measurement).** An accepted edit typically takes 2–4 attempts (seed or wording). Above about 6 min per attempt, iteration within one sitting stops being practical. Above 15 min it is impractical.

## 9. Production decision per budget (directive §21; the same rule for both budgets)
| outcome | rule |
|---|---|
| **VALIDATED FOR LOCAL/PERSONAL USE** | G2 PASS **and** class COMFORTABLE or USABLE |
| **REJECTED** | adherence FAIL ≥ 3 **or** preservation FAIL ≥ 3 (of 16, text-derived included), **or** O fails in ≥ 2 runs, **or** class NOT PRACTICAL |
| **EXPERIMENTAL** | everything else: capability shown, but quality, memory, time or repeatability borderline. This includes a G2 PASS whose class is only MARGINAL. |

- **Overall label for Qwen editing:** VALIDATED if at least one budget is VALIDATED (scoped to that exact budget, like Z-Image's per-resolution combinations), else EXPERIMENTAL if any budget is EXPERIMENTAL, else REJECTED.
- **Improvement Clause:** directive §21 asks for one label. Per-budget verdicts follow the project's exact-combination rule. Never derive validity from a nearby configuration.
- **If a budget is VALIDATED:** the code gets an explicit table of validated edit configurations (exact `configuration_id` per budget), and only those report `validated: true`. That is a separate, cited commit. Everything else stays experimental and needs `allow_experimental`.
- **Licence.** VALIDATED never means commercially usable. Qwen-Image-2.1 stays under the Qwen Research License (non-commercial).

## 10. Descriptive aids (never override a visual verdict; computed only after the freeze)
- `research/editing/edit_metrics.py` on the staged source versus the output: outside-change-region MAE/PSNR/SSIM, inside-region MAE, and Sobel structure correlation.
- Per-run wall, phases, peak footprint, swap growth and pressure samples, collected in `benchmark.csv`.

## 11. Outputs of the gate
`source-manifest.json`, `benchmark.csv` (one row per run), `scores.csv` (frozen rater scores plus the unblinded mapping), `results.md` (verdicts, memory class, decision, G0-vs-G2 comparison), and `research/qwen/QWEN-EDITING-QUALITY.md` § G2 (Qwen-specific). The benchmark definition here stays model-independent.

## Amendment 1 (2026-10-07; committed 12:11:01 PST in `f16e092`, 4 s before the G2 chain started at 12:11:05; this header previously said "~12:15 PST"): source acquisition. Made before any G2 edit ran; no G2 output exists. Criteria unchanged.
**What happened.** `fetch_sources.py` (as committed in `8694119`, after this pre-registration) downloaded and decoded the full-size sources. That is the first time any full-size source was decoded. Two problems turned up:

1. **Filename bug (tooling).** Commons' `imageinfo.url` now ends in a `?utm_…` query string, and the script used it in the local filename. Fix: take the name from the URL path.
   - The two files from that first attempt (R01, R02) were moved aside, not deleted.
   - Their manifest is kept at `acquisition/source-manifest-attempt1.json`.
   - Both re-downloaded files are byte-identical to attempt 1 (sha256 `df373d2f…` and `55f8ef80…`).
2. **Two camera files rejected by photo-gen's own input staging (a product defect).**
   - R02 (Panasonic DMC-GF6) and R04 (Sony DSC-W530) are **MPO** multi-picture JPEGs: a primary JPEG plus a preview image, saved as ordinary `.jpg`.
   - `inputs.py` rejected them with "input format MPO is not accepted". It would do the same for any user of such a camera.
   - The script now records a staging rejection instead of aborting, so the other 14 sources were acquired and staged normally.

**Improvement Clause (directive, material plan change):**
- **Original approach:** G2 runs on the original downloaded camera files through `bin/photo-gen edit`, exactly as a user would.
- **Proposed change:** fix the input pipeline so an MPO stages as its primary image (frame 0), with a warning. Every other multi-frame or animated input is still rejected. This is commit `e653122`, with a test; tests 92/92.
- **Evidence:**
  - Re-staging the 14 already-staged originals with the fixed code reproduces all 14 `pixel_sha256` values and sizes.
  - R02 and R04 stage at their primary sizes, 4592×3448 and 2592×1944, not the preview.
  - They were staged from the already-downloaded files, with the sha256 re-verified (`fetch_sources.py --restage`).
- **Why it is better than the alternatives:**
  - Keeping R02 and R04 unfixed would fail them at submission at both budgets and trip criterion O. `len(ops_bad) ≥ 2` then means REJECTED, so the gate would reject Qwen for a photo-gen staging bug unrelated to the backend.
  - Replacing them would change pre-registered items.
  - Dropping them would break the N = 16 thresholds.
  - Pre-converting them would hide a defect that real users would hit.
- **Expected information gain:** G2 measures the edit backend on all 16 pre-registered real photographs. The MPO defect is reported separately as a photo-gen finding.
- **What it replaces:** the "reject MPO" input behaviour. Nothing in §2–§9 changes: no task, seed, region, threshold or rule.

**Checks on the staged sources (before freezing the chain):**
- **Orientation matches §3:** 5 portrait (R08, R11, R12, R13, R15) and 11 landscape. R11, R13 and R15 carry EXIF orientations 6, 8 and 6; they are upright after staging.
- **Regions:** every pre-registered region was drawn on the 900-px previews. Each was checked on the staged image and is on its intended object; no region was changed.
  - R12: the man walking towards the camera is right of the image centre but in the middle of the walkway. He is the only figure that fits the instruction, so it is unchanged.
- **Colour:** R15 carries a Display P3 profile. As §3 states, it is ignored (no colour management), and the rater sees the staged pixels.
- **Provenance:** 14 sources are CC0 and 2 are Public domain (R09, R15); every licence passed the script's CC0/PD check. `source-manifest.json` records every field listed in §3.

## Amendment 2 (2026-10-07; committed 16:49:21 PST in `cf96d4a`, before the rater started; this header previously said "~16:55 PST"): rating procedure. Made after the 45 G2 edits and `g2_blind.py prepare`, before any G2 output was viewed or scored by anyone. Criteria unchanged.
**Run records at this point (mechanical, from `benchmark.csv`, no output viewed):** 45/45 completed, rc 0, no aborts, 0 critical-pressure samples; all 5 repeats equal their originals in RGB pixels, RGBA and both ids. These records feed O, D and the memory class only.

**Procedural notes (nothing in §2–§9 changes):**
- **Shuffle seed:** `g2_blind.py prepare` was run with seed 20261007 (§5 fixes a seeded shuffle but did not name the seed). Key sha256 `652bfa45…`, sealed read-only before any composite existed.
- **Zoom (fixed now, uniformly, for every item):** composites are up to 1608 px wide; an image viewer downscales them, which would put the text checks (dropped letters, ghosting) and grain/grid artifacts below what the rater can see. The rater **may crop any region of any composite at native composite resolution** (e.g. `sips -c … --cropOffset …`), writing crops only to a scratch directory outside the repository. Crops are views of the same composite, not new information.
- **Durability:** the rater appends each row to `g2/blind/scores-draft.csv` as soon as the item is scored, in ITEMS.md order, so that a partial sheet survives an interruption. One rater, as §5 requires; the sheet is not split across instances.
- **Format checks before `freeze`, beyond `g2_blind.py`'s vocabulary checks:** every ITEMS.md "text: scored" item has text ∈ {PASS, PARTIAL, FAIL} and every other item has NA; `quality_family` is empty when quality is PASS. A violation is sent back to the same rater as a format-only correction (no content comment); the session assistant does not view composites before the freeze.

**Disclosed limits of the anonymization (§5):**
- **Pixel dimensions.** §5 says equal display size hides the budget. That holds only partly: the output size is derived per budget with multiple-of-32 rounding, so the aspect ratio differs slightly between budgets for 15 of 16 tasks (R07 is the exception), and so do the composite sheet sizes (e.g. R01: 1024×1418 at 512, 1024×1472 at 1024). Sheet size can show that two items are different runs of the same task, but not which budget is which. Disclosed alongside the sharpness hint; not re-prepared.
- **Rater context.** The rater is a fresh subagent whose harness may load the repository's `CLAUDE.md`, which names the edit backend and mentions G2, but contains no run, item or key information. The rater prompt names no model, budget, seed, run kind, threshold or criterion.

## Corrections (2026-10-08, Phase 6)
The two amendment headers above gave approximate clock times ("~12:15", "~16:55") that were later than the commits that actually carry the amendments. The headers now give the commit times from `git log`; the earlier wording is quoted in each header. The amendments' content, and every criterion, threshold, task, seed and region, are unchanged.
