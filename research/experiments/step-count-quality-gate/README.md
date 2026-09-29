# Step-count quality gate (research only)

**Question:** can ordinary Z-Image-Turbo at bf16 + 4 steps (then 5 and 6) replace FAST (bf16 + 8) per resolution, with no material quality loss?

- **Status:** Stage A (N = 4) PRE-REGISTERED 2026-09-29. See `protocol.md` (seeds, criteria, discrepancies, Improvement Clause).
- **Stage A (N = 4) DONE:** 512² VALIDATED (→ ULTRA profile), 768²/1024² REJECTED.
- **Stage B (N = 5) DONE 2026-09-29:** VALIDATED at 512², 768² (narrowest possible pass) and 1024². Not in production. See `results.md` § Stage B, `protocol-stageB.md`, `stage_metrics.py`.
- **Stage C (N = 6):** not started (separate decision).
- **Files:**
  - `protocol.md`: the pre-registration;
  - `confirm-prompts.json`: held-out prompts, written before any result;
  - `jobs-A-*.json`;
  - `run-stageA.sh`;
  - results → `benchmark.csv`, `blind-mapping.json`, `scores.csv`, `results.md`.
- **Images** stay local in `work-*/` (gitignored). Pixel hashes are recorded in the results JSONL.
