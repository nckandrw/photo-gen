# Quantization candidate map (Phase 3 §11)

Scope: map the candidates and decide what is measurable now. The Q4 pack stays production; nothing here changes it.

## What is known (measured)
- **E00, synthetic weights, L = 4128, one block's linears:** q4 is the fastest weight format on this M5 in both activation precisions.

  | activations | q4 (ms) | q8 (ms) | bf16 weights (ms) |
  |---|---:|---:|---:|
  | fp32 | 199 | 220 | 253 (separate) / 234 (fused) |
  | bf16 | 145 | 156 | 161 / 145 (fused) |

  (Sums of the E00 QKV-separate + out-proj + FFN-separate rows; "fused" uses the fused QKV and w1w3 rows.)
- **Nuance:** with bf16 activations, *fused* bf16-weight matmuls (145.3 ms) tie q4 (145.0 ms). "q4 is fastest" holds for the separate-projection layout mflux actually uses (161 vs 145 ms). The decisive argument against bf16 weights on this machine is memory (12.3 GB DiT), not speed alone.
- q4 group-64 layout: uint32-packed weights, bf16 scales and biases → **4.5 bits per weight**. The DiT is 3.46 GB.
- Available pre-quantized packs (mflux-community, DiT sizes): q3 2.69 GB · q4 3.46 · q5 4.23 · q6 5.00 · q8 6.54 · bf16 12.31 GB. Only q4 is on disk.
- **The quality of q4 vs higher-precision weights has never been measured in this project.** The E00 comparison was speed only, so any "quality tier" claim for q5/q6/q8 is an **OPEN QUESTION**.

## Mechanism: why fewer bits is not automatically faster here
- At L ≈ 4128 the DiT linears are strongly **compute-bound**. For Q/K/V: 121.7 GFLOP vs ~7.4 MB of q4 weight + 31.7 MB of activation per matmul → ~3,000 FLOP/byte, far above any M5 ridge point.
- The measured effective throughput (7–10 TFLOPS, see `nax-status.md` §1.4) is matrix-unit territory.
- Weight bytes still matter through **re-reads across M-tiles**. With bm = 64, each weight tile is streamed ≈ 65× at 1024² unless it stays cached (L2/SLC behaviour: UNVERIFIED). That traffic scales with bits:

  | weights | re-read traffic per Q-projection |
  |---|---:|
  | q4 | ≈ 0.48 GB |
  | bf16 | ≈ 1.9 GB |

  At ~150 GB/s that is 3 vs 12.5 ms against ~12 ms of compute. This hypothesis is **consistent with** the E00 ordering q4 < q8 < bf16, but unproven.
- Dequantization is done in-register inside the NAX qmm kernel. Its cost depends on the unpack pattern. 3-, 5- and 6-bit values straddle 32-bit words, so they can unpack more slowly than 4- and 8-bit ones despite sitting between them in size.
- **Prediction** (to be tested, not asserted):
  - q3 ≈ q4 or slower (unpack cost);
  - q5/q6 slower than q4, by less than q8's +7–10%;
  - mxfp4/nvfp4 ≈ q4 ± a few %;
  - group 128 marginally faster than group 64.

  No format is expected to give more than a single-digit % DiT gain over q4.

## Candidate matrix
| candidate | mechanism | expected speed vs q4 | expected memory | quality risk | measurable now? | status |
|---|---|---|---|---|---|---|
| affine q4 g64 (production) | — | 1.00 | 3.46 GB | — (reference) | — | **REFERENCE** |
| affine q4 g128 | fewer scales (4.25 bpw) | ≈ 1.00–0.98× time | −0.1 GB | low–medium | speed: yes (synthetic); quality: needs bf16 source weights | **PENDING (speed)** |
| affine q4 g32 | more scales (5 bpw) | slightly slower | +0.2 GB | lower than g64 | speed: yes | PENDING (speed) |
| affine q3 | smaller traffic, harder unpack | unknown (≈) | 2.69 GB | **high** (3-bit on a distilled 6B) | speed: yes; quality: pack download (2.7 GB) | PENDING (speed); quality BLOCKED (download approval) |
| affine q5 / q6 | quality headroom | slower (predicted) | 4.23 / 5.00 GB | lower than q4 | speed: yes; quality: pack download | PENDING (speed); quality BLOCKED (download approval) |
| q8 / bf16 weights | — | slower (measured) | 6.5 / 12.3 GB | lowest | done | **REJECTED for speed** (E00); still unmeasured as a *quality* tier |
| mxfp4 (g32, e8m0 scales, no bias) | FP4 microscaling | ≈ | ≈ 4.25 bpw | medium–high without QAT | speed: yes; quality: needs bf16 source | PENDING (speed) |
| nvfp4 (g16, fp8 scales) | FP4 with finer scales | ≈ | ≈ 4.5 bpw | medium | speed: yes | PENDING (speed) |
| mxfp8 | FP8 microscaling | ≈ q8 | ≈ 8.25 bpw | low | speed: yes | PENDING (speed) |
| mixed / layer-sensitive precision | spend bits where the sensitivity map says blocks matter | ≈ q4 ± | ≈ q4 | depends on the map | needs `block-sensitivity-map.md` + bf16 source weights | **DEFERRED** until the map exists |
| timestep-aware weight precision | different weights per step | ≈ | **2 weight copies** (> 16 GB budget with the TE) | — | — | **REJECTED (memory)** on a 16 GB machine; activation-precision timestep switching is already moot (bf16 passes at every step) |
| activation quantization (int8/fp8 activations) | low-bit A×W matmul | potentially large | — | high | MLX 0.32.2 exposes no int8/fp8-activation matmul | **BLOCKED** (no kernel) |

## What needs the user's approval
- **Quality** of any non-q4 format needs real source weights. There are two options:
  - (a) download the mflux-community q3/q5/q6 packs (2.7–5.0 GB each, pre-quantized by the same tool);
  - (b) download the bf16 pack (12.3 GB) and quantize locally to every format. This is the only way to test g32/g128, mxfp4, nvfp4 and mixed precision from a single clean source.

  Either option is a new model download. The project rule is that models are never auto-downloaded, so this is **not done without explicit approval**.
- Recommendation: measure speed first (chain P3B, no download). Ask for downloads only for formats that are ≥ 3% faster end to end, or for a quality tier the user actually wants.

## Chain P3B measurement
`quant_microbench.py <fp32|bf16> <L> <out.json>`: 19 formats × (bf16 at L = 4128, bf16 at L = 1056, fp32 at L = 4128). Results are appended below.

## Chain P3B speed map (2026-09-28; `p3b/quant-*.json`; synthetic weights, one block's 7 linears, production shapes)
**Confound (disclosed):** within each process, formats ran in a fixed order (bf16 → q3 … q8 → mxfp4, nvfp4, mxfp8) on a warming chip. Later formats are systematically disadvantaged, so differences under ≈ 5% are not interpretable.

| format | bf16, L4128 (FAST 1024²) | bf16, L1056 (FAST 512²) | fp32, L4128 (REFERENCE 1024²) | weight error (Gaussian) |
|---|---:|---:|---:|---:|
| **affine q4 g64 (production)** | **1.000** (151.2 ms) | **1.000** (37.5 ms) | **1.000** (279.0 ms) | 0.097 |
| affine q4 g128 | 0.994 | 1.146 | 0.991 | 0.107 |
| affine q3 g128 / g64 | 0.986 / 0.996 | 1.344 / 1.488 | 0.963 / 1.003 | 0.20–0.22 |
| affine q5 (g32–g128) | 1.08–1.09 | 1.28–1.46 | 1.17–1.20 | 0.04–0.05 |
| affine q6 (g32–g128) | 1.14–1.18 | 1.31–1.46 | 1.21–1.24 | 0.02–0.03 |
| affine q8 | 1.17–1.25 | 1.27–1.46 | 1.25–1.29 | 0.006–0.007 |
| bf16 weights | 1.033 | 1.298 | 1.207 | 0 |
| nvfp4 / mxfp4 / mxfp8 | 1.21 / 1.24 / 1.24 | 1.19 / 1.42 / 1.61 | 1.07 / 1.10 / 1.31 | 0.097 / 0.117 / 0.023 |

**Findings**
- **No format meets the ≥ 3% speed threshold.** The best nominal gain, q3 g128 at −1.4% (bf16, 1024²), is inside the order confound, and its weight error is 2.3× q4's. **q4 g64 stays the fastest measured format**, and at 512² it is ≥ 15% faster than every alternative, which suggests its kernel tiles are the best-tuned.
- **Higher precision (q5/q6/q8) costs +8% to +46%.** It could only matter as a *quality* tier. The quality cost of q4 has never been measured.
- **FP4/FP8 microscaling formats are slower** than affine q4 on this M5 / MLX 0.32.2 (+7% to +61%).

**Status:**
- speed search for a faster format: **CLOSED** (no candidate);
- q5/q6 as a *quality* tier: **OPEN QUESTION**, needs downloads plus a blinded gate, low priority;
- mixed or layer-sensitive precision: **DEFERRED**. It can't beat q4 on speed per these numbers; it could only trade quality.
