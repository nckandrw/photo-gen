# photo-gen experiment backlog (Z-Image-Turbo on MacBook Air M5 16 GB)

**Baseline (REFERENCE, permanent):**
- fp32 + 9 steps (= 9 NFE in mflux; see experiments/scheduler-nfe-note.md). Production since 2026-09-25: transformer release before VAE.
- mflux 0.20.0 / MLX 0.32.2, q4, `--low-ram`.
- 1024²: cold ≈84.6–86.6 s wall (denoise 78.6–81.5 s), sustained ≈133.7 s.
- Peak footprint ≈7.3 GB; pixel-deterministic.

**Ranking criteria (explicit, per experiment):** expected benefit (on the measured baseline), confidence in that benefit, implementation effort, measurement cost, quality risk, memory risk. The order below sorts by (benefit × confidence) ÷ (effort + measurement cost), with high-quality-risk items needing E08 first.
**Grounding:** E00 (block microbenchmark), E01 (activation dtype probe), E02/E02b/E02ab (bf16 stream), `z-image-architecture-map.md`.

| # | Experiment | Source idea | Expected benefit (basis) | Confidence | Effort | Measurement cost | Quality risk | Memory risk | Status |
|---|---|---|---|---|---|---|---|---|---|
| **E02** | **bf16 hidden stream in the DiT.** Cast the timestep embedding to bf16 (pad-token cast is a no-op: they load as bf16; E10); RoPE result cast back to the input dtype (diffusers semantics) | Own finding (E01: production DiT runs fp32 activations); Z-Image paper / diffusers bf16 reference | **Measured: −29.1% denoise (78.33 → 55.55 s, 1.41×)** in a controlled cool A/B; matches E00 prediction | high (speed) | low (3 small runtime patches) | low (timing) + E08 for quality | low–medium: PSNR 42.3 dB (apple), 34.6 dB (neon) vs fp32; text and composition identical by inspection; not pixel-identical | none (7.28 vs 7.35 GB) | **ADOPTED as opt-in** (2026-09-24): quality gate PASSED (24 blinded pairs, fp32-better 0 / bf16-better 2 / ties 22; sustained denoise ratio 0.70) → photo-gen `precision: bf16` (fp32 stays default). See experiments/bf16-quality-report.md |
| **E03** | Step-count sweep 9→8→7→6→5→4 (same seed/prompts) | Decoupled-DMD (8-NFE distillation); consistency/LCM background | ≈11% per removed step (per-step cost is constant) | high for time | trivial (existing `steps`, experimental flag) | medium (needs E08 quality) | **high** below 8 NFE (distilled for 8) | none | **8 steps ADOPTED as FAST profile (bf16 + 8, validated at 1024²)** — blinded gate 0/1/23; 7–4 steps EXPERIMENTAL. See experiments/8step-quality-gate-report.md, step-sweep-report.md |
| **E04** | Exact micro-optimizations: `mask=None` in SDPA; compute the context refiner once per image | E00 (mask), architecture map (step-invariant context refiner) | ≈1–2% combined at short prompts, more with long prompts | high (mask: bit-identical output) | low | low | **none** (exact) | none | **DONE** — mask=None exact but no speed-up in bf16 (rejected); context-refiner caching <1% (deferred). See experiments/microopt-report.md |
| **E06** | Make `--low-ram`'s transformer release effective before VAE decode (mflux closure keeps ~3.5 GB alive) | Own finding (MFLUX phase) | ≈3.5 GB lower peak during VAE decode (MLX 5.70 → ≈2.2 GB); no speed change | high | low (upstream issue/PR or runtime patch) | low | none | reduces | **DONE — exact, −0.8 GB peak at 1024², −3.5 GB VAE-phase peak**; awaiting sign-off for production (experiments/vae-lifecycle-report.md) |
| **E05** | Cross-step redundancy instrumentation: per-block relative ‖Δh‖ and ‖Δout‖ across the 9 steps, per token | FastCache, TokenCache, 6Bit-Diffusion (block I/O-difference principle), DeepCache | Measurement only. Decides whether any block/step caching is viable at 8 NFE (few-step models often have little redundancy). | — | medium | medium | none (measurement) | small (instrumentation) | **DONE — redundancy NOT substantial; no caching prototype** (experiments/cache-audit-report.md) |
| **E09** | Pruning payoff bound: time a block with FFN width reduced 37.5% (random weights, q4) vs the full block | TMP (6B→4B by MLP width) | Bounds the speed a TMP-pruned Z-Image *would* give here (FFN = 56% of block time → ≈20% ceiling, ESTIMATE) before seeking cloud recovery training | high (for the bound) | low | low | n/a (proxy) | n/a | **DONE (proxy)** — bf16: −26% block time; fp32 figure unreliable (pruning-tmp-assessment.md) |
| **E08** | Evaluation harness upgrade: offline prompt subsets from T2I-CompBench++, OneIG-Bench (text), GenEval-style counts/positions; multi-seed; blind comparisons | GenEval / GenEval 2 / T2I-CompBench++ / OneIG / ImageReward | Enables accept/reject for E02/E03/E07 on quality instead of n=1 inspection | — | medium (separate env for judges) | medium | — | — | needed before adopting E02/E03 |
| **E07** | Quantization sensitivity: per-layer q4 vs q8/bf16 error; group size 32/64/128; per-step error accumulation | PTQ4DiT, Q-DiT, Timestep-Aware Correction | Quality (q4 is already the fastest format here per E00) | low–medium | medium–high | medium | — | may increase | later |
| **E10** | Attention share at 1536² and long prompts | ToMA, SageAttention, FlashAttention | Decides whether attention-side work ever exceeds its ≈18% ceiling on this pipeline | high (for the decision) | low | low | none | none | later |
| C1 | Few-step re-distillation (<8 NFE) | Decoupled-DMD, LCM, moment matching | Potentially large | low | very high (training, datacenter GPUs) | high | high | — | deferred |
| C2 | Custom Metal/NAX kernels (fused RoPE / norms / modulation) | FlashAttention principle | The ≈1.2 s/step non-matmul remainder is the target (≤13%) | low | high | medium | none if exact | none | deferred |
| C3 | LoRA / SaRA / IntLoRA adapters on the q4 base | PEFT papers | Customization, not speed | — | high | high | — | small | deferred |
| C4 | Lightweight VAE decoder | Lightweight decoders paper | ≤3% time (VAE is 2–3 s of 87 s) | high (that it's small) | high (training) | medium | medium | reduces | **deprioritized by measurement** |

## Phase 3 addendum (2026-09-29): 4-step probe outcome and the resulting next frontier
- **REJECTED:** Z-Image base + alibaba-pai 4-step distill LoRA (runtime adapter) as a 4-NFE candidate. It loses blind to plain Turbo at 4 steps on visual quality (grain). It is slower (+6%) and uses more memory (+0.84 GB). `experiments/4step-probe/results.md`.
- **Next (highest value per compute):** a pre-registered direct blinded gate, FAST (bf16/8) vs bf16/6, 5 and 4, at 512²/768²/1024², with fresh seeds.
  - Motivation: Turbo 4 was blind-equivalent to Turbo 8 at 1024² (2/3/19) at 0.50× denoise.
  - It needs no training or new weights, and gives a ≈ 2× production speed-up if it passes.
- **Deprioritised:** C1 / F-D few-step *training* (published adapters did not beat step reduction); mixed-lineage specialist models.

## Phase 4 addendum (2026-10-07): image editing (Qwen-Image-2.1), the next frontier
Directive §26 applies: correct → measured → **then** optimized. Nothing below is started. Each item names its first measurement.

| # | frontier | first step (measured on this M5) | what would justify going further | risk / blocker |
|---|---|---|---|---|
| Q-G | **Production gate** for one fixed edit configuration (needed before any adoption) | A pre-registered **blinded** G2 on fresh sources/seeds: e.g. budget 512 vs 1024 per category, or q4 vs q8 at 512 (q8 is the quantization mflux validated) | a configuration that is no worse on adherence/preservation than its control, with memory never critical | the licence blocks commercial use regardless; the rater is the AI assistant (as in all gates) |
| Q-S | Fewer denoising steps (1024 denoise ≈ 474 s cold = 95% of an edit) | Survey only: published few-step options for 2.1 (Viggle `viggle_turbo` scheduler + LoRA; alibaba-pai `Qwen-Image-2.1-Fun-Acc-LoRAs`; mflux `--use-step-cache`, ~1.2× and approximate), each with an acquisition audit | a ≥2× denoise reduction that passes a blinded gate vs 40 steps | LoRAs need licence audits; the step cache is non-exact; mflux #831 (scheduler ignored for edits) must be fixed first |
| Q-M | 1024 denoise memory (11.0 GB MLX peak; warn-level pressure) | Probe the split: DiT 4.1 + VAE 1.35 + prefix KV cache (≈ 2.2 GB bf16) + attention activations; a lifetime-only VAE release during denoise (reload before decode) as a pixel-parity candidate | ≥1 GB lower peak at identical pixels | the VAE is needed for encode and decode; reload costs ≈ 1–2 s |
| Q-U | One venv for both tasks | Test whether mflux 0.21.0 with `--float32` reproduces REFERENCE `fe47d88d`/`9ae59f59` (upstream #803 says it "keeps the old float32 stream") and whether its #802 release equals our transformer-release patch | exact hashes for every pinned configuration | the Z-Image worker patches target 0.20.0 internals; any mismatch keeps the two-venv design |
| Q-C | More edit capability (multi-reference, masks, RGBA) | Only on a user request; each is a separate capability with its own benchmark category | — | mask/auto-mask/verify are mflux additions, not upstream pipeline features |

## Phase 5 update (2026-10-07): after G2
**G2 rejected the q4 configuration at 512 and 1024** (`research/editing/real-world/results.md`). The failures are incidental text being garbled and edits leaking to adjacent objects; adherence was strong.

| # | status after Phase 5 |
|---|---|
| Q-G | **DONE: REJECTED** (G2, provenance-blind; both budgets fail A2/A5/S; 1024 also MARGINAL on wall time) |
| Q-M | **DONE: ADOPTED** as P2 (`research/qwen/QWEN-MEMORY-LIFETIME.md`): 1024 peak 12.08 → ~10.9 GB, pixel-identical |
| Q-S | **ON HOLD.** Directive §24–§25: no speed work on a configuration that failed its quality gate |
| Q-U, Q-C | unchanged (not started) |
| Q-V | **DONE (Phase 7): MIXED.** The VAE-only round trip (the edit's exact path) keeps 3/12 text elements legible at 512 (scaling loses 6) and 7/12 at 1024 (the VAE loses 3 of 10). The output path limits small text; stop Qwen-Image-2.1 editing work is recommended (`research/qwen/QWEN-QV-DIAGNOSTIC.md`) |
| Q-A | **Justified if editing remains a goal** (Phase 7). Entry screen: a candidate's VAE/conditioning round trip keeps the G2 text elements legible at a feasible budget, before any editing gate (the Q-V harness generalises) |
| Q-Q | **DONE (Phase 6): AGAINST.** q8 vs q4 on the six G2 text FAILs: 1 of 19 garbled elements rescued, text FAIL 6/6 in both arms; q4 not supported as the primary cause (`research/qwen/QWEN-QQ-DIAGNOSTIC.md`) |
| Q-VR | **DONE (Phase 8): RUNTIME-MATCHED.** MLX matches the official Diffusers CPU reference (residual = TF32 default; 24/24 text calls identical); Texture-Fix decoder no text rescue; identity edit drifts beyond the ceiling (n = 1) (`research/qwen/QWEN-QVR-REFERENCE.md`) |
| Q-A (Phase 8) | **Desk survey DONE** (`research/editing/QA-ALTERNATIVE-MODELS.md`). Next: FLUX.2 [klein] 4B VAE round-trip entry screen (VAE file only); not started |

New items. **Not started.** Each needs the user's decision to continue with Qwen at all.

| # | frontier | first step (measured on this M5) | what would justify going further | risk / blocker |
|---|---|---|---|---|
| Q-Q | **Is the incidental-text failure a q4 artifact?** | Desk check first: the q8 (or q4-DiT / q8-encoder mixed) export size and the per-phase memory under P2 (text encoder and DiT are never resident together). If feasible, export from the retained source checkpoint (`QWEN-ASSET-PROVENANCE.md` §6), then re-run only the G2 text items (R02, R12, R15) on the **same seeds**, scored provenance-blind against the frozen q4 outputs. | text-preservation FAILs disappear on most items. Only then would a full fresh-seed G2 of that configuration be justified; G2's thresholds stay unchanged. | memory: q8 DiT ≈ 2× q4; the export needs the 33 GB checkpoint; the cause may instead be the VAE round trip or the budget (1024 garbles less than 512), which Q-Q would not fix |
| Q-V | **Phase 7 candidate (after Q-Q): is incidental text lost in the VAE round trip or in the DiT?** | Encode + decode each staged G2 source at the 512 and 1024 output sizes with the q4 export's VAE only (no DiT, no text encoder); score the same text elements as Q-Q (`qq_blind.ELEMENTS`) | if the VAE alone keeps the text legible, the DiT's re-synthesis is the failure (then Q-A); if it garbles, the VAE/budget is the ceiling | cheap (seconds per image); answers only VAE vs not-VAE |
| Q-A | An alternative editing model that preserves incidental text | Desk survey only: licence, size vs 16 GB, mflux/MLX support, published text-preservation evidence | a candidate that fits 16 GB, with a licence compatible with the intended use | every Qwen-Image-Edit 20B variant is out on memory (`QWEN-SOURCE-AUDIT.md` §3) |

## Rejected (with reason)
| Idea | Why rejected | Evidence |
|---|---|---|
| Fused QKV projection | ≤1.4% faster with q4 weights: within noise | E00 (46.78 vs 46.12 ms fp32; 35.0 vs 34.72 ms bf16) |
| Fused SwiGLU w1/w3 | No gain with q4 | E00 (88.84 vs 88.93 ms) |
| q8 or bf16 weights "for speed" | q4 is the fastest weight format on this GPU (q8 +8%, bf16 +22% per block) | E00 |
| Qwen-2.1-style prefix KV cache for caption tokens | Not exact: caption tokens are timestep-modulated in all 30 main blocks | architecture map |
| Reproducing TMP pruning locally | No pruned Z-Image weights or code published; needs recovery distillation of a 6B model (not feasible on a 16 GB laptop) | HF/GitHub search 2026-09-24; paper text |

## Blocked
- **TMP 6B vs 4B head-to-head:** blocked until a pruned checkpoint is published, or cloud training is authorized. E09 bounds the payoff first.

## Pass 2 addendum (2026-09-25): text-encoder substitution (uncensoring addendum, Tier 1)
- heretic V2 TE: compatible, bit-exact conversion (only abliterated o_proj/down_proj differ), zero performance cost, no quality regression (blinded 24 pairs).
- **No behavioural difference** on 12 borderline prompts; stock is not restrictive on any of them.
- **CLOSED / REJECTED 2026-09-25** (directive §10): no performance, memory or quality advantage. The user prompt-file test was not run, by decision. Artifacts were removed; provenance is in experiments/tev2/PROVENANCE-heretic-v2.json.

## Pass 3 (2026-09-25): closures and the next research frontier
**Closed this pass (see experiments/STATUS.md for the full register)**
- E06 transformer release → **ADOPTED** into production.
- E05 cross-step caching → **REJECTED**.
- E04 micro-optimizations → **REJECTED / DEFERRED**.
- heretic-v2 → **CLOSED**.
- 7/6/5/4 steps → **EXPERIMENTAL** (no further work without a use case).
  - *Update 2026-09-29 (768² confirmation):* bf16 + 5 @768² NOT CONFIRMED (3/1/28; criterion 4, poster subtitle both seeds); 768² stays FAST (bf16 + 8). Open for the user: a dedicated 6-step gate at 768² (not started). Resolution matrix: 512² → 4, 768² → 8, 1024² → 5.
  - *Update 2026-09-29 (BALANCED pass):* bf16 + 5 @1024² ADOPTED as BALANCED; @768² PROMISING / CONFIRMATION PENDING (focused 32-pair blind confirmation, `experiments/step-count-quality-gate/protocol-confirm768.md`); @512² EXPERIMENTAL (dominated by ULTRA). bf16 + 4: @512² ADOPTED, @768²/@1024² REJECTED. Stage C (6 steps) DEFERRED: only if the 768² confirmation fails, and only by a dedicated gate. Target: minimum validated compute per practical resolution (512² → 4, 768² → 5 pending, 1024² → 5). No automatic resolution-based step selection yet.
  - *Update 2026-09-29 (step-count gate):* bf16 + 4 is ADOPTED as ULTRA at 512² only (REJECTED at 768²/1024²). bf16 + 5 is VALIDATED at 512², 768² (narrowest pass) and 1024², but is not in production. Open decisions for the user: FAST → 5 steps at 768²/1024²; an optional text-focused confirmatory sample at 768²; Stage C (bf16 + 6, seeds 8086/5150). Resolution-aware step selection is a hypothesis only. Stage B's 768² came out worse than 1024², against the σ ordering, so a simple σ threshold is not supported. `experiments/step-count-quality-gate/results.md`.
- 8 steps → **gate PASSED; FAST profile = bf16 + 8** (experiments/8step-quality-gate-report.md).
- Upstream: issues **submitted** (#761, #760); E10 corrected the promotion-source claim.

**Next frontier (priority order per directive §16).** Each item lists its first *measurement*, which must justify any build.

| # | frontier | first step (cheap, measured on this M5) | what would justify going further | risk / blocker |
|---|---|---|---|---|
| F-A | Structured model reduction: FFN width / layer / block importance | Per-block importance from the existing audit (residual magnitude and sensitivity), plus a layer-skip *probe*: skip one block at a time, 12 prompts, bf16, PSNR/SSIM + blinded spot check. Tells whether any block is near-redundant **without training** | ≥1–2 blocks removable with no visible regression, or a clear low-importance FFN subset → a recovery-distillation plan | Real width pruning needs recovery training (TMP); no arbitrary weight deletion. E09 proxy bound: −26% block time at −37.5% FFN width (bf16) |
| F-B | Quantization | E00-style block microbench of MLX 0.32.2 modes on real Z-Image shapes: affine q4 g32/g64/g128, **mxfp4**, **nvfp4**, **mxfp8**, affine q8; bf16 activations; time, bandwidth (bytes/weight incl. scales) and kernel path. Then per-layer error vs bf16 weights | a format ≥10% faster per block at acceptable per-layer error → full-model conversion + blinded gate | "4-bit" ≠ "4-bit": different scale layouts and kernels. Conversion from the bf16 checkpoint is needed; quality must be gated |
| F-C | Apple-Silicon / MLX kernels | Profile one bf16 block: q4 GEMM achieved bandwidth vs M5 peak; the ≈1.2 s/step non-matmul remainder (RoPE, norms, adaLN, SiLU·mul); whether NAX paths engage (Metal capture / MLX debug) | a measured gap to roofline ≥20% on a kernel that is ≥15% of block time | Custom Metal kernels are a maintenance burden; only for measured M5 wins |
| F-D | Few-step (<8 NFE) | Feasibility study only: data and compute requirements of Decoupled-DMD / LCM-style re-distillation for a 6B DiT; low-cost cloud options; whether the result converts back to mflux q4 | a credible path at the user's budget and a return path to MLX | Training-scale compute; no local training |
| F-E | VAE | Measure VAE share in the new production path (≈2–3 s of ≈80–90 s at 1024² bf16) and memory (now 2.23 GB VAE-phase peak) | only if VAE becomes ≥10% of wall time after other gains | Replacement needs a quality + runtime comparison first |
| F-0 | mflux 512² sigma shift (e^μ 1.88 vs official static 3.0) | A/B at 512²: mflux default vs a static-3.0 schedule, **if** achievable without modifying mflux (custom sigmas via API) | a visible quality difference at 512² | Scheduler changes are out of production scope; research only |

