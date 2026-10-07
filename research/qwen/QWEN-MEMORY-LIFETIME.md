# Qwen-Image-2.1 edit: memory lifetime (Phase 5, directive §5–§8)

**Verdict: ADOPT P2.** All five pre-registered criteria hold (`memory/PROTOCOL.md` §5, committed in `6d95ada` before any A/B run). The production edit runtime now requests both lifetime patches; the switch is a separate commit that cites this report.

- **Pre-registration:** `research/qwen/memory/PROTOCOL.md`.
- **Chain:** `memory/mem-chain.sh` → `memory/mem-chain.log`. It ran 10:33:37–11:48:41 PST on 2026-10-07 at git `6d95ada`, with heavy apps closed, on AC.
- **Tally (mechanical):** `memory/analyze_mem.py` → `memory/ab-summary.json`.
- **Per-run evidence:** `research/qwen/runs/M5-{512,1024}-*/` (`worker/identity.json`, `monitor.csv`, `conditions.txt`, `console.log`). PNGs are not committed; their identity is the sha256.
- **Worker:** `app/photogen/runtimes/mflux_qwen_edit_worker.py` at `6d95ada`, sha256 `3094e942…`, byte-identical for every run here and for the production preflight.

## 1. What changes
| arm | worker flags | lifecycle |
|---|---|---|
| **P0** (production at Phase 4 close) | `defer_transformer_load` | text encoder resident from load until `before_loop`; VAE resident from load to the end |
| **P2** (candidate, now adopted) | P0 + `release_text_encoder_after_encode` + `release_vae_during_denoise` | text encoder dropped once its output is evaluated (before the reference VAE encode); at `before_loop`, the VAE is swapped for a fresh lazily loaded copy (mflux's own `load_components`, same export and arguments), whose decoder bytes are read again at the first decode tile |

Both patches only change *when* objects are freed. They change no weight, graph, kernel, scheduler or argument. The mflux 0.21.0 source reading behind the design is in `PROTOCOL.md` §2.

## 2. Exact parity and determinism (criteria 1 and 2)
| input | budget | P0 RGB | P2 RGB | P0 RGBA | P2 RGBA |
|---|---|---|---|---|---|
| E05 | 512 | `bd548f1bf8cace9b…` | `bd548f1bf8cace9b…` | `bdc03c3672237ec9…` | `bdc03c3672237ec9…` |
| E08c | 512 | `41ee9205515b4b6c…` | `41ee9205515b4b6c…` | `75fe5d7b1b30b5a5…` | `75fe5d7b1b30b5a5…` |
| E05 (a, b) | 1024 | `792fdaa977a16567…` ×2 | `792fdaa977a16567…` ×2 | `d4a6f9b55a6c26d7…` ×2 | `d4a6f9b55a6c26d7…` ×2 |
| E08c | 1024 | `396ff1007a21ef2a…` | `396ff1007a21ef2a…` | `f6362fe60c06690b…` | `f6362fe60c06690b…` |

- **P0 E05 matches G0** at both budgets (512 `bd548f1b…`, 1024 `792fdaa9…`). The baseline is therefore the worker that produced G0.
- **Determinism:** E05-P0a = E05-P0b, and E05-P2a = E05-P2b.
- **Full hashes:** `ab-summary.json`.
- **Preflight on the Phase 5 code** (real CLI, GPU lock honoured):
  - Z-Image regression 5/5 exact: REFERENCE 1024 `fe47d88d`, FAST 1024 `7b45cfbe`, BALANCED 1024 `befe1b3c`, ULTRA 512 `6aa2b842`, REFERENCE 512 `9ae59f59`;
  - production edit E05 at 512 → `bd548f1b` (`memory/preflight/`).

## 3. Per-stage memory
- **Footprint:** the process's physical footprint from libproc (rusage field 7, the current value), sampled at the stage boundary.
- **Peak:** the lifetime maximum footprint (field 28).
- **MLX:** `mx.get_active_memory()` at the boundary, and the per-phase `mx.get_peak_memory()`.
- All values are in GB.

### 3.1 1024 (E05; the a/b repeats agree to within 0.2 GB, except `before_loop`, which is ±0.8 GB in P2)
| stage | P0 footprint | P2 footprint | P0 MLX active | P2 MLX active |
|---|---|---|---|---|
| startup | 0.27 | 0.27 | — | — |
| after load (VAE + text encoder; DiT deferred) | 6.68 | 6.68 | 6.14 | 6.14 |
| after text + vision encode | 7.78 | **2.22–2.25** | 6.15 | **1.37** |
| after reference VAE encode | 8.59–8.61 | **3.84–3.85** | 6.17 | **1.39** |
| before loop | 2.73 | **0.78–1.54** | 1.39 | **0.04** |
| after denoise step 0 (DiT loaded) | 11.47–11.68 | **10.35–10.46** | 9.85 | **8.50** |
| after loop (DiT dropped) | 4.98–5.16 | **3.85–3.86** | — | — |
| after VAE decode | 2.94–3.03 | 2.79–2.88 | 1.40 | 1.06 |
| end | 2.81–2.86 | 2.52–2.59 | — | — |
| **peak footprint (lifetime max)** | **12.08 / 12.08** | **10.96 / 10.73** | | |

| phase MLX peak | P0 | P2 | Δ |
|---|---|---|---|
| text + vision encode | 7.19 | 7.19 | 0 |
| reference VAE encode | 9.77 | 4.99 | −4.78 |
| denoise (binding at 1024 in both arms) | 11.01 | 9.66 | **−1.35** |
| VAE decode | 6.12 | 5.78 | −0.34 |

E08c at 1024 has the same pattern: peak footprint 12.24 → 10.66 GB; denoise MLX peak 10.96 → 9.61; reference VAE-encode MLX peak 9.72 → 4.94.

### 3.2 512
| | E05 P0 | E05 P2 | E08c P0 | E08c P2 |
|---|---|---|---|---|
| peak footprint | 8.87 | **8.15** | 8.87 | **8.05** |
| text + vision encode MLX peak | 7.39 | 7.39 | 7.41 | 7.41 |
| reference VAE encode MLX peak | 7.85 | 3.07 | 7.88 | 3.10 |
| denoise MLX peak | 7.23 | 5.88 | 7.27 | 5.91 |
| overall MLX peak (binding phase) | 7.85 (VAE encode) | **7.39 (text encode)** | 7.88 (VAE encode) | **7.41 (text encode)** |

### 3.3 Object residency (from the code path, confirmed by the MLX-active deltas above)
| stage | P0 resident | P2 resident |
|---|---|---|
| text + vision encode | VAE (fp32, 1.35) + text encoder (q4) | same; the text encoder is dropped as the encode returns |
| reference VAE encode | VAE + **text encoder** | VAE |
| denoise | **VAE** + DiT (q4, read at step 0) + prefix KV cache/activations | DiT + KV cache/activations (the VAE is a lazy, unread copy) |
| VAE decode | VAE (encoder + decoder) | lazy VAE: only the **decoder** is materialized (MLX active after decode 1.06 ≈ decoder 1.04 GB; the encoder weights are never read again) |

### 3.4 How the saving breaks down
- **At 1024, binding peak: −1.35 GB.** Denoise binds in both arms, so the median peak reduction of **1.35 GB** is the VAE's own size, removed from the denoise phase. Releasing the text encoder lowers only the reference-VAE-encode phase at 1024 (MLX 9.77 → 4.99). That phase is not binding, so it does not move the 1024 peak.
- **At 512, binding phase moves to text + vision encode: −0.7–0.8 GB footprint.** The text-encode phase is untouched by either patch (7.39 GB MLX), and it now caps the 512 peak. This matches the expectation disclosed in `PROTOCOL.md` §5.
- **Remaining headroom.** At 1024 the denoise residue (DiT q4 + KV cache + 1024 activations ≈ 8.5 GB active after step 0, 9.66 GB phase peak) is now the whole binding phase. Lifetime work has nothing left to remove there; further reduction would have to change computation (attention chunking, KV-cache policy) and needs a quality gate, not a parity gate. No such change is proposed in Phase 5 (directive §24–§25).

## 4. Time, swap and pressure (criteria 3–5)
| run | order | wall s | denoise s | decode s | swap growth GB | warn samples | critical | min free % |
|---|---|---|---|---|---|---|---|---|
| 1024 E05 P0a | 1 | 546.9 | 523.7 | 13.81 | 2.809 | 8 | 0 | 28 |
| 1024 E05 P2a | 2 | 576.5 | 555.7 | 10.77 | 0.367 | 5 | 0 | 29 |
| 1024 E05 P2b | 3 | 560.3 | 540.0 | 10.62 | 0.112 | 4 | 0 | 29 |
| 1024 E05 P0b | 4 | 565.5 | 542.6 | 12.77 | 1.257 | 7 | 0 | 31 |
| 1024 E08c P2 | 5 | 549.5 | 529.8 | 9.58 | 0.316 | 3 | 0 | 29 |
| 1024 E08c P0 | 6 | 558.4 | 535.6 | 12.63 | 1.297 | 6 | 0 | 29 |
| 512 E05 P0 | — | 114.9 | 104.9 | 1.57 | 0.234 | 2 | 0 | 27 |
| 512 E05 P2 | — | 100.6 | 93.2 | 1.51 | 0.069 | 1 | 0 | 30 |
| 512 E08c P0 | — | 109.7 | 101.5 | 2.75 | 0.033 | 1 | 0 | 32 |
| 512 E08c P2 | — | 109.4 | 101.6 | 2.41 | 0.000 | 1 | 0 | 37 |

- **Wall at 1024:** median 558.4 s (P0) vs 560.3 s (P2), ratio **1.0033**, within the ≤ 1.03 limit. Denoise is about 96% of the wall in both arms.
- **Decode at 1024:** P2 − P0 = −3.04, −2.15, −3.05 s. The lazy decoder re-read was expected to cost up to +3 s; the paired P2 decode was instead *faster* in every pair. The cause is not isolated, and no speed claim is made.
- **No speedup is claimed at 512 either.** The E05 gap (114.9 → 100.6 s) does not repeat on E08c (109.7 → 109.4 s).
- **Swap growth at 1024:** median 1.297 GB (P0) vs 0.316 GB (P2).
  - P0a's 2.81 GB is the first run after the cooldown, an order effect.
  - The ABBA design still shows P0 above P2 in every position: P0b, run 4, grew 1.26 GB against 0.37 and 0.11 for the P2 runs that preceded it.
- **No critical-pressure sample and no abort** in any run.
- **Disclosed observation (a timing context, not part of the criteria).** The harness runs are slower than the production preflight of the same edit:
  - E05 512 P0 denoise was 104.9 s (median step 2.54 s), against 79.0 s (median step 1.86 s) in the preflight `bin/photo-gen edit` that ran 2 minutes earlier with the same worker, flags and pixels.
  - Possible causes: the fanless machine's thermal state after the Z-Image preflight, and the 1 Hz monitor. They are not separated here.
  - The A/B criteria compare paired, interleaved runs, so they are unaffected. Absolute timings from monitored chains, G2 included, should be read as "sustained, monitored".

## 5. Verdict against `PROTOCOL.md` §5
| # | criterion | result | pass |
|---|---|---|---|
| 1 | exact RGB + RGBA parity P2 = P0, all 5 pairs; P0 E05 = G0 at 512 and 1024 | 5/5 pairs exact; G0 match at both budgets | ✅ |
| 2 | determinism at 1024 (P0a = P0b, P2a = P2b) | both exact | ✅ |
| 3 | median 1024 peak reduction ≥ 0.75 GB, and median swap growth not higher | 1.35 GB (1.12 / 1.35 / 1.57); swap 0.316 vs 1.297 | ✅ |
| 4 | median 1024 wall P2 ≤ 1.03 × P0, and decode delta ≤ +3 s | ratio 1.0033; decode delta −3.05 to −2.15 s | ✅ |
| 5 | no P2 abort or critical sample | none | ✅ |

**ADOPT.** The diagnostic arms P1/PV were not run; the protocol runs them only if P2 fails parity.

## 6. Adoption (separate commit after this report)
- **Runtime constants:** in `app/photogen/runtimes/mflux_qwen_edit.py`, `RELEASE_TEXT_ENCODER_AFTER_ENCODE` and `RELEASE_VAE_DURING_DENOISE` become `True`, next to `DEFER_TRANSFORMER_LOAD`, and are sent in the worker request.
- **Recorded policy:** the sidecar's `execution.memory_policy` becomes the policy the **worker reports it applied**, not the requested flags. It includes `text_encoder_released_after_encode` and `vae_reloaded_lazily`, so a patch that silently failed to install would show in the record.
- **Worker:** unchanged (still `3094e942…`). The configuration identity is unchanged by design, because the memory policy is pixel-neutral by this gate and lives under `execution`.
- **Production-path parity after the switch:** the same E05 512 seed-42 edit through `bin/photo-gen edit` must reproduce `bd548f1b…` / `bdc03c36…` and the preflight's `configuration_id` / `edit_id`. Result: see §7.
- **Memory policy stays model-specific (directive §8).** Z-Image keeps its own `_install_transformer_release` and is untouched. The Qwen flags live only in the Qwen runtime.

## 7. Production-path confirmation (after the adoption commit)
The adoption is commit `973ef7f`. The same edit then ran through the real CLI, `bin/photo-gen edit` (GPU lock honoured), at that commit. Evidence: `memory/postadopt/` (CLI JSON, log, copy of the sidecar, conditions).

| | preflight (P0, `6d95ada`) | after adoption (P2, `973ef7f`) |
|---|---|---|
| RGB `pixel_sha256` | `bd548f1bf8cace9b…` | `bd548f1bf8cace9b…` ✅ |
| RGBA sha256 | `bdc03c3672237ec9…` | `bdc03c3672237ec9…` ✅ |
| `configuration_id` | `3cd79615e8a685fc…` | `3cd79615e8a685fc…` ✅ |
| `edit_id` | `584040d912f19396…` | `584040d912f19396…` ✅ |
| worker sha256 | `3094e942…` | `3094e942…` |
| `execution.memory_policy` (worker-reported) | `defer_transformer_load` only | all three requested; `text_encoder_released_after_encode` and `vae_reloaded_lazily` true |
| peak footprint | 8.906 GB | **8.167 GB** |
| MLX peak (phase) | 7.851 (VAE encode) | 7.385 (text encode) |
| reference-VAE-encode MLX peak | 7.851 | 3.071 |
| denoise MLX peak | 7.232 | 5.881 |
| wall (generation_seconds) | 86.4 s | 79.7 s (single runs; no speed claim) |

The production path reproduces the A/B exactly: same pixels, same identity ids, the patches applied, and the same per-phase MLX peaks as `M5-512-E05-P2`.
