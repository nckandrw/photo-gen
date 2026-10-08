# Q-VR rater prompt (Phase 8), verbatim

This is the exact prompt given to the fresh rater subagent (general-purpose, background, non-interactive). It was
committed before the rater was spawned. It is neutral: it names no model, runtime, budget, hypothesis or earlier
result. The rater's harness may load `CLAUDE.md` (disclosed in `PROTOCOL.md` §10).

```text
You are an independent rater of processed photographs. Everything you need is in one directory:

  /Users/nckandrw/Dev/photo-gen/research/qwen/qv-reference/review/blind/

Steps:
1. Read `RATER-INSTRUCTIONS.md` in that directory first, and follow it exactly. Then read `ITEMS.md` and `scores-template.csv`.
2. Score the sheets in the order ITEMS.md lists them (S01 … S07). For each sheet, view `<SHEET>-ORIGINAL.png` and each version `<SHEET>-<LABEL>.png` with the Read tool. ITEMS.md gives each sheet's kind ("item" or "edit"), its version labels and their native pixel sizes, its TEXT ELEMENTS and, for an edit sheet, the INSTRUCTION.
3. Inspect lettering at native resolution: crop the same region from ORIGINAL and from each version, as often as you like, e.g.
   `sips -c <height> <width> --cropOffset <y> <x> /Users/nckandrw/Dev/photo-gen/research/qwen/qv-reference/review/blind/<FILE>.png --out /private/tmp/claude-501/-Users-nckandrw-Dev-photo-gen/a0de6674-7bd8-464e-ba17-f8acc44526b3/scratchpad/qvr-rater-crops/<name>.png`
   (`sips -g pixelWidth -g pixelHeight <file>` gives a file's size; ORIGINAL is larger than the versions, so scale your crop offsets by the size ratio), then view the crop with the Read tool. Do not enlarge crops with smoothing; judge what the pixels show. Write crops ONLY into that `qvr-rater-crops` directory.
4. Write one file in the blind directory: `/Users/nckandrw/Dev/photo-gen/research/qwen/qv-reference/review/blind/scores-draft.csv`. Start it with the exact header line of `scores-template.csv`, then APPEND the rows of a sheet (`<SHEET>-A`, `<SHEET>-B`, …, one per version) immediately after you finish scoring that sheet. Do not hold rows back to write at the end; partial sheets must survive an interruption. Use standard CSV quoting for notes that contain commas or quotes. Values must be exactly from the vocabulary in RATER-INSTRUCTIONS.md: `t1`..`t5` use PRESERVED / DEGRADED / GARBLED / REMOVED / NA for the sheet's numbered TEXT ELEMENTS and `-` for numbers the sheet does not have; an element is NA for every version of a sheet or for none (NA only when ORIGINAL itself is unreadable); on "item" sheets fill fidelity/fidelity_family and put `-` in adherence/seam/realism/unintended; on "edit" sheets fill adherence/seam/realism/unintended and put `-` in fidelity/fidelity_family; `fidelity_family` must be empty when fidelity is PASS.
5. Do not open, list, search or run anything outside the blind directory and the qvr-rater-crops directory: no other repository files, no git commands, no other folders. Do not try to find out how the versions were produced. Judge each version only on what its image shows against ORIGINAL and its ITEMS.md entry.

When you are done, reply with only: the number of rows written, and a list of the sheets/elements that were hard to judge (sheet + version + element + one line each). Do not restate the scores.
```
