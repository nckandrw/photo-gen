# Release notes: validated repository states

photo-gen has no semantic versioning. Each tag marks a **known-good, restorable state validated on the target machine** (MacBook Air M5, 16 GB, 8-core GPU, macOS 27.0; see [HARDWARE.md](HARDWARE.md)). Tags are immutable; they are never moved or rewritten.

## photo-gen-m5-16gb-v2 (2026-09-28)
The next validated state of the same application, not a new application. The changes from v1:

**Validation**
- **FAST (bf16 + 8 NFE) validated at 512², 768² and 1024²** by direct, pre-registered, blinded REFERENCE-vs-FAST gates:

  | size | REF better | FAST better | ties |
  |---|---:|---:|---:|
  | 512² | 0 | 0 | 24 |
  | 768² | 2 | 0 | 22 |
  | 1024² | 0 | 1 | 23 |

  Evidence: `research/experiments/fast-resolution-gates-report.md`. In v1, FAST was valid at 1024² only, through a chain of two gates.
- **Profile validation tightened.** Validity is now checked against one explicit table of exact combinations (`VALIDATED_COMBINATIONS`): precision + steps + resolution.
  - fp32 + 9 (REFERENCE) and bf16 + 8 (FAST): 512², 768², 1024².
  - bf16 + 9: 1024² only, its gated size.
- **Fixed mislabel:** in v1, bf16 + 9 at 512²/768² was recorded as `validated_configuration: true` although it was never gated there. It now requires `--allow-experimental`, and a regression test pins the matrix.

**Unchanged from v1**
- REFERENCE = fp32 + 9 NFE is the permanent default and canonical baseline. Regression hashes are unchanged.
- The transformer-release memory optimization stays in production (pixel-identical).
- bf16 remains explicit: only via `--profile fast` or `--precision bf16`.
- Experimental combinations (7–4 steps, other sizes, bf16 + 9 outside 1024²) are explicitly gated behind `--allow-experimental`.
- Runtime and model pins: Python 3.12.14, mflux 0.20.0, MLX / mlx-metal 0.32.2, Z-Image-Turbo q4 @ `d2d30500`.

**Added**
- MIT `LICENSE` for photo-gen's own code.
- `docs/THIRD-PARTY-LICENSES.md`.
- This file.

**Research added since v1** (does not change production)
- The sigma-schedule audit is CLOSED (an implementation difference, quality-neutral).
- The 768² cold timings and regression hashes.
- The 4-step probe acquisition audit.

**Verified before tagging:** see the tag message and the `MEMORY.md` entry of the same date (tests, CLI REFERENCE, CLI FAST at 512²/768²/1024², API smoke test, exact hashes).

## photo-gen-m5-16gb-v1 (2026-09-25)
The first preserved state, commit `db10040`.
- REFERENCE fp32 + 9 NFE at 512², 768², 1024²; FAST bf16 + 8 NFE at 1024² (chained gates).
- Transformer-release fix in production.
- Verified from a clean clone: 39/39 tests; CLI REFERENCE `fe47d88d…`, CLI FAST `7b45cfbe…`, API REFERENCE 512² `9ae59f59…`.
