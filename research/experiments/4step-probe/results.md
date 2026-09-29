# 4-step probe: results and classification

**Classification: C — REJECTED** (as a speed/quality candidate), with one **E — new research direction** noted. Details below.

Production is unchanged: no profile, config, registry, hash or tag was modified.

## Identity (verified before use; `asset-manifest.json`)
- **A / B:** Z-Image-Turbo q4, `mflux-community/z-image-turbo-mflux-q4` @ `d2d30500`, verified by `photo-gen verify`. The cold A run reproduced the production FAST hash `7b45cfbe…`.
- **C:** Z-Image **base** q4, `mflux-community/z-image-base-mflux-q4` @ `087eaf40` (Apache-2.0), plus `alibaba-pai/Z-Image-Fun-Lora-Distill` @ `f9a4db41`, file `Z-Image-Fun-Lora-Distill-4-Steps-2603-ComfyUI.safetensors` (Apache-2.0).
  - 15/15 files verified against HF digests.
  - The LoRA applied to **204 layers, 612/612 keys matched** (`lora-keycheck.stdout.txt`).
  - Runtime adapters (`--no-bake-lora`), `linear` scheduler, guidance 0, bf16 patch. 24/24 benchmark runs had `--no-bake-lora` and `linear` in their argv.
- **Runtime:** mflux 0.20.0, MLX / mlx-metal 0.32.2, 1024², `--low-ram`, transformer release on.

## Comparison (1024²; sustained = median of 24 runs each; cold = one run each after 600 s idle)
| metric | A: Turbo 8 (FAST) | B: Turbo 4 | C: Base + 4-step LoRA |
|---|---:|---:|---:|
| wall, cold | 53.8 s | 29.9 s | 32.3 s |
| wall, sustained | 94.2 s | 50.1 s | 53.3 s |
| denoise, cold | 48.5 s | 24.5 s | 26.3 s |
| denoise, sustained | 87.8 s | 43.7 s | 46.3 s |
| per-step, sustained | 10.98 s | 10.92 s | 11.57 s (LoRA side branch +6%) |
| VAE, sustained | 2.88 s | 2.85 s | 2.86 s |
| model load | 1.03 s | 1.04 s | 1.79 s (LoRA load +0.75 s) |
| peak memory | 5.85 GB | 5.85 GB | **6.69 GB** |
| swap growth | 0 | 0 | 0 |
| memory pressure, max | 1 | 1 | **2** (warn) |
| **paired denoise ratio vs A** (median, 23 pairs) | 1.00 | **0.504** | **0.541** |
| **paired denoise ratio C/B** | — | — | **1.062** |
| grid16 (16-px periodicity; ≈ 1 = none) | 1.11 (0.94–1.62) | 1.10 (0.85–1.36) | **5.4 (3.9–11.5)** |
| prompt adherence (blind, pairs decided by adherence) | A 5 vs C 8 | B 5 vs C 6 | **on par / slightly ahead** (6–5, 8–5; not significant) |
| composition (blind) | = | = | = |
| text (blind) | 1 duplicate ("IMAGE" ×2) | 1 garbled line | exact in both p05/p07 seeds |
| fine detail / visual (blind, pairs decided by visual quality) | A won 11 of 11 | B won 13 of 13 | **lost all 24**: consistent grain / grid |
| **overall blind result** | beats C **16–8** | beats C **18–6** | loses both; A vs B = 2 / 3 / 19 ties |

- Timing pairs exclude p10-s4242, which straddles the pause.
- Cold wall ratios vs A: B 0.555, C 0.600.

## Answers to the directive's questions
| # | question | answer |
|---|---|---|
| **Q1** | Is C meaningfully faster than FAST? | **Yes:** denoise 0.54×, wall 0.58× (sustained, paired); cold wall 0.60×. It meets the pre-registered bar (≤ 0.60 denoise and ≤ 0.65 cold wall). But **Turbo 4 is faster still** (0.50×): C costs +6% per image over plain Turbo 4, from the LoRA side branch. |
| **Q2** | Is C materially better than Turbo 4? | **No, it is worse overall:** C 6 vs B 18 (the rule needed C − B ≥ +4). **All 18 B wins that weren't adherence-decided came from C's grain.** On adherence alone C was 6–5, which is not significant. No text regression (C was better on p05-s6174). |
| **Q3** | Does C approach FAST quality? | **No:** A − C = 16 − 8 = 8, the boundary of "approaching" (≤ 8). Given Q2, this is moot. |
| **Q4** | Different memory? | **Yes, +0.84 GB** (6.69 vs 5.85 GB) from the runtime LoRA. Pressure reached level 2 in some C runs. Baking would remove the side branch, but mflux's bake transient needed 10.5 GB peak and swapped (smoke test). **Material** by the pre-registered +0.5 GB rule. |
| **Q5** | Different thermal behaviour? | **No distinct behaviour** beyond the constant +6% per-step. Per-step times rise with position identically for A, B and C (A 8.92 → 11.15 s, B 8.91 → 11.34 s, C 9.57 → 12.17 s from the first to the last third). |
| **Q6** | New failure mode? | **Yes: a 16-px periodic grain/grid** (the DiT patch size) in C images: grid16 3.9–11.5 in all 24 C images vs ≤ 1.62 in every A/B image. It meets the pre-registered rule (≥ 2 C images, 0 A/B). It is not caused by bf16 or baking, and it is far stronger without the LoRA or with a high-σ schedule, which points to incomplete denoising of the base model at 4 steps. |

## Classification
**C — REJECTED.**
- The pre-registered rule is "REJECTED if Q2 is no". A specialised 4-step Base + LoRA **does not outperform simple step reduction on Turbo**, at 1024² on this M5:
  - it is slower (+6%);
  - it uses more memory (+0.84 GB);
  - it has a new grain artifact;
  - it lost the blinded review to Turbo 4 by 6–18.
- **The directive's hypothesis is not supported** for this adapter and model lineage.

**Why it failed** (directive §17):
- **Quality:** yes, but **specifically visual quality**. The base model + this LoRA at 4 NFE leaves visible residual structure (grain), even with a near-official schedule. Prompt adherence was not worse (6–5 / 8–5).
- **Speed:** no. C is ≈ as fast as Turbo 4, but not faster.
- **Memory:** yes. The runtime adapter costs +0.84 GB; baking is impractical on 16 GB in mflux 0.20.0.
- **Scheduler:** partly. The base CLI default schedule is much worse (grid16 38). `linear` was the best available choice. A schedule sweep might reduce the grain, but it was not tested (see E below).
- **Lineage:** Turbo was distilled *with RL post-training on the full model*. The PAI LoRA is a rank-128 adapter on the base. Turbo's 8-step distillation already makes it robust at 4 steps.
- **LoRA compatibility:** fine (612/612 keys, clean application).

**E: new research directions.**
- *(E1, lower value)* C lost only on grain, and its adherence was not worse. A test of whether the grain disappears with another scheduler, 5–6 steps, or the 2-step/8-step LoRA variants could revisit C. **Deprioritised:** even grain-free, C would at best tie Turbo 4 on speed, and it costs +0.84 GB.
- *(E2, the most useful finding)*
- **Turbo 4 was blind-equivalent to Turbo 8 at 1024²** (A 2 / B 3 / 19 ties) at **0.50× denoise**.
- This contradicts the earlier unblinded step-sweep's "preview quality" label for 4 steps. That review used 400-px contact sheets at seed 42, so it was coarse and unblinded.
- It suggests the cheapest real speed-up is **not a new model but a properly gated lower step count on Turbo**.
- **Recommendation:** run a pre-registered, direct blinded FAST (bf16/8) vs bf16/4, 5 and 6 gate on the established protocol (72 pairs, three resolutions, fresh seeds).
- It stays **EXPERIMENTAL** until that gate passes. The probe does not change the production profiles.

## Disclosures
- **Pause:** the sustained block was paused 2026-09-28 22:52 → 2026-09-29 08:55 (user request).
  - The chip was *not* cooler after the resume: the laptop had been in use. Per-step times after the resume were similar or higher.
  - Timing claims use per-condition paired ratios. The one straddling condition is excluded.
- **Smoke-test deviations** (`README.md` §Smoke): LoRA baking was found and corrected to runtime adapters before the benchmark, and the grid metric was added before the benchmark.
- **Blinding:** C's grain made its images recognisable as a style. See `quality-results.md`.

## Artifacts
- **Committed (text):** `experiment-config.json`, `asset-manifest.json`, `benchmark.csv` (72 rows with run position, gap, timings, memory, grid16, pixel hash), `metrics-summary.json`, the results JSONL, the blind manifests, frozen scores and unblinded keys, `lora-keycheck.stdout.txt`.
- **Local only (gitignored):** images in `work*/`, composites, `models/research/`.
