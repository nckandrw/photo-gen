# 4-step probe: Z-Image Base + 4-step LoRA vs Z-Image-Turbo (research only)

**Status:** PRE-REGISTERED 2026-09-28. This README, `experiment-config.json`, `blind-protocol.md` and `asset-manifest.json` were written before any benchmark image existed.

**Production is untouched:**
- no change to `app/`, `config/`, the profiles, the validated hashes or the v2 tag;
- the experimental weights live in the gitignored `models/research/`;
- the worker is `probe_worker.py`. It imports and reuses the production worker's patches and probes but does not modify them.

## Hypothesis
A model *specifically adapted* for 4-step generation gives a better speed/quality trade-off on the M5 than Turbo simply sampled at 4 steps.

## Candidates (1024², bf16, `--low-ram`, transformer release on)
| id | model | steps = NFE | scheduler | CFG | notes |
|---|---|---:|---|---|---|
| **A** TURBO FAST | Z-Image-Turbo q4 @ `d2d30500` | 8 | `linear` (mflux default for Turbo) | off (forced) | = production FAST |
| **B** TURBO 4 | same | 4 | `linear` | off | the step-reduction control (EXPERIMENTAL) |
| **C** BASE + 4-STEP LORA | Z-Image **base** q4 @ `087eaf40` + `Z-Image-Fun-Lora-Distill-4-Steps-2603` @ `f9a4db41`, scale 1.0 | 4 | `linear`, a **deliberate deviation from the base CLI default** | off (guidance 0.0) | **a different lineage, not Turbo.** The LoRA was trained for the base model. |

## Discrepancies found before running (Discrepancy Clause)
1. **Scheduler.**
   - mflux's Z-Image *base* CLI defaults to `flow_match_euler_discrete`. At 4 steps and 1024² its empirical μ gives e^μ ≈ 9.9, so σ = 1, 0.967, 0.908, **0.767** → 0, and the last Euler step jumps from σ 0.77 to a clean image.
   - The LoRA card recommends the "simple" scheduler, and says its 2603 version is adapted to sigmas below 0.5. The official Z-Image `scheduler_config` is static shift 3.0: σ = 1, 0.900, 0.750, 0.500 → 0.
   - mflux `linear` at 1024² gives 1, 0.905, 0.759, 0.513 → 0, within 0.013 of static 3.0. It is the same built-in scheduler A and B use.
   - **C therefore uses `linear`.** The base default is run as a smoke-only variant (C_fm) so its behaviour is documented, not assumed.
2. **Precision.**
   - mflux's native stream is fp32 (the E01/E10 promotion). A and B use production's bf16 patch.
   - C uses the *same* patch, so the precision is equal across arms. The patch targets the shared `ZImage` modules.
   - The smoke test checks it with a dtype probe, and compares against a native-fp32 variant (C_fp32).
3. **CFG.** The base model supports CFG. The LoRA "distills both steps and CFG", so C runs guidance 0.0 (mflux encodes no negative prompt at guidance ≤ 1): one forward per step, the same NFE accounting as Turbo.
4. **LoRA application:** runtime, unfused (`x·A·B` side branch, rank 128). This adds real compute (≈ 5% estimated), which the timings include. `--bake-lora` is not used, to avoid altering the q4 weights.
5. **The model pack for A/B declares no license** (see `docs/THIRD-PARTY-LICENSES.md`). C's assets are Apache-2.0.

## Stages
1. **Smoke + cold** (one image each, p01, seed 42, each run after 600 s idle): A, B, C, then the smoke-only C_fm and C_fp32.
   - Checks: loads, the LoRA applies, completes, image valid and not blank, dtype probe, metadata, worker exit/cleanup, peak footprint.
   - **The benchmark runs only if C passes.**
2. **Sustained benchmark:** 12 suite prompts × seeds {4242, 6174} × {A, B, C} = 72 runs.
   - The per-condition order rotates through all 6 permutations, so position is balanced.
   - Recorded per run: position, start time, gap since the previous run.
3. **Blinded review** (`blind-protocol.md`): pairwise C vs B, C vs A, A vs B.
4. **Analysis and report** (`results.md`, `quality-results.md`, `benchmark.csv`).

## Pre-registered decision rules (per the directive's §14–15)
- **Q1, meaningfully faster than FAST:** C/A paired denoise ratio ≤ 0.60 (median, sustained) *and* cold wall ratio ≤ 0.65.
- **Q2, materially better than Turbo-4:** in C vs B, C-better − B-better ≥ 4 of 24, with no text regression in p05/p07 (C at least as correct as B in every pair).
- **Q3, close to FAST:** in C vs A, A-better − C-better ≤ 3 → *competitive*; ≤ 8 → *approaching*; > 8 → *inferior*.
- **Q4, memory:** peak footprint difference vs A; material if > +0.5 GB.
- **Q5, thermal:** per-step time vs position in the sustained block, compared with A and B at matched positions.
- **Q6, new failure modes:** any artifact type seen in ≥ 2 C images and in no A/B images.

**Classification:**
- **A PROMISING:** Q1 yes + Q2 yes + Q3 competitive or approaching + no new systematic failure mode.
- **B INTERESTING BUT INFERIOR:** Q1 yes + Q2 yes + Q3 inferior.
- **C REJECTED:** Q2 no (no advantage over plain step reduction), or Q1 no.
- **D BLOCKED:** the smoke test fails for technical reasons.
- **E NEW RESEARCH DIRECTION:** unexpected behaviour (e.g. a scheduler effect) that suggests a better experiment.

In every case the result stays **EXPERIMENTAL**. Nothing enters production without its own validation.
