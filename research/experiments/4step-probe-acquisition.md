# 4-step probe: acquisition audit (before any download)

Audited 2026-09-28 from Hugging Face API metadata, model cards and file trees at pinned revisions. **Status: EXPERIMENTAL research only.** Nothing here touches the production profiles (REFERENCE, FAST) or the v2 tag.

## 1. The research question (directive §7)
"Can 4 steps be faster?" is already answered. Turbo at bf16 + 4 inference steps is ≈ 2× faster than FAST, but it is "preview" quality (`step-sweep-report.md`).

**The question this probe answers:** can a configuration that was specifically *distilled* for 4 steps recover quality while keeping ≈ 2× lower latency than FAST, without any training on our side?

The candidate LoRA was trained for exactly this objective. Its card says it "distills both steps and CFG" and "requires only 4 steps instead of 8". So the probe addresses the question directly. That is the condition under which the directive allows the download.

**The important caveat:**
- The LoRA was trained for **Z-Image base**, not Turbo. The card says it "does not use any Z-Image-Turbo related weights" and is meant for Z-Image derivatives, "not to replace Z-Image-Turbo".
- So the probe tests a **different model pipeline** (base + LoRA at 4 NFE) against Turbo FAST (8 NFE) and Turbo bf16/4.
- A positive result would mean a second model family on disk, not a faster Turbo.

## 2. Assets
| asset | source | revision | size | license | license compatibility | required dependencies |
|---|---|---|---:|---|---|---|
| Z-Image base, mflux q4 | `mflux-community/z-image-base-mflux-q4` | `087eaf40738482a1a99394ce1b490ab12738c1f6` (lastModified 2026-09-26) | 5,902,983,962 B (text_encoder 2.26 GB, transformer 3.46 GB, vae 0.16 GB, tokenizer 11 MB) | **Apache-2.0**. The card declares `license: apache-2.0` and states "the original model's license applies unchanged". Upstream `Tongyi-MAI/Z-Image` is Apache-2.0. | ✔ research use; ✔ may be referenced by name/revision/hash in Git; ✗ not committed (we don't redistribute weights) | mflux 0.20.0 `z-image` model config (already installed; no new packages) |
| 4-step distill LoRA | `alibaba-pai/Z-Image-Fun-Lora-Distill`, file `Z-Image-Fun-Lora-Distill-4-Steps-2603-ComfyUI.safetensors` | `f9a4db417ab7d8c1c5ffa9c0f03bdd72ae4a070c` | 568.3 MB | **Apache-2.0** (card metadata) | ✔ research use; ✔ referenceable; ✗ not committed | mflux LoRA loader (installed) |
| optional: 2-step LoRA | same repo, `…-2-Steps-2603-ComfyUI.safetensors` | same | 568.3 MB | Apache-2.0 | same | same; **not downloaded** unless the 4-step probe is promising |

- **Total additional storage:** ≈ 6.47 GB (4-step only). 257 GB free on the volume.
- **Reuse check:** only the 3 tokenizer files are byte-identical to the production Turbo pack. The text encoder, transformer and VAE differ by LFS digest, so the full base pack is needed.
- **Location:** `models/research/z-image-base-mflux-q4/` and `models/research/loras/`. `models/**` is gitignored. Every file's sha256 is verified against the HF LFS digest after download and recorded in `4step-probe-files.sha256` (committed).
- **Redistribution:** none planned. Both are Apache-2.0, which would permit redistribution with notices, but photo-gen only records identity.

## 3. Expected mflux/MLX compatibility
| aspect | status | evidence |
|---|---|---|
| base model loads | **LIKELY** | `z-image` ModelConfig exists in mflux 0.20.0; the pack is built for mflux (`library_name: mflux`, it ships `manifest.json`) |
| LoRA key format | **LIKELY** | header read (77 KB range-read, earlier): 612 tensors `diffusion_model.{layers,context_refiner,noise_refiner}.N.{attention.to_q/k/v, feed_forward.w1/w2/w3}.{lora_down,lora_up,alpha}`, rank 128, bf16. `z_image_lora_mapping.py` accepts these patterns. |
| CFG-free sampling | **VERIFIED from source** | the base CLI's guidance defaults to 0.0, and `z_image.py` encodes no negative prompt at guidance ≤ 1.0, so it is one forward pass per step |
| scheduler | **OPEN** | The base CLI defaults to `flow_match_euler_discrete` (empirical μ). The LoRA card recommends the "simple" scheduler, with sigmas mostly < 0.5 for the 2603 versions. Both `--scheduler linear` and the default are tested; this is disclosed as a probe variable. |
| LoRA runtime overhead | estimate ≈ 5% | mflux applies LoRA unfused (`x·A·B` side branch at rank 128) |
| memory | expect ≈ FAST + 0.57 GB | same DiT size |

## 4. Experiment it enables (pre-registered design; run after chain B smoke tests)
**Arms** (1024², seeds never used before):
- **P4-base-LoRA:** base q4 + 4-step LoRA, 4 steps, bf16 stream, `--low-ram`, guidance 0, scheduler {default, linear}.
- **FAST:** Turbo bf16/8, the production reference for speed/quality trade.
- **Turbo-4:** Turbo bf16/4, inference-only; the "untrained 4-step" baseline.

**Measurements:**
- cold + paired sustained denoise/wall;
- peak footprint;
- a blinded review on the 12-prompt suite: P4 vs Turbo-4 (does distillation recover quality?) and P4 vs FAST (how far from production?).

**Decision rule:**
- P4 is **interesting** only if it beats Turbo-4 in the blinded review, *and* its denoise is ≤ 0.6 × FAST.
- It could become a profile only after its own full gate. It stays **EXPERIMENTAL** regardless of the probe outcome.

## 5. Expected information gain
**High for the directive's question.** It is the only zero-training way to observe distilled 4-step quality on this machine. A negative result closes the "free 2× via a published few-step adapter" branch for Z-Image. It also sharpens the case for (or against) a costed Turbo-specific distillation.

## 6. Status
**AUDIT PASSED** (licensing and information value). The download is approved under directive §6.

Download commands (pinned):
```sh
source mflux/env.sh
mflux/.venv/bin/hf download mflux-community/z-image-base-mflux-q4 --revision 087eaf40738482a1a99394ce1b490ab12738c1f6 --local-dir models/research/z-image-base-mflux-q4
mflux/.venv/bin/hf download alibaba-pai/Z-Image-Fun-Lora-Distill Z-Image-Fun-Lora-Distill-4-Steps-2603-ComfyUI.safetensors --revision f9a4db417ab7d8c1c5ffa9c0f03bdd72ae4a070c --local-dir models/research/loras
```
