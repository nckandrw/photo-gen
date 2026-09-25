# Sigma-schedule audit: mflux resolution-dependent shift vs the official static shift 3.0

Status: **PROTOCOL PRE-REGISTERED 2026-09-25 (file written before chain P3A was launched at 14:06:41; no audit A/B image existed yet; see file mtime log in phase3-plan.md).** Results are appended below the protocol. The protocol text is not edited after generation.

No production change is made by this audit. Production keeps mflux's default schedule, by directive.

## 1. Source findings (desk audit, complete before any run)

### 1.1 Where e^μ ≈ 1.88 comes from
`mflux/models/common/schedulers/linear_scheduler.py::_get_sigmas` (mflux 0.20.0; byte-identical to upstream main 9ca480fd, 2026-09-23, md5 00757bc1…):

```
sigmas = linspace(1, 1/N, N)
mu     = m * (W * H / 256) + b,   m = (max_shift - base_shift) / (max_seq_len - base_seq_len),  b = base_shift - m * base_seq_len
sigma' = e^mu / (e^mu + (1/sigma - 1))
```

The `z-image-turbo` ModelConfig (`model_config.py`) sets `requires_sigma_shift=True` and **does not override the shift parameters**. It therefore inherits the class defaults `base_shift=0.5, max_shift=1.15, base_seq_len=256, max_seq_len=4096, sigma_shift_terminal=None`. Those are the FLUX.1 dynamic-shift constants.

W·H/256 = image tokens (VAE ×8, patch 2 → 16 px per token):

| resolution | tokens | μ | e^μ |
|---|---:|---:|---:|
| 512² | 1024 | 0.630 | **1.878** |
| 768² | 2304 | 0.847 | **2.332** |
| 1024² | 4096 | 1.150 | **3.158** |

e^μ is near 3.0 at 1024² only because 1024² equals FLUX's `max_seq_len` (4096 tokens). It is not tuned to Z-Image.

### 1.2 The official schedule
- `Tongyi-MAI/Z-Image-Turbo/scheduler/scheduler_config.json`: `FlowMatchEulerDiscreteScheduler`, `use_dynamic_shifting: false`, `shift: 3.0`.
- **Official repo** (`Tongyi-MAI/Z-Image` @ 26f23eda, `src/zimage/pipeline.py` + `scheduler.py`):
  - The pipeline *computes* μ with the same FLUX formula and passes `mu=` to `set_timesteps`.
  - The scheduler then **ignores μ**, because `use_dynamic_shifting=False`: `sigmas = shift*s/(1+(shift-1)*s)`.
  - `DEFAULT_INFERENCE_STEPS = 8`.
- **diffusers** (main 4295ee3e, `pipeline_z_image.py`): same pattern. μ is computed via `calculate_shift` ("Copied from … flux"), and `FlowMatchEulerDiscreteScheduler` applies it only if `config.use_dynamic_shifting`, which is false.
- **Result: the official schedule is resolution-independent static shift 3.0 at every resolution.**

### 1.3 Is mflux's behaviour intentional?
- mflux knows how to express a static shift: `ernie-image(-turbo)` sets `sigma_base_shift = sigma_max_shift = 1.3863` (= ln 4, i.e. static e^μ = 4). Z-Image has no such override.
- No upstream issue, PR or commit message states a rationale for dynamic shifting on Z-Image. Searched: mflux-community/mflux issues/PRs for "shift", "z-image sigma", "z-image scheduler" and "use_dynamic_shifting". The closest is PR #353 / issue #355 (a user `--shift` override), closed unmerged, with no discussion of the default.
- **Most consistent explanation:** the official pipeline computes μ, but that μ is dead code under `use_dynamic_shifting=False`. A port that applies the computed μ unconditionally reproduces exactly mflux's behaviour.
- **Classification of intent: UNVERIFIED.** The code evidence supports "implementation difference", but "porting slip" is an inference. No maintainer statement exists either way.

### 1.4 Sigmas (8 steps = FAST; the terminal 0 is omitted)
| schedule | e^μ | σ1…σ8 | max abs diff vs official |
|---|---:|---|---:|
| official static 3.0 (any resolution) | 3.000 | 1, .9545, .9000, .8333, .7500, .6429, .5000, .3000 | — |
| mflux 1024² | 3.158 | 1, .9567, .9045, .8403, .7595, .6546, .5128, .3109 | 0.013 |
| mflux 768² | 2.332 | 1, .9423, .8749, .7954, .6999, .5832, .4373, .2499 | 0.063 |
| mflux 512² | 1.878 | 1, .9293, .8492, .7578, .6525, .5298, .3849, .2115 | **0.115** |

At 9 steps (REFERENCE) the max differences are 0.013 / 0.062 / 0.116. There is no official 9-step recipe, so static-3.0 at 9 steps would itself be a non-official configuration.

At 512², mflux gives the model timesteps up to 0.115 lower (less noise) through the middle and end of the trajectory than the distilled Turbo model was trained on. The last step jumps from σ = 0.21 instead of 0.30.

### 1.5 Question 7: would changing it alter canonical behaviour? Answered from code: **yes**
- Any schedule change alters the sigmas fed to every step at every resolution, 1024² included (Δ ≤ 0.013).
- **Every** regression hash would change: 1024² `fe47d88d…` / `7b45cfbe…` / `11b19277…` and 512² `9ae59f59…` / `c70c38b0…` / `0b9cc20a…`.
- Adopting the official schedule in production would therefore be a new configuration, needing its own gate. It could not be a transparent fix.

### 1.6 Runtime (question 6), prediction from code
The schedule changes only scalar sigma values. NFE, tensor shapes, kernels and the compiled graph are unchanged, so the runtime effect should be **none**. This is to be confirmed with paired timings (§2), not asserted.

## 2. Empirical protocol

### Plumbing (done before the A/B; `sigma/parity-results.jsonl`)
- `sigma_sched.py` subclasses mflux's `LinearScheduler` and overrides only `_get_sigmas`. It is loaded through mflux's own external-scheduler hook (`--scheduler sigma_sched.X`) by `sigma_worker.py`, which wraps the **unmodified production worker**.
- The parity control `MfluxDynamicControl` (mflux's formula re-implemented through the external path) reproduced the production hashes exactly:

  | run | expected | got |
  |---|---|---|
  | 512² fp32/9 | 9ae59f59… | 9ae59f59… ✔ |
  | 512² bf16/8 | 0b9cc20a… | 0b9cc20a… ✔ |
  | 1024² bf16/8 | 7b45cfbe… | 7b45cfbe… ✔ |

  `compile_calls` = 1 and transformer release = True in every run. The sigmas dumped from the running process match §1.4.
- **Conclusion: the external-scheduler path introduces no confound.** The only variable in the A/B is the sigma values.

### Arms
- **M** = mflux default schedule: the production worker with no scheduler argument, i.e. canonical behaviour.
- **S** = `OfficialStatic3`: the official schedule, via `sigma_worker.py`.
- Identical in both arms: model (q4 @ d2d30500), **bf16, 8 steps** (the official recipe is 8 NFE), seed, prompt, resolution, `--low-ram`, transformer release on.

### Matrix
| res | prompts | seeds | pairs | role |
|---|---|---|---:|---|
| 512² | 12 (suite) | 2718, 31415 | 24 | **primary** (largest Δσ) |
| 768² | 12 | 2718, 31415 | 24 | **primary** |
| 1024² | 12 | 2718 | 12 | **sanity check**: e^μ 3.16 vs 3.0 should give near-identical images. Large differences here would point to plumbing, not the schedule. |

- Seeds 2718 and 31415 have never been used in this project (grep of all job files: only 42, 7, 1234 exist). The rater has seen no image from them.
- Order is ABBA per pair (pair i even: M then S; odd: S then M), back to back, with the 1 Hz monitor.

### Measurements
- **Per run:** wall, denoise, VAE, peak footprint, swap, pressure, pixel hash, sigmas used.
- **Per pair:**
  - PSNR/SSIM of S vs M;
  - Laplacian-variance ratio S/M, a descriptive sharpness/high-frequency proxy only, not a quality verdict;
  - paired denoise ratio S/M.
- **Blinded review:** one `blind_stage.py` directory per resolution, recording the same fields as the 8-step gate: text, composition, prompt adherence, fine texture/detail, artifacts, overall preference (L / R / =), notes.

### Pre-registered classification (per resolution, from the 24 primary pairs)
Let nS = S-better overall and nM = M-better overall.

| outcome | condition | classification |
|---|---|---|
| a | \|nS − nM\| ≤ 3, no class-level pattern, no text difference | **quality-neutral numerical difference** at this sample size (a small effect is not excluded) |
| b | nS − nM ≥ 4, or a class-level pattern favouring S (same dimension, both seeds) | **quality-relevant implementation difference**: mflux deviates from the recipe with a visible cost (bug-like). Report upstream with the evidence; no production change without a separate gate. |
| c | nM − nS ≥ 4, or a class-level pattern favouring M | **beneficial adaptation**: the mflux shift helps at this resolution, whether intended or not |

- Runtime: |median paired denoise ratio − 1| ≤ 0.03 → "no runtime effect".
- 1024² sanity check: expected outcome (a). If 1024² is not (a), the whole audit is flagged for a plumbing re-check before interpretation.

### Relation to the FAST resolution gates
The 512²/768² FAST gates (`fast-resolution-gates-report.md`) compare REFERENCE and FAST **with the same mflux schedule in both arms**. They are therefore valid within mflux whatever this audit finds; the audit answers a separate question. If outcome (b) occurs, that gate stays valid as a statement about production behaviour, and the schedule becomes a separate candidate change.

## 3. Results
(appended after generation and unblinding)

### 3.1 512² (primary), 24 pairs, bf16/8, seeds 2718 + 31415. Generated 14:28–14:48, sustained ABBA.
**Run integrity:** 48/48 rc = 0; `compile_calls` = 1 in every run. Each S run's dumped sigmas = official static 3.0; M runs used the production path.

**Blinded review** (`sigma/blind-512/`):
- key sha256 `9052a685…`;
- scores frozen before unblind: `SCORES-FROZEN.txt`, sha256 `9d1b0077…`.

| composite | pair | preference | reason (as scored blind) | winner after unblind |
|---|---|---|---|---|
| C03 | p03-s2718 | L (minor) | text-through-glass present (gibberish), almost absent in R | **M** |
| C09 | p09-s2718 | R | L had a duplicated red balloon | **M** (the S image had the artifact) |
| C24 | p12-s31415 | L | consistent top-down view; R's mugs drawn in side view | **M** |
| other 21 | — | = | — | tie |

**Tally:** M better 3 · S better 0 · ties 21.

Systematic but not quality-ranked: in p07 (vintage poster), the M image had a cream "paper" background in **both** seeds and the S image was white. Text was exact in both arms for p05 and p07, both seeds.

**Objective (S vs M, `sigma/summary-512.json`)**
| metric | value |
|---|---|
| denoise ratio S/M | median **0.999** (0.84–1.11, ABBA noise) |
| wall ratio S/M | median 0.992 |
| peak footprint | 5.40 vs 5.41 GB |
| swap growth | ≤ 2 MB |
| pressure | max 2 in both arms |
| PSNR | median 21.2 dB (min 14.0) |
| SSIM | median 0.854 (min 0.58) |
| Laplacian-variance ratio S/M | median 0.96 (0.76–1.34) |

**Classification against the pre-registered rule**
- nM − nS = 3. That is at the edge of outcome (a) (|nS − nM| ≤ 3), and short of (c) (≥ 4). There is no class-level pattern (no prompt class favoured in both seeds).
- Literal deviation, disclosed: rule (a) also requires "no text difference". C03 is a text-*presence* difference (gibberish in both, so not correctness), minor, favouring M.
- **Verdict (512²):**
  - **Not (b).** The official schedule shows no visible quality advantage; the "bug with a visible cost" hypothesis is **not supported**.
  - The result is **quality-neutral at this sample size with a weak directional lean toward mflux's default** (0 S-better).
  - Runtime: **no effect** (|0.999 − 1| ≤ 0.03).
- The images are *different samples* (median PSNR 21 dB): the schedule changes content, not quality.
- Interpretation (hypothesis, not tested): at 512², mflux's weaker shift spends more of the 8 steps at low noise, including a final step from σ = 0.21 instead of 0.30. That is consistent with the slightly higher high-frequency energy of M (Laplacian ratio S/M = 0.96).

### 3.2 768² (primary), 24 pairs, bf16/8, seeds 2718 + 31415. Generated 14:49–15:37, sustained ABBA.
**Run integrity:** 48/48 rc = 0; `compile_calls` = 1.

**Blinded review** (`sigma/blind-768/`):
- key sha256 `e3c3a067…`;
- frozen scores sha256 `be994d81…`.

| composite | pair | preference (blind) | winner after unblind |
|---|---|---|---|
| C08 | p08-s2718 | R: the L image showed two wine glasses (prompt: one) and a foreground glass cropping the kettle | **M** |
| C24 | p12-s31415 | R (minor): in the L image one cup had a handle, the others didn't | **M** |
| other 22 | — | = | tie |

**Tally:** M better 2 · S better 0 · ties 22.
- Text exact in both arms (p05, p07, both seeds).
- p12 counts correct in both arms at 768² (3 cups + 2 plates), in two rows in both.

**Objective (S vs M)**
| metric | value |
|---|---|
| denoise ratio S/M | median **1.005** (0.95–1.13) |
| wall ratio S/M | median 1.004 |
| footprint | 5.95 GB both |
| swap growth | 0 |
| PSNR | median 25.6 dB |
| SSIM | median 0.932 |
| Laplacian ratio S/M | median 0.976 |

**Verdict (768²):** outcome **(a)**, quality-neutral (nM − nS = 2, no text difference, no class-level pattern). No runtime effect. The lean again favours M. Images are closer between arms than at 512², consistent with the smaller sigma difference (max 0.063 vs 0.115).

### 3.3 Pooled 512² + 768² (descriptive, not a pre-registered test)
- 48 pairs: **M better 5, S better 0, ties 43.**
- Two-sided sign test on the 5 non-tied pairs: p = 0.0625, so not significant at 0.05.
- Four of the five M-wins were an S image with a duplicated or inconsistent object (balloon, wine glass, cup handle, mug perspective).

**Timestamp correction (disclosed):** the free-text header of the 768² score sheet says "scored ~16:00". That was a wrong estimate, written at ~15:38. The 512² header's "~14:55" is likewise approximate. The authoritative times are in each blind MANIFEST.json:
- sigma/blind-512 created 2026-09-25T14:49:02 frozen 2026-09-25T14:50:03
- sigma/blind-768 created 2026-09-25T15:37:52 frozen 2026-09-25T15:38:59
- **Review-speed disclosure:** each 24-composite review took about 1 minute of wall time between `prepare` and `freeze`. The rater (Claude) views composites in parallel batches of 4. The blinding is intact (the key was sealed and hashed, and scores were frozen before unblind). But a single AI rater at this speed is a real limitation: fine micro-detail differences are less likely to be caught than object-level ones (duplications, perspective, text).

### 3.4 1024² (sanity check), 12 pairs, seed 2718. Generated 15:37–16:19.
**Run integrity:** 24/24 rc = 0; `compile_calls` = 1.

**Objective (S vs M)**
| metric | value |
|---|---|
| PSNR | median **32.7 dB** (min 21.4) |
| SSIM | median **0.981** (min 0.89) |
| denoise ratio S/M | median 1.001 |
| Laplacian ratio S/M | median 1.007 |

**Blinded review** (`sigma/blind-1024/`, key `55b06b41…`, frozen scores `c9f68c4e…`):
- 11 ties, all near-identical pairs.
- C07 (p07): **S better**. The M image rendered the subtitle "Island of Fire" twice; S rendered it once.

**Sanity check: PASSED.** Outcome (a): near-identical images, as predicted for e^μ 3.16 vs 3.0, so there is no plumbing confound. The one text difference is the same failure class (a duplicated subtitle) already seen in both arms of earlier gates. It is a sample-level difference, not a schedule effect that can be established from one pair.

## 4. Conclusions (answers to the directive's seven questions)
| # | question | answer | confidence |
|---|---|---|---|
| 1 | where does e^μ ≈ 1.88 come from? | mflux's `LinearScheduler` applies the FLUX dynamic shift (base 0.5, max 1.15, 256→4096 tokens) to Z-Image-Turbo, which inherits the `ModelConfig` defaults; W·H/256 = 1024 tokens at 512² → μ = 0.630 | **VERIFIED** (source) |
| 2 | is it intentional mflux behaviour? | **UNVERIFIED.** No rationale found upstream. The pattern is consistent with porting the official pipeline's μ computation without its `use_dynamic_shifting=false` guard. | inference only |
| 3 | consistent with the intended Turbo recipe? | **No.** The official pipeline and diffusers use static shift 3.0 at every resolution; mflux matches it only near 1024² | **VERIFIED** (source) |
| 4 | does 768² behave similarly? | yes, to a lesser degree: e^μ 2.33, max Δσ 0.063 (vs 0.115 at 512²) | **VERIFIED** |
| 5 | does it affect image quality? | **no measurable quality cost** at 512² or 768² (24 blinded pairs each). The images differ as samples (PSNR 21–26 dB), and preferences lean toward mflux's default (pooled M 5 / S 0 of 48). At 1024² the arms are near-identical. | medium (single AI rater, 24 pairs per resolution) |
| 6 | does it affect runtime? | **no** (denoise ratio 0.999 / 1.005 / 1.001) | **VERIFIED** (measured) |
| 7 | would changing it alter canonical behaviour? | **yes**: every regression hash at every resolution | **VERIFIED** (source) |

**Classification of the discrepancy:**
- It is an **implementation difference** (source-verified).
- Its intent is unverified.
- On the evidence, it is **quality-neutral** at 512²/768², so it is **not** a bug with a visible cost.
- If anything, it is a weakly beneficial adaptation. That is not significant (sign test p = 0.06).

**Consequences**
- No production change: the schedule stays mflux's default, as directed.
- The FAST resolution gates remain valid as tests of production behaviour.
- Upstream: worth reporting to mflux as an *informational* note (the code differs from the official schedule; no measured quality cost on our suite). It should not be framed as a bug. Draft, not submitted.
