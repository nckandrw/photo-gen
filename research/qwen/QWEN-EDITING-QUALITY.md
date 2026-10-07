# Qwen-Image-2.1 editing quality: G0 capability gate, G1 runtime A/B, G2 real-photograph gate

> **Phase 5 outcome (2026-10-07):** the real-photograph gate **G2 REJECTED both gated configurations** (512 `3cd79615…`, 1024 `fffe8df3…`). See [§ G2](#g2-phase-5-real-photograph-gate-rejected-at-512-and-1024) and `research/editing/real-world/results.md`. The G0/G1 sections below are the Phase 4 record, unchanged.

- **Benchmark:** PHOTO-GEN editing benchmark v1 (`research/editing/`; pre-registered in `c6c01a9`; sources and regions frozen in `cf21eaa` before any edit).
- **Configuration under test:** Qwen-Image-2.1 q4 on mflux 0.21.0 through the production path (`bin/photo-gen edit`), 40 steps, guidance 1.0, prefix KV cache, seed 42.
- **Rubric and gate:** `research/editing/README.md` §2 and §4.
- **Rater:** the AI assistant running the session. Not blind: G0 has a single configuration.
- **Priming (disclosed):** E05's instruction is the smoke instruction, and the smoke had already shown how Qwen handles background edits.
- **Order:** each suite was scored in one sitting from review sheets (source | output), and the scores were frozen (sha256, read-only) **before** `edit_metrics.py` was run.

## G0 at output_resolution 512
Runs `G0-512-*`, 2026-10-07 01:34–01:59, AC, apps closed, git `a7cc451`. Scores: `g0/scores-512.json`, frozen sha256 `0a80b2c2d0f42fcc2776b093b45e7cc8834b57ecf85c11630429e87eb97bbc34`. Metrics: `g0/metrics-512.json` (computed after the freeze).

| test | category | adherence | preservation | composition | quality | text | outside-region SSIM / PSNR | structure corr. |
|---|---|---|---|---|---|---|---|---:|
| E01 | object replacement | PASS | PASS | PASS | PASS | — | 0.888 / 28.4 dB | 0.64 |
| E02 | object addition | PASS | PASS | PASS | PASS | — | 0.880 / 23.0 dB | 0.87 |
| E03 | object removal | PASS | PASS | PASS | PASS | — | 0.951 / 33.5 dB | 0.95 |
| E04 | colour/material | PASS | PASS | PASS | PASS | — | 0.954 / 32.0 dB | 0.89 |
| E05 | background | PASS | PASS | PASS | MINOR | — | (background edit)¹ | 0.58 |
| E06 | style | PASS | PASS | PASS | PASS | — | (global) | 0.40 |
| E07 | localized | PASS | PASS | PASS | PASS | — | 0.842 / 29.2 dB | 0.85 |
| E08 | preservation (busy scene) | PASS | **PARTIAL** | PASS | PASS | — | **0.599 / 16.8 dB** | 0.38 |
| E09 | composition-preserving | PASS | PASS | PASS | MINOR | — | (global) | 0.75 |
| E10 | text-preserving | PASS | PASS | PASS | PASS | PASS | 0.959 / 33.8 dB | 0.95 |
| E11 | text replacement | PASS | PASS | PASS | PASS | PASS | 0.931 / 29.9 dB | 0.91 |

¹ For E05 the registered box is the *preserve* box (vase + flowers incl. some surrounding background); its inside MAE is 31.2.

**Findings**
- **Every requested edit happened** (11/11 adherence PASS), including both text tasks. E10 kept "SPRING SALE" letter-exact while repainting the flower. E11 rendered "COFFEE" in a matching bold serif on the same board.
- **One preservation failure, E08** (the busy-scene test). The model turned the **oranges** into pineapples as well as the bananas. The metric agrees: outside-region SSIM 0.60, against ≥ 0.84 everywhere else.
- **Two MINOR quality defects:**
  - E05: two sun-like glows on the horizon, and the subject keeps its daylight lighting, so it looks pasted;
  - E09: faint daylight patches remain on the wall at night.
- **No MAJOR defect;** no grain, seams or malformed objects.

**Gate G0 (512): CAPABLE**
- **R:** 12/12 rc 0; no watchdog abort; no critical-pressure sample; swap growth ≤ 0.36 GB.
- **D:** the E05 repeat is pixel-identical (`bd548f1b…`).
- **C:** all four conditions hold:
  - adherence PASS 11/11 (needs ≥ 7);
  - adherence PASS or PARTIAL 11/11 (≥ 9);
  - preservation PASS or PARTIAL 11/11 (≥ 8);
  - MAJOR 0 (≤ 2).

## G0 at output_resolution 1024
- **Runs:** `G0-1024-*` (E05 = `G0-1024-E05-cold`), 2026-10-07 02:09–04:00, AC, apps closed, git `a7cc451`.
- **Scores:** `g0/scores-1024.json`, frozen sha256 `3d52f2add0f45295e5d84770d31220fd0d66b878f37051e54472dfdc5f330b2f`.
- **Metrics:** `g0/metrics-1024.json`, computed after the freeze.
- **Additional priming disclosed:** the 512 scores had been made and frozen earlier the same session.

| test | adherence | preservation | composition | quality | text | outside-region SSIM / PSNR | structure corr. |
|---|---|---|---|---|---|---|---:|
| E01 | PASS | PASS | PASS | PASS | — | 0.814 / 26.1 dB | 0.51 |
| E02 | PASS | PASS | PASS | PASS | — | 0.850 / 24.3 dB | 0.79 |
| E03 | PASS | PASS | PASS | PASS | — | 0.932 / 32.9 dB | 0.92 |
| E04 | PASS | PASS | PASS | PASS | — | 0.951 / 32.9 dB | 0.88 |
| E05 | PASS | PASS | PASS | MINOR | — | (background edit) | 0.37 |
| E06 | PASS | PASS | PASS | PASS | — | (global) | 0.36 |
| E07 | PASS | PASS | PASS | PASS | — | 0.758 / 26.2 dB | 0.73 |
| E08 | PASS | **PASS** | PASS | PASS | — | **0.894 / 28.5 dB** | 0.77 |
| E09 | PASS | PASS | PASS | MINOR | — | (global) | 0.75 |
| E10 | PASS | PASS | PASS | PASS | PASS | 0.947 / 30.8 dB | 0.92 |
| E11 | PASS | PASS | PASS | PASS | PASS | 0.876 / 27.7 dB | 0.85 |

**Findings**
- **11/11 adherence PASS and 11/11 preservation PASS.** The 512 failure (E08, oranges replaced) does **not** occur at 1024: the oranges, apples, crates and the chalkboard are kept. The metric agrees, with outside SSIM 0.60 → 0.89.
- **MINOR (2), both lighting consistency:**
  - E05: the subject keeps daylight lighting against the sunset, but no double sun this time;
  - E09: the daylight window patches persist on the wall at night, more visibly than at 512.
- **No MAJOR defect.** No over-sharpening of the kind mflux's VALIDATION.md reported for its 1024 panda inputs (D5); every 1024 edit here applied its change. This does not contradict D5: it covers different inputs and a single seed, and the upstream failures were reproduced with the official pipeline.
- **The metrics are not comparable across budgets.** 1024 compares finer detail, so its outside-region SSIM/PSNR is naturally lower on textured scenes (E01, E07, E11), even where the visual verdict is the same.

**Gate G0 (1024): CAPABLE**
- **R:** 12/12 rc 0; no abort; 0 critical samples; swap growth 1.3–2.1 GB per run.
- **D:** the cold vs repeat E05 is pixel-identical (`792fdaa9…`).
- **C:** adherence 11/11; preservation PASS 11/11; MAJOR 0.

## Summary across budgets
| | 512 | 1024 |
|---|---|---|
| G0 | **CAPABLE** | **CAPABLE** |
| adherence PASS | 11/11 | 11/11 |
| preservation PASS / PARTIAL / FAIL | 10 / 1 / 0 | 11 / 0 / 0 |
| quality MINOR / MAJOR | 2 / 0 | 2 / 0 |
| text tasks | 2/2 PASS | 2/2 PASS |
| time per edit (sustained median) | 103 s | 556 s (497 s cold) |

**Status remains EXPERIMENTAL.** G0 is a capability and reliability gate on one seed per test, scored by one non-blind rater. It is not a quality-equivalence gate, so no edit configuration becomes "validated" from it. Production adoption would need:
- a pre-registered, blinded G2 on fresh sources and seeds for one fixed configuration (backlog Q-G);
- for any commercial use, a licence other than the Qwen Research License.

## G1: runtime A/B (mflux vs sd.cpp), blinded, bounded
- **Protocol:** `research/editing/README.md` §5. Run list frozen in `2b55619` (`g1-chain.sh`).
- **Subset:** E01, E05, E07, E11 at the 512 budget.
- **Like-for-like inputs:** both runtimes received the same pre-resized 512² reference, made with mflux's own resize path (`g1/refs.json`).
  - mflux on that reference reproduced its G0-512 output exactly (E01 `5c4f1eb6…`), so the mflux arm = the G0-512 outputs.
  - sd.cpp's log confirms a 512×512 reference (`image_seq_len=1024`).
- **Blinding:** `research/experiments/blind_stage.py`, seed 20261007, key sha256 `bac40ba3…`. Scores frozen (sha256 `957ef229…`) before unblinding.

| pair | winner (adherence → preservation → quality) | reason |
|---|---|---|
| E01 car → blue motorcycle | **mflux** | sd.cpp **failed adherence**: the red car became a blue car fused with motorcycle parts (a malformed hybrid); mflux produced a proper motorcycle |
| E05 background → sunset beach | **sd.cpp** | both adhere and preserve; mflux's output has two sun-like glows (the MINOR defect already scored in G0) |
| E07 hair → blond | tie | both correct, identity preserved |
| E11 BAKERY → COFFEE | tie | near-identical; both letter-exact in a matching serif |

- **Result:** mflux 1 / sd.cpp 1 / 2 ties. **No quality separation on this bounded subset.** The two losses differ in severity: sd.cpp's was an adherence failure, mflux's a MINOR quality defect.
- **Disclosed weakness of the blinding:** the mflux arm reuses G0-512 outputs this rater had already scored, and two of them (E01 and E05) were recognizable. Both decisions rest on large, objective defects (a malformed hybrid; a double sun), not on preference.
- **Not tested:** sd.cpp repeat determinism (no repeat run; bounded).

The decisive differences are **performance and memory**, not quality (`QWEN-RUNTIME-COMPARISON.md` §2).

## G2 (Phase 5): real-photograph gate, REJECTED at 512 and 1024
The full record is in `research/editing/real-world/results.md` and the pre-registration in `protocol.md` (the benchmark is model-independent). This section summarizes what it means for this backend.

- **Configuration under test:** the Phase 4 configuration (q4 export @ `d26bb61`, mflux 0.21.0 upstream defaults: 40 steps, guidance 1.0, prefix KV cache), now with the adopted P2 memory policy, which is pixel-neutral (`QWEN-MEMORY-LIFETIME.md`). `configuration_id` `3cd79615…` at 512 and `fffe8df3…` at 1024.
- **Inputs:** 16 CC0/PD camera photographs with pre-registered MUST CHANGE / MUST NOT CHANGE lists.
- **Runs:** 45 edits on fresh seeds: 16 primary + 4 second-seed + repeats per budget.
- **Rating:** provenance-blind, by a fresh subagent; frozen before unblinding.

| | 512 | 1024 |
|---|---|---|
| adherence (16 primary) | 15 PASS / 1 PARTIAL / 0 FAIL | 15 PASS / 1 PARTIAL / 0 FAIL |
| preservation (16 primary) | 7 PASS / 5 PARTIAL / **4 FAIL** | 9 PASS / 3 PARTIAL / **4 FAIL** |
| text (R02, R08, R12, R15) | R08 PASS; **R02, R12, R15 FAIL** | R08 PASS; **R02, R12, R15 FAIL** |
| quality MINOR / MAJOR | 6 / 0 | 1 / 0 |
| composition FAIL | 0 | 0 |
| second-seed adherence + preservation FAILs | 3 of 4 items | 2 of 4 items |
| operations / determinism | 23/23 clean; 3/3 repeats bit-identical | 22/22 clean; 2/2 repeats bit-identical |
| wall, monitored harness (median) | 104 s | 592 s |
| peak footprint (median) | 8.16 GB | 10.87 GB |
| memory/UX class | COMFORTABLE | MARGINAL (wall time) |
| **decision** | **REJECTED** | **REJECTED** |

**Failure modes (systematic: they recur across seeds and budgets, and the repeats are deterministic):**
1. **Incidental text is re-synthesized and garbled.**
   - Where the edit is elsewhere in the frame, existing small lettering is not carried through: street-name signs, sub-plates, banners, posters, door decals.
   - That is 8 of 8 text-preservation items; 1024 garbles somewhat less than 512.
   - Requested text replacement works (R08: 4 of 4 PASS).
2. **The edit leaks to adjacent or related elements.**
   - Similar neighbouring objects are swapped too: in a market stall, the mango, netted and red-apple piles became green apples along with the dragon fruit.
   - Colour or material spreads to attached parts: laces with the shoes, edging with the yarn, the glass stem with the wine.
   - G0's E08 (oranges → pineapples) was the first instance.

**What G0 missed.**
- G0's synthetic sources had one prominent sign per text test and few dense clusters of similar objects.
- G0 was rated by the session assistant, not blind, without native-resolution inspection.
- G0 stays a valid *capability* result (CAPABLE). G2 shows that capability does not carry over to reliable preservation on real photographs.

**Status after G2.**
- **Integration validated; capability shown; G2 quality REJECTED; local production REJECTED** (not promoted). Every edit stays `validated: false` behind `--allow-experimental`, as a research opt-in.
- **Commercial use:** not permitted (Qwen Research License).
- **Not established:** whether failure mode 1 comes from the q4 export (DiT or text/vision encoder), from the VAE round trip, or from the output budget. Only an export from the retained source checkpoint could separate the first from the others (`QWEN-ASSET-PROVENANCE.md` §6). Per directive §24–§25, no speed or model work is started on a rejected configuration.

