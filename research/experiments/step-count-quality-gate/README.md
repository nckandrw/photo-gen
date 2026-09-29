# Step-count quality gate (research only)

**Question:** can ordinary Z-Image-Turbo at bf16 + 4 steps (then 5 and 6) replace FAST (bf16 + 8) per resolution, with no material quality loss?

- **Status:** Stage A (N = 4) PRE-REGISTERED 2026-09-29. See `protocol.md` (seeds, criteria, discrepancies, Improvement Clause).
- **Production is unchanged.** bf16 + 4, 5, 6 are CANDIDATE / QUALITY GATE PENDING.
- **Files:**
  - `protocol.md`: the pre-registration;
  - `confirm-prompts.json`: held-out prompts, written before any result;
  - `jobs-A-*.json`;
  - `run-stageA.sh`;
  - results → `benchmark.csv`, `blind-mapping.json`, `scores.csv`, `results.md`.
- **Images** stay local in `work-*/` (gitignored). Pixel hashes are recorded in the results JSONL.
