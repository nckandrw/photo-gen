# Release notes: validated repository states

photo-gen has no semantic versioning. Each tag marks a **known-good, restorable state validated on the target machine** (MacBook Air M5, 16 GB, 8-core GPU, macOS 27.0; see [HARDWARE.md](HARDWARE.md)). Tags are immutable; they are never moved or rewritten.

## Unreleased (`main`, after v4; not a validated tag): Phase 7 Q-V diagnostic
**No tag; local commits.** Text-to-image and the app are unchanged since v4. Research only:
- **Q-V** (`research/qwen/QWEN-QV-DIAGNOSTIC.md`): a VAE-only round trip of the staged G2 photos, bit-exact against the edit's path.
  - At 512 it keeps 3/12 incidental-text elements legible; at 1024, 7/12. The pre-registered class is MIXED.
  - Recommendation: stop Qwen-Image-2.1 editing work.
  - Qwen stays research-only, G2 REJECTED, Q-Q AGAINST.
- **Dependabot:** the 4 alerts on the edit-venv lock are documented (`docs/REPRODUCIBILITY.md` §5.1); the lock is unchanged.

## photo-gen-m5-16gb-v4 (2026-10-08): Phase 5 (real-photograph editing gate: Qwen editing REJECTED) + Phase 6 (corrections, explicit status, Q-Q diagnostic)
**Tag:** `photo-gen-m5-16gb-v4`, an annotated tag on the Phase 6 closing commit (`git rev-list -n1 photo-gen-m5-16gb-v4`). It contains the 15 Phase 5 commits after v3 (`0d15f49` … `63c24a5`) and the Phase 6 commits after them, with no history rewritten. v3 (`401e400`) is unchanged.

**Text-to-image production behaviour is unchanged since v3:** the same profiles, `VALIDATED_COMBINATIONS` and regression hashes. Phase 5 added backend-identity stamping to the Z-Image runtime (`51d4d6a`) and re-verified the regression set 5/5 exactly (`6d95ada`). Phase 6 changed no Z-Image runtime, worker or manifest code, and re-checked REFERENCE 512² and ULTRA 512² through the real CLI before tagging (PHASE6-INDEX §2).

**Phase 6 (2026-10-08):**
- **Corrections** (`e7e0b61`; docs only, marked in place): R04's task label (black olives), criterion S counted as FAIL marks, and approximate times replaced by commit times. Frozen G2 scores unchanged.
- **Explicit status in the app** (`a4f9d57`):
  - `/capabilities` and `/status` report `tasks["image-edit"].status = "research-only"`, plus a `quality_status` record: integration validated · capability validated (G0) · quality G2 REJECTED · local production REJECTED · research/testing opt-in only · Qwen Research License, non-commercial.
  - The job warning, the no-opt-in error and the CLI help name G2.
  - `validated: false` and `--allow-experimental` are unchanged, and `configuration_id` is unchanged.
- **Q-Q diagnostic** (`research/qwen/QWEN-QQ-DIAGNOSTIC.md`): q8 against q4 weights on G2's six text failures, with arm-blind paired review. Result **AGAINST**: higher precision did not materially reduce incidental-text corruption (1 of 19 garbled elements rescued; text FAIL 6/6 in both arms). q4 is not supported as the primary cause.
  - The q8 export (18.46 GB) was deleted after its identity was recorded.
  - The source checkpoint is still retained, unchanged.

**Phase 5 (2026-10-07):**
- **Text-to-image unchanged:** profiles and `VALIDATED_COMBINATIONS` are as in v3. The Phase 5 app reproduced the Z-Image regression set exactly (5/5 at `6d95ada`, `research/qwen/memory/preflight/zimage-*.json`); no Z-Image runtime, worker, job, store or manifest code changed after that run. The Z-Image sidecar is still pinned by its golden test.
- **Backend identity:**
  - every job row has a `backend_id`, stamped from the runtime's manifest; a `schema_migrations` migration backfilled the old rows;
  - at execute time a job whose backend, model, revision or manifest no longer matches is refused;
  - edit sidecars carry `configuration_id` (manifest + steps + output resolution) and `edit_id` (adds input pixels, instruction, seed).
- **Edit memory policy P2** (adopted, pixel-identical on 5/5 pairs): the text encoder is released after encoding, and only a lazy VAE copy is kept during denoise. 1024 peak footprint 12.08 → ~10.9 GB; 512 peak 8.9 → 8.2 GB (`research/qwen/QWEN-MEMORY-LIFETIME.md`).
- **Inputs:** a camera MPO (multi-picture JPEG) is staged as its primary image, with a warning. This photo-gen defect was found while acquiring G2's sources (`e653122`).
- **Real-photograph editing gate G2: REJECTED at 512 and 1024** (`research/editing/real-world/results.md`).
  - Adherence 0 FAIL on the 16 primary items per budget (one second-seed FAIL at 512).
  - Preservation 4 FAIL at each budget: incidental text garbled, edits leaking to adjacent objects.
  - 45/45 runs clean; repeats bit-identical.
  - Memory/UX: 512 COMFORTABLE, 1024 MARGINAL.
  - **Editing is not a production feature.** It stays a research opt-in (`--allow-experimental`, `validated: false`). The Qwen Research License forbids commercial use in any case.
- **Assets:** the byte-identical duplicate q4 export was deleted (+10.67 GB). The 33 GB source checkpoint is retained locally, with a deletion trigger (`research/qwen/QWEN-ASSET-PROVENANCE.md`).
- **Tests:** 92/92 at Phase 5 close; **93/93 at v4**. **Resume indexes:** `research/qwen/PHASE5-INDEX.md`, `research/qwen/PHASE6-INDEX.md`.

## photo-gen-m5-16gb-v3 (2026-10-07): Phase 4 close, `401e400`
**Tag:** `photo-gen-m5-16gb-v3`, an annotated tag on `401e400`. It was created and pushed at the start of Phase 5, before any Phase 5 change, and is immutable. It marks text-to-image production plus the Phase 4 experimental editing integration, before Phase 5's hardening and quality gate. The changes it contains since v2:
- **Since v2 (2026-09-29):** ULTRA (bf16 + 4, 512² only) and BALANCED (bf16 + 5, 1024² only) profiles, each with its own blinded gate (`research/experiments/step-count-quality-gate/results.md`). Their CLI end-to-end check was closed 2026-10-06 (BALANCED `befe1b3c…`, 768² refused).
- **Phase 4 (2026-10-07): image-task layer + experimental Qwen editing.**
  - **Task layer:** explicit task router (`text-to-image` → Z-Image, `image-edit` → Qwen); one queue, store, GPU lock and API.
  - **API/CLI:** `POST /edit` and `photo-gen edit` / `verify --edit`; additive API fields only.
  - **Backend:** Qwen-Image-2.1 (Qwen Research License, non-commercial) on mflux 0.21.0 in a separate venv. Every edit is experimental; benchmark gate G0 (capability) is recorded in `research/qwen/QWEN-EDITING-QUALITY.md`.
  - **Z-Image unchanged.** The real regression through the refactored app gave fe47d88d, 7b45cfbe, befe1b3c, 6aa2b842 and API 9ae59f59, all exact. The cold BALANCED wall was 35.6 s (recorded 36.1 s). The sidecar is pinned by a golden test. 72/72 tests.

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
