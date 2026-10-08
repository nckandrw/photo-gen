# Q-Q rater prompt (Phase 6), verbatim

This is the exact prompt given to the fresh rater subagent (`general-purpose`, background, non-interactive). It was recovered on 2026-10-08 from the session-local subagent transcript (`~/.claude-.claude-nck/projects/-Users-nckandrw-Dev-photo-gen/402b96d5-87ed-48b5-9f7c-27d6595006a4/subagents/agent-a17d9469e95020ffc.jsonl`, not committed) so that the review can be re-run identically. The rater received nothing else from the session. It read the files in its blind directory, and its harness may load `CLAUDE.md` (see the protocol's disclosures). Prompt sha256: `ac18e63a767f80c40e61830fcad68690563240780130d57fbb3d2778056583b8`.

To reuse it for another review, change only the directory paths (and the crop directory, which must be outside the repository), then spawn a **fresh** general-purpose subagent in the background.

```text
You are an independent rater of photo edits. Everything you need is in one directory:

  /Users/nckandrw/Dev/photo-gen/research/qwen/qq/review/blind/

Steps:
1. Read `RATER-INSTRUCTIONS.md` in that directory first, and follow it exactly. Then read `ITEMS.md`, `scores-template.csv` and `preference-template.csv`.
2. Score the sheets in the order ITEMS.md lists them (P01 … P08). For each sheet, view its composite `<SHEET>.png` with the Read tool. ITEMS.md says for each sheet which panel is the original, which is result A and which is result B.
3. Zoom: for any sheet you may crop any region of the composite at native resolution to inspect details (lettering, edges, textures, artifacts), as often as you like, e.g.
   `sips -c <height> <width> --cropOffset <y> <x> /Users/nckandrw/Dev/photo-gen/research/qwen/qq/review/blind/<SHEET>.png --out /private/tmp/claude-501/-Users-nckandrw-Dev-photo-gen/402b96d5-87ed-48b5-9f7c-27d6595006a4/scratchpad/qq-rater-crops/<SHEET>-<name>.png`
   (`sips -g pixelWidth -g pixelHeight <file>` gives a composite's size), then view the crop with the Read tool. Crop the same region from the original panel and from both results when you compare lettering. Write crops ONLY into that `qq-rater-crops` directory.
4. Write two files in the blind directory:
   - `/Users/nckandrw/Dev/photo-gen/research/qwen/qq/review/blind/scores-draft.csv`: start it with the exact header line of `scores-template.csv`, then APPEND the two rows `<SHEET>-A` and `<SHEET>-B` immediately after you finish scoring that sheet;
   - `/Users/nckandrw/Dev/photo-gen/research/qwen/qq/review/blind/preference-draft.csv`: start it with the exact header line of `preference-template.csv`, then APPEND one row per sheet immediately after you compare its A and B.
   Do not hold rows back to write at the end; partial sheets must survive an interruption. Use standard CSV quoting for notes that contain commas or quotes. Values must be exactly from the vocabulary in RATER-INSTRUCTIONS.md: `t1`..`t5` use PRESERVED / DEGRADED / GARBLED / REMOVED / NA for the sheet's numbered TEXT ELEMENTS and `-` for numbers the sheet does not have; an element is NA for both A and B or for neither; `quality_family` must be empty when quality is PASS.
5. Do not open, list, search or run anything outside the blind directory and the qq-rater-crops directory: no other repository files, no git commands, no other folders. Do not try to find out how results A and B were produced or which configuration made which. Judge each result only on what its composite shows against its ITEMS.md entry.

When you are done, reply with only: the number of rows written to each file, and a list of the sheets/elements that were hard to judge (sheet + element + one line each). Do not restate the scores.
```
