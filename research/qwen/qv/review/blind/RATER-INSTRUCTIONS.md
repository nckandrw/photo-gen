# Rater instructions (provenance-blind)

Each sheet is ONE composite image `<SHEET>.png` with three panels of the same photograph:
- **ORIGINAL**: the photograph, reduced in size (the largest panel);
- **A** and **B**: two processed versions of the same photograph, each shown at its own native pixel size.
For portrait photographs the panels are side by side (ORIGINAL left, then A, then B); for landscape photographs they are
stacked (ORIGINAL top, then A, then B). ITEMS.md states the layout of each sheet.

You are not told how A and B were produced, and you must not try to find out. They are NOT edits: nothing was supposed
to change. Judge how faithfully each one keeps the original, above all its lettering. `ITEMS.md` lists, per sheet,
numbered TEXT ELEMENTS (lettering in the photograph, by location only); read their wording off the ORIGINAL panel.

Read ONLY the files in this directory (`ITEMS.md`, this file, the `<SHEET>.png` composites, the two templates).
Do not open any other file in the repository. Inspect lettering at native resolution: crop the same region of ORIGINAL,
A and B (for example `sips -c <h> <w> --cropOffset <y> <x> in.png --out <file>`), writing crops ONLY to a scratch
directory outside the repository. Do not enlarge crops with smoothing: judge what the pixels show. Score the sheets in
the order listed in ITEMS.md, A and B each on their own merits (rows `<SHEET>-A` and `<SHEET>-B`), then compare them.

## 1. Per processed version (scores-draft.csv; one row per version)
**Text elements `t1`..`t5`** (the sheet's numbered TEXT ELEMENTS; `-` for numbers the sheet does not have):
- `PRESERVED`: the same wording as in ORIGINAL is readable and the lettering looks like the original's (allowing the
  softening that a smaller size causes);
- `DEGRADED`: the same wording is still correctly readable, but glyphs are visibly softened, deformed or partly missing;
- `GARBLED`: the wording can no longer be read as the original's: wrong, invented or duplicated letters, gibberish, or
  unreadable where ORIGINAL is readable (say in the note whether it is wrong letters or blur);
- `REMOVED`: the element or its lettering is gone or replaced by something else;
- `NA`: the element's lettering cannot be read in ORIGINAL either (give the same NA for A and B). If ORIGINAL is
  readable but you are unsure about A or B because the text is tiny, choose the category you can defend and say so in
  the note; do not use NA for that.

**`fidelity`** (everything apart from the lettering): `PASS` = matches ORIGINAL apart from the softening a smaller size
causes; `MINOR` = visible deviation (colour, texture, small artifacts) that is not distracting; `MAJOR` = distracting
deviation or changed content/structure. For MINOR or MAJOR name the family in `fidelity_family`: seam/halo, grain/grid,
malformed-object, texture-smear, lighting-mismatch, colour-cast, detail-loss/blur, ghosting/duplication, oversharpening,
other:<one word>. Leave it empty for PASS.

Write one short factual note per version (what decided the scores, naming the elements).

## 2. Per sheet (preference-draft.csv; one row per sheet)
`text_preference`: which version keeps the TEXT ELEMENTS better: `A`, `B`, or `SAME` (no material difference). Judge
only the listed text elements; one short note.

## Output
Append each row to `scores-draft.csv` / `preference-draft.csv` (headers exactly as in the templates) as soon as it is
scored, in ITEMS.md order, so that a partial sheet survives an interruption. Values exactly as above.
