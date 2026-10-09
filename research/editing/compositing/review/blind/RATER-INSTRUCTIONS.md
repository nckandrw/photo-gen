# Rater instructions (provenance-blind)

Each sheet is one photograph and one editing INSTRUCTION (quoted in `ITEMS.md`). The files of a sheet:
- `<SHEET>-ORIGINAL.png`: the unedited photograph, reduced to a long side of at most 2048 px;
- `<SHEET>-ORIGINAL-FULL.png`: the same unedited photograph at full resolution (use it when a version is larger than
  2048 px, and for reading small lettering);
- `<SHEET>-A.png`, `<SHEET>-B.png`, …: versions of the photograph, each at its own native size. You are not told how
  they were produced, and you must not try to find out. Versions differ in size; some may look nearly identical;
  one or more may not carry out the instruction at all. Score each version on its own merits against ORIGINAL and the
  instruction.

Read ONLY the files in this directory. Inspect at native resolution: crop the same region from ORIGINAL (or
ORIGINAL-FULL) and from each version, e.g. `sips -c <h> <w> --cropOffset <y> <x> in.png --out <file>`, writing crops
and any helper files ONLY to the scratch directory named in your prompt. Do not enlarge crops with smoothing
(nearest-neighbour enlargement is allowed). Score sheets in the order listed in `ITEMS.md`, one row per version
(`<SHEET>-A`, `<SHEET>-B`, …).

## Per version
- **`adherence`**: `PASS` = the instruction is fully carried out; `PARTIAL` = partly (e.g. remnants of the object, only
  part of the change); `FAIL` = not carried out.
- **`seam`**: visible boundaries, edges, halos, tone steps or discontinuities: `NONE`, `MINOR` (visible on
  inspection), `MAJOR` (obvious at normal viewing).
- **`realism`** of the whole image as a photograph: `PASS`, `MINOR` (small implausibilities), `MAJOR` (clearly
  implausible: wrong or orphan shadows/reflections, floating or cut objects, broken geometry, impossible content).
- **`unintended`**: changes OUTSIDE what the instruction asks for, compared with ORIGINAL, semantic or geometric:
  `NONE`, `MINOR`, `MAJOR`.
- **`geometry`**: does the edited region fit the unchanged scene (perspective, scale, contact with surfaces,
  continuity of edges and lines)? `PASS`, `MINOR`, `MAJOR`.
- **`primary_defect`**: the single most serious defect, or `none`: `leftover-of-target` (part of something that should
  have changed or gone is still there), `truncated-edit` (the edited content is cut off), `orphan-shadow-or-reflection`
  (a shadow/reflection with no cause, or a missing one), `seam-or-tone-step`, `ghosting` (semi-transparent mix of old
  and new content), `resolution-mismatch` (a region visibly blurrier or sharper than its surroundings),
  `collateral-change` (something not asked for was changed), `text-damage`, or `other:<one word>`.
- **`t1`..`t5`** (the sheet's TEXT ELEMENTS, all outside what the instruction asks to change; `-` for numbers the sheet
  does not have): `PRESERVED` (same wording readable, lettering like the original's allowing for size), `DEGRADED`
  (same wording still correctly readable but visibly softened/deformed), `GARBLED` (no longer readable as the
  original's: wrong letters or unreadable blur; say which in the note), `REMOVED` (gone or replaced), `NA` (unreadable
  in ORIGINAL too; then NA for every version of the sheet).
- **`notes`**: one or two short sentences: what you saw, where.

## Output and revisions
Copy `scores-template.csv` to `scores-draft.csv` in this directory and APPEND rows as you finish each sheet. The draft
is **append-only**: to change an earlier row, append a new row with the same `id` and `revision` + 1 (the first row of
an id has `revision` 1). Never edit or delete earlier rows. The latest revision of each id counts; all are kept.
