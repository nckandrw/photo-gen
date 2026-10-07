# PHOTO-GEN editing benchmark (v1)

**This benchmark belongs to PHOTO-GEN, not to any model.** The definitions, sources, metrics and rubric here are model-independent.

```text
PHOTO-GEN BENCHMARK
├── Generation  → research/experiments/ (Z-Image; the step-count, FAST and BALANCED gates)
└── Editing     → research/editing/
    ├── synthetic controls → this suite (v1, E01–E11, Z-Image-generated sources; gates G0/G1)
    └── real world         → research/editing/real-world/ (real camera photographs; gate G2, Phase 5)
                  results per backend: research/qwen/ (Qwen-Image-2.1 on mflux 0.21.0; the sd.cpp comparator)
```

**Phase 5 (2026-10-07).** This suite is the **synthetic-control** half of the editing benchmark. It stays in place (no files moved) because committed reports and tools reference its paths. The real-photograph half, gate G2, is in `real-world/` and is now the main quality evidence; see `real-world/README.md`.

**Pre-registered 2026-10-07, before any benchmark edit was run.** It was committed with `suite-v1.json`. Sources are generated and frozen first, then `regions.json` is written, and only then are edits run.

## 1. Suite
`suite-v1.json` has 11 tests, one per category of directive §9:
- object replacement;
- addition;
- removal;
- colour/material;
- background;
- style;
- localized;
- preservation of untouched regions;
- composition-preserving;
- text-preserving;
- text replacement.

Each test specifies its source, instruction, expected change, expected preserved elements and edit scope (local, background or global).

- **Sources.** Z-Image REFERENCE (fp32 + 9, 1024²) generated through `bin/photo-gen generate`. They are deterministic (byte-identical regeneration was established for this backend in Phase 1–3), carry no third-party licence, and their PNGs are never committed. Identity (prompt, seed, pixel sha256, file sha256) goes into `sources.json`, and every seed attempt is recorded.
- **Instructions.** Taken verbatim from, or patterned on, official documentation (`instruction_source` per test): the Qwen-Image-2.1 card, the mflux 0.21.0 reference README, the sd.cpp Qwen-2.1 doc, the Qwen-Image-Edit-2509 card, and the directive's own example. None is invented for convenience except E09, whose pattern is disclosed.
- **Change regions (`regions.json`).** For each local edit: normalized boxes `[x0, y0, x1, y1]` of where the change is expected, drawn on the frozen source **before any edit is run**. Background and global edits have no region; their preservation is judged on structure (§3).

## 2. Evaluation dimensions
The generation hierarchy (1 prompt adherence, 2 composition, 3 visual quality) gains a **4th: preservation**. Did the model change what it was asked to, and nothing else? Each test is scored per dimension:

| dimension | PASS | PARTIAL / MINOR | FAIL / MAJOR |
|---|---|---|---|
| **edit adherence** | the requested change is fully present and recognizable | present but incomplete or wrong in an attribute (shade, partial removal, wrong object type) | absent, or a different change |
| **preservation** | every `expected_preserved` element is recognizably unchanged (small global tone/sharpness shifts allowed) | exactly one listed element materially altered, or an unrequested object added or removed | scene regenerated, identity lost, or ≥ 2 listed elements altered |
| **composition** | layout and viewpoint unchanged | — | layout or viewpoint changed |
| **visual quality** | natural, no visible artifact | MINOR: visible but not distracting (soft edges, slight tone shift) | MAJOR: seams, grain/grid, malformed objects, heavy over-sharpening |
| **text** (E10, E11) | exact letters, legible, style kept | legible but misspelled or restyled | illegible, missing or garbled |

The rater is disclosed with every score sheet. In v1 it is the AI assistant running the session, as in the Phase 3 gates.

## 3. Objective aids (`edit_metrics.py`)
These are descriptive only and never override a visual verdict.
- **Preservation outside the change region** (local edits): MAE, PSNR and SSIM between the source (Lanczos-resized to the output size) and the output, excluding the region dilated by 3% of the image side.
- **Change magnitude inside the region:** MAE inside the region, as a proxy for whether anything happened there.
- **Structure** (all edits): correlation of Sobel edge maps between source and output, a proxy for composition and layout preservation that also applies to global/background edits.

## 4. Gate G0: capability and reliability (per backend × output resolution)
This is the first gate (directive §24). No meaningful model-versus-model control exists yet, so G0 tests capability, not equivalence.

- **R (reliability):**
  - all 11 edits complete with rc 0 and a non-blank, correctly sized output;
  - no watchdog abort: swap growth > 6 GB or critical memory pressure for ≥ 20 consecutive seconds. Thresholds are as in `research/qwen/run_edit.sh`.
  - Any miss → **NOT RELIABLE**.
- **D (determinism):** one test (E05) is repeated and must reproduce its pixel sha256. A miss withdraws any determinism claim and is disclosed.
- **C (capability):** all four conditions must hold:
  - adherence PASS on ≥ 7 of 11;
  - adherence PASS or PARTIAL on ≥ 9 of 11;
  - preservation PASS or PARTIAL on ≥ 8 of 11;
  - no more than 2 MAJOR quality defects.
- **Verdict:** **CAPABLE** (R, D and C hold), **LIMITED** (R and D hold, C fails), or **NOT RELIABLE**.
- **Scope.** G0 never makes a configuration "validated" for production. It decides whether the backend proceeds to a blinded quality gate and production hardening.

## 5. Gate G1: runtime A/B, blinded (bounded)
- **Arms:** the selected backend (mflux 0.21.0 q4) against the serious alternative runtime (sd.cpp `master-908`, Q4_K DiT + official Qwen3-VL-8B-Instruct Q4_K_M + mmproj) on the same sources, instructions and output size.
- **Procedure:** blind with `research/experiments/blind_stage.py` (prepare → score → freeze → unblind).
- **Score:** per pair, which side is better on adherence → preservation → quality (lexicographic), or tie.
- **Bounding** (Improvement Clause): sd.cpp's measured Qwen-2.1 t2i cost on this machine (813.9 s at 1024², memory-critical) makes the full suite impractical. G1 uses the 512 budget and a subset, and it stops early if an sd.cpp edit exceeds 20 min or trips the watchdog. Stopping is a recorded result.

## 6. Storage
- **Committed:** definitions, `sources.json`, `regions.json`, per-run JSON (requests, results, monitors), score sheets, metrics and reports.
- **Not committed:** PNGs (sources, outputs, composites), per the repository image policy. Every PNG's identity is recorded by sha256.
