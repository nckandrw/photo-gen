# Steps, NFE and sigma schedules: mflux vs the official Z-Image-Turbo recipe (2026-09-25)

**Why this exists:** a discrepancy found while preparing the 8-step gate. photo-gen's README said "9 steps (the official Turbo configuration: 8 DiT evaluations)". That is **false for mflux**.

## Verified facts
1. **mflux runs one DiT evaluation per requested step.**
   - Source: `ZImage.generate_image` loops `for t in config.time_steps` with `time_steps = range(init_time_step, num_inference_steps)`, calling `predict` once per t (mflux 0.20.0, identical on upstream main 9ca480f).
   - Timing agrees: denoise ≈ 10.3–10.45 s × N for N = 4…8 (step-sweep).
   - **So mflux `--steps 9` = 9 NFE.**
2. **The official "9 steps = 8 DiT forwards" was a diffusers artifact.**
   - The model card says `num_inference_steps=9, # This actually results in 8 DiT forwards`.
   - diffusers PR #13730 (merged 2026-05-29, commit 32ecbe38) explains why: the old pipeline set `scheduler.sigma_min = 0.0`, so the 9-step schedule was `[1.0, 0.875, …, 0.125, 0.0, 0.0]`, i.e. 8 meaningful updates plus 1 no-op.
   - diffusers now defaults to **8 steps** = the same 8 meaningful updates, with no wasted forward.
3. **The official sigma schedule is static shift 3.0** (`scheduler_config.json`: `use_dynamic_shifting: false`, `shift: 3.0`) and doesn't depend on resolution: base `linspace(1, 1/8, 8)` → `3s/(1+2s)` = [1, .9545, .9000, .8333, .7500, .6429, .5000, .3000] → 0.
4. **mflux applies a resolution-dependent exponential shift instead** (`LinearScheduler`: μ from width × height/256, base_shift 0.5, max_shift 1.15; `sigma_shift_terminal=None`):

| config | e^μ | sigmas (before the terminal 0) |
|---|---:|---|
| mflux 8 steps @1024² | 3.158 | 1, .9567, .9045, .8403, .7595, .6546, .5128, .3109 |
| mflux 9 steps @1024² | 3.158 | 1, .9619, .9170, .8633, .7979, .7164, .6123, .4743, .2830 |
| mflux 8 steps @512² | 1.878 | 1, .9293, .8492, .7578, .6525, .5298, .3849, .2115 |
| official (any resolution) | 3.000 (static) | 1, .9545, .9000, .8333, .7500, .6429, .5000, .3000 |

## Consequences
- **mflux 8 steps @1024² ≈ the official Turbo trajectory:** same 8 NFE, sigmas within ≈0.01–0.013, because e^μ = 3.16 vs 3.0.
- **The photo-gen REFERENCE (fp32 + 9 steps) is 9 NFE on a finer, non-canonical schedule:** one extra evaluation beyond the distillation recipe.
  - It remains the validated, reproducible reference (unchanged, by directive).
  - It must not be described as "the official 8-NFE configuration".
- **The 8-step gate is still a valid empirical A/B within mflux.** Its interpretation is "does removing mflux's extra step, i.e. returning to ≈ the canonical 8-NFE schedule, cost quality?", not "does going below the recipe cost quality?".
- **At 512² mflux's shift is much weaker** than the official static 3.0: e^μ 1.88, sigmas lower through the middle of the trajectory.
  - Consequence for quality: **not measured**. Hypothesis only; not included in the upstream issue without evidence.
  - Candidate future check: an A/B of mflux default vs a static-3.0 custom schedule at 512², if mflux exposes custom sigmas without source modification.
- **Earlier docs used "8 NFE" loosely for mflux's 9-step runs** (cache-audit framing, paper map). Corrected wording: "9 steps = 9 NFE in mflux". The cache audit measured 8 transitions between 9 evaluations; its numbers are unaffected.

## Not changed
The scheduler, the sigma computation and any mflux file (standing constraints). This note only corrects documentation and interpretation.
