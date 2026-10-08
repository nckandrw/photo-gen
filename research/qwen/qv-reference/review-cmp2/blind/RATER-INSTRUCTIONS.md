# Rater instructions (provenance-blind)

Each sheet is a set of image files of ONE photograph:
- `<SHEET>-ORIGINAL.png`: the photograph, reduced in size. It is the ground truth for what the lettering says.
- `<SHEET>-A.png`, `<SHEET>-B.png`, `<SHEET>-C.png`, ...: processed versions of the same photograph, each at its own
  native pixel size. You are not told how they were produced, and you must not try to find out. Some versions may look
  identical or nearly identical to each other; score each one on its own merits anyway.

There are two kinds of sheet; `ITEMS.md` gives each sheet's kind, its panel labels, its sizes and its numbered TEXT
ELEMENTS (lettering in the photograph, by location only; read their wording off ORIGINAL).

Read ONLY the files in this directory (`ITEMS.md`, this file, the sheet images, `scores-template.csv`). Do not open any
other file in the repository. Inspect lettering at native resolution: crop the same region from ORIGINAL and from each
version (for example `sips -c <h> <w> --cropOffset <y> <x> in.png --out <file>`), writing crops ONLY to a scratch
directory outside the repository. Do not enlarge crops with smoothing: judge what the pixels show. Score the sheets in
the order listed in ITEMS.md; within a sheet, one row per version (`<SHEET>-A`, `<SHEET>-B`, ...).

## Text elements `t1`..`t5` (both kinds; `-` for numbers the sheet does not have)
- `PRESERVED`: the same wording as in ORIGINAL is readable and the lettering looks like the original's (allowing the
  softening that a smaller size causes);
- `DEGRADED`: the same wording is still correctly readable, but glyphs are visibly softened, deformed or partly missing;
- `GARBLED`: the wording can no longer be read as the original's: wrong, invented or duplicated letters, gibberish, or
  unreadable where ORIGINAL is readable (say in the note whether it is wrong letters or blur);
- `REMOVED`: the element or its lettering is gone or replaced by something else;
- `NA`: the element's lettering cannot be read in ORIGINAL either (then give NA for every version of that sheet). If
  ORIGINAL is readable but you are unsure about a version because the text is tiny, choose the category you can defend
  and say so in the note; do not use NA for that.

## Kind "item": nothing was supposed to change
Judge how faithfully each version keeps ORIGINAL, above all its lettering. Fill `fidelity`, `fidelity_family`, `t1..t5`,
`notes`; put `-` in `adherence`, `seam`, `realism`, `unintended`.
- **`fidelity`** (everything apart from the lettering): `PASS` = matches ORIGINAL apart from the softening a smaller size
  causes; `MINOR` = visible deviation (colour, texture, small artifacts) that is not distracting; `MAJOR` = distracting
  deviation or changed content/structure. For MINOR or MAJOR name the family in `fidelity_family`: seam/halo,
  grain/grid, malformed-object, texture-smear, lighting-mismatch, colour-cast, detail-loss/blur, ghosting/duplication,
  oversharpening, other:<one word>. Leave it empty for PASS.

## Kind "edit": an instruction was applied (ITEMS.md quotes it)
Judge each version as a complete edited photograph. Fill `adherence`, `seam`, `realism`, `unintended`, `t1..t5`,
`notes`; put `-` in `fidelity` and `fidelity_family`.
- **`adherence`**: `PASS` = the instruction is fully carried out; `PARTIAL` = partly (e.g. remnants of the object);
  `FAIL` = not carried out.
- **`seam`**: visible boundaries, edges, halos or discontinuities: `NONE`, `MINOR` (visible on inspection), `MAJOR`
  (obvious).
- **`realism`** of the whole image as a photograph: `PASS`, `MINOR` (small implausibilities), `MAJOR` (clearly
  implausible: wrong shadows/reflections, broken geometry, impossible content).
- **`unintended`** changes OUTSIDE what the instruction asks for, compared with ORIGINAL: `NONE`, `MINOR`, `MAJOR`.
- Text elements as above (they are all outside what the instruction asks to change).

## Output
Copy `scores-template.csv` to `scores-draft.csv` in this directory and append one row per version as you go. Notes: one
short sentence per text element you call anything but PRESERVED, naming what you see. When done, stop; the session
assistant runs a format check and may return format-only corrections.
