# G2 rater prompt (Phase 5), verbatim

This is the exact prompt given to the fresh rater subagent (`general-purpose`, background, non-interactive). It was recovered on 2026-10-08 from the session-local subagent transcript (`~/.claude-.claude-nck/projects/-Users-nckandrw-Dev-photo-gen/402b96d5-87ed-48b5-9f7c-27d6595006a4/subagents/agent-aea8756bf210b8408.jsonl`, not committed) so that the review can be re-run identically. The rater received nothing else from the session. It read the files in its blind directory, and its harness may load `CLAUDE.md` (see the protocol's disclosures). Prompt sha256: `06c822370b076f26e922bfdd0a77bdcbafffea49e917c6a23cd825d18d0c318b`.

To reuse it for another review, change only the directory paths (and the crop directory, which must be outside the repository), then spawn a **fresh** general-purpose subagent in the background.

```text
You are an independent rater of photo edits. Everything you need is in one directory:

  /Users/nckandrw/Dev/photo-gen/research/editing/real-world/g2/blind/

Steps:
1. Read `RATER-INSTRUCTIONS.md` in that directory first, and follow it exactly. Then read `ITEMS.md` and `scores-template.csv`.
2. Score the items in the order ITEMS.md lists them (Q01 … Q40). For each item, view its composite `<ID>.png` with the Read tool. ITEMS.md says for each item which panel is the original and which is the edited result.
3. Zoom: for any item you may crop any region of the composite at native resolution to inspect details (lettering, edges, textures, artifacts), as often as you like, e.g.
   `sips -c <height> <width> --cropOffset <y> <x> /Users/nckandrw/Dev/photo-gen/research/editing/real-world/g2/blind/<ID>.png --out /private/tmp/claude-501/-Users-nckandrw-Dev-photo-gen/402b96d5-87ed-48b5-9f7c-27d6595006a4/scratchpad/rater-crops/<ID>-<name>.png`
   (`sips -g pixelWidth -g pixelHeight <file>` gives a composite's size), then view the crop with the Read tool. Write crops ONLY into that `rater-crops` directory.
4. Write `/Users/nckandrw/Dev/photo-gen/research/editing/real-world/g2/blind/scores-draft.csv`: start it with the exact header line of `scores-template.csv`, then APPEND one row per item immediately after you finish scoring that item (do not hold rows back to write at the end; a partial sheet must survive an interruption). Use standard CSV quoting for notes that contain commas or quotes. Values must be exactly from the vocabulary in RATER-INSTRUCTIONS.md; `text` must be NA unless ITEMS.md says "text: scored" for that item; `quality_family` must be empty when quality is PASS.
5. Do not open, list, search or run anything outside the blind directory and the rater-crops directory: no other repository files, no git commands, no other folders. Do not try to find out which model, settings or run produced an item. Judge each item only on what its composite shows against its ITEMS.md entry.

When you are done, reply with only: the number of rows written, and a list of the items that were hard to judge (ID + one line each). Do not restate the scores.
```
