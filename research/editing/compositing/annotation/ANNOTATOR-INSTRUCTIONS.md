# Mask annotation instructions (source-only)

You are drawing **edit masks** for seven photo-editing tasks. For each task you see only the **source photograph**
and the task description in `cases.json`: instruction, must_change, must_not_change, what, and text elements to
protect. You are not shown any edited result, and you must not look for one. Read only the files in this directory.

## What a mask is used for
An image editor will produce an edited version of each photograph. The final image is then assembled as

    final = (1 − α) · original + α · edited

where α comes from your mask:
- **α = 0 outside your mask**: those pixels stay exactly as in the original photograph.
- **Inside your mask, α ramps linearly from about 0 at the mask edge to 1 at 16 px inside** (measured at a
  1184-px-long-side canvas; the band scales with the canvas, ≈ 1.35 % of the long side). Further inside, α = 1: those
  pixels come entirely from the edited image.
- Mask edges that lie on the image border are not ramped.
- No automatic enlargement or shrinking is applied. Your polygons are used exactly as drawn.

## What to include
Mark every region the requested edit may legitimately change, so that the edited content inside the mask is complete
and nothing that should change is left outside it:
- the target object or region itself, including its attachments (e.g. things carried on or attached to it);
- shadows and contact areas the target casts or touches, reflections of the target (wet ground, glass, glossy
  surfaces), and anything visibly coloured or lit by it if the edit would change that;
- for a **removal**: the area the object covers plus its shadow and reflection, so the revealed background can be
  filled;
- for an **addition**: the plausible area where the new object, and its shadow, could appear according to the
  instruction;
- a **margin** of your choice, remembering that the outer ~16 px band of the mask still shows part of the original.
  For a removal, an object edge sitting inside that band would partly show through.

## What to exclude
- Content the instruction does not ask to change, especially everything in `must_not_change`.
- **Every text element listed in `text_elements_to_protect`, and any other lettering not targeted by the instruction.**
  Keep the mask off it, with its feather band, if you can do so without cutting the target.
- Do not make the mask much larger than needed: everything inside it may be re-synthesised by the editor.

## Format
Copy `masks-template.json` to `masks-draft.json` **in this directory** and fill in, per case:
- `polygons`: a list of polygons. Each polygon is a list of `[x, y]` points in **normalised source coordinates**: x
  from 0 (left) to 1 (right), y from 0 (top) to 1 (bottom). The editable region is their union. Use as many polygons
  and points as needed, but keep them simple.
- `components`: the parts included, e.g. `["target", "contact shadow", "reflection on wet road", "attachment: roof load"]`.
- `rationale`: 1–3 sentences on why the mask has this shape and margin.
- `difficulty`: `STRAIGHTFORWARD` or `AMBIGUOUS`, with the ambiguity named in the rationale.

The grid views (`views/<case>-grid.png`) show normalised coordinates: lines every 0.05, labelled every 0.1. To check a
mask, render it over the source:

    /Users/nckandrw/Dev/photo-gen/mflux/.venv/bin/python3.12 /Users/nckandrw/Dev/photo-gen/research/editing/compositing/annotation/overlay.py /Users/nckandrw/Dev/photo-gen/research/editing/compositing/annotation/masks-draft.json <CASE> <SCRATCH>/<CASE>-overlay.png

and view the result. `<SCRATCH>` is the scratch directory named in your prompt; write overlays and crops only there.
You may revise your polygons as often as you like **before you hand back**. That is your own drafting against the
source photograph, which is allowed. Once you hand back, the masks are frozen.
