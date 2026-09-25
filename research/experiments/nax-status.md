# NAX usage status: which photo-gen kernels dispatch through NAX? (Phase 3 §13)

Classification scale: **VERIFIED** (direct runtime evidence of the kernel being dispatched) · **LIKELY** (source dispatch conditions are met, and there is indirect evidence) · **NOT VERIFIED** · **NOT USED**.

Part 1 (static and indirect) was written 2026-09-25 while chain P3A was running. Part 2 (runtime capture) comes from chain P3B.

## Part 1: static evidence
### 1.1 Availability gate: MLX v0.32.2 (tag commit 1f8e74e3), `mlx/backend/metal/device.cpp::is_nax_available`
```
can_use_nax = __builtin_available(macOS 26.2, …)
arch = device.get_architecture().back();  gen = device.get_architecture_gen()
can_use_nax &= gen >= (arch == 'p' ? 18 : 17)
```
- This machine: `mx.device_info()` reports `architecture = applegpu_g17g` on macOS 27.0.
  - arch suffix 'g' → required gen ≥ 17;
  - gen = 17 → **is_nax_available() = true**.
- This is the eligibility the earlier research established. It is not dispatch evidence.
- Compile-time kill switch: `MLX_METAL_NO_NAX`. The PyPI wheel ships NAX kernels (below), so it was not set.

### 1.2 Kernels present in the installed binary (`mlx/lib/mlx.metallib`)
| family | examples (symbol names from `strings`) | relevance |
|---|---|---|
| `affine_qmm_t_nax_{float,float16_t,bfloat16_t}_gs_{32,64,128}_b_{2,3,4,5,6,8}_bm{32,64}_bn64_bk64_wm2_wn2` | `affine_qmm_t_nax_bfloat16_t_gs_64_b_4_bm64_bn64_bk64_wm2_wn2_al` | **every q4 linear in the DiT** (group 64, 4-bit, transposed) |
| `affine_qmm_n_nax_*`, `affine_gather_qmm_*_nax_*` | — | not on photo-gen's path (no MoE/gather) |
| `mxfp4 / mxfp8 / nvfp4 _qmm_t_nax_*` | `mxfp8_qmm_t_nax_bfloat…` | alternative quantization formats (§11) |
| `steel_gemm_fused_nax_*`, `steel_gemm_splitk_nax_*` | `steel_gemm_fused_nax_nn_bfloat16_bfloat16_bm128_bn128_bk256_wm4_wn4` | unquantized matmuls (e.g. any non-quantized linear) |
| `steel_attention_nax` | — | SDPA, full self-attention |

### 1.3 Dispatch conditions on photo-gen's shapes (source `quantized.cpp`, `scaled_dot_product_attention.cpp` @ v0.32.2)
**q4 linears (`QuantizedMatmul::eval_gpu`)**
- DiT activations are `[1, L, 3840]` (L = 4128 at 1024², 1056 at 512²) with 2-D weights → `M = L`, `B = 1`, `transpose = true`.
- M ≥ the qmv limit → `qmm_splitk`.
  - `split_k = max(1, 512 / (ceil(M/32)·ceil(N/32)))`. At 1024² with N = 3840: 129 × 120 = 15,480 threadgroups → split_k = 1 → falls through to `qmm`.
  - Also true at 512²: 33 × 120 = 3,960 → split_k = 1.
- `qmm` takes the NAX path iff `is_nax_available() && transpose && K % 64 == 0 && (env::enable_tf32() || x.dtype != float32)`.
  - K ∈ {3840, 10240} are both divisible by 64.
  - **`MLX_ENABLE_TF32` defaults to 1** (`mlx/utils.h`: `get_var("MLX_ENABLE_TF32", 1)`). photo-gen never sets it, and `prod_runner` strips `MLX_*` variables.
- So by source, **both fp32 (REFERENCE) and bf16 (FAST) q4 linears satisfy the NAX condition.**

**SDPA**
- `sdpa_full_self_attention_nax` is chosen iff `is_nax_available() && D ∈ {64, 96, 128, 256} && (enable_tf32 || dtype != float32)`.
- photo-gen has D = 128, so both precisions satisfy it.

**Implication for the REFERENCE precision label (flagged discrepancy).**
- If the fp32 path does dispatch NAX with the TF32 default, then REFERENCE's matmul and attention inner products run at **TF32-class precision** (10-bit mantissa inputs, as the TF32 name implies), not full IEEE fp32.
- "fp32" in photo-gen means *fp32 activations/storage*. It has never been a claim of fp32 matmul arithmetic.
- REFERENCE stays the reference: it is deterministic and hash-pinned, and nothing changes. But the label needs this footnote once Part 2 confirms the dispatch.

### 1.4 Indirect evidence: throughput (E00, synthetic weights, L = 4128, same shapes as production)
FLOPs = 2·M·N·K per matmul.

| op (q4) | activations | time (ms) | GFLOP | effective TFLOPS |
|---|---|---:|---:|---:|
| Q, K, V (3 × 3840→3840) | bf16 | 35.0 | 365 | **10.4** |
| FFN w1 + w3 (2 × 3840→10240) | bf16 | 66.2 | 649 | **9.8** |
| FFN w2 (10240→3840) | bf16 | 32.1 | 325 | **10.1** |
| Q, K, V | fp32 | 46.8 | 365 | **7.8** |
| FFN w1 + w3 | fp32 | 88.8 | 649 | **7.3** |

- Assumption (UNVERIFIED for M5): 8 GPU cores × 128 FP32 lanes × 2 FLOP/FMA × ~1.6–1.8 GHz ≈ **3.3–3.7 TFLOPS** SIMD fp32 peak. Earlier Apple GPUs ran fp16 at the same per-lane rate.
- The measured 7–10 TFLOPS is **2–3× above that assumed SIMD peak**, for both precisions. That is consistent with a matrix unit (NAX), and hard to explain without one.
- This is indirect evidence only: the core count and clock are assumptions, not measurements.

### 1.5 Status after Part 1
| photo-gen op | NAX status (Part 1) |
|---|---|
| DiT q4 linears, bf16 activations (FAST) | **LIKELY** |
| DiT q4 linears, fp32 activations (REFERENCE) | **LIKELY** (via the TF32 default) |
| DiT SDPA (D = 128), both precisions | **LIKELY** |
| adaLN / embedder / final-layer linears | **NOT VERIFIED** (need to check which are quantized; tiny M = 1 → qmv/gemv path, which has no NAX variant) |
| VAE decoder convolutions | **NOT VERIFIED** (conv path not yet traced) |
| Text encoder (Qwen3-4B q4, L ≈ tens of tokens) | **NOT VERIFIED** (small M; may hit qmv/split-K instead) |

## Part 2: runtime verification (chain P3B), method
1. **Metal capture** (`MTL_CAPTURE_ENABLED=1`, `mx.metal.start_capture`) of one q4 linear + one SDPA at production shapes, in each of three processes:
   - bf16;
   - fp32;
   - fp32 with `MLX_ENABLE_TF32=0` (control: the source says this must remove NAX from the fp32 path).

   Then list the compute-pipeline function names recorded in the `.gputrace` bundle. A `*_nax_*` name in the trace counts as **VERIFIED**.
2. **Causal toggle:** the same op, timed with `MLX_ENABLE_TF32=0` vs default in fp32. Per the source, this is the only runtime switch that changes NAX selection. For bf16 there is no runtime switch, so capture is the only direct evidence.
3. **End-to-end check** (only if 1 or 2 is positive): one production-worker fp32 generation with `MLX_ENABLE_TF32=0` at 512². Record the hash and time vs the REFERENCE hash `9ae59f59…`. A different hash would mean the TF32 default affects REFERENCE numerics.

Results are appended below.
