# Transformer lifetime / VAE memory A/B (E06) — 1024², fp32 (production numerics)

**Question.** mflux `--low-ram` sets `model.transformer = None` after the denoise loop, but `ZImage._predict` returns `mx.compile(predict)`, and that closure still references the transformer. Does making the release effective (`exp_zimage.py --release-transformer`) lower memory without changing output?

**Design.**
- Prompts p01 (apple) and p05 (neon text), seed 42, 9 steps, `--low-ram`, fp32.
- Arms: `cur` (production) vs `rel` (holder cleared plus `gc.collect(); mx.clear_cache()` in `MemorySaver.call_after_loop`).
- Order ABBA per prompt (cur, rel, rel, cur); 8 runs from 20:50 to 21:09, run back to back straight after the 48-run A/B (sustained regime).
- Data: `vaelc/results.jsonl`, `results-mon-p0*-r*-{cur,rel}.csv`.

## Results
| arm | runs | peak footprint (GB) | VAE-phase MLX peak (GB) | MLX active entering VAE (GB) | VAE decode (s) | pixel sha256 |
|---|---:|---|---:|---:|---|---|
| cur | 4 | 7.334, 7.367, 7.362, 7.351 (mean **7.354**) | 5.697 | 3.473 | 2.94–3.02 | p01 fe47d88d…, p05 9000cfb7… |
| rel | 4 | 6.559, 6.557, 6.559, 6.557 (mean **6.558**) | 2.228 | 0.004 | 2.85–2.97 | **identical** to cur for both prompts |

- **Peak process footprint: −0.80 GB (−10.8%).**
- **VAE-phase MLX peak: −3.47 GB (−61%).** The ≈3.47 GB is exactly the q4 DiT (3.46 GB) that the compiled closure was keeping alive.
- **Output: pixel-identical** (verified by hash on both prompts, both repetitions). This is an exact change.
- **Time:** no effect. VAE decode 2.97 vs 2.91 s; denoise is unaffected (the patch acts after the loop).
- **System:** swap growth 0 in all 8 runs; memory pressure level 1 in both arms; free-memory minimum 43–54% (cur) vs 49–56% (rel).

**Why the footprint falls by only 0.8 GB when the VAE peak falls by 3.5 GB [inference]:** with the release effective, the lifetime maximum is no longer set during VAE decode. It is set during denoise (DiT weights + activations ≈ the 5.70 GB generate-phase MLX peak measured in E02), or during text encoding (3.6–3.7 GB MLX peak). The VAE phase stops being the peak-memory phase.

**Consistency with the earlier 512² check:** VAE MLX peak 5.63 → 2.16 GB, footprint 7.26 → 5.93 GB, output identical. At 512² the saving is larger because the denoise activations are smaller.

**Measurement caveat:** the `generate` phase peak printed by `exp_zimage.py` is reset by the nested `vae_decode` probe, so it is not the denoise peak. The kernel lifetime footprint is the authoritative figure.

## Verdict
**Exact and beneficial: −0.8 GB peak footprint at 1024², no speed or quality effect.**
- Recommended for photo-gen as a default-on worker patch, or better, fixed upstream (section 2 of `upstream-mflux-issue-DRAFT.md`).
- **Not yet applied to production.** It changes the validated memory profile (for the better), so it goes in with its own parity check (pixel hash must stay fe47d88d…) and user sign-off.
