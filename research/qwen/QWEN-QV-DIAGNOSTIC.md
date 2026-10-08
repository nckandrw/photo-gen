# Q-V diagnostic (Phase 7): does the Qwen VAE round trip itself garble incidental text?

**Pre-registered class: MIXED** (`research/qwen/qv/PROTOCOL.md` §8), applied mechanically to the frozen provenance-blind sheets.

**The output path is not clean.**
- Even a perfect copy of the reference latents, decoded exactly as the edit decodes, loses incidental text.
- **At 512 it is a severe limit:** of 12 lettering elements readable in the original, scaling to the 512 budget already leaves 6 unreadable, and the VAE round trip loses 4 of the remaining 6. The round trip keeps **3 of 12** legible.
- **At 1024 it is a partial limit:** the scaled input keeps 10 of 12 legible. The round trip loses 3 of those (one per photo) and keeps **7 of 12** legible.
- The 1024 loss falls between the pre-registered thresholds. VAE-IMPLICATED needs 5 or more losses; BUDGET-LIMITED and VAE-CLEARED need 1 or fewer. Hence MIXED.
- In every sheet the blind rater preferred the scaled input's lettering to the round trip's (6/6).

**What this does not show:**
- It does not show that the VAE is the sole cause of G2's failure.
- It does not show that no model could keep the text. A regenerating model can render text anew, as R08's requested text replacement showed in G2.

What it shows is that, for these photographs at these budgets, **faithfully copying the reference latents does not keep the incidental text** (§1 and §7 give the exact wording).

**Status unchanged:** G2 REJECTED (frozen); Q-Q AGAINST (frozen); Qwen editing research-only, `validated: false`, Qwen Research License non-commercial.

| | |
|---|---|
| question | Does the Qwen-Image-2.1 VAE round trip, at the edit's output budgets, materially degrade or garble incidental text in the real photographs behind the G2 rejection? There is no DiT, no text encoder and no prompt. |
| sources | Staged G2 inputs **R02** (street, 4592×3448, Panasonic MPO primary image), **R12** (night street, 3024×4032), **R15** (storefront, 3024×4032). Pixel sha256 equals the G2 sidecars (gate). |
| text elements | `research/qwen/qq/qq_blind.py` `ELEMENTS`, verbatim (Q-Q's; locations only). R02 has 2, R12 5, R15 5, so 12 per budget. |
| VAE | `models/qwen/qwen-image-2.1-edit-mflux-q4/vae/0.safetensors`, sha256 `248d52c5…` (the manifest pin); config `vae/config.json` `fa1ef934…`; fp32 weights; `Qwen/Qwen-Image-2.1` @ `d26bb61`. Loaded alone with mflux's own `Qwen21Initializer.load_components`, vae-only, as production P2 reloads the decode VAE. |
| runtime | mflux 0.21.0, MLX / mlx-metal 0.32.2, in the edit venv with the production worker environment (`_worker_env`); MLX cache limit 1 GB, as under `--low-ram`. |
| budgets | `output_resolution` 512 (outputs 576×448 for R02, 448×576 for R12 and R15) and 1024 (1184×896, 896×1184). These equal the G2 output sizes (gate). |
| path (the edit's own functions) | `open_oriented().convert("RGBA")` → LANCZOS to `dimensions(budget, aspect)` → `/127.5 − 1` → `vae.encode` (untiled; latent mean) → `pack_latents` → **bf16** → `unpack_latents` → fp32 → `VAEUtil.decode` with `TilingConfig()` (512-px tiles) → `ImageUtil.to_pil` (RGBA). This is a **ceiling:** the output of a DiT that copied the reference latents perfectly. |
| timeline (commit times) | Pre-registered `a390bef` 2026-10-08 23:50:11 → chain 23:50:16–23:55:48 → records and sheets `0b2514d` 23:56:12 → rater prompt `6e527f0` 23:56:30 → frozen `670642e` 2026-10-09 00:25:20 → unblinded `f718359` 00:26:34. Times are Asia/Manila (UTC+8). |

## 1. Gates (all passed)
- **Pipeline equivalence** (`runs/QVGATE-512-E05/worker/gate.json`): one real 3-step edit of the G0 source E05 at 512 through the **production worker** (q4 export, policy P2), with read-only capture hooks.
  - The harness reproduced the edit's VAE encode **input** and **output** bit for bit.
  - The latents entering `unpack_latents` were `mlx.core.bfloat16`.
  - The tiling configs were identical.
  - Decoding the edit's captured latent through the harness reproduced the edit's decoded output bit for bit.
  - So the Q-V path is the edit's own path, not an approximation.
- **Source:** 6/6 staged inputs equal the G2 pixel sha256.
- **Geometry:** 6/6 round-trip sizes equal the G2 output sizes.
- **VAE identity:** every run read the pinned shard.
- **Determinism:** each item ran in two fresh processes (a and b). All 6 are **bit-identical** in the scaled input, the round trip (RGB and RGBA) and both variants. The VAE encode returns the latent mean, so nothing in the path is random.

## 2. Results (frozen sheets, unblinded; `qv/qv-summary.json`)
**Text categories over the 12 elements per budget** (none NA: every element was readable in the full-resolution original):

| budget | panel | PRESERVED | DEGRADED | GARBLED | REMOVED | NA | legible (P+D) |
|---|---|---:|---:|---:|---:|---:|---:|
| 512 | scaled input | 4 | 2 | 6 | 0 | 0 | 6 |
| 512 | **round trip** | 2 | 1 | 9 | 0 | 0 | **3** |
| 1024 | scaled input | 9 | 1 | 2 | 0 | 0 | 10 |
| 1024 | **round trip** | 4 | 3 | 5 | 0 | 0 | **7** |

**Per element** (scaled input → round trip; in brackets, the q4 *edit*'s category from Q-Q's frozen sheet, which is cross-rater; P/D/G = PRESERVED/DEGRADED/GARBLED):

| item (sheet) | t1 | t2 | t3 | t4 | t5 |
|---|---|---|---|---|---|
| R02 512 (V03) | G → G [G] | G → G [G] | | | |
| R02 1024 (V04) | **P → G** [G] | P → D [G] | | | |
| R12 512 (V05) | **D → G** [G] | **P → G** [G] | **D → G** [G] | P → D [G] | G → G [G] |
| R12 1024 (V02) | P → D [G] | P → P [D] | P → D [G] | P → P [G] | **D → G** [G] |
| R15 512 (V01) | P → P [G] | **P → G** [G] | G → P [G] | G → G [G] | G → G [NA in Q-Q] |
| R15 1024 (V06) | P → P [P] | P → P [P] | **P → G** [D] | G → G [G] | G → G [G] |

Elements: R02 t1 street-name sign, t2 no-entry sub-plate. R12 t1 banner, t2 "Quarry Quarter" sign, t3 green sign, t4 left fascia and "Q" sign, t5 right-edge signs. R15 t1 shop sign, t2 window banner, t3 door-number decal, t4 door poster, t5 red sticker. Bold marks a legible input lost by the round trip (L).

**Classification counts:**

| | 512 | 1024 |
|---|---:|---:|
| N: readable in the original | 12 | 12 |
| S: scaled input already not legible (scaling loss) | **6** | 2 |
| K: scaled input legible | 6 | 10 |
| L: of K, round trip GARBLED or REMOVED (VAE loss) | **4** (R12 3, R15 1) | **3** (R02 1, R12 1, R15 1) |
| softened, PRESERVED → DEGRADED | 1 | 3 |
| round trip legible | 3 | 7 |

**Rules, in order:**
1. INCONCLUSIVE: no; all gates pass and K₁₀₂₄ = 10 ≥ 3.
2. VAE-IMPLICATED: no; it needs L₁₀₂₄ ≥ 5, and L₁₀₂₄ = 3.
3. BUDGET-LIMITED: no; it needs L₁₀₂₄ ≤ 1, although its 512 condition does hold (S₅₁₂ + L₅₁₂ = 10 ≥ 6).
4. VAE-CLEARED: no.
5. → **MIXED.**

**Other per-sheet results:**
- **Blind text preference:** the scaled input was preferred over the round trip on **6/6** sheets; never SAME, never the round trip.
- **Fidelity** (everything apart from lettering): the scaled input was PASS on 6/6. The round trip was PASS on 4/6 and MINOR detail-loss/blur on 2/6 (R15 512, R12 512). The rater found that loss only in 3× crops of window contents and faces.

**Robustness (descriptive; the frozen scores are not re-scored).**
- MIXED sits between two boundaries:
  - if two of the three 1024 losses had not been counted (L₁₀₂₄ = 1), the class would be **BUDGET-LIMITED**;
  - with two more (L₁₀₂₄ = 5), it would be **VAE-IMPLICATED**.
- **The rater's own flags:**
  - two of the three 1024 losses were flagged hard to judge: R12 t5, a faint fascia in the original too, and R15 t3, a "3 versus 8" call resting on 1–2 px;
  - one 512 call went the "wrong" way: R15 t3, GARBLED in the input and PRESERVED in the round trip. At 3–5 px glyph height, element calls are noisy.
- **A post-freeze, unblinded look by the session assistant** (it cannot count):
  - R02 t1 at 1024, the street sign, is a clear loss: the scaled input reads "NIEUWE UILENBURGER / STRAAT / CENTRUM", and the round trip renders wrong letters (roughly "UILENDUGER", "CENIRUM");
  - R12 t5 and R15 t3 at 1024 are borderline differences.
- **The 512 result does not depend on these calls:** the round trip keeps 3 of 12, and scaling alone removes 6.

## 3. Secondary: following Q-Q's edit-garbled text through Q-V (cross-rater; descriptive)
**E** = the 19 core units that the q4 *edit* garbled, from Q-Q's frozen sheet.

| | all | 512 | 1024 |
|---|---:|---:|---:|
| scaling (Q-V scaled input not legible) | 7 | 5 | 2 |
| VAE (input legible, round trip not) | 6 | 4 | 2 |
| regeneration (round trip legible, so the output path doesn't explain the edit's loss) | 6 | 2 | 4 |

**Caveats.** Two things differ between these comparisons, and the primary evidence is §2 only:
- **Different raters:** this is the Q-V rater against the Q-Q rater.
- **Different reference panels:** the Q-Q rater compared against the **scaled input**, while the Q-V rater compared against the **full-resolution original**. So "scaling" here mostly reflects that difference, as protocol §9 anticipated.
- The comparison "round trip 7/12 against q4 edit 4/12 legible at 1024" is cross-rater too.

**Reading.** About two thirds of the edit's garbled units are already unreadable after the output path alone (scaling or VAE): 9 of 11 at 512. At 1024 the split is even, 4 output path against 4 regeneration.

## 4. Metrics (descriptive; computed after the freeze)
**Scaled input against round trip, whole image:**

| item | SSIM | PSNR dB | MAE |
|---|---:|---:|---:|
| R02 512 / 1024 | 0.926 / 0.946 | 29.4 / 31.3 | 5.5 / 4.3 |
| R12 512 / 1024 | 0.934 / 0.943 | 30.4 / 33.4 | 4.8 / 3.7 |
| R15 512 / 1024 | 0.910 / 0.919 | 31.1 / 32.1 | 4.7 / 4.2 |

- **Text-box SSIM does not track the visual result** (boxes fixed in advance, `qv/text-boxes.json`):
  - median 0.958 where the round trip is legible (n = 10), 0.934 where it lost the text (n = 14);
  - the ranges overlap. R15-1024 t3 was lost at SSIM 0.963, while R15-1024 t2 was preserved at 0.962.
  - As in G2, a metric gate would miss this failure. None is proposed.
- **Variants** (pixel differences from the primary; never rated):
  - fp32 latents instead of bf16: max 6–22/255, mean 0.09–0.16, 30–41% of pixels differ;
  - untiled instead of tiled decode: max 20–101/255, mean 0.21–0.54, 41–75% of pixels differ.
  - The bf16 cast and the tiling both change pixels slightly. The primary path is the one the edit uses (gate).

## 5. Memory and time (descriptive; not optimisation)
| | 512 (6 runs) | 1024 (6 runs) |
|---|---|---|
| VAE load | ≈ 0.65 s | ≈ 0.65 s |
| encode | 0.40 s | 1.46 s [1.33–1.60] |
| decode (tiled) | 1.88 s [1.82–1.91] | 10.2 s [8.0–11.9] |
| primary total (load → round trip) | 3.1 s | 12.7 s |
| process wall (with startup and both variants) | ≈ 7.5 s | ≈ 32 s |
| peak footprint after the primary path | 5.19–5.98 GB | 6.05–6.93 GB |
| MLX peak (primary) | 5.51 GB | 6.10 GB |
| swap growth / critical samples | 0 / 0 | ≤ 1.72 GB / 3, all in the untiled-variant phase (end-of-run footprint up to 12.5 GB), none in the primary path |

- **Equivalence-gate run** (a 3-step E05 edit plus the harness): 18.3 s, peak footprint 8.04 GB, swap +0.7 GB, 0 critical.
- **Cost:** the diagnostic is cheap, seconds per image at a few GB.

## 6. Limitations and disclosures
- **Small study:** 3 photographs, 2 budgets, 12 elements per budget, and one rater. At 512, glyphs are 3–5 px tall, and element calls are noisy (§2 robustness).
- **The ceiling framing:**
  - The round trip is what a perfect copy of the reference would give.
  - A real edit decodes **regenerated** latents. The DiT can do worse than the ceiling (regeneration loss) and, in principle, could render text anew.
  - Q-V does not separate encoder loss from decoder loss.
- **Leaked hypothesis:** the rater's harness may load `CLAUDE.md`, which named "VAE round-trip ceiling test" as the next candidate. The panel order was randomised, and the prompt was neutral (`review/RATER-PROMPT.md`).
- **The panels reveal the budget,** because native-resolution inspection needs native sizes.
- **The original panel was downscaled** from the full-resolution staged source to a long side of 2048. The scaled input and round trip were shown at native size, never upscaled.
- **Improvement Clause items** (declared in the protocol before any output):
  - the E05 pipeline-equivalence gate;
  - the scaled-input control panel, which separates scaling loss from VAE loss;
  - the ceiling framing with the bf16 cast and tiled decode the edit uses (both confirmed by the gate);
  - two fresh-process runs for every item;
  - the 1 GB MLX cache cap that `--low-ram` applies.
- **Rater audit** (`review/RATER-AUDIT.json`):
  - 165 reads: 9 blind files and 156 crops;
  - writes: the two drafts plus helper scripts inside its own crop directory;
  - no path outside the allowed directories, and no access to the key or run records;
  - the audit's two `git ` matches are the word "digit" inside score notes (checked in the transcript); no git command was run.
- **Conditions:** the chain started with 4.3 GB of swap already in use (not a clean start). Pixels are deterministic, so this affects only the memory records. The monitor sampled about every 2.5 s, not every 1 s.
- **No exports were created;** the q8 export was not recreated; G2, Q-Q, `app/` and `config/` are untouched.

## 7. What this means
- **Chronology, kept separate:**
  - **G0:** capability shown (CAPABLE at 512 and 1024);
  - **G2:** real-world quality REJECTED (incidental text garbled; edit leakage);
  - **Q-Q:** q4 not supported as the primary cause (AGAINST);
  - **Q-V:** the output path itself loses incidental text. It is severe at 512 (a perfect copy keeps 3 of 12) and partial at 1024 (a perfect copy loses 3 of 10 legible elements, one per photo). MIXED by the pre-registered rules.
- **Unresolved:** at 1024, how the edit's text losses divide between the output path and regeneration. The cross-rater split is about 4 to 4.
- **Why that need not be resolved** (decision-relevant facts, descriptive):
  - At 512, a perfect copy of the reference already loses most of the lettering on all three photographs. No Qwen-Image-2.1 configuration at 512 can preserve this text by copying.
  - At 1024, a perfect copy still loses at least one element that the scaled input kept legible, **on every item** (within one rater): R02 t1 (the street sign; clear), R12 t5 and R15 t3 (both flagged as borderline by the rater). G2's text criterion allows no "text changed where it had to stay", so even a perfect DiT would plausibly still fail text preservation on all three items at 1024. This is descriptive; nothing is re-scored.
  - 1024 is already MARGINAL on time (≈ 592 s per edit, G2).
  - **Budgets above 1024 were not tested** in any phase. That they would be impractical on this 16 GB machine is an **untested extrapolation** from 1024 (592 s and 10.9 GB per edit, already MARGINAL). The recommendation does not rest on it.
  - So no remaining Qwen-Image-2.1 experiment at the tested budgets is likely to change the G2 outcome.
- **Recommendation (not implemented):**
  - **Stop Qwen-Image-2.1 editing work.** Keep the task research-only, as it is, or remove it if you decide to.
  - **If image editing is still a goal, the Q-A desk survey is now justified.** Q-V provides the reason a model change is needed: on this machine, the Qwen output path itself limits small-text preservation.
  - **Proposed entry screen for Q-A:** a candidate's VAE and conditioning path should keep the G2 text elements legible at a budget that fits 16 GB, checked by a round trip like this one (the harness generalises), **before** any editing gate is spent on it.

## 8. Storage
- **Kept:** the dense source checkpoint (RETAIN LOCALLY, unused by Q-V), and the canonical q4 export (only its VAE was read).
- **Not recreated:** the q8 export.
- **Outputs:** all `QV-*` / `QVGATE-*` outputs are kept (gitignored PNGs; hashes in the run records).
- **Crops (directive §11):** the rater's native-resolution crops and helper scripts are kept in `research/qwen/qv/review/rater-crops/`, and the post-freeze spot check in `review/spot-check/`, outside the scoring surface. The PNGs are gitignored; every file's sha256 is in `research/review-crops/MANIFEST.sha256`. The same manifest preserves the G2 and Q-Q rater crops (`research/review-crops/`), which were also in session-local scratch.
- **Dependabot:** the 4 alerts on the edit-venv lock are documented in `docs/REPRODUCIBILITY.md` §5.1; the lock is unchanged.
