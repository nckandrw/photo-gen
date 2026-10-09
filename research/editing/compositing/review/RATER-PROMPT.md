# CMPF rater prompt (Phase 9), verbatim
Committed before the rater was spawned. Fresh general-purpose subagent, background. Neutral: it names no method,
hypothesis or earlier result. The rater's harness may load `CLAUDE.md` (disclosed in PROTOCOL.md §7).

```text
You are an independent rater of edited photographs. Everything you need is in one directory:

  /Users/nckandrw/Dev/photo-gen/research/editing/compositing/review/blind/

1. Read RATER-INSTRUCTIONS.md there first and follow it exactly. Then read ITEMS.md and scores-template.csv.
2. Score the sheets in the order ITEMS.md lists them (S01 … S07). For each sheet view <SHEET>-ORIGINAL.png and each version <SHEET>-<LABEL>.png with the Read tool; use <SHEET>-ORIGINAL-FULL.png for full-resolution reference. Inspect details at native resolution by cropping the same region from the reference and from each version (sips -g pixelWidth -g pixelHeight <file> gives sizes; versions and references differ in size, so scale crop offsets accordingly), e.g.
   sips -c <h> <w> --cropOffset <y> <x> <file> --out /private/tmp/claude-501/-Users-nckandrw-Dev-photo-gen/a0de6674-7bd8-464e-ba17-f8acc44526b3/scratchpad/cmpf-rater/<name>.png
   Write crops and any helper files ONLY into that cmpf-rater directory.
3. Write /Users/nckandrw/Dev/photo-gen/research/editing/compositing/review/blind/scores-draft.csv: start with the exact header line of scores-template.csv, then APPEND the rows of a sheet (one per version, revision 1) immediately after you finish that sheet. The file is append-only: to change an earlier row, append a new row with the same id and revision + 1; never edit or delete rows. Use standard CSV quoting for notes with commas or quotes. Use exactly the vocabulary in RATER-INSTRUCTIONS.md.
4. Do not open, list, search or run anything outside the blind directory and the cmpf-rater directory: no other repository files, no git, no other folders, no web. Do not try to find out how the versions were produced.

When you are done, reply with only: the number of rows written (including revisions), and a list of the sheet/version/field calls that were hard to judge (one line each). Do not restate the scores.
```
