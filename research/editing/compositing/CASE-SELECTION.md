# Phase 9 case selection (fixed before any mask or composite; PROTOCOL.md §2)

**Rule.**
1. Exclude by **category**: global or background edits, the text-replacement task, and the Phase 8 pilot.
2. Among the remaining local tasks, take the coverage categories the directive requires (§6).
3. Within a category with several eligible tasks, take the **lowest-numbered** task.
4. Use the **1024 budget, primary-seed** G2 output for every case.

The rule does not look at G2 output images. The session assistant, acting as selector, *has* read G2's frozen text
outcomes (`research/editing/real-world/results.md`), listed below for transparency. They are used only to name the
"collateral change" category the directive asks for, never to pick an easy case. R05 is kept although its frozen
1024 adherence was PARTIAL (a possible EDITOR FAILURE, PROTOCOL.md §8).

| task | G2 category (`task-manifest.json`) | frozen G2 1024 A/P/C/Q/T | decision | reason |
|---|---|---|---|---|
| R01 | colour change (clothing) on a portrait | PASS/PASS/PASS/PASS/– | **SELECTED: simple control** | lowest-numbered simple single-object change (eligible: R01, R03, R04, R07, R10) |
| R02 | object removal | PASS/FAIL/PASS/PASS/FAIL | **demonstration, not counted** | Phase 8 pilot; post-hoc mask history (directive §6) |
| R03 | material change (product) | PASS/PARTIAL/PASS/PASS/– | not selected | the control category is filled by R01 (lowest-numbered); its leakage (laces) lies inside a natural "both shoes" mask |
| R04 | object replacement (food) | PASS/PASS/PASS/PASS/– | not selected | control category filled by R01 |
| R05 | object addition (interior) | **PARTIAL**/PASS/PASS/PASS/– | **SELECTED: addition, uncertain placement** | lowest-numbered addition (eligible: R05, R16) |
| R06 | global change (season) | PASS/PASS/PASS/PASS/– | excluded | global: no localized region; compositing would undo the requested change |
| R07 | colour change (vehicle) | PASS/PASS/PASS/PASS/– | not selected | control category filled by R01 |
| R08 | text replacement (sign) | PASS/PASS/PASS/PASS/PASS | excluded | the target is text itself, a different question |
| R09 | localized replacement in a busy scene | PASS/**FAIL**/PASS/PASS/– | **SELECTED: collateral change to similar objects** | the only task whose leakage reached neighbouring objects (preservation FAIL) |
| R10 | colour change on fine texture | PASS/PARTIAL/PASS/PASS/– | not selected | control category filled by R01 |
| R11 | transparent object: liquid colour change | PASS/PARTIAL/PASS/PASS/– | **SELECTED: transparent/refractive** | the only transparent-object task; its leakage (stem) lies outside a "wine in the bowl" region |
| R12 | person removal, night street, text preserve | PASS/**FAIL**/PASS/PASS/**FAIL** | **SELECTED: removal with incidental text** | required by the directive; R02 excluded |
| R13 | background (sky) change | PASS/PASS/PASS/MINOR/– | excluded | background edit with acceptable global light change |
| R14 | style transformation | PASS/PASS/PASS/PASS/– | excluded | global |
| R15 | text-preserving facade edit | PASS/**FAIL**/PASS/PASS/**FAIL** | **SELECTED: complex non-convex mask with text** | the only facade/inverse-region task; challenging boundaries |
| R16 | object addition (simple scene) | PASS/PASS/PASS/PASS/– | not selected | addition category filled by R05 (lowest-numbered) |

**Primary cases (6):** R01, R05, R09, R11, R12, R15, all at 1024 with the primary seed. **Demonstration (1):** R02-1024.

**Coverage against directive §6:**
- R12-1024: yes.
- Several localized non-text cases: R01, R05, R09, R11.
- Challenging geometry or boundaries: R15 (non-convex facade around windows), R05 (placement and shadows), R11
  (refraction).
- A case with collateral changes: R09, with R11's stem.
- Incidental text to preserve: R12, R15.
