# Q-Q diagnostic (Phase 6): does higher weight precision reduce incidental-text garbling?

**Conclusion.** Higher precision did not materially reduce incidental-text corruption in the tested cases. This experiment does not support q4 quantization as the primary cause.
- **Pre-registered class: AGAINST** (`research/qwen/qq/PROTOCOL.md` §8), applied mechanically to the frozen arm-blind sheets.
- **What did not move:**
  - q8 rescued 1 of 19 text elements that q4 garbled;
  - G2-style text FAIL was 6/6 in both arms;
  - every other dimension was identical between the arms on every core pair.
- **The one directional signal:** q8 never made an element worse, and the blind paired preference chose q8 on 5 of 8 sheets and q4 on none. So precision may help slightly at the glyph level, but it is not what makes the text fail.
- **Cost:** q8 materially increased memory and time on this machine. At 1024: 810 s against 570 s per edit, 13.8 GB against 10.9 GB peak, and +3.1 GB against +0.55 GB swap.
- **G2 is untouched:** its verdict (REJECTED at 512 and 1024) and its frozen scores stand. Qwen's status does not change, and no precision becomes a default.

| | |
|---|---|
| question | Is G2's failure mode (a), garbled incidental text, caused by the q4 quantization of the DiT and/or the Qwen3-VL encoder? Only candidate 1 of the four in `QWEN-ASSET-PROVENANCE.md` §6 was tested. |
| design | **The only change is the weight representation:** q4 (canonical export) against q8 (a research export from the same source). Fixed: the staged G2 inputs, instructions, seeds and budgets; mflux 0.21.0 / MLX 0.32.2; the production worker `3094e942…` with policy P2; 40 steps, guidance 1.0, prefix KV cache; the same VAE (gate V). Both arms ran in one interleaved chain. |
| items | **Core:** R02, R12 and R15 at their G2 primary seeds, at 512 and 1024. These are the six text FAILs that by themselves establish the G2 rejection. **Supplementary:** R12's second seed at both budgets. **Determinism:** q8 R12 repeats. 18 runs in total. |
| review | Arm-blind and paired: each sheet shows the original, result A and result B, with sides randomized and the key sealed. A fresh subagent rated per-element text categories with G2's rubric. Frozen before unblinding. |
| timeline | Pre-registered `fea3872` (08:40) → export `135decd` → smoke and frozen chain `924bc96` → chain 08:51:44–11:04:18 → sheets `f73c16c` → frozen `77f8a35` (11:32) → unblinded `f1f353e`. All times are local, Asia/Manila (UTC+8; `date` prints "PST"). |

## 1. The q8 export
**Source:** `models/research/qwen-image-2.1`, `Qwen/Qwen-Image-2.1` @ `d26bb61`.
- Re-verified before and after the export: all 87 files have the same sha256, size and inode, and 28/28 match the upstream manifest.
- Records: `assets/qwen-assets-verification-phase6-pre-qq.json` and `-post-export.json`.

**Tool and method:** mflux 0.21.0's own export path, `QwenImage21Edit(quantize=8, model_path=src).save_model`, run per component (`qq/export_q8_split.py`).
- A single-pass q8 export would hold about 18.4 GB at once.
- mflux refuses mixed bit widths across components, so the DiT and the text encoder are both 8-bit. Their effects cannot be separated here.

| | q4 (canonical) | q8 (research) |
|---|---|---|
| path | `models/qwen/qwen-image-2.1-edit-mflux-q4` | `models/research/qwen-image-2.1-edit-mflux-q8` (**deleted after this report**, §6) |
| quantization | MLX affine 4-bit, group 64, DiT + Qwen3-VL text/vision encoder incl. `lm_head`; VAE fp32 | MLX affine **8-bit**, group 64, same layers; VAE fp32 |
| files / bytes | 18 / 10,638,923,400 | 22 / 18,460,980,668: DiT 7,655,323,166; text encoder 9,443,220,789; VAE 1,351,006,915 |
| identity | pinned in `config/backend-qwen21-edit-mflux.json` | every file's sha256 in `qq/export/merge-q8.json` (sha256 `f7db6d08…`); every shard `quantization_level: 8`, `mflux_version: 0.21.0` |
| relative RMS weight error vs dense bf16 (median over sampled layers) | DiT 0.095, text encoder 0.093 | DiT 0.0075, text encoder 0.0074 (**about 12.7× smaller**; 29 and 43 layers; `qq/export/qerr-*.json`) |

**Gates and checks (all passed):**
- **E (procedure):** the per-component loader at `quantize=4` reproduces **every** tensor of the canonical q4 export, compared in memory with no q4 file written: vae 238/238, transformer 753/753, text_encoder 1440/1440.
- **V (same VAE):** the q8 VAE tensors are byte-identical to q4's (238/238). The processor, scheduler, `model_index` and the three configs are byte-identical too.
- **Export determinism:** two q8 vae+transformer exports, attempt 1 (amendment 1) and attempt 2, are identical in all 9 files.
- **Export cost:** peak footprint 10.82 GB (vae+transformer) and 11.23 GB (text encoder); no watchdog abort; about 2 minutes in total.

## 2. Runs and mechanical gates
- **Chain:** 18/18 runs finished with rc 0, no watchdog abort and 0 critical-pressure samples. Every run reported the full P2 policy applied.
- **Gate Q:** all 8 q4 runs are **bit-identical to their G2 runs** (RGB `pixel_sha256` and RGBA sha256). The diagnostic harness therefore reproduces G2's configuration exactly.
- **Gate D:** the q8 R12 repeats equal their originals at 512 and 1024. q8 is deterministic too.
- **The arms really differ:** q4 and q8 pixels differ in all 8 pairs, so q8 was not a no-op.

## 3. Results (frozen arm-blind scores, unblinded; `qq/qq-summary.json`)
**Text elements.** Categories: PRESERVED / DEGRADED / GARBLED / REMOVED / NA (not readable in the original panel); "legible" = PRESERVED or DEGRADED. The elements were defined from the sources before any q8 output existed.
- R02: t1 street-name sign; t2 plate under the no-entry sign.
- R12: t1 banner; t2 "Quarry Quarter" hanging sign; t3 small green sign; t4 left fascia and "Q" sign; t5 right-edge signs.
- R15: t1 shop sign; t2 window banner; t3 door number decal; t4 door poster; t5 red sticker.

| pair (sheet) | t1 | t2 | t3 | t4 | t5 | text, q4 / q8 | blind text preference |
|---|---|---|---|---|---|---|---|
| R02 512 (P07) | G → G | G → G | | | | FAIL / FAIL | SAME |
| R02 1024 (P08) | G → G | G → G | | | | FAIL / FAIL | SAME |
| R12 512 (P05) | G → G | G → G | G → G | G → G | G → G | FAIL / FAIL | q8 |
| R12 1024 (P03) | G → G | D → D | G → G | G → G | G → G | FAIL / FAIL | SAME |
| R15 512 (P01) | **G → D** | G → G | G → G | G → G | NA | FAIL / FAIL | q8 |
| R15 1024 (P02) | P → P | P → P | D → D | G → G | G → G | FAIL / FAIL | q8 |
| *supp.* R12 s2 512 (P06) | G → G | G → G | G → G | G → G | G → G | FAIL / FAIL | q8 |
| *supp.* R12 s2 1024 (P04) | G → G | D → **P** | G → G | G → G | G → G | FAIL / FAIL | q8 |

(P = PRESERVED, D = DEGRADED, G = GARBLED; each cell is q4 → q8.)

**Classification counts (core, N = 6):**

| measure | value | STRONG needs | AGAINST needs |
|---|---|---|---|
| assessable units | 23 | | |
| G4: q4 not legible | 19 | | |
| R: rescued by q8 | **1** (R15-512 t1, the small word on the shop sign) | ≥ 3 and ≥ G4/2 | **≤ 1 ✅** |
| W: worsened by q8 | 0 | ≤ 1 | |
| rescues across tasks / budgets | R15 only / 512 only | ≥ 2 tasks, every budget | |
| q8 text FAIL (G2 dimension) | **6/6** (q4: 6/6) | | **≥ 5 ✅** |
| blind preference q8 / q4 / SAME | 3 / 0 / 3 | q8 ≥ 4, q4 ≤ 1 | |
| **class** | **AGAINST** | | |

- **Supplementary pairs (R12 second seed):**
  - 10 assessable units, 9 not legible under q4; 0 rescued, 0 worsened;
  - one legible element improved (t2 at 1024, DEGRADED → PRESERVED);
  - the preference chose q8 on both sheets.
- **Other dimensions, core pairs, identical between arms:**
  - adherence PASS 6/6;
  - preservation FAIL 6/6 (the text mapping alone forces it);
  - composition PASS 6/6;
  - quality: the same 2 MINOR and 4 PASS.

  Nothing regresses under q8, and nothing changes a G2 outcome.
- **Inter-rater (descriptive):** the q4 outputs are the G2 pixels. On all 8, this rater's text FAIL and preservation FAIL equal the frozen G2 rater's.
- **Budget, an observation and not a tested variable:** in both arms more text survives at 1024 (4 of 12 core elements legible under q4) than at 512 (0 of 11). That is consistent with G2's "1024 garbles less than 512".

**Robustness (descriptive; the frozen scores are not re-scored).**
- The AGAINST class rests on R ≤ 1. One more rescued unit (R = 2) would make the class INCONCLUSIVE.
- **A candidate exists:** after the freeze I looked at a few crops, unblinded and knowing the hypothesis. On R15 at 512, element t2 (the window banner), q8's first line reads like the source ("…in our new webstor…") where q4's is garbled, while the second line is degraded in both. The rater scored that element GARBLED in both arms, and that score stands. A post-freeze, unblinded look cannot count.
- **The same look confirmed the rater elsewhere:** R12's banner at 1024 and R15's door poster and sticker at 1024 are garbled in the same way in both arms.
- **The conclusion holds under either class.** Text FAIL is 6/6 and preservation FAIL is 6/6 in both arms. Even with two rescued units, no G2 outcome on any tested item would change. Meanwhile memory and time rose materially (§4). That is the directive's "evidence against" case: "q4 is not supported as the primary explanation".

## 4. Memory and time (same chain, sustained, monitored, interleaved; descriptive)
| budget / arm | n | wall s (median [range]) | denoise s | step s | text encode s | peak footprint GB | denoise MLX peak GB | swap growth GB | warn samples | critical |
|---|---:|---|---:|---:|---:|---|---:|---|---|---:|
| 512 q4 | 4 | 103.6 [84.0–108.5] | 95.7 | 2.30 | 1.1 | 8.16 [8.16–8.19] | 5.86 | 0.00 | 0% | 0 |
| 512 q8 | 5 | **133.5** [126.7–137.7] | 115.2 | 2.92 | 11.0 [9.9–19.7] | **12.03** [11.93–12.06] | 9.34 | **1.86** [1.74–2.64] | 9% [5–17%] | 0 |
| 1024 q4 | 4 | 569.7 [559.7–585.5] | 550.3 | 13.77 | 4.3 | 10.87 [10.87–10.88] | 9.73 | 0.55 [0.42–0.76] | 2% | 0 |
| 1024 q8 | 5 | **809.7** [766.4–863.8] | 772.4 | 17.95 | 20.2 | **13.76** [13.69–13.83] | **13.19** | **3.08** [2.57–3.65] | **76%** [54–79%] | 0 |

- **Peaks:**
  - At 512 the q8 peak is the text-encode phase (MLX 11.37 GB). The q8 text encoder alone is about 9.4 GB.
  - At 1024 it is denoise, at 13.19 GB MLX: the 7.66 GB q8 DiT plus activations and the KV cache. That is about 3.5 GB above q4.
- **At 1024, q8 pages throughout:** warn-level pressure in about three quarters of the samples, and 18–20 s steps against about 14 s for q4.
- **By G2's memory/UX definitions** (`real-world/protocol.md` §8; descriptive, not a gate), q8 would be **MARGINAL at both budgets**. At 512 it fails COMFORTABLE and USABLE on swap; at 1024 its maximum swap of 3.65 GB sits just under MARGINAL's 4 GB limit. q4 at 512 stays COMFORTABLE.
- **No speed claim.** These are same-chain medians.

## 5. Limitations
- **Small study:** 3 tasks, 6 core pairs, one seed per pair plus one supplementary seed, and one rater.
- **Not separated:**
  - DiT and text-encoder precision were raised together;
  - q8 is not dense bf16. Its weight error is about 12.7× smaller than q4's but not zero. A further gain from q8 to bf16 is not excluded. A bf16 run would need about 33 GB of weights and does not fit this machine's working set.
- **Harness:** the production worker was run directly, not `bin/photo-gen edit`, because the production runtime correctly refuses a non-manifest model. Gate Q shows the harness reproduces G2's q4 configuration exactly.
- **Rater, instructions and timing:**
  - The rater's harness may load `CLAUDE.md`, which describes G2's text failure. That primes both arms equally.
  - The MUST NOT CHANGE lists, taken unchanged from G2's task manifest, quote some sign wording, for both arms. The text-element descriptions give locations only.
  - At 512 small text is near the limit of what both the output and the resized original panel can show; one element was NA.
  - The rater moved four sheets' quality scores (P03–P06) from MINOR to PASS for both arms, so that quality judges non-text artifacts only (`review/RATER-REPORT.md`). Quality is not part of the classification.
- **Disclosed tooling changes after the pre-registration commit `fea3872`:**
  - amendment 1 (the export directory bug);
  - `make_pairs.py` and `smoke.sh` were added before any q8 output on a G2 item existed;
  - `rater_audit.py` was extended after the rater finished, to record shell-redirect writes. It is an audit tool, not scoring.

**Rater audit (`review/RATER-AUDIT.json`):**
- 242 reads: 12 blind files and 230 crops;
- writes: only the two draft sheets, by shell redirection;
- no path outside the blind and crop directories;
- no access to the key or run records.

## 6. Storage disposition (directive §10; `PROTOCOL.md` §10)
- **Dense source checkpoint:** RETAIN LOCALLY, unchanged (re-verified twice in Phase 6).
- **Canonical q4 export:** kept; the backend depends on it.
- **The deleted duplicate:** not recreated. Gate E compared tensors in memory only.
- **q8 export: DELETED** after this report was committed. No follow-up experiment named here needs it: the recommended next test (§7) uses only the VAE, which is identical in the q4 export.
  - It can be recreated exactly in about 2 minutes from the retained source, with the committed tool. Gate E and the attempt-1/attempt-2 identity show the procedure is exact.
  - Its identity (every file's sha256) is in `qq/export/merge-q8.json`.
  - The deletion is logged in `QWEN-ASSET-PROVENANCE.md` §7.
- **Run outputs:** all `QQ-*` / `QQSMOKE-*` outputs are kept (gitignored PNGs; hashes in the run records).

## 7. What this means, and the next question (not run here)
- **Status lines unchanged:**
  - integration: validated;
  - capability: validated (G0 CAPABLE);
  - quality: G2 REJECTED;
  - local production: REJECTED (research opt-in only);
  - commercial use: not permitted (Qwen Research License).
- **Of the remaining G2 candidates, the cheapest discriminator is a VAE round-trip ceiling test.** It would encode and decode each staged source at the 512 and 1024 output sizes, with no DiT and no text encoder, and score the same text elements.
  - **If the VAE alone garbles the text,** the VAE or the budget sets the ceiling, and no DiT precision can fix it.
  - **If it reconstructs the text legibly,** the DiT's re-synthesis of unedited regions is responsible.
  - It needs only the q4 export's VAE, and takes seconds per image.
  - The budget effect seen in both arms here (more text legible at 1024) makes this test the natural next step.
- **Q-A** (an alternative editing model that preserves incidental text and fits 16 GB) remains the fallback.
- Neither is started in Phase 6.
