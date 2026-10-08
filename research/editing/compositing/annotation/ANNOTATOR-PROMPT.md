# CMPF mask-annotator prompt (Phase 9), verbatim
Committed before the annotator was spawned. Fresh general-purpose subagent, background. It gets only the
source-only workspace; it is never shown an edited result.

```text
You are drawing edit masks on photographs. Everything you need is in one directory:

  /Users/nckandrw/Dev/photo-gen/research/editing/compositing/annotation/

1. Read ANNOTATOR-INSTRUCTIONS.md there first and follow it exactly. Then read cases.json and masks-template.json.
2. For each of the seven cases (R01, R05, R09, R11, R12, R15, R02), view views/<CASE>.png and views/<CASE>-grid.png with the Read tool, and draw the mask as normalised polygons.
3. Write /Users/nckandrw/Dev/photo-gen/research/editing/compositing/annotation/masks-draft.json (start from the template; fill each case as you finish it, so partial work survives an interruption).
4. Check each mask with the overlay helper named in the instructions, writing overlays and any crops ONLY to this scratch directory: /private/tmp/claude-501/-Users-nckandrw-Dev-photo-gen/a0de6674-7bd8-464e-ba17-f8acc44526b3/scratchpad/cmpf-annotator/ (crop with `sips -c <h> <w> --cropOffset <y> <x> <in> --out <scratch>/<name>.png`). Revise until each mask follows the instructions.
5. Do not open, list, search or run anything outside the annotation directory and that scratch directory (other than the helper's interpreter): no other repository files, no git, no other folders, no web. Do not look for edited versions of these photographs.

When you are done, reply with only: the cases completed and, per case, one line naming what you found ambiguous (or "none").
```
