# Quality rubric — fixed BEFORE generating benchmark outputs (2026-09-24 ~11:30)

Applies identically to Z-Image-Turbo and Qwen-Image-2.1 outputs (1024², seed 42, each model's own production config).
No overall score. Each dimension is scored per image where applicable, using the anchors below; "n/a" when the prompt doesn't exercise it. Observations are written before scores.

Scale per dimension: **0 / 1 / 2**
- **0** — requirement clearly not met, or a conspicuous defect.
- **1** — partially met, or a noticeable minor defect.
- **2** — fully met with no noticeable defect at 100% zoom of the 1024² image.

| Dimension | What is checked (concrete, per prompt) |
|---|---|
| Prompt adherence | Every noun/attribute in the prompt present (checklist per prompt below); 1 point lost per missing item class |
| Spatial relationships | Stated positions (left/center/right/behind/background) correct |
| Text legibility | Exact string reproduced: 2 = exact characters incl. spacing/punctuation; 1 = readable with ≤2 character errors; 0 = otherwise |
| Composition | Framing matches explicit instruction (rule of thirds = subject centroid within ±1/12 of a third-line) |
| Photorealism | Plausible lighting/materials; no painterly/CGI look when realism requested |
| Anatomy / hands | Finger count 5 per visible hand, no fused/extra digits, plausible joints |
| Fine detail | Texture present at 100% zoom (wood grain, fabric, skin pores), no mush |
| Reflections / transparency | Reflections consistent with light sources; refraction through glass/water plausible |
| Artifacting | Absence of grid patterns, banding, seams, noise, duplicated objects |

Prompt checklists:
1. apple — red apple; wooden table; soft window light.
2. desk — wooden desk; red notebook LEFT; black fountain pen CENTER; white ceramic mug BEHIND notebook; small brass clock RIGHT; green plant FAR BACKGROUND; light from LEFT; exactly five objects.
3. neon — neon sign; dark cyberpunk alley; text exactly `QWEN IMAGE 2.1`.
4. cebu — Cebu city street (Philippine urban cues); dusk; after light rain (wet pavement); warm storefront reflections; 35 mm look.
5. portrait — cinematic portrait; subject on a third-line; softly blurred urban background; warm evening light.
6. glass — two human hands; transparent glass with water; realistic fingers; refraction; reflections; readable text visible through glass (any text; legibility judged).

Procedure: images viewed at full resolution in a fixed order (prompt 1–6), Z-Image then Qwen for each prompt. Scorer: Claude (single rater — a limitation recorded in the final report). No re-generation or cherry-picking: exactly one image per model per prompt at seed 42.
