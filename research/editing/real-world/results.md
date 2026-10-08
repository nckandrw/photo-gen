# G2 real-photograph editing gate: results

**Decision (protocol §9, applied mechanically to the frozen scores): REJECTED at 512 and REJECTED at 1024. Overall label for Qwen editing: REJECTED.**

| | |
|---|---|
| what was gated | **one fixed edit configuration per output budget:** Qwen-Image-2.1 @ `d26bb61`, local q4 export (manifest sha256 `536fba17…`), mflux 0.21.0 `mflux-generate-qwen-2.1-edit` upstream defaults (40 steps, guidance 1.0, prefix KV cache), memory policy P2, through the production path `bin/photo-gen edit`. `configuration_id` **`3cd79615…`** (512) and **`fffe8df3…`** (1024). |
| what it does not cover | Qwen-Image-2.1 in general: other exports (q8, bf16), other runtimes, step counts, output budgets or instructions were not gated. The verdict is about these two configurations on this machine. |
| machine | MacBook Air M5, 16 GB, macOS 27.0, on AC power, heavy apps closed (`docs/HARDWARE.md`) |
| runs | 45 edits, 2026-10-07 12:11:05 → 16:45:07 PST, git `f16e092` (chain `g2-chain.sh`, log `g2-chain.log`) |
| rating | provenance-blind (not A/B blind: there is one configuration). A fresh subagent rated 40 composites; sheet frozen at 17:13 (sha256 `f14deba4…`, commit `6577b09`) before the key was opened |
| pre-registration | `protocol.md` (commit `8694119`, before any source fetch or edit) + amendment 1 (source acquisition, before any edit) + amendment 2 (rating procedure, before any output was viewed). No criterion, threshold, task, seed or region changed after any output existed. |

## 1. Gate criteria (protocol §7) per budget
| criterion | threshold | 512 | 1024 |
|---|---|---|---|
| **A1** adherence | 0 FAIL, ≤ 2 PARTIAL | 0 FAIL, 1 PARTIAL ✅ | 0 FAIL, 1 PARTIAL ✅ |
| **A2** preservation | 0 FAIL, ≤ 3 PARTIAL | **4 FAIL**, 5 PARTIAL ❌ | **4 FAIL**, 3 PARTIAL ❌ |
| **A3** composition | ≤ 1 FAIL | 0 ✅ | 0 ✅ |
| **A4** quality | ≤ 1 MAJOR; no family on ≥ 6 items | 0 MAJOR; max family 2 (malformed-object) ✅ | 0 MAJOR; max family 1 ✅ |
| **A5** text | 0 FAIL, ≤ 1 PARTIAL over R02, R08, R12, R15 | **3 FAIL** (R02, R12, R15) ❌ | **3 FAIL** (R02, R12, R15) ❌ |
| **O** operational | all rc 0, no abort, 0 critical samples | 23/23 ✅ | 22/22 ✅ |
| **D** determinism | repeats identical (RGB, RGBA, both ids) | R08, R09, R12: all identical ✅ | R09, R12: all identical ✅ |
| **S** seed robustness | ≤ 1 adherence + preservation FAIL over 4 second-seed items | **3** (R09 adh + pres, R12 pres) ❌ | **2** (R09 pres, R12 pres) ❌ |
| **G2** | all of the above | **FAIL** | **FAIL** |
| memory/UX class (§8) | | **COMFORTABLE** | **MARGINAL** |
| **decision (§9)** | REJECTED if preservation FAIL ≥ 3 | **REJECTED** (4 preservation FAILs) | **REJECTED** (4 preservation FAILs) |

Mechanical tally: `analyze_g2.py` → `results-summary.json`. Per-run records: `benchmark.csv`. Frozen scores with the unblinded mapping: `scores.csv`.

## 2. Per-item scores (frozen; A = adherence, P = preservation, C = composition, Q = quality, T = text)
| task | edit | 512 A/P/C/Q/T | 512 second seed | 1024 A/P/C/Q/T | 1024 second seed |
|---|---|---|---|---|---|
| R01 | top white → dark green (portrait) | PASS/PASS/PASS/PASS/– | | PASS/PASS/PASS/PASS/– | |
| R02 | remove the van (street) | PASS/**FAIL**/PASS/PASS/**FAIL** | | PASS/**FAIL**/PASS/PASS/**FAIL** | |
| R03 | blue canvas shoes → brown suede | PASS/PARTIAL/PASS/PASS/– | | PASS/PARTIAL/PASS/PASS/– | |
| R04 | guacamole → black olives | PASS/PASS/PASS/PASS/– | | PASS/PASS/PASS/PASS/– | |
| R05 | add a sleeping grey cat | PASS/PASS/PASS/MINOR/– | | PARTIAL/PASS/PASS/PASS/– | |
| R06 | winter scene (global) | PASS/PARTIAL/PASS/MINOR/– | | PASS/PASS/PASS/PASS/– | |
| R07 | car turquoise → red | PASS/PASS/PASS/PASS/– | | PASS/PASS/PASS/PASS/– | |
| R08 | sign "MacBike" → "CityBike" | PASS/PARTIAL/PASS/MINOR/PASS | PASS/PARTIAL/PASS/MINOR/PASS | PASS/PASS/PASS/PASS/PASS | PASS/PASS/PASS/PASS/PASS |
| R09 | dragon fruit → green apples (market) | PARTIAL/**FAIL**/PASS/MINOR/– | **FAIL**/**FAIL**/PASS/MINOR/– | PASS/**FAIL**/PASS/PASS/– | PASS/**FAIL**/PASS/PASS/– |
| R10 | turquoise yarn → red | PASS/PARTIAL/PASS/PASS/– | | PASS/PARTIAL/PASS/PASS/– | |
| R11 | red wine → white wine | PASS/PARTIAL/PASS/MINOR/– | PASS/PARTIAL/PASS/PASS/– | PASS/PARTIAL/PASS/PASS/– | PASS/PARTIAL/PASS/PASS/– |
| R12 | remove a man (night street) | PASS/**FAIL**/PASS/PASS/**FAIL** | PASS/**FAIL**/PASS/PASS/**FAIL** | PASS/**FAIL**/PASS/PASS/**FAIL** | PASS/**FAIL**/PASS/PASS/**FAIL** |
| R13 | blue sky → sunset sky | PASS/PASS/PASS/MINOR/– | | PASS/PASS/PASS/MINOR/– | |
| R14 | watercolour (global style) | PASS/PASS/PASS/PASS/– | | PASS/PASS/PASS/PASS/– | |
| R15 | paint the brick wall white, keep all lettering | PASS/**FAIL**/PASS/PASS/**FAIL** | | PASS/**FAIL**/PASS/PASS/**FAIL** | |
| R16 | add a croissant | PASS/PASS/PASS/PASS/– | | PASS/PASS/PASS/PASS/– | |

The rater's note for every item is in `scores.csv`.

*Correction (2026-10-08, Phase 6):* R04's edit label in this table previously read "guacamole → black-bean dip". The task was black olives (`task-manifest.json`, both run sidecars, `g2/blind/ITEMS.md`, the rater's notes). Only the label changed; no score did.

## 3. Why it was rejected: two systematic failure modes
Adherence was strong on the primary items: 30 of 32 PASS and none FAIL. One second-seed item did fail adherence: R09 at 512, where the dragon fruit was left unchanged. The one primary PARTIAL at each budget is mild (R09 at 512; R05 at 1024, where the cat is resting rather than asleep). Composition never failed. No MAJOR artifact occurred. **The failures are in preservation**, and they repeat across seeds and budgets, so they are properties of the configuration rather than unlucky samples.

**(a) Incidental text elsewhere in the photo is re-synthesized and garbled: R02, R12, R15.**
- Each of these three tasks asks for an edit somewhere else in the frame (remove a van, remove a person, paint a wall) and lists the existing lettering as MUST NOT CHANGE.
- Result: **text FAIL on all 8 of these items** (both budgets; R12 on both seeds).
  - R02: the street-name sign "NIEUWE UILENBURGER STRAAT" became gibberish, and so did the "uitgezonderd" sub-plate under the no-entry sign.
  - R12: the "MATHEW STREET / BIRTHPLACE of THE BEATLES" banner and the "Club Cut / Barber Shop" sign were garbled.
  - R15: the door poster ("SAVE LIVES / STOP THE CITY") and the "319" decal were garbled. At 512 the window lettering "shop in our new webstore" also degraded.
- **This happens even though the edit itself succeeded every time:** the van, the man and the brick colour were handled cleanly, with plausible fill.
- 1024 garbles less than 512: R12's "Quarry Quarter" sign and R15's window lettering survive at 1024. It does not garble nothing, though.
- **Requested text, by contrast, works.** R08 ("MacBike" → "CityBike") is text PASS on all 4 items. G0's text tasks passed too.
- What fails is the preservation of small, secondary lettering that the model has to carry through unchanged. In a real photograph that is street signs, posters, decals and banners.
- Signs and text are a required category of real-world use (directive §11), so this is not an edge case.

**(b) The edit leaks to adjacent or related elements: R09, plus the PARTIALs of R03, R10 and R11.**
- **R09 (busy market stall):** the green apples replaced the mango, pink-netted and red-apple piles as well as the dragon fruit. At 512 the dragon fruit itself became indistinct beige fruit (primary) or was left unchanged (second seed). Preservation FAIL on all 4 items. The rater applied the rubric's "identity of an object lost" clause.
- **The same mechanism, milder, produced these PARTIALs:**
  - R03: the laces turned brown with the uppers (both budgets).
  - R10: the dark-blue edging and cuffs turned red with the turquoise yarn (both budgets).
  - R11: the red glass stem lost its colour with the wine (all 4 items).
- R12's second seed at 512 also removed two other passers-by. That item is a FAIL anyway, through its text.
- **The other two PARTIALs, both at 512, are not leakage:**
  - R06: the winter edit buried the rocky trail and flattened mid-ground ridges.
  - R08 (both seeds): a distant woman with a pram was smeared and distorted. That is re-synthesis of small far-away detail, akin to mode (a). Neither recurred at 1024.
- The commit message of `0ccc0b7` says "all PARTIALs"; this paragraph is the correct attribution.
- **G0 had already shown this mode once** (E08 at 512: the oranges became pineapples along with the bananas). G2 shows it is systematic on real, cluttered photographs.

**What the verdict rests on (descriptive; the frozen scores are not re-scored).**
- At each budget the four preservation FAILs are R02, R09, R12 and R15. Three of them (R02, R12, R15) carry a text FAIL. By the pre-registered §6 mapping, a text FAIL on text that had to stay is itself a preservation FAIL.
- So **REJECTED (preservation FAIL ≥ 3) does not depend on R09**, which is the judgement the rater flagged as hardest.
- It does depend on the six forcing text FAILs. After the freeze, the session assistant looked at all six at native resolution, comparing each output against the source resized to the same size. That is the conditioning input, and it is what the rater saw. All six show clearly garbled lettering that is legible in the resized source.
- The rater revised three preservation scores in its own draft before hand-back (§6). Those revisions don't change any tallied count, because those items carry text FAILs.

## 4. Memory, time and operations (protocol §8, §19)
All values are over all runs at the budget, as medians with the range in brackets. Wall time is the job's `generation_seconds` **under the monitored harness** (`run_edit.sh`, 1 Hz monitor). In the memory A/B that harness ran slower than unmonitored production edits of the same request; at 512 that was about 100–115 s monitored against 80–86 s unmonitored (`research/qwen/QWEN-MEMORY-LIFETIME.md` §4). The classes are applied to the monitored times as measured. The wall times rise with position in the chain (runs 20 s apart; fanless machine). Under the same monitor, the first two 512 runs took 80.1 s and 82.9 s, then 94, 99 and 108 s; the median of runs 5–23 is 105 s. The first 1024 run, after a 120 s pause, took 523 s against a 592 s median. So cold-versus-sustained (most likely thermal) explains the gap that `QWEN-MEMORY-LIFETIME.md` §4 attributed to monitoring at least as well as monitoring overhead does; the cause is still not isolated. Medians here are **sustained-chain** figures.

| | 512 (23 runs) | 1024 (22 runs) |
|---|---|---|
| wall per edit | **104 s** [80–115] | **592 s** [523–634] (≈ 9.9 min) |
| denoise | 96 s [73–107] | 571 s [504–613] |
| text + vision encode / VAE encode / VAE decode | 1.2 / 0.4 / 2.4 s | 4.6 / 1.4 / 10.2 s |
| peak footprint (libproc lifetime max) | **8.16 GB** [8.07–8.37] | **10.87 GB** [10.72–11.10] |
| MLX peak | 7.37 GB | 7.21 GB |
| swap growth per run | 0.00 GB [0.00–0.04] | 0.45 GB [0.10–1.19] |
| warn-level pressure samples | ≤ 1 per run (≤ 1.4%) | 4–11 per run (≤ 2.7%) |
| critical-pressure samples / aborts | 0 / 0 | 0 / 0 |
| min free memory | 32% | 27% |
| **class (§8)** | **COMFORTABLE** | **MARGINAL** |

- **1024 is MARGINAL on wall time alone.** The median of 592 s is above the 360 s USABLE limit. Memory is no longer the binding constraint: the P2 lifetime policy keeps the peak at about 10.9 GB, with no critical pressure and at most 1.19 GB of swap growth. This finding stands independently of the quality verdict.
- **O passes at both budgets:** 45/45 rc 0 with valid outputs, no watchdog abort, and every run applied the full P2 policy (`execution.memory_policy`).
- **D passes:** all 5 repeats (R08, R09, R12 at 512; R09, R12 at 1024) reproduce their originals bit for bit (RGB `pixel_sha256`, RGBA sha256, `configuration_id`, `edit_id`). That includes R09 and R12, whose content failed, so the failures are deterministic properties of the seed and configuration, not run-to-run noise.
- **Camera MPO inputs:** R02 and R04 went through the production path as primary-image MPO (amendment 1; fix `e653122`). R04 scored PASS on everything at both budgets. R02's failure is the text mode in §3(a); it is unrelated to the input format.

## 5. G0 versus G2
| | G0 (Phase 4) | G2 (this gate) |
|---|---|---|
| sources | 11 Z-Image-generated images | 16 real camera photographs (CC0/PD Wikimedia Commons) |
| seeds | 42 (one per test) | fresh pre-registered seeds; second seeds on 4 hard cases; repeats |
| rater | the session assistant, not blind | a fresh subagent, provenance-blind, with native-resolution crops |
| adherence PASS (primary) | 11/11 at each budget | 15/16 at each budget (0 primary FAIL; 1 second-seed FAIL at 512, R09) |
| preservation FAIL (primary) | 0 at each budget (E08 PARTIAL at 512) | **4 at each budget** |
| text | 2/2 PASS (one prominent sign each) | requested text 4/4 PASS; preserved incidental text **0/8** items |
| quality MAJOR | 0 | 0 |
| result | CAPABLE at 512 and 1024 | REJECTED at 512 and 1024 |

- **G0 measured capability; G2 measures reliability on real photographs.**
- Synthetic sources hold few small, unrelated text elements and few dense clusters of similar objects. Real street, shop and market photographs are full of both.
- The E08 partial in G0 was the first sign of failure mode (b). G2's sources contain far more incidental text than G0's, and that is where failure mode (a) appears.

## 6. Procedure, audit and disclosures
- **Rater:**
  - It read only `g2/blind/` (instructions, ITEMS.md, template, 40 composites) and its own crops, which are outside the repository: 46 reads of blind files and 137 of crops.
  - It wrote only `g2/blind/scores-draft.csv`.
  - It touched no key, run record, protocol or output path. The audit was extracted from its tool calls: `g2/RATER-AUDIT.json`. Its hand-back report is verbatim in `g2/RATER-REPORT.md`.
- **Rater revisions before hand-back (allowed; disclosed):**
  - Q01, Q07 and Q21 (R15-512, R02-1024, R02-512) were first appended with preservation PARTIAL. The rater revised them to FAIL after settling on counting two hit listed elements as FAIL (rubric §6).
  - Their text score (FAIL) was unchanged from the first append, and the §6 mapping already makes them preservation FAILs, so no tallied count changed.
  - Six other edits changed notes only.
- **Format checks** (amendment 2; `check_scores_format.py`): 40 rows, 12 text-scored items, no violation. No correction was sent to the rater.
- **Anonymization limits (amendment 2):**
  - sheet sizes differ between budgets for 15 of 16 tasks;
  - sharpness may hint at the budget;
  - the rater's harness may load the repository's `CLAUDE.md`, which names the backend but carries no item information.
  - The rater cross-referenced same-scene items in its notes (e.g. "same treatment as Q03", later removed). Recognizing a repeated scene is unavoidable with one instruction per photograph.
- **Spot check after the freeze:** the session assistant looked at R02, R12 and R15 at both budgets at native resolution (§3). This was descriptive only; it confirmed the rater's description of the garbled lettering. No score was changed or re-derived.
- **Descriptive metrics** (§10; computed after the freeze): `g2-metrics.json`. Whole-region metrics do not detect the text failures; for example, R12's outside-region SSIM is 0.85–0.88 although its lettering is garbled. That is why the gate is a visual one.
- **Timing baseline:** a sustained chain under the monitored harness (§4). Protocol §8 attributed the slower times to the monitor; the chain-position evidence in §4 points at cold versus sustained instead. The classes are unaffected: 512 stays under 180 s, and 1024 is above 360 s even on its first run.

## 7. What this means
- **Not promoted.** No edit configuration is validated, and the code keeps every edit at `validated: false` behind `allow_experimental`. Protocol §9 adds a validated-configuration table only for a VALIDATED budget, so nothing changes in `app/`.
- **Status lines** (directive §27):
  - **integration:** validated (backend identity, manifests, P2 memory policy, MPO inputs, sidecars, determinism);
  - **capability:** validated (G0 CAPABLE at 512 and 1024; G2 adherence 0 FAIL on the 16 primary items per budget, plus one second-seed FAIL at 512);
  - **quality:** G2 **REJECTED** at 512 and 1024 (incidental-text preservation and edit leakage);
  - **local production:** **REJECTED.** Not a production feature. It stays reachable only as an explicit research opt-in (`--allow-experimental`);
  - **commercial use:** not permitted under the Qwen Research License (non-commercial). photo-gen's MIT licence covers only photo-gen's code.
- **Where the edit backend is still usable at the user's own risk:** single-subject colour, material, sky, style and addition edits on photographs without important small text. R01, R04, R07, R13, R14 and R16 passed at both budgets. This describes the observed failures; it is not a validation.
- **Open questions (not run; directive §24–§25 put speed and model work after a quality pass):**
  - Is mode (a) caused by the q4 quantization of the DiT or the text/vision encoder, by the VAE round trip, or by the output-resolution budget? Only the first needs the source checkpoint (`research/qwen/QWEN-ASSET-PROVENANCE.md` §6).
  - Would a different editing model preserve incidental text on this machine?
