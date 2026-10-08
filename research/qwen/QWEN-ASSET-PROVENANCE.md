# Qwen-Image-2.1 assets: provenance, verification and storage disposition (Phase 5 §9 + addendum)

These are three separate artifacts. The **source checkpoint** is the upstream model. The **runtime export** is the q4 pack the edit backend executes. The **duplicate export** was a byte-identical second copy of the export, left by incident 1. Do not conflate them.

Full verification record: `research/qwen/assets/qwen-assets-verification.json`, written by `research/qwen/assets/verify_assets.py` on 2026-10-07 at about 09:55. That run read every byte with no inode/mtime cache: it computed sha256 and git-blob-sha1 for every file, plus size, inode and link count, and it listed symlinks. The tool is read-only.

## 1. Source checkpoint (upstream original)
| | |
|---|---|
| path | `models/research/qwen-image-2.1` (gitignored) |
| upstream | `Qwen/Qwen-Image-2.1` on Hugging Face, revision **`d26bb61231c349cf6b7896fa83353113880e1ba3`** (lastModified 2026-09-30T02:14:09Z) |
| licence | `other` / `qwen-research`: **Qwen Research License, non-commercial** (research or evaluation only). Accepted by the user for research use on 2026-10-06. Never committed or redistributed. |
| files | **28** upstream files, all matching `research/qwen/upstream-file-manifest.json`: LFS files by sha256, small files by git-blob-sha1 (`source_vs_upstream`: 28 checked, 0 mismatched, 0 missing) |
| extra local files | 59 Hugging Face download-cache metadata files under `.cache/huggingface/` (locks, `.metadata`, the revision tree JSON). They aren't model content. |
| size | 33,134,957,942 bytes (**33.13 GB = 30.9 GiB**). The ledger's "31 GiB" and the directive's "33 GB" are the same quantity in different units. |
| full sha256 for every file | `source_checkpoint.files` in the verification JSON. This also adds sha256 for the small files that upstream identifies only by git-sha1. |
| upstream still serves this revision | yes. On 2026-10-07 `GET https://huggingface.co/api/models/Qwen/Qwen-Image-2.1/revision/d26bb61…` returned sha `d26bb61…`, 28 siblings, not gated. |

**File-count reconciliation.** `research/qwen/download-verification.json` says "30/30". That count covers two repositories: the 28 files of `Qwen/Qwen-Image-2.1` plus the 2 sd.cpp comparator GGUFs from `Qwen/Qwen3-VL-8B-Instruct-GGUF` @ `f982a07` (in `models/text_encoders/`). There is no discrepancy.

## 2. Canonical runtime export (what the edit backend executes)
| | |
|---|---|
| path | `models/qwen/qwen-image-2.1-edit-mflux-q4` (gitignored) |
| identity | 18 files, **all 18 sha256 + sizes equal the pins** in `config/backend-qwen21-edit-mflux.json` (`canonical_vs_manifest`: 0 mismatched, 0 missing, 0 unpinned files present). Manifest file sha256 `536fba17e382b799…`. |
| size | 10,638,923,400 bytes (10.64 GB = 9.9 GiB) |
| how it was made | `research/qwen/export_q4.py` via `export-q4.sh`, in `mflux-qwen/.venv`. API: `mflux.models.qwen21.variants.edit.qwen_image_21_edit.QwenImage21Edit(quantize=4, model_path=<source>).save_model(<dst>)`. |
| export configuration | `quantize=4`: MLX affine, group size 64 (mflux default), applied to the transformer and the Qwen3-VL text/vision encoder including `lm_head`; VAE fp32 (unquantized). The processor/tokenizer, `model_index.json` and the scheduler config are copied by `save_model`. |
| export software | mflux 0.21.0 (wheel sha256 `b2e38fd3…`), MLX/mlx-metal 0.32.2, transformers 5.15.0, torch 2.13.0, CPython 3.12.14 (lock `config/qwen-python-requirements.lock.txt`) |
| export record | `research/qwen/export/run2/` (console, monitor, `run2.export.json`; it is byte-identical to `models/qwen/qwen-image-2.1-edit-mflux-q4.export.json`) |
| reproducibility | Two independent exports (00:04 and 00:11 on 2026-10-07) are byte-identical in all 18 files (§3). Re-running the same export from the same source revision with the same locked venv reproduces this pack. |

## 3. Duplicate export (incident 1) and its deletion
| check (addendum §1) | result |
|---|---|
| path | `models/qwen/ABORTED-20261007T0005-qwen-image-2.1-edit-mflux-q4` |
| complete file list vs canonical | identical path set (18 files; none only in one side) |
| per-file sha256 and size | **all 18 identical** (`byte_identical: true`) |
| shared storage (hardlinks, shared inodes, symlinks) | none: 0 shared inodes, 0 files with link count > 1, 0 symlinks on either side. The canonical copy doesn't depend on the duplicate's blocks. |
| referenced by any script, config or run result | no. `grep -rl ABORTED-20261007` over `app/ config/ bin/ research/ docs/` and the root `*.md` files finds only narrative text (`INCIDENTS.md`, `PHASE4-INDEX.md`, `MEMORY.md`) plus this verification. No harness, chain, run result or manifest uses the path. |
| export record preserved | its `.export.json` is byte-identical to the committed `research/qwen/export/run1-aborted/aborted-run.export.json`; console, monitor and time logs are committed there too. The 523-byte file under `models/qwen/` is kept. |

**Disposition: DELETED** (the weight directory only), per the directive's §9 and the addendum's §2. The order was: commit this record, then delete, then `bin/photo-gen verify --edit --full`, then `df`. The outcome is recorded in §5.

## 4. Source checkpoint disposition
- **Through G2: RETAIN LOCALLY, unchanged** (addendum §3). It isn't modified, re-quantized or moved.
- After G2: classify it as RETAIN LOCALLY, ARCHIVE or DELETE (addendum §4). That decision is recorded in §6 below once G2 is complete.

**What deletion would lose (research/reproducibility view):**
- **Local re-export.** A different quantization (q8, mixed precision, a different group size), a re-export after an mflux upgrade, or an independent check of the q4 pack against the dense weights would all need a 33 GB re-download first.
- **Dense-weight research.** Block-sensitivity, quantization-error maps, distillation teacher weights and kernel experiments all need the dense bf16 weights. Phase 3 needed the equivalent for Z-Image.
- **Insurance against upstream change.** The revision is pinned and was still served on 2026-10-07, but the repository is a third party's. A force-push, a takedown or a licence change could make `d26bb61` unobtainable. The local copy is the only artifact whose bytes are verified against the recorded manifest.

**What would remain if it were deleted:** enough metadata to identify and re-acquire it exactly. That is the repo, the revision, the 28-file manifest with digests (`upstream-file-manifest.json`), full sha256 for every file (verification JSON), the licence identity, the export script, configuration and software lock, and the canonical export's 18 pins.

## 5. Deletion log
- **2026-10-07 10:20 PST.** After commit `0d15f49` (this record plus the verification), I ran `rm -r` on `models/qwen/ABORTED-20261007T0005-qwen-image-2.1-edit-mflux-q4` after checking that it was a real directory and not a symlink. Only that directory was removed. The canonical export, both `.export.json` files and the source checkpoint were not touched.
- **Afterwards, `bin/photo-gen verify --edit --full`:** `ok: true`, 18/18 files re-hashed in full (`hashed_now` 18), 0 failed (`research/qwen/assets/verify-edit-full-after-delete.json`).
- **Disk:** free space went from 186,092,972 KiB to 196,517,288 KiB, so **+10.67 GB freed** (the directory held 10.64 GB of file bytes; the rest is filesystem block overhead). Free space is now 201.2 GB (`df-before.txt`, `df-after.txt`).

## 6. Post-G2 decision on the source checkpoint
Recorded 2026-10-07 and committed at 17:23:40 PST in `0ccc0b7`, after G2 completed and was tallied (scores frozen 17:13). *Correction (2026-10-08):* this line previously said "decided at about 17:45 PST"; the commit time is the evidence. Outcome: **REJECTED at 512 and 1024**; `research/editing/real-world/results.md`.

**Re-verification after G2.**
- `verify_assets.py` was re-run at 16:50, after the last G2 edit, to a new file: `assets/qwen-assets-verification-post-g2.json`, log `verify-assets-post-g2.log`. It is a full read with no cache, and took 31 s.
- **Source checkpoint:** all 87 files (28 upstream plus 59 HF cache metadata) have the **same sha256, size and inode** as in the pre-G2 record. The 28 upstream files still match `upstream-file-manifest.json` (0 mismatched, 0 missing). Nothing modified, moved or re-quantized it.
- **Canonical export:** 18/18 files equal the manifest pins, with the same sha256 and inodes as before G2.
- **Duplicate path:** absent (0 files). The JSON's `duplicate byte_identical: false` reflects only that absence, since the path sets differ, and is not a finding about any content.

**Report (addendum §5)**
| item | value |
|---|---|
| canonical Qwen source path | `models/research/qwen-image-2.1` (`Qwen/Qwen-Image-2.1` @ `d26bb61231c349cf6b7896fa83353113880e1ba3`; 28 upstream files, 33,134,957,942 bytes) |
| canonical q4 export path | `models/qwen/qwen-image-2.1-edit-mflux-q4` (18 files, 10,638,923,400 bytes; pinned in `config/backend-qwen21-edit-mflux.json`) |
| redundant copy deleted | **yes**: `models/qwen/ABORTED-20261007T0005-qwen-image-2.1-edit-mflux-q4`, 2026-10-07 10:20 PST, after the byte-identity check in §3; +10.67 GB freed (§5) |
| 33 GB source | **RETAIN LOCALLY** (for now, with the reclassification trigger below) |
| disk impact of this decision | **0 GB.** Retaining frees nothing. Free space at 16:50 was 193,512,168 KiB = **198.2 GB** (58% of the volume used). Deleting would free about 33.1 GB. |

**Rationale.**
1. **G2 leaves exactly one open question, and only the source checkpoint can answer it locally.**
   - G2 rejected the q4 configuration mainly because incidental text is garbled (failure mode 1 in `results.md` §3). The cause is not isolated.
   - **Candidates:** the q4 quantization of the DiT or of the Qwen3-VL text/vision encoder; the fp32 VAE encode/decode round trip; the output-resolution budget (1024 garbles less than 512).
   - Of these, only the first needs the dense weights: a q8 or mixed-precision export from `d26bb61`, re-run on the G2 text items. Whether such an export fits in 16 GB has not been evaluated.
   - Without the local checkpoint, that diagnostic starts with a 33 GB download.
   - This is a reason to keep the option open, **not** a claim that quantization is the cause.
2. **There is no clear reason to delete,** which the addendum requires for DELETE. The volume has 198 GB free and nothing in the project is short of space.
3. **ARCHIVE needs storage the project doesn't have.** No external or cold storage is configured, and moving 33 GB off the machine needs the user's hardware.
4. **Dense weights are the input to the next research layer** (directive §30: model modification, specialization). For Qwen that layer is now conditional on the user deciding the backend is still worth pursuing after a REJECTED gate, so this point carries less weight than 1 and 2.

**Reclassification trigger.**
- **Reclassify as DELETE** if the user decides to pursue no further Qwen work, i.e. neither the export diagnostic in 1 nor removal/replacement research that would need the dense weights.
- DELETE is then justified: the model can be reacquired exactly. Upstream still served `d26bb61` (28 siblings, not gated) on 2026-10-07, every file's digest is pinned in `upstream-file-manifest.json`, and full sha256 values are in both verification JSONs.
- Before deleting: re-run `verify_assets.py`, then check `df` before and after, then log the deletion here, as in §5.
- **ARCHIVE instead** if cold storage becomes available and the user wants to avoid a re-download.

**What deleting the source would lose** (§4 already covers the general case):
- The ability to run the export diagnostic in 1 without a 33 GB re-download, and under the risk that upstream changes or withdraws `d26bb61`.
- Independent re-verification of the q4 pack against the dense weights.
- Any dense-weight research on Qwen (quantization-error maps, block sensitivity, distillation teacher).
- The only local copy whose bytes have been checked against the recorded manifest.

What would remain is enough to identify and reacquire it exactly (§4): the repository, the revision, the 28-file manifest and digests, full sha256 for every file, the licence identity, and the export script, configuration, software lock and 18 pins.
