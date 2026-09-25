# Production transformer-release fix: final regression gate and merge (2026-09-25)

## Mechanism (not "garbage collection")
```
MemorySaver.call_after_loop (--low-ram): model.transformer = None
        ↓
but ZImage._predict returned mx.compile(predict), and predict's closure still references the transformer;
generate_image keeps that function in its local `predict` through VAE decode
        ↓
the q4 DiT (≈3.47 GB) stays resident during VAE decode
        ↓
fix: predict reads the transformer from a holder dict; after the loop the holder is cleared
     (transformer AND compiled function), then gc.collect() + mx.clear_cache()
        ↓
the transformer has no remaining references → reclaimable before VAE decode
```
- **Code:** `app/photogen/runtimes/mflux_zimage_worker.py::_install_transformer_release`. It is the same holder design as the verified experiment (`exp_zimage.py --release-transformer`).
- **Unchanged:** the predict body is mflux 0.20.0's (same calls, same M1/M2 no-compile branch). No mflux files change.
- **Control:** the worker request field `release_transformer` (runtime sends `true`), recorded per job as `effective_parameters.transformer_release`.

## Gate design
- **Harness:** the real production worker (`prod_runner.py` → `python -m photogen.runtimes.mflux_zimage_worker`), same environment as the runtime. The only difference between arms is `release_transformer` false/true.
- **Matrix:** {fp32, bf16} × {512², 1024²} × {pre, post} × 2 reps, ABBA per config (16 runs, 05:06–05:22). p01 prompt, seed 42, 9 steps.
- **Data:** `memfix/results.jsonl`, `memfix/work/*.result.json`, `memfix/work/*.mon.csv`.
- **Earlier failed attempts, preserved:** a harness PIL import error (0 runs) and a relative-path error (16 × rc=1, the worker never started). See `memfix-console-attempt{1,2}-*.log` and `memfix/results-attempt2-relpath-error.jsonl`.

## Results
| config | pixel sha256 (all 4 runs) | peak footprint pre → post (GB) | VAE-phase MLX peak pre → post | process MLX peak pre → post |
|---|---|---|---|---|
| fp32 512² | 9ae59f59… (= production 512² reference) | 6.88 / 7.26 → 5.92 / 5.93 | 5.63 → 2.16 | 5.63 → 3.61 |
| fp32 1024² | fe47d88d… (= production 1024² reference) | 7.26 / 7.35 → 6.56 / 6.56 | 5.70 → 2.23 | 5.70 → 3.61 |
| bf16 512² | c70c38b0… | 7.00 / 7.25 → 5.41 / 5.41 | 5.63 → 2.16 | 5.63 → 3.61–3.72 |
| bf16 1024² | 11b19277… (= gated bf16 reference) | 7.26 / 7.33 → 5.84 / 5.84 | 5.70 → 2.23 | 5.70 → 3.61 |

- **Pixel output:** identical pre vs post in every configuration and repetition. Repeatability: 4/4 identical hashes per configuration.
- **Memory:** post-fix footprint is lower and *more consistent* (pre varies 6.88–7.35 GB; post is flat to ±0.01 GB).
  - bf16 benefits most at 1024² (−1.46 GB): its denoise-phase peak is lower than fp32's, so once the VAE-phase retention is gone, its lifetime peak falls further.
- **Swap / pressure:** 0 MB in all 16 runs; pressure level 1–2 in both arms.
- **Recompilation:** `mx.compile` was called exactly once per run in both arms (passive `compile_calls` probe). No hidden recompilation.
- **Startup cost:** load 1.07–1.13 s and text-encode 0.64–0.74 s in both arms. No extra worker startup cost.
- **Scheduler / random state / post-processing:** unchanged. The identical pixel hashes prove the same latents, schedule and decode.
- **Clean exit:** rc=0 for all 16. Process time = wall − 0.2–0.3 s (no hang at exit).

**Runtime**
| config | denoise pre (s) | denoise post (s) | median s/step pre / post |
|---|---|---|---|
| fp32 512² | 17.88, 18.10 | 17.80, 17.75 | 1.92–1.97 / 1.93–1.94 |
| bf16 512² | 18.79, 18.31 | 18.66, 18.39 | 2.02 / 2.01–2.06 |
| bf16 1024² | 80.68, 80.14 | 83.55, 81.00 | r1 pair **8.89 / 8.89** |
| fp32 1024² | 85.58, 112.92 | 105.31, 110.28 | 9.45 → 12.51 over the session (thermal ramp) |

- **fp32 1024²:** the chip was heating through this block. The pre arm went 85.6 → 112.9 s across the ABBA, and the adjacent r1 pair shows post *faster* (110.3 vs 112.9 s).
- **VAE time:** unchanged within noise (0.38–3.05 s; the largest value is a post run in the hottest part of the session).
- **Verdict:** no material runtime regression. The fix acts after the denoise loop, and the per-step medians match when thermal state matches.

## Verdict: GATE PASSED; merged into production (2026-09-25)
- The runtime sends `release_transformer: true` for every job (both precisions).
- **Tests:** `app/tests/test_worker_lifetime.py`, run against the real mflux classes with a stand-in transformer:
  1. documents the upstream retention (fails if upstream fixes it → re-evaluate);
  2. asserts the fix makes the transformer unreachable after `call_after_loop` and records `released: true`.
- **Reference preserved:** fp32/9 output is pixel-identical (fe47d88d… at 1024², 9ae59f59… at 512²). Only the memory profile changes, which the README and manifest notes now reflect.

## End-to-end check through the real photo-gen CLI (2026-09-25 ~08:50, `e2e/summary.json`)
`bin/photo-gen generate --prompt '<p01>' --seed 42 [--profile …]` at 1024², run back to back:
| run | pixel sha256 | transformer_release | mx.compile calls | peak footprint | wall |
|---|---|---|---:|---:|---:|
| `--profile reference` | fe47d88d… ✔ | released | 1 | 6.559 GB | 83.3 s |
| `--profile fast` | 7b45cfbe… ✔ | released | 1 | 5.834 GB | 66.6 s |
| no profile (default) | fe47d88d… ✔ | released | 1 | 6.560 GB | 122.8 s (third run, heat-soaked) |

The merged fix reproduces in the application itself (runtime → worker), not only in the test harness.
