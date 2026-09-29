# Experiment status register (research/experiments/)
Updated 2026-09-25.

**Statuses**
- **REFERENCE:** a permanent baseline.
- **ADOPTED:** in production.
- **ADOPTED AS OPT-IN:** in production, requires an explicit request.
- **PENDING:** a gate is in progress.
- **EXPERIMENTAL:** allowed, but not quality-equivalent.
- **REJECTED:** measured and not worth it.
- **DEFERRED:** below the current value bar.
- **BLOCKED:** needs something that doesn't exist yet.
- **CLOSED:** the question has been answered.

Negative results are kept on purpose.

| experiment | status | evidence | one-line result |
|---|---|---|---|
| fp32 + 9 steps, `--low-ram`, q4 (mflux 0.20.0 / MLX 0.32.2, M5 16 GB) | **REFERENCE** | MFLUX-ZIMAGE-RESULTS.md, PHOTO-GEN-PARITY-20260924.md, production-memory-fix-report.md | pixel hash 1024² fe47d88d…, 512² 9ae59f59…; 9 steps = 9 NFE in mflux (scheduler-nfe-note.md) |
| E02 bf16 hidden stream | **ADOPTED AS OPT-IN** (`precision: bf16`; bf16 + 9 validated at **1024² only**, experimental at 512²/768² since 2026-09-28) | E02-RESULTS.md, bf16-quality-report.md | blinded 24 pairs: 0 fp32-better / 2 bf16-better / 22 ties; ≈30% less denoise time vs fp32 in the same session |
| E06 transformer release before VAE | **ADOPTED** (production default, both precisions) | vae-lifecycle-report.md, production-memory-fix-report.md | pixel-identical; 1024² footprint fp32 6.56 GB, bf16 5.84 GB (was ≈7.3) |
| E03 8 steps (bf16) = **FAST profile** | **ADOPTED** (`profile: fast`; **validated at 512², 768², 1024²** by direct REFERENCE-vs-FAST blinded gates, 2026-09-25: 0/0/24, 2/0/22, 0/1/23; fast-resolution-gates-report.md) | 8step-quality-gate-report.md, PERFORMANCE-MAP.md | quality: blinded 24 primary pairs (bf16/9 vs bf16/8), 0 worse / 1 better / 23 ties; timing: 36 ABBA pairs, denoise ratio 0.887; cold 1024² end to end vs REFERENCE: wall 1.54×, denoise 1.61× |
| E03 7/6/5/4 steps | **EXPERIMENTAL** (research only). **bf16 + 4 = ULTRA profile: ADOPTED at 512² only** (Stage A gate 1/0/23; production 2026-09-29, hash 512² `6aa2b842`); **REJECTED at 768² (1 text pair) and 1024² (text class)**. **bf16 + 5 (Stage B gate passed at all three sizes, 2026-09-29; blind 1/0/23, 3/0/21, 0/0/24; paired denoise 5/8 ≈ 0.63): @1024² ADOPTED as the BALANCED profile; @768² NOT CONFIRMED → stays FAST** (Stage B narrowest pass; focused 32-pair confirmation 3/1/28 failed criterion 4, the poster subtitle 8-better in both seeds; pooled descriptive 6/1/49); **@512² EXPERIMENTAL, not useful for production** (ULTRA bf16 + 4 dominates). **bf16 + 6: Stage C DEFERRED**; a dedicated 6-step gate at 768² awaits the user's decision (`step-count-quality-gate/results.md`) | step-sweep-report.md (original: 7–6 draft, 5–4 preview; small, unblinded, seed 42), 4step-probe/results.md §E2 (blinded Turbo-4 vs FAST 2/3/19 at 1024²) | not validated, not production, not quality-equivalent until the gate completes |
| E05 cross-step caching (block / token / FFN reuse, FBCache-style) | **REJECTED** | cache-audit-report.md | per-step block change 19–46%; ≤3.5% block-skip ceiling; no stable tokens; corroborated upstream (#753) |
| E04/M1 SDPA `mask=None` | **REJECTED** | microopt-report.md | exact, but no speed-up in bf16 |
| M3 context refiner once per image | **DEFERRED** | microopt-report.md | <1% bound |
| Fused QKV / fused SwiGLU (q4) | **REJECTED** | EXPERIMENT-BACKLOG.md (E00) | ≤1.4% / 0% |
| q8 / bf16 weights "for speed" | **REJECTED** | E00 | q4 is the fastest weight format here |
| Qwen-2.1-style caption KV prefix cache | **REJECTED** | z-image-architecture-map.md | not exact: caption tokens are timestep-modulated |
| E09 FFN-width pruning payoff (proxy) | measured → feeds **FFN pruning: RESEARCH CANDIDATE** | pruning-tmp-assessment.md | −26% block time in bf16 at −37.5% FFN width (proxy only) |
| TMP pruning reproduction | **BLOCKED** | pruning-tmp-assessment.md | no pruned weights or code; recovery training infeasible locally |
| Tier-1 TE substitution (heretic V2) | **CLOSED / REJECTED** | te-heretic-v2-report.md, tev2/PROVENANCE-heretic-v2.json | compatible and zero-cost, but no advantage; artifacts removed |
| User explicit-prompt TE test (`te_userfile_ab.py`) | **CLOSED** (not run, by decision) | te-heretic-v2-report.md | — |
| Upstream mflux report | **SUBMITTED** 2026-09-25: mflux-community/mflux #761 (fp32 stream), #760 (transformer lifetime) | upstream-mflux-issue-SUBMITTED.md | awaiting maintainer response |
| E10 fp32-promotion ablation | **CLOSED** (answered) | e10/, E02-RESULTS.md correction | the two required sources are the timestep embedding and RoPE; pad tokens are not a source (corrects E01/E02 docs) |
| Performance map (tiers) | **REFERENCE DATA** | PERFORMANCE-MAP.md | cold + ABBA sustained; 1024² sustained block not steady-state (disclosed) |
| mflux 512² sigma shift ≠ official static 3.0 | **CLOSED** (2026-09-25: implementation difference, quality-neutral) | sigma-schedule-audit.md, sigma/ | source-verified FLUX dynamic shift vs official static 3.0; blinded 24 pairs each: 512² M 3 / S 0 / 21 ties, 768² M 2 / S 0 / 22 ties, 1024² sanity 11 ties + 1 S; no runtime effect; production unchanged |
| Block-sensitivity map (34 blocks) | **MEASURED** (2026-09-28) | block-sensitivity-map.md, p3b/ | main blocks equal-cost (≈307 ms bf16 @1024² hot); cr0/cr1 cheap but critical; late blocks L25–L28 least important; no block removable without visible change; 512↔1024 rank ρ 0.75 |
| Structured FFN-width reduction (group-aligned, no recovery) | **BLOCKED** (needs recovery training) | ffn-reduction-design.md, p3b/ffn-sweep-summary.json | 90% width already breaks text ("QWEN IMAGE 3.1"); 60% collapses; −6…−20% denoise @1024² |
| Quantization speed map (19 formats) | **CLOSED** for speed | quantization-map.md, p3b/quant-*.json | q4 g64 fastest or within noise at every shape; q5/q6/q8 +8…+46%; fp4/fp8 microscaling slower |
| Kernel profile (FAST 1024²) | **MEASURED** | kernel-profile.md | q4 matmuls 74% @≈10.4 TFLOPS (NAX), SDPA 15%, RoPE+elementwise 11%; compile gain 2.7%; kernel counts NOT MEASURED |
| NAX dispatch | **VERIFIED** (q4 qmm + SDPA, both precisions) | nax-status.md | fp32 REFERENCE uses NAX via MLX's TF32 default; TF32 off → 3.2× slower qmm and a different REFERENCE hash |
| Custom Metal kernels for non-matmul ops | **DEFERRED** (low ceiling) | kernel-profile.md | all non-matmul ops ≤11% of the block, compile already fuses part |
| 4-step probe (Z-Image base + PAI 4-step LoRA vs Turbo 8 / Turbo 4, 1024²) | **REJECTED** (2026-09-29) | 4step-probe/results.md, quality-results.md, benchmark.csv | blind: C lost 6–18 to Turbo 4 and 8–16 to FAST; all losses from a 16-px grain (grid16 5.4 vs 1.1); adherence on par (6–5, 8–5); +6% time and +0.84 GB vs Turbo 4 |
| Turbo bf16 + 4 steps at 1024² (probe control) | **SUPERSEDED by Stage A gate: REJECTED at 1024²** | 4step-probe/results.md §E2 | blind vs FAST: 2 / 3 / 19 ties at 0.50× denoise; contradicts the older unblinded step-sweep label. Needs its own pre-registered gate before any production use |

