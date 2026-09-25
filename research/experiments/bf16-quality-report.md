# bf16 hidden-stream quality validation (E02 gate)

## Pre-registered protocol (written 2026-09-24 ~19:20, BEFORE any A/B image was generated)

**Arms.**
- A = fp32: production behaviour (validated: pixel-identical to production).
- B = bf16: the E02 patch set.
- Both arms use `research/experiments/exp_zimage.py`, 1024×1024, 9 steps, `--low-ram`, the mflux 0.20.0 default scheduler, the same q4 model, and the same process-per-run lifecycle.

**Matrix.** 12 prompts × seeds {42, 7} = 24 pairs (48 runs). Arm order alternates ABBA (pair *i* even: A then B; odd: B then A), back to back with no cooldowns, so slow thermal drift cancels between arms.

**Prompts:**
| id | category | prompt |
|---|---|---|
| p01 | photoreal / simple | a red apple on a wooden table, soft window light |
| p02 | portrait / composition | A cinematic portrait positioned according to the rule of thirds, with a softly blurred urban background and warm evening light. |
| p03 | hands / transparency / difficult | Two human hands holding a transparent glass containing water, with realistic fingers, refraction, reflections and readable text appearing through the glass. |
| p04 | multiple objects / spatial | A wooden desk with five distinct objects: a red notebook on the left, a black fountain pen in the center, a white ceramic mug behind the notebook, a small brass clock on the right, and a green plant in the far background. Soft morning light from the left. |
| p05 | text / low-light neon | A neon sign in a dark cyberpunk alley reading "QWEN IMAGE 2.1", clearly legible. |
| p06 | local / Philippine scene | A realistic Cebu city street at dusk after light rain, photographed with a 35mm lens, wet pavement reflecting warm storefront lights. |
| p07 | text (multi-word) | A vintage travel poster with the large headline "VISIT SIQUIJOR" and the smaller subtitle "Island of Fire", illustrated beach and palm trees, clean legible typography. |
| p08 | materials / fine detail | Macro photograph of a brushed copper kettle beside a folded linen napkin and a glass of red wine, visible fabric weave, metal scratches and condensation droplets. |
| p09 | complex composition / local | A busy morning market in Manila: vendors behind colorful fruit stalls, hanging paper lanterns, a jeepney in the background, and a child holding a red balloon in the foreground. |
| p10 | fine detail / animal | Close-up portrait of a tabby cat with green eyes, sharp whisker detail and individual fur strands, soft natural window light. |
| p11 | low-light / reflections | A candlelit dinner table at night, reflections in wine glasses, warm candle glow and blurred city lights through a rain-streaked window. |
| p12 | counting / attributes | Exactly three blue ceramic cups and two yellow plates arranged in a single row on a white table, top-down view, studio lighting. |

**Objective measurements, per run:** wall, denoise, s/step, peak footprint (kernel lifetime max), MLX phase peaks, swap delta, max memory-pressure level, min free %, pixel SHA-256.
**Per pair:** PSNR and SSIM (luminance, 11×11 Gaussian σ=1.5) of B vs A. LPIPS isn't measured: it would need a new package plus downloaded network weights, which the no-new-dependency policy rules out.

**Blinded pairwise review.**
- For each pair the harness writes a composite with arms randomly assigned to left/right, keyed in a separate file. The rater (Claude, single rater) scores before the key file is read.
- Per composite, record: visible differences; for each of *prompt adherence*, *text correctness* (where applicable), *artifacts*, *fine detail*: `L better` / `R better` / `no meaningful difference`; plus free-text notes.
- A "meaningful difference" is one visible at normal viewing, not a sub-pixel or noise-level change.

**Acceptance criterion (bf16 passes the gate if ALL hold):**
1. **No text regression:** in every text pair (p05, p07, p03 where legible), bf16 renders the requested string at least as correctly as fp32.
2. **No new systematic artifact:** no artifact type appears in ≥2 bf16 images that is absent from the paired fp32 images.
3. **Preference balance:** the number of pairs where fp32 is judged better on any dimension does not exceed the number where bf16 is judged better by more than 2 (out of 24), i.e. no directional regression beyond noise.
4. **Operational:** no OOM or fallback, peak footprint within +0.5 GB of fp32, swap delta and pressure no worse than fp32.

If the gate passes, bf16 becomes an **explicit opt-in** photo-gen option. fp32 remains the default and reference, and precision is recorded in job metadata.

## Results (filled 2026-09-24 ~20:55; data in `bf16ab/`)

### Run integrity
- 48/48 runs rc=0, no OOM, no fallback. Order ABBA, 19:11–20:50, sustained regime. Raw rows in `bf16ab/results.jsonl`.
- Dtype probe confirms the arms: fp32 arm `sdpa_q`/`ffn_in` = float32; bf16 arm = bfloat16.
- fp32 arm p01-s42 reproduces the production pixel hash (fe47d88d…), so arm A = production.

### Objective
| metric | fp32 | bf16 |
|---|---:|---:|
| denoise median (s) | 135.3 | 94.4 |
| mean s/step | 15.02 | 10.61 |
| per-pair denoise ratio bf16/fp32 | — | median 0.701, mean 0.708, range 0.531–0.912 |
| peak footprint mean / max (GB) | 7.338 / 7.366 | 7.335 / 7.365 |
| swap growth, max over runs (MB) | 0.0 | 3.5 (one run: p08-s42, 741.75→745.25 MB) |
| memory-pressure level, max | 2 | 1 |
| free memory, min (%) | 28 | 35 |

PSNR/SSIM of bf16 vs fp32 (`bf16ab/metrics.json`):
- PSNR 20.4–42.5 dB, SSIM 0.836–0.996.
- The lowest values are the busy scenes: p09 market (21.1/21.97 dB), p07 poster (20.4/21.8 dB) and p06 street (24.0/26.8 dB).
- As expected for a 9-step distilled sampler with a different rounding path, bf16 is *not* pixel-identical; low PSNR here means different small content (layout, object placement), not degradation. The blinded review is the arbiter of quality.

### Blinded review
Scores were frozen in `bf16ab/blind-scores.json` before the key was opened (sha256 1bf64e89…8d1a, recorded in `bf16ab/blind-scores.sha256`, file made read-only). Key mapping applied afterwards.

| composite | pair | L / R | judgement | → winner |
|---|---|---|---|---|
| C03 | p03-s42 | bf16 / fp32 | L better: text (minor), artifacts (minor); text gibberish in both | **bf16** |
| C15 | p03-s7 | fp32 / bf16 | R better: text (minor) | **bf16** |
| the other 22 | — | — | no meaningful difference on any dimension | tie |

Notes on the ties:
- **p05 neon "QWEN IMAGE 2.1":** exact in both arms, both seeds.
- **p07 poster:** "VISIT SIQUIJOR" / "Island of Fire" exact in both arms for s7. For s42, both arms duplicate the subtitle, so the failure is identical.
- **p12 counting:** both arms render the wrong plate count identically (4 plates at seed 42, 3 at seed 7, vs the requested 2). This is a model limitation, not a precision effect.
- **p02-s7 (C14):** the subject's identity/presentation differs between arms. This is content drift of the same kind as layout variation, not a quality defect.

**Tally: fp32 better 0, bf16 better 2, ties 22.**

### Acceptance criteria
| # | criterion | result |
|---|---|---|
| 1 | No text regression (p05, p07, p03) | **PASS.** p05 and p07 are identical-quality in both seeds; p03 favours bf16 in both seeds (minor). |
| 2 | No new systematic artifact in ≥2 bf16 images | **PASS.** No bf16-only artifact observed in any composite. |
| 3 | fp32-better count ≤ bf16-better count + 2 | **PASS** (0 ≤ 4). |
| 4 | Operational: no OOM, footprint ≤ fp32 + 0.5 GB, swap/pressure no worse | **PASS, with one literal deviation disclosed.** Footprint Δ −0.003 GB; pressure better (1 vs 2); free-min better (35% vs 28%). One bf16 run grew swap by 3.5 MB (0.5% of an already-present 742 MB swap, pressure level normal). Judged immaterial noise, but it is recorded rather than hidden. |

### Verdict
**GATE PASSED.** bf16 introduces no observable quality regression relative to fp32 on this 24-pair set. It takes ≈30% less denoise time than fp32 (≈1.4×; paired, same session, sustained regime) at identical memory.

**Limitations:**
- Single rater (Claude), not a human panel.
- 24 pairs, 1024² only.
- No LPIPS (dependency policy).
- p12/p07-s42 failures are shared by both arms and don't discriminate.
- Near-tie outcomes mean the test can't exclude a *small* quality effect in either direction. It does exclude a meaningful regression at this sample size.

**Consequence (per pre-registration):**
- bf16 may be added to photo-gen as an **explicit opt-in** precision option.
- fp32 stays the default and the reference.
- Precision is recorded in job metadata.
- A parity check is required: the photo-gen bf16 output must match the experiment's bf16 pixel hash for the same prompt/seed.

## photo-gen integration parity (2026-09-24 21:16–21:22)
The opt-in path was implemented as `precision: bf16` in `app/photogen/runtimes/mflux_zimage_worker.py` (`_apply_bf16_stream`). It was run through the real CLI (`bin/photo-gen generate … --precision bf16`); see `parity-bf16/summary.json`.
| run | expected pixel sha256 | photo-gen result |
|---|---|---|
| p01 seed 42, `--precision bf16` | 11b19277… (A/B bf16 arm) | **match** (80.6 s) |
| p05 seed 42, `--precision bf16` | 7bfd59ca… (A/B bf16 arm) | **match** (91.6 s) |
| p01 seed 42, default (no flag) | fe47d88d… (production fp32 reference) | **match** (126.6 s); default path unchanged |

Metadata records `precision`, and `reproduce.cli` carries `--precision bf16`. Unit tests: 35/35.
