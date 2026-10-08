# Rater instructions (arm-blind paired review)

Each sheet is ONE composite image `<SHEET>.png` with three panels of the same scene:
- portrait scenes: **left = the original photograph**, **middle = result A**, **right = result B**;
- landscape scenes: **top = the original photograph**, **middle = result A**, **bottom = result B**.
A and B are two edited results of the same original and the same instruction, produced by two configurations of an
image-editing system. You are not told how the configurations differ or which is which, and you must not try to find
out. `ITEMS.md` gives, per sheet, the instruction, what MUST CHANGE, what MUST NOT CHANGE, and a numbered list of
TEXT ELEMENTS (lettering in the original that must stay unchanged).

Read ONLY the files in this directory (`ITEMS.md`, this file, the `<SHEET>.png` composites, the two templates).
Do not open any other file in the repository. You may crop any region of a composite at its native resolution
(for example `sips -c <h> <w> --cropOffset <y> <x> in.png --out <file>`), writing crops ONLY to a scratch directory
outside the repository; crops are views of the same composite. Score every sheet in the order listed in ITEMS.md.
Score A and B each on their own merits (one row each, ids `<SHEET>-A` and `<SHEET>-B`), then compare them.

## 1. Per result (scores-draft.csv; one row per result; score in this order)
| dimension | PASS | PARTIAL / MINOR | FAIL / MAJOR |
|---|---|---|---|
| adherence | the MUST CHANGE is fully present and recognizable | present but incomplete or wrong in an attribute (shade, partial removal/recolour, wrong object type, leftovers) | absent, or a different change |
| preservation | every MUST NOT CHANGE element is recognizably unchanged (small global tone/sharpness shifts are allowed) | exactly ONE listed element materially altered, OR one unrequested object added or removed | scene regenerated, identity of a person/object lost, or >= 2 listed elements materially altered |
| composition | layout, viewpoint and framing unchanged | - | layout, viewpoint, crop or zoom changed |
| quality | natural, no visible artifact | MINOR: visible but not distracting | MAJOR: distracting or unrealistic (seams/halos, grain/grid, malformed objects, smeared texture, implausible lighting, heavy over-sharpening) |
| text | exact wording, no duplication/dropped letters/ghosting, legible | legible but a minor glyph/style deviation | wrong or misspelled word, garbled, duplicated or ghosted letters, illegible, or text changed where it had to stay |

For quality MINOR or MAJOR name the artifact family in `quality_family`: seam/halo, grain/grid, malformed-object,
texture-smear, lighting-mismatch, colour-cast, detail-loss/blur, ghosting/duplication, oversharpening, other:<one word>.
Leave it empty for PASS.

**Text elements `t1`..`t5`** (the numbered TEXT ELEMENTS of the sheet; `-` for numbers the sheet does not have):
- `PRESERVED`: the same wording as in the original is readable, and the lettering looks like the original's
  (allowing the softening any resize causes);
- `DEGRADED`: the same wording is still correctly readable, but the glyphs are visibly deformed, smeared or partly missing;
- `GARBLED`: the wording can no longer be read as the original's: wrong, invented or duplicated letters, gibberish, or
  unreadable where the original panel is readable (say in the note whether it is wrong letters or blur);
- `REMOVED`: the element or its lettering is gone or replaced by something else;
- `NA`: the element's lettering cannot be read in the ORIGINAL panel either (give the same NA for A and B).

Write one short factual note per result (what decided the scores, naming the elements).

## 2. Per sheet (preference-draft.csv; one row per sheet)
`text_preference`: which result preserves the TEXT ELEMENTS better: `A`, `B`, or `SAME` (no material difference).
Judge only the listed text elements; one short note.

## Output
Append each row to `scores-draft.csv` / `preference-draft.csv` (headers exactly as in the templates) as soon as it is
scored, in ITEMS.md order, so that a partial sheet survives an interruption. Values exactly as above.
