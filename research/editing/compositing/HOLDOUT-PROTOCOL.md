# Future holdout set for preservation-aware editing (specification only; Phase 9 directive §15)

**Status: specification. Not collected, not run.** It is written now so that a future method can be judged on images
it was never tuned on. The G2 set (16 photos, Phases 5–9) is a **development** set from Phase 9 on.

## 1. Purpose
This set is a one-shot confirmation of a method frozen on the development set: compositing, automatic localisation,
local generation, or another editor. It is never used to tune.

## 2. Sources
- **Count and licence:** 16–24 new real camera photographs, CC0 / public domain (Wikimedia Commons or equivalent).
- **Acquisition record per image:** URL, licence, author, file sha256, EXIF summary.
- **Not reused:** no image already in G0, G2 or any phase report.
- **Coverage (each ≥ 3 images; one image may count for several):**
  - incidental text at several sizes, including glyphs of 5–20 px at the 1024 budget;
  - neighbouring similar objects;
  - occlusion and thin structures (hair, foliage, wires);
  - cast shadows and reflections on wet or glossy surfaces;
  - complex boundaries;
  - portrait and landscape at several sizes from about 2 to about 24 MP;
  - daylight, night and indoor camera conditions.

## 3. Tasks and masks
- **Who writes them:** one task per image, from the **source only**, by someone (or an isolated subagent) who has not
  seen any edit output of it.
- **Task content:** instruction, must-change, must-not-change, text elements by location, and category.
- **Masks:** if the method needs masks, they are drawn under the frozen annotation rule (PROTOCOL.md §3 of the method
  under test) before any output exists. They are hashed and committed.

## 4. Freeze and one-shot rule
1. The method's code, parameters, mask rule, rubric and pass bar are frozen and committed **before** the holdout is
   acquired.
2. The images, tasks and masks are committed before any edit runs.
3. Edits run once, at a pre-registered budget and seed.
4. **No change to the method after any holdout output is seen.** A change makes the set a development set and
   requires a new holdout.

## 5. Review and decision
- **Review:** a provenance-blind fresh rater, with the Phase 9 rubric (adherence, seam, realism, unintended,
  geometry, defect, text).
- **Records:** append-only drafts, freeze before unblinding, audit.
- **Pass bar:** fixed before acquisition. A suggested starting point is ≥ 80 % viable, with no recurring MAJOR failure
  class.

## 6. Cost note
Acquisition is light. Generating the edits requires the editor under test (for Qwen-2.1 at 1024, ≈ 10 min per edit
on this Mac, measured in G2), so the holdout run is a separately authorised step.
