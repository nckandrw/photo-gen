# photo-gen paper index

Metadata verified from the arXiv API on 2026-09-24 (`arxiv-meta.json`; all 27 IDs resolve to the cited titles; 2307.06350 is now titled *T2I-CompBench++*).
Status vocabulary: UNREAD / READ / AUDIT / PROTOTYPE / BENCHMARK / REJECTED / ADOPTED. **READ (abstract)** means only the abstract has been read so far; mechanism claims for those are provisional. 'not checked' = code/licence not yet verified.
Paper results are **never** photo-gen results; transferability is classified per the research addendum §21.

## Z-Image: An Efficient Image Generation Foundation Model with Single-Stream Diffusion Transformer
- paper: Z-Image: An Efficient Image Generation Foundation Model with Single-Stream Diffusion Transformer
- arxiv: 2511.22699
- year: 2025
- authors: Z-Image Team et al. (24)
- category: model / architecture
- directly_relevant: yes — it is our model
- model_architecture: S3-DiT 6.15B, Qwen3-4B TE, Flux VAE
- training_or_inference: training + inference
- requires_retraining: no
- requires_model_change: no
- hardware_assumptions: trained/benchmarked on H800
- apple_silicon_relevance: direct: defines everything we run
- code_available: Tongyi-MAI/Z-Image (Apache-2.0) — checked
- license: Apache-2.0 (model+code) — checked
- candidate_experiment: architecture map (done); fp32-promotion finding E01/E02
- expected_risk: low
- expected_benefit: high (understanding; enabled E02)
- status: AUDIT
- transferability: DIRECTLY TRANSFERABLE

## TMP: Tree-structured Mixed-policy Pruning for Large-scale Image Generation and Editing
- paper: TMP: Tree-structured Mixed-policy Pruning for Large-scale Image Generation and Editing
- arxiv: 2606.27089
- year: 2026
- authors: Peizhen Zhang et al. (13)
- category: pruning (structured width)
- directly_relevant: yes — reports Z-Image-Turbo 6B→4B
- model_architecture: MLP expansion −37.5% (Z-Image); MoE/DiT generally
- training_or_inference: compression + recovery training
- requires_retraining: YES (tree-structured mixed-policy feature distillation + velocity alignment)
- requires_model_change: yes (new checkpoint)
- hardware_assumptions: datacenter GPUs; no latency/memory reported for Z-Image
- apple_silicon_relevance: high if a pruned checkpoint existed: FFN = 56% of block time (E00)
- code_available: HunyuanImage-3.0 integration claimed; NO Z-Image code/weights found (HF + GitHub searched 2026-09-24)
- license: not checked (HunyuanImage repo NOASSERTION)
- candidate_experiment: BLOCKED locally; proxy E09: timing of a width-reduced random-weight block to bound the speed gain
- expected_risk: high (needs training)
- expected_benefit: potentially 15–25% denoise (ESTIMATE, FLOP share)
- status: AUDIT — BLOCKED (no artifact)
- transferability: PARTIALLY TRANSFERABLE (method needs training we cannot run locally)

## Decoupled DMD: CFG Augmentation as the Spear, Distribution Matching as the Shield
- paper: Decoupled DMD: CFG Augmentation as the Spear, Distribution Matching as the Shield
- arxiv: 2511.22677
- year: 2025
- authors: Dongyang Liu et al. (11)
- category: few-step distillation
- directly_relevant: yes — produced Z-Image-Turbo's 8-step recipe
- model_architecture: DMD decomposition: CFG-augmentation engine + DM regularizer
- training_or_inference: training
- requires_retraining: yes
- requires_model_change: yes
- hardware_assumptions: datacenter
- apple_silicon_relevance: conceptual: explains why Turbo runs guidance 0 / 8 NFE
- code_available: not checked
- license: not checked
- candidate_experiment: E03 step sweep 9→8→7→6→5→4 (inference-only)
- expected_risk: low (inference sweep)
- expected_benefit: high: linear in steps
- status: READ (abstract)
- transferability: CONCEPTUALLY USEFUL (training); step sweep is directly testable

## FastCache: Fast Caching for Diffusion Transformer Through Learnable Linear Approximation
- paper: FastCache: Fast Caching for Diffusion Transformer Through Learnable Linear Approximation
- arxiv: 2505.20353
- year: 2025
- authors: Dong Liu et al. (6)
- category: cross-step caching (hidden-state)
- directly_relevant: yes (DiT)
- model_architecture: DiT; token saliency + block-level cache with linear approximation
- training_or_inference: inference (+ small learned linear maps)
- requires_retraining: light (fit linear approximations)
- requires_model_change: no
- hardware_assumptions: CUDA
- apple_silicon_relevance: depends on redundancy in 9-step Turbo (unknown; few steps usually = low redundancy)
- code_available: not checked
- license: not checked
- candidate_experiment: E05 cross-step block-delta instrumentation first
- expected_risk: medium (quality at 9 steps)
- expected_benefit: unknown until E05
- status: READ (abstract)
- transferability: PARTIALLY TRANSFERABLE (redundancy unverified for 8-NFE models)

## Token Caching for Diffusion Transformer Acceleration
- paper: Token Caching for Diffusion Transformer Acceleration
- arxiv: 2409.18523
- year: 2024
- authors: Jinming Lou et al. (8)
- category: token caching
- directly_relevant: yes (DiT)
- model_architecture: DiT; token pruning/reuse by block & timestep
- training_or_inference: inference (+ router training)
- requires_retraining: light
- requires_model_change: no
- hardware_assumptions: CUDA
- apple_silicon_relevance: bookkeeping (gather/scatter) cost on MLX unknown
- code_available: not checked
- license: not checked
- candidate_experiment: after E05; measure gather/scatter overhead on MLX
- expected_risk: medium
- expected_benefit: unknown
- status: READ (abstract)
- transferability: PARTIALLY TRANSFERABLE

## ToMA: Token Merge with Attention for Diffusion Models
- paper: ToMA: Token Merge with Attention for Diffusion Models
- arxiv: 2509.10918
- year: 2025
- authors: Wenbo Lu et al. (4)
- category: token reduction
- directly_relevant: partially
- model_architecture: DiT/UNet; submodular merge, GPU-friendly ops
- training_or_inference: inference
- requires_retraining: no
- requires_model_change: no
- hardware_assumptions: CUDA + FlashAttention
- apple_silicon_relevance: attention ≈18% of block here → ceiling small at 1024²
- code_available: not checked
- license: not checked
- candidate_experiment: low priority; only if attention share grows (≥1536²)
- expected_risk: medium
- expected_benefit: ≤ ~10% at 1024² (ceiling; ESTIMATE)
- status: READ (abstract)
- transferability: CONCEPTUALLY USEFUL (its FLOPs-vs-wall-clock lesson applies)

## PTQ4DiT: Post-training Quantization for Diffusion Transformers
- paper: PTQ4DiT: Post-training Quantization for Diffusion Transformers
- arxiv: 2405.16005
- year: 2024
- authors: Junyi Wu et al. (5)
- category: PTQ for DiT (W8A8/W4A8)
- directly_relevant: partially
- model_architecture: DiT; salient-channel balancing, timestep calibration
- training_or_inference: post-training quantization
- requires_retraining: calibration only
- requires_model_change: yes (re-quantized weights)
- hardware_assumptions: integer GEMM hardware
- apple_silicon_relevance: MLX q4 is weight-only (activations fp32 in production, bf16 after E02); MLX has no W4A8 GEMM path we use
- code_available: not checked
- license: not checked
- candidate_experiment: E07 per-layer/timestep sensitivity of q4 vs bf16 weights
- expected_risk: medium
- expected_benefit: memory/quality, speed unclear on MLX
- status: READ (abstract)
- transferability: CONCEPTUALLY USEFUL

## Q-DiT: Accurate Post-Training Quantization for Diffusion Transformers
- paper: Q-DiT: Accurate Post-Training Quantization for Diffusion Transformers
- arxiv: 2406.17343
- year: 2024
- authors: Lei Chen et al. (8)
- category: PTQ for DiT (granularity)
- directly_relevant: partially
- model_architecture: DiT; group-size allocation, dynamic activation quant
- training_or_inference: post-training quantization
- requires_retraining: calibration
- requires_model_change: yes
- hardware_assumptions: integer kernels
- apple_silicon_relevance: group-size choice is an MLX knob (we use 64) — testable
- code_available: not checked
- license: not checked
- candidate_experiment: E07 (group size / mixed bits per layer)
- expected_risk: medium
- expected_benefit: unclear
- status: READ (abstract)
- transferability: PARTIALLY TRANSFERABLE (weight-granularity part)

## Timestep-Aware Correction for Quantized Diffusion Models
- paper: Timestep-Aware Correction for Quantized Diffusion Models
- arxiv: 2407.03917
- year: 2024
- authors: Yuzhe Yao et al. (7)
- category: timestep-aware quant correction
- directly_relevant: partially
- model_architecture: diffusion (UNet-era)
- training_or_inference: inference-time correction
- requires_retraining: calibration
- requires_model_change: no
- hardware_assumptions: —
- apple_silicon_relevance: relevant only if quant error is step-dependent here (unmeasured)
- code_available: not checked
- license: not checked
- candidate_experiment: E07 includes per-step error measurement
- expected_risk: low
- expected_benefit: unclear
- status: READ (abstract)
- transferability: CONCEPTUALLY USEFUL

## 6Bit-Diffusion: Inference-Time Mixed-Precision Quantization for Video Diffusion Models
- paper: 6Bit-Diffusion: Inference-Time Mixed-Precision Quantization for Video Diffusion Models
- arxiv: 2603.18742
- year: 2026
- authors: Rundong Su et al. (6)
- category: mixed-precision + delta caching (video DiT)
- directly_relevant: partially
- model_architecture: video DiT; NVFP4/INT8 per timestep; block input-output difference predicts sensitivity
- training_or_inference: inference
- requires_retraining: no
- requires_model_change: no
- hardware_assumptions: NVFP4 (Blackwell) / INT8
- apple_silicon_relevance: NVFP4 unavailable on M5; the principle (block I/O difference → precision/skip decision) is testable
- code_available: not checked
- license: not checked
- candidate_experiment: E05 records block input/output deltas (serves this too)
- expected_risk: medium
- expected_benefit: unclear
- status: READ (abstract)
- transferability: CONCEPTUALLY USEFUL

## FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness
- paper: FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness
- arxiv: 2205.14135
- year: 2022
- authors: Tri Dao et al. (5)
- category: attention kernel (IO-aware)
- directly_relevant: background
- model_architecture: exact attention via tiling
- training_or_inference: inference kernel
- requires_retraining: no
- requires_model_change: no
- hardware_assumptions: CUDA SRAM/HBM
- apple_silicon_relevance: MLX already ships fused SDPA (mx.fast.scaled_dot_product_attention, NAX paths); measured 43.7 ms/block fp32, 27.1 ms bf16
- code_available: n/a
- license: n/a
- candidate_experiment: none beyond E02 (dtype) and mask=None
- expected_risk: —
- expected_benefit: already realized by MLX
- status: AUDIT
- transferability: CONCEPTUALLY USEFUL (already embodied in MLX SDPA)

## SageAttention: Accurate 8-Bit Attention for Plug-and-play Inference Acceleration
- paper: SageAttention: Accurate 8-Bit Attention for Plug-and-play Inference Acceleration
- arxiv: 2410.02367
- year: 2024
- authors: Jintao Zhang et al. (6)
- category: low-bit attention
- directly_relevant: partially
- model_architecture: 8-bit QK^T with smoothing
- training_or_inference: inference kernel
- requires_retraining: no
- requires_model_change: no
- hardware_assumptions: CUDA INT8 tensor cores
- apple_silicon_relevance: would need custom Metal/NAX kernel; attention ≈18% of block → ceiling small
- code_available: not checked
- license: not checked
- candidate_experiment: Tier C only
- expected_risk: high (kernel work)
- expected_benefit: ≤ ~9% denoise (ESTIMATE, half of attention share)
- status: READ (abstract)
- transferability: NOT TRANSFERABLE as-is (hardware-specific); concept only

## SANA: Efficient High-Resolution Image Synthesis with Linear Diffusion Transformers
- paper: SANA: Efficient High-Resolution Image Synthesis with Linear Diffusion Transformers
- arxiv: 2410.10629
- year: 2024
- authors: Enze Xie et al. (11)
- category: efficient architecture (linear DiT, 32× AE)
- directly_relevant: background
- model_architecture: new model family
- training_or_inference: training
- requires_retraining: yes (new model)
- requires_model_change: yes
- hardware_assumptions: laptop GPU claims
- apple_silicon_relevance: design philosophy for a future Apple-first model
- code_available: not checked
- license: not checked
- candidate_experiment: none now
- expected_risk: —
- expected_benefit: long-term
- status: READ (abstract)
- transferability: CONCEPTUALLY USEFUL

## MobileDiffusion: Instant Text-to-Image Generation on Mobile Devices
- paper: MobileDiffusion: Instant Text-to-Image Generation on Mobile Devices
- arxiv: 2311.16567
- year: 2023
- authors: Yang Zhao et al. (5)
- category: mobile T2I design
- directly_relevant: background
- model_architecture: UNet redesign + distillation
- training_or_inference: training
- requires_retraining: yes
- requires_model_change: yes
- hardware_assumptions: mobile NPU/GPU
- apple_silicon_relevance: philosophy only
- code_available: not checked
- license: not checked
- candidate_experiment: none now
- expected_risk: —
- expected_benefit: long-term
- status: READ (abstract)
- transferability: CONCEPTUALLY USEFUL

## SnapGen: Taming High-Resolution Text-to-Image Models for Mobile Devices with Efficient Architectures and Training
- paper: SnapGen: Taming High-Resolution Text-to-Image Models for Mobile Devices with Efficient Architectures and Training
- arxiv: 2412.09619
- year: 2024
- authors: Dongting Hu et al. (19)
- category: mobile T2I design
- directly_relevant: background
- model_architecture: small DiT/UNet + cross-arch distillation
- training_or_inference: training
- requires_retraining: yes
- requires_model_change: yes
- hardware_assumptions: mobile
- apple_silicon_relevance: philosophy only
- code_available: not checked
- license: not checked
- candidate_experiment: none now
- expected_risk: —
- expected_benefit: long-term
- status: READ (abstract)
- transferability: CONCEPTUALLY USEFUL

## Toward Lightweight and Fast Decoders for Diffusion Models in Image and Video Generation
- paper: Toward Lightweight and Fast Decoders for Diffusion Models in Image and Video Generation
- arxiv: 2503.04871
- year: 2025
- authors: Alexey Buzovkin et al. (2)
- category: lightweight VAE decoder
- directly_relevant: partially
- model_architecture: ViT/Taming decoders distilled
- training_or_inference: training
- requires_retraining: yes (decoder)
- requires_model_change: yes (decoder)
- hardware_assumptions: CUDA
- apple_silicon_relevance: VAE is ≈3% of wall here (2–3 s of 87 s) → time benefit small; memory benefit already via tiling
- code_available: not checked
- license: not checked
- candidate_experiment: deprioritized by measurement
- expected_risk: medium
- expected_benefit: ≤3% time
- status: READ (abstract)
- transferability: CONCEPTUALLY USEFUL (low value on this pipeline)

## DeepCache: Accelerating Diffusion Models for Free
- paper: DeepCache: Accelerating Diffusion Models for Free
- arxiv: 2312.00858
- year: 2023
- authors: Xinyin Ma et al. (3)
- category: cross-step caching (UNet)
- directly_relevant: background
- model_architecture: UNet skip-branch reuse
- training_or_inference: inference
- requires_retraining: no
- requires_model_change: no
- hardware_assumptions: —
- apple_silicon_relevance: not directly applicable to DiT; motivates E05
- code_available: n/a
- license: n/a
- candidate_experiment: E05 (DiT analogue)
- expected_risk: —
- expected_benefit: —
- status: READ (abstract)
- transferability: CONCEPTUALLY USEFUL

## Consistency Models
- paper: Consistency Models
- arxiv: 2303.01469
- year: 2023
- authors: Yang Song et al. (4)
- category: consistency models
- directly_relevant: background
- model_architecture: few/one-step theory
- training_or_inference: training
- requires_retraining: yes
- requires_model_change: yes
- hardware_assumptions: —
- apple_silicon_relevance: future few-step research
- code_available: n/a
- license: n/a
- candidate_experiment: none now
- expected_risk: —
- expected_benefit: long-term
- status: READ (abstract)
- transferability: CONCEPTUALLY USEFUL

## Latent Consistency Models: Synthesizing High-Resolution Images with Few-Step Inference
- paper: Latent Consistency Models: Synthesizing High-Resolution Images with Few-Step Inference
- arxiv: 2310.04378
- year: 2023
- authors: Simian Luo et al. (5)
- category: latent consistency models
- directly_relevant: background
- model_architecture: LCM distillation
- training_or_inference: training
- requires_retraining: yes
- requires_model_change: yes
- hardware_assumptions: —
- apple_silicon_relevance: future few-step research
- code_available: n/a
- license: n/a
- candidate_experiment: none now
- expected_risk: —
- expected_benefit: long-term
- status: READ (abstract)
- transferability: CONCEPTUALLY USEFUL

## Multistep Distillation of Diffusion Models via Moment Matching
- paper: Multistep Distillation of Diffusion Models via Moment Matching
- arxiv: 2406.04103
- year: 2024
- authors: Tim Salimans et al. (4)
- category: moment-matching distillation
- directly_relevant: background
- model_architecture: multistep distillation
- training_or_inference: training
- requires_retraining: yes
- requires_model_change: yes
- hardware_assumptions: —
- apple_silicon_relevance: future few-step research
- code_available: n/a
- license: n/a
- candidate_experiment: none now
- expected_risk: —
- expected_benefit: long-term
- status: READ (abstract)
- transferability: CONCEPTUALLY USEFUL

## SaRA: High-Efficient Diffusion Model Fine-tuning with Progressive Sparse Low-Rank Adaptation
- paper: SaRA: High-Efficient Diffusion Model Fine-tuning with Progressive Sparse Low-Rank Adaptation
- arxiv: 2409.06633
- year: 2024
- authors: Teng Hu et al. (6)
- category: sparse low-rank fine-tuning
- directly_relevant: future
- model_architecture: PEFT
- training_or_inference: training
- requires_retraining: yes (adapter)
- requires_model_change: adapter
- hardware_assumptions: GPU training
- apple_silicon_relevance: MLX training possible in principle (mflux has LoRA training) — untested
- code_available: not checked
- license: not checked
- candidate_experiment: Tier C
- expected_risk: medium
- expected_benefit: customization
- status: READ (abstract)
- transferability: PARTIALLY TRANSFERABLE

## IntLoRA: Integral Low-rank Adaptation of Quantized Diffusion Models
- paper: IntLoRA: Integral Low-rank Adaptation of Quantized Diffusion Models
- arxiv: 2410.21759
- year: 2024
- authors: Hang Guo et al. (5)
- category: integer LoRA on quantized weights
- directly_relevant: future
- model_architecture: PEFT on quantized models
- training_or_inference: training
- requires_retraining: yes (adapter)
- requires_model_change: adapter
- hardware_assumptions: integer kernels
- apple_silicon_relevance: q4 base + adapter matches our deployment shape
- code_available: not checked
- license: not checked
- candidate_experiment: Tier C
- expected_risk: medium
- expected_benefit: customization w/o re-quantization
- status: READ (abstract)
- transferability: PARTIALLY TRANSFERABLE

## GenEval: An Object-Focused Framework for Evaluating Text-to-Image Alignment
- paper: GenEval: An Object-Focused Framework for Evaluating Text-to-Image Alignment
- arxiv: 2310.11513
- year: 2023
- authors: Dhruba Ghosh et al. (3)
- category: evaluation (GenEval)
- directly_relevant: evaluation
- model_architecture: object/count/position/color
- training_or_inference: evaluation
- requires_retraining: no
- requires_model_change: no
- hardware_assumptions: detector model (GPU ok)
- apple_silicon_relevance: needs detector stack in a separate env
- code_available: not checked
- license: not checked
- candidate_experiment: E08 evaluation harness (subset)
- expected_risk: low
- expected_benefit: better measurement
- status: READ (abstract)
- transferability: DIRECTLY TRANSFERABLE (as a tool)

## GenEval 2: Addressing Benchmark Drift in Text-to-Image Evaluation
- paper: GenEval 2: Addressing Benchmark Drift in Text-to-Image Evaluation
- arxiv: 2512.16853
- year: 2025
- authors: Amita Kamath et al. (6)
- category: evaluation (GenEval 2)
- directly_relevant: evaluation
- model_architecture: VLM-judged; addresses drift
- training_or_inference: evaluation
- requires_retraining: no
- requires_model_change: no
- hardware_assumptions: judge VLM
- apple_silicon_relevance: judge must run locally or externally — privacy/offline policy applies
- code_available: not checked
- license: not checked
- candidate_experiment: E08
- expected_risk: low
- expected_benefit: better measurement
- status: READ (abstract)
- transferability: DIRECTLY TRANSFERABLE (as a tool, judge-dependent)

## T2I-CompBench++: An Enhanced and Comprehensive Benchmark for Compositional Text-to-image Generation
- paper: T2I-CompBench++: An Enhanced and Comprehensive Benchmark for Compositional Text-to-image Generation
- arxiv: 2307.06350
- year: 2023
- authors: Kaiyi Huang et al. (6)
- category: evaluation (T2I-CompBench++)
- directly_relevant: evaluation
- model_architecture: attribute binding, spatial, numeracy
- training_or_inference: evaluation
- requires_retraining: no
- requires_model_change: no
- hardware_assumptions: —
- apple_silicon_relevance: prompt set usable offline
- code_available: not checked
- license: not checked
- candidate_experiment: E08 prompt subset
- expected_risk: low
- expected_benefit: better measurement
- status: READ (abstract)
- transferability: DIRECTLY TRANSFERABLE (prompt set)

## OneIG-Bench: Omni-dimensional Nuanced Evaluation for Image Generation
- paper: OneIG-Bench: Omni-dimensional Nuanced Evaluation for Image Generation
- arxiv: 2506.07977
- year: 2025
- authors: Jingjing Chang et al. (9)
- category: evaluation (OneIG-Bench)
- directly_relevant: evaluation
- model_architecture: alignment, text, reasoning, style, diversity
- training_or_inference: evaluation
- requires_retraining: no
- requires_model_change: no
- hardware_assumptions: —
- apple_silicon_relevance: TMP reports on OneIG → common ground
- code_available: not checked
- license: not checked
- candidate_experiment: E08 text-rendering subset
- expected_risk: low
- expected_benefit: better measurement
- status: READ (abstract)
- transferability: DIRECTLY TRANSFERABLE (prompt set)

## ImageReward: Learning and Evaluating Human Preferences for Text-to-Image Generation
- paper: ImageReward: Learning and Evaluating Human Preferences for Text-to-Image Generation
- arxiv: 2304.05977
- year: 2023
- authors: Jiazheng Xu et al. (8)
- category: evaluation (ImageReward)
- directly_relevant: evaluation
- model_architecture: reward model
- training_or_inference: evaluation
- requires_retraining: no
- requires_model_change: no
- hardware_assumptions: GPU inference
- apple_silicon_relevance: reward model is not a human substitute
- code_available: not checked
- license: not checked
- candidate_experiment: optional in E08
- expected_risk: low
- expected_benefit: auxiliary signal
- status: READ (abstract)
- transferability: DIRECTLY TRANSFERABLE (as auxiliary metric)
