# Blind-review protocol (adopted 2026-09-25)

**Tool:** `research/experiments/blind_stage.py`. The stages are separate commands, so no stage can silently redo another.

1. **Generate first, blind second.**
   - Images come from their own runner (ABBA order). Output filenames contain the arm, and they are never viewed by the rater.
   - The raw outputs, run logs and result JSONL stay in place.
2. **`prepare <pairs.json> <blind_dir> <seed>`**
   - Hashes every input image first; a missing input aborts before anything is created.
   - Refuses an existing `blind_dir`.
   - Writes the L/R key **atomically, before any composite exists**, then renders composites named only `Cnn.png`.
   - Writes `MANIFEST.json` (input, key and composite hashes, seed) and makes the key read-only.
3. **Score** the composites in order, recording each dimension per composite in a draft file. The key is not read.
4. **`freeze <blind_dir> <scores>`** copies the scores to `SCORES-FROZEN.*`, records the sha256 in the manifest and makes both read-only. Freezing twice is refused.
5. **`unblind <blind_dir>`** refuses unless the frozen scores and the key both still match their recorded hashes. Only then is the key printed.
6. **Failure handling:**
   - Any failure writes `INCIDENT-<ts>.json` and stops. Nothing is deleted.
   - The incident is assessed: could blinding have been compromised?
   - If artifacts are regenerated, use a new `blind_dir` (and a new seed if the old key could have been seen). The incident record is kept.

## Incident record: teab key, 2026-09-24/25 (reconstructed after the fact)
**What happened**
- `pair_metrics.py blind` wrote `teab/.blind-key-DO-NOT-OPEN.json` and then crashed while saving the first composite: `teab/blind/` did not exist (FileNotFoundError).
- I deleted the partial key file (`rm -f`) and re-ran with the same seed (20260925). That regenerated the identical mapping and all 24 composites.

**Could blinding have been compromised?**
- No. The key was never opened or printed before scores were frozen.
- The regenerated mapping is identical (same seed, same pair order), so nothing about the review changed.

**Process violation**
- The deletion removed an artifact without recording it at the time. The incident was disclosed in the final report and is recorded here.
- The new tool prevents recurrence: the directory is created before the key, the key is written atomically, reuse is refused, and failures become incident records instead of deletions.

**Evidence kept:** `teab/.blind-key-DO-NOT-OPEN.json` (regenerated), `teab/blind-scores.txt` plus its `.sha256`, and all raw images.
