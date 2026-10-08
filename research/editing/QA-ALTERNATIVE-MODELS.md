# Q-A: alternative image-editing models, desk assessment (Phase 8, Workstream B)

**Status: research-only desk survey (2026-10-09).** No model was downloaded, integrated or run for this document.
It shortlists candidates for a future **controlled** evaluation; it does not select a winner.

**The requirement** (directive §19): high-quality real-photo editing with strong incidental-text preservation and
low collateral change, at practical sustained performance on the MacBook Air M5, 16 GB.

**Evidence labels used below:**
- **M**: measured by us;
- **L**: local evidence from installed software (mflux 0.21.0 in `mflux-qwen/.venv`: its entry points and READMEs);
- **P**: primary-source claim (the model's own card, config file or paper);
- **S**: secondary source (third-party pages, aggregators, community posts);
- **E**: our arithmetic estimate;
- **I**: inference.

## 1. Why the VAE is the first discriminator
Phases 7–8 showed that on these photographs the **output path itself** loses incidental text: even a perfect copy of
the reference latents loses most lettering at 512 and some at 1024 (Q-V, **M**). Phase 8 compared the MLX path with the
official CPU reference: the numerical differences are at the level of MLX's TF32 default and vanish with it off
(Q-VR; `research/qwen/QWEN-QVR-REFERENCE.md`, **M**; the final class is in that report). A candidate whose VAE round trip cannot keep the G2 text
elements legible cannot pass G2's text criterion, however good its editor is. So a candidate's VAE is screened first.

**VAE geometry from the official config files (P, text files only):**

| model family | VAE (config `_class_name`) | spatial factor | latent channels | latent values per pixel | published text-rich reconstruction (S, Qwen team's OmniDoc-TokenBench, ~10 px English glyphs at 256²: PSNR / OCR NED) |
|---|---|---:|---:|---:|---|
| **Qwen-Image-2.1** (current) | `AutoencoderKLQwenImage21` (RGBA) | 16 | 64 | 0.25 | an f16c64 Qwen-Image-VAE-2.0 variant scores 26.00 / 0.924; the paper says Qwen-Image-2.0's VAE is "an intermediate variant", and does not name 2.1's |
| **FLUX.2 [klein] 4B** | `AutoencoderKLFlux2` (BN-normalised, 2×2 patchified for the DiT) | 8 | 32 | 0.50 | FLUX.2-dev's VAE: 27.72 / 0.954 (the klein config matches; weight identity with dev not verified) |
| LongCat-Image-Edit, Step1X-Edit v1.2, OmniGen2 | `AutoencoderKL` with FLUX.1 scaling (0.3611 / 0.1159) | 8 | 16 | 0.25 | FLUX.1-dev: 26.24 / 0.955 |
| Qwen-Image-Edit-2509 / 2511, Qwen-Image-Layered | `AutoencoderKLQwenImage` (Layered: 4 input channels) | 8 | 16 | 0.25 | Qwen-Image VAE: 24.94 / 0.907. This conflicts with the Qwen-Image technical report's own in-house text PSNR (36.63 vs FLUX's 32.65). |
| FIBO / FIBO-Edit | Wan 2.2 (`fibo_vae`, **L**) | 16 | 48 | 0.19 | Wan2.2 VAE: 21.67 / 0.831 |

**Reading:** FLUX.2's VAE carries **twice** the latent values per pixel of every other candidate, at the finer 8× grid.
It is also the only VAE besides FLUX.1's that is at or near the top of the one text-rich third-party table found.
These benchmark numbers are secondary and from one team's protocol, and the glyphs that fail in G2 are 2–13 px
(`research/qwen/qv-reference/glyph-heights.json`). **Only our own round-trip screen on R02/R12/R15 decides.**

## 2. Candidates
Hugging Face revisions are the current heads on 2026-10-09 (`api/models`).

| | FLUX.2 [klein] 4B | Qwen-Image-Edit-2511 | LongCat-Image-Edit | Qwen-Image-Layered |
|---|---|---|---|---|
| repo @ revision | `black-forest-labs/FLUX.2-klein-4B` @ `e7b7dc27f9` | `Qwen/Qwen-Image-Edit-2511` @ `6f3ccc0b56` | `meituan-longcat/LongCat-Image-Edit` @ `7b54ef423a` | `Qwen/Qwen-Image-Layered` @ `8f0ca708df` |
| licence | **Apache-2.0** (P; the 9B variants are non-commercial) | Apache-2.0 (P) | Apache-2.0 (P) | Apache-2.0 (P) |
| size | 4B rectified-flow DiT (5 double + 20 single blocks, P) + Qwen3 text encoder (`Qwen3ForCausalLM`, P; joint dim 7680 = 3 × 2560 suggests Qwen3-4B, I); repo weights 23.7 GB (P) | 20B MMDiT (60 layers, P) + Qwen2.5-VL-7B; 57.7 GB (P) | 6.2B DiT (10 double + 20 single, P) + Qwen2.5-VL-7B; 29.3 GB (P) | 20B MMDiT + Qwen2.5-VL-7B; 57.7 GB (P) |
| editing mechanism | reference images as extra tokens (multi-reference editing, ≤ 4 images, P/S); distilled 4 steps, guidance 1 | reference conditioning through VL encoder + VAE latents; 40 steps, true CFG 4.0 (P example) | image-conditioning branch on VAE features + 3D RoPE (S, report) | decomposition into variable RGBA layers; edit a layer, recompose (P, paper) |
| mask/local edit | none native (I) | none native (I) | none native (I) | **by construction** at layer level (P) |
| Apple Silicon runtime | **mflux 0.21.0 `mflux-generate-flux2-edit`, installed** (L) | mflux 0.21.0 `mflux-generate-qwen-edit` (L; "uses `Qwen/Qwen-Image-Edit-2511`") | none found (S; not in mflux 0.21.0, L) | none found (L) |
| memory on 16 GB | q4 DiT ≈ 2.3 GB, q4 text encoder ≈ 2.3 GB, VAE 0.16 GB (E); a community claim says a q4 pipeline fits 16 GB (S). Not measured. | q4 DiT ≈ 10–11 GB (E) + encoder: tighter than Qwen-2.1's 10.8 GB peak at 1024 (M, G2); likely pages (I) | bf16 ≈ 29 GB (E); q4 ≈ 7–8 GB (E); no runtime | as 2511 (E) |
| speed | 4 steps; M1 Max t2i 1024² ≈ 30–42 s (S) | 40 steps × CFG 2 passes × 20B: an order of magnitude above Qwen-2.1's 592 s per 1024 edit (E); Lightning LoRA (4–8 steps) exists (L, mflux README) | unknown on Mac | as 2511 |
| real-photo editing evidence | vendor examples; arena Elo for 9B edit (S) | strong community reputation; card claims "mitigate image drift" (P), no preservation numbers | self-reported CEdit-Bench (S) | paper results on decomposition (P) |
| incidental-text preservation evidence | **none found**; card lists generated text "may be inaccurate or subject to distortion" (P) | none found | none found | none found |
| confidence (that it could pass G2 on this Mac) | **medium** (best VAE, cheapest, runs locally; editor quality on real photos unknown) | low–medium (heavy; weakest f8 VAE on the one text table) | low (no Mac runtime) | low (research direction, not a near-term editor) |
| cheapest verification step | **VAE round-trip entry screen** (VAE file only, ~160 MB) | VAE round-trip screen (~250 MB) | FLUX.1 VAE screen (shared with Kontext/Step1X/OmniGen2) | none before a decomposition-quality study |

**Also surveyed, not shortlisted:**
- FLUX.2 [klein] 9B / 9B-kv: non-commercial, ~29 GB (S).
- FLUX.1 Kontext dev: non-commercial and gated (P), 12B; mflux `mflux-generate-kontext` exists (L).
- Step1X-Edit v1.2: Apache-2.0, 41.8 GB, FLUX.1 VAE, no MLX runtime.
- OmniGen2: Apache-2.0, 31.2 GB, FLUX.1 VAE, no MLX runtime.
- FIBO-Edit: mflux `fibo-edit` (L), Wan 2.2 VAE with the weakest published text NED.
- `Tongyi-MAI/Z-Image-Edit`: not public (the API returned not-found/unauthorised).

## 3. Ranked shortlist and the next verification step
1. **FLUX.2 [klein] 4B.** It is the only candidate that combines an Apache licence, a runtime already installed and
   pinned (mflux 0.21.0), a 4-step distilled editor small enough for 16 GB, and the highest-capacity VAE (f8c32).
   **Next:** an acquisition audit, then a VAE-only round trip of the staged G2 sources R02/R12/R15 at the budgets the
   editor would use. This reuses the Q-V harness design: an equivalence gate against its real edit path, the blind
   tool, and a pass bar fixed in advance. It is cheap: a ~160 MB VAE file, seconds per image. Only if it passes does
   an editing gate (G2-style) follow.
2. **Qwen-Image-Edit-2511.** It has the strongest editing reputation, but it is a heavy runtime on 16 GB, and its VAE
   is the weakest f8 VAE in the one text-rich table found. **Next:** the same VAE screen. It runs only if the
   screen passes and a memory preflight is safe.
3. **LongCat-Image-Edit.** Its FLUX.1 VAE is good on text (published), but there is no Mac runtime, so porting cost
   comes first. It is deferred.
4. **Qwen-Image-Layered.** It is a preservation-by-construction idea worth tracking (§4), but it is not a near-term
   editor here.

## 4. Original R&D opportunities (directive §20; none started)

| direction | prior art (availability) | rationale | feasibility here | novelty | cheapest falsification |
|---|---|---|---|---|---|
| **Text-aware hard preservation** (composite original pixels back outside the edit; protect detected text) | the classic masked composite; KV-Edit (ICCV 2025, training-free background KV reuse in DiTs, code public, S) | Q-V/Q-VR: the output path loses text even with a perfect copy, so keeping the *input pixels* is the only way to keep tiny text; the Phase 8 CMP baseline measures the simplest form | high: pixel ops, no model change | low for compositing; moderate for automatic text-region protection plus seam-free blending | Phase 8 CMP (one case); next, a mask from the edit instruction instead of a hand box |
| **Localized regeneration** (regenerate only the edit region's tokens) | KV-Edit; inpainting models (FLUX Fill, mflux `fill`, L) | removes global drift: the Phase 8 identity probe (and CMP: 56 % of pixels outside the box changed) shows the editor regenerates the whole frame | medium: needs token masking inside the DiT loop (worker patch) | moderate on MLX | KV-Edit-style background-token reuse on one G2 item with Qwen-2.1 or FLUX.2 klein |
| **Higher-capacity or text-aware VAE** | Qwen-Image-VAE-2.0 (f16c128: NED 0.962, weights not stated as released, P); FLUX.2 VAE (f8c32) | Phase 8: the runtime is not the cause; the representation is | high for a screen (VAE-only runs) | low (adopt); high (train) | the Q-A VAE entry screen |
| **Residual editing** (predict a delta and apply it only where it is non-zero) | instruction-editing works that predict deltas (S, scattered) | preserves everything the delta does not touch, by construction | low now: needs training | high | none without a training-feasibility phase |
| **Drift control in latent space** | VAE-LFA (arXiv 2605.08250, training-free, multi-turn; no code linked, P) | targets low-frequency drift | medium | low | apply to the R15-512 identity probe's drift |
| **Efficient specialisation / compression / distillation** | LoRA, Lightning step-distillation (L) | speed on 16 GB | requires a separate training-feasibility study (directive §21) | — | — |

## 5. What this survey does not establish
- No candidate's editing quality on real photographs, text preservation or memory use on this Mac was measured.
- The benchmark numbers in §1 come from one third-party protocol, at 256² and ~10 px glyphs, and are not ours.
- Mac feasibility comes from local entry points and arithmetic, never from CUDA reports.
- Licences are as stated on the repositories on 2026-10-09; re-check them at acquisition.

**Sources:**
- Hugging Face model APIs and config files: the candidates' `model_index.json`, `vae/config.json`, `transformer/config.json`.
- FLUX.2 [klein] 4B model card.
- Qwen-Image-Edit-2511 model card.
- Qwen-Image-VAE-2.0 Technical Report, arXiv 2605.13565 (Table 3).
- KV-Edit, arXiv 2502.17363 (ICCV 2025).
- VAE-LFA, arXiv 2605.08250.
- LongCat-Image Technical Report, arXiv 2512.07584.
- Qwen-Image-Layered, arXiv 2512.15603.
- mflux 0.21.0 READMEs (local).
