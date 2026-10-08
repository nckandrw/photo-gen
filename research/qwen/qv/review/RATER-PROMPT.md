# Q-V rater prompt (Phase 7), verbatim

This is the exact prompt given to the fresh rater subagent (general-purpose, background, non-interactive). It was committed before the rater was spawned. It is neutral: it names no model, budget, hypothesis or earlier result. The rater's harness may load `CLAUDE.md` (disclosed in `PROTOCOL.md` §6).

```text
You are an independent rater of processed photographs. Everything you need is in one directory:

  /Users/nckandrw/Dev/photo-gen/research/qwen/qv/review/blind/

Steps:
1. Read `RATER-INSTRUCTIONS.md` in that directory first, and follow it exactly. Then read `ITEMS.md`, `scores-template.csv` and `preference-template.csv`.
2. Score the sheets in the order ITEMS.md lists them (V01 … V06). For each sheet, view its composite `<SHEET>.png` with the Read tool. ITEMS.md says for each sheet where the ORIGINAL, version A and version B are, and the native pixel size of A and B.
3. Inspect lettering at native resolution: crop the same region of ORIGINAL, A and B, as often as you like, e.g.
   `sips -c <height> <width> --cropOffset <y> <x> /Users/nckandrw/Dev/photo-gen/research/qwen/qv/review/blind/<SHEET>.png --out /private/tmp/claude-501/-Users-nckandrw-Dev-photo-gen/402b96d5-87ed-48b5-9f7c-27d6595006a4/scratchpad/qv-rater-crops/<SHEET>-<name>.png`
   (`sips -g pixelWidth -g pixelHeight <file>` gives a composite's size), then view the crop with the Read tool. Do not enlarge crops with smoothing; judge what the pixels show. Write crops ONLY into that `qv-rater-crops` directory.
4. Write two files in the blind directory:
   - `/Users/nckandrw/Dev/photo-gen/research/qwen/qv/review/blind/scores-draft.csv`: start it with the exact header line of `scores-template.csv`, then APPEND the two rows `<SHEET>-A` and `<SHEET>-B` immediately after you finish scoring that sheet;
   - `/Users/nckandrw/Dev/photo-gen/research/qwen/qv/review/blind/preference-draft.csv`: start it with the exact header line of `preference-template.csv`, then APPEND one row per sheet immediately after you compare its A and B.
   Do not hold rows back to write at the end; partial sheets must survive an interruption. Use standard CSV quoting for notes that contain commas or quotes. Values must be exactly from the vocabulary in RATER-INSTRUCTIONS.md: `t1`..`t5` use PRESERVED / DEGRADED / GARBLED / REMOVED / NA for the sheet's numbered TEXT ELEMENTS and `-` for numbers the sheet does not have; an element is NA for both A and B or for neither (NA only when ORIGINAL itself is unreadable); `fidelity_family` must be empty when fidelity is PASS.
5. Do not open, list, search or run anything outside the blind directory and the qv-rater-crops directory: no other repository files, no git commands, no other folders. Do not try to find out how versions A and B were produced. Judge each version only on what its composite shows against ORIGINAL and its ITEMS.md entry.

When you are done, reply with only: the number of rows written to each file, and a list of the sheets/elements that were hard to judge (sheet + element + one line each). Do not restate the scores.
```
