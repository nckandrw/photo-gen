# G2 rater instructions (provenance-blind)

You are scoring image edits. Each item is ONE composite image `<ID>.png`:
- landscape images: **top = the original photograph**, **bottom = the edited result**;
- portrait images: **left = the original photograph**, **right = the edited result**.
`ITEMS.md` gives, per ID, the edit instruction, what MUST CHANGE and what MUST NOT CHANGE.

Read ONLY the files in this directory (`ITEMS.md`, this file, the `<ID>.png` composites, `scores-template.csv`).
Do not open any other file in the repository. You are not told which model, settings or run produced an item, and
you must not try to find out. Score every item on its own merits, in the order listed in ITEMS.md.

Score in this order (the first dimension that fails matters most):

| dimension | PASS | PARTIAL / MINOR | FAIL / MAJOR |
|---|---|---|---|
| adherence | the MUST CHANGE is fully present and recognizable | present but incomplete or wrong in an attribute (shade, partial removal/recolour, wrong object type, leftovers) | absent, or a different change |
| preservation | every MUST NOT CHANGE element is recognizably unchanged (small global tone/sharpness shifts are allowed) | exactly ONE listed element materially altered, OR one unrequested object added or removed | scene regenerated, identity of a person/object lost, or >= 2 listed elements materially altered |
| composition | layout, viewpoint and framing unchanged | - | layout, viewpoint, crop or zoom changed |
| quality | natural, no visible artifact | MINOR: visible but not distracting | MAJOR: distracting or unrealistic (seams/halos, grain/grid, malformed objects, smeared texture, implausible lighting, heavy over-sharpening) |
| text (only where ITEMS.md says "text: scored") | exact wording, no duplication/dropped letters/ghosting, legible | legible but a minor glyph/style deviation | wrong or misspelled word, garbled, duplicated or ghosted letters, illegible, or text changed where it had to stay |

For quality MINOR or MAJOR, name the artifact family in `quality_family`, one of: seam/halo, grain/grid,
malformed-object, texture-smear, lighting-mismatch, colour-cast, detail-loss/blur, ghosting/duplication,
oversharpening, other:<one word>. Leave it empty for PASS. Use `text = NA` where text is not scored.
Write one short factual note per item (what you saw that decided the scores).

Output: a CSV with exactly the header of `scores-template.csv`
(id,adherence,preservation,composition,quality,quality_family,text,notes), one row per ID, values exactly as above.
