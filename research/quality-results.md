# Quality benchmark results — 1024², seed 42, one image per model per prompt (no re-rolls)

Rubric: `quality-rubric.md` (fixed before generation). Scale 0/1/2 per dimension, "–" = not exercised. Single rater (Claude), viewing each 1024² image downscaled in the viewer (not true 100% pixel zoom), which limits fine-artifact detection. **No overall score.**
Z = Z-Image-Turbo (sd.cpp, Q4_K + Qwen3-4B Q4_K_M, 9 steps, tensor API disabled). Q = Qwen-Image-2.1 (sd.cpp, Q4_K + Heretic Q4_K_M, 25 steps, tensor API enabled).
Images: `outputs/zi-p-1024.png`, `outputs/qw-p-1024.png` (prompt 1); `outputs/{zi,qw}-q-{desk,neon,cebu,portrait,glass}.png`.

## Observations

**1 · apple.** Z: pale red apple with water droplets (not requested) on light oak, bright window behind. Q: saturated deep-red glossy apple on dark weathered wood, window with foliage bokeh. Both fully meet the checklist.

**2 · desk.** Z: all five objects present. Notebook left, fountain pen centre (nib visible), brass twin-bell clock right, and light from the left window. However, the mug sits centre-back rather than clearly "behind the notebook", and the plant is behind the clock at mid-depth, not in the far background. Q: all five present. Notebook left, fountain pen centre, mug directly behind the notebook, brass clock right, plant blurred in the far background, window light from the left. Clock dial: Q appears to skip the "4" (…3, 5, 6…); Z's dial looks plausible at this scale.

**3 · neon.** Z: `QWEN IMAGE 2.1` exact, on three lines inside a framed neon box on a grimy wall with pipes. It reads as a wall or back-room, and the "alley" is weak. Q: `QWEN IMAGE 2.1` exact on one line, suspended across a deep cyberpunk alley with buildings, AC units and haze, so the context is strongly met. Q shows a faint fine vertical/grid texture in dark regions at this viewing scale (possible artifact, unconfirmed).

**4 · cebu.** Z: tropical street at overcast dusk. Wet reflective asphalt with warm streetlight/storefront reflections, motorbikes, palms, two-storey shophouses. Plausible SE-Asian, generic Philippine cues. Q: dense overhead wiring, shuttered sari-sari-style stores, a tricycle-like vehicle, warm storefront glow on wet asphalt, darker dusk. Stronger Philippine-specific cues. Both photoreal with a 35 mm look.

**5 · portrait.** Z: young woman **centred** in frame (face centroid at x≈0.50). Blurred street with bokeh, backlit sunset sky, subtle warm light. The rule of thirds is **not** met. Q: woman placed on the right third (body/face centroid x≈0.55–0.62, within the ±1/12 band of the 0.667 line), with a blurred city street, warm bokeh and warm side light. Skin texture and freckles are visible.

**6 · glass.** Z: two hands (both thumbs visible, fingers seen refracted through the water) holding a tall tumbler. Plausible refraction of the fingers. Text reads **"Ohsnmad houch"**: crisp letters but nonsense words, rendered *on* the glass surface rather than seen through it. Q: a close-up of a faceted tumbler held by fingers on the left and a thumb on the right. That's consistent with two hands but ambiguous. Excellent refraction, caustics and reflections. **No text at all.** Slightly over-sharpened edges.

## Scores (0/1/2)

| Prompt | Model | Adherence | Spatial | Text | Composition | Photoreal | Hands | Detail | Refl./transp. | Artifacting |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 apple | Z | 2 | – | – | – | 2 | – | 2 | – | 2 |
| 1 apple | Q | 2 | – | – | – | 2 | – | 2 | – | 2 |
| 2 desk | Z | 2 | 1 | – | – | 2 | – | 2 | – | 2 |
| 2 desk | Q | 2 | 2 | – | – | 2 | – | 2 | – | 1 (clock dial) |
| 3 neon | Z | 1 (alley weak) | – | 2 | – | 2 | – | 2 | 1 | 2 |
| 3 neon | Q | 2 | – | 2 | – | 2 | – | 2 | 2 | 1 (possible grid texture) |
| 4 cebu | Z | 1 (weak locale cues) | – | – | – | 2 | – | 2 | 2 | 2 |
| 4 cebu | Q | 2 | – | – | – | 2 | – | 2 | 2 | 2 |
| 5 portrait | Z | 1 | – | – | **0** (centred) | 2 | – | 2 | – | 2 |
| 5 portrait | Q | 2 | – | – | 2 | 2 | – | 2 | – | 2 |
| 6 glass | Z | 2 | – | 1 (legible glyphs, nonsense words, on-surface) | – | 2 | 2 | 2 | 2 | 2 |
| 6 glass | Q | 1 (no text; hands ambiguous) | – | **0** (no text) | – | 2 | 1 (ambiguous count) | 2 | 2 | 1 (over-sharpening) |

## Per-dimension summary (descriptive, no winner)
- **Prompt adherence / spatial / composition:** Q met every explicit layout instruction (desk positions, rule of thirds, alley context). Z missed the rule of thirds and two depth relations, and gave weaker scene context on 2 prompts.
- **Text:** both rendered `QWEN IMAGE 2.1` exactly. On the open-ended "readable text through glass" task, Z produced legible but meaningless text and Q produced none.
- **Photorealism / detail:** no separable difference at this viewing scale. Both scored 2 on every prompt.
- **Transparency / refraction:** both strong on glass. Q's caustics are more elaborate.
- **Artifacting:** Q showed small defects (clock numeral, possible faint grid in dark areas, over-sharpening). No artifacts noted in Z.
- **Limitations:** n = 1 seed per prompt; single rater; downscaled viewing; the models use different step counts and runtimes by design. This is not a statistically powered quality comparison.
