# Reproducing the validated build

Goal: rebuild the exact known-good photo-gen environment on the validated machine (see [HARDWARE.md](HARDWARE.md)) and prove it by reproducing the reference pixel hashes.

**Scope, stated plainly:**
- These steps were derived from the project's own records ([`research/mflux-versions.md`](../research/mflux-versions.md), the backend manifest) and from the environment that produced every result in this repository.
- A full from-scratch rebuild on a clean machine has **not** been performed. The repository was verified by a clean `git clone` + test run on the original machine (see the commit's verification notes in `MEMORY.md`).
- On other hardware these steps may run, but the result is **unvalidated** (and pixel hashes may differ).

## 0. What is and isn't in Git
| in Git | not in Git (and why) | how to get it back |
|---|---|---|
| `app/`, `bin/`, `config/`, `docs/`, `research/` text evidence, `CLAUDE.md`, `MEMORY.md` | — | `git clone` |
| — | `mflux/.venv/`, `mflux/python/`, `mflux/tools/`, `mflux/cache/` (toolchain, ~2.3 GB) | §2 |
| — | `models/mflux/z-image-turbo-mflux-q4/` (5.9 GB of weights) | §3 |
| — | `data/` (jobs DB, outputs, logs) | created automatically by the app |
| — | research PNGs (~770 MB) | file hashes in [`research/EXCLUDED-IMAGES.sha256`](../research/EXCLUDED-IMAGES.sha256); mflux ones regenerate bit-exact from their recorded prompt/seed/config |
| — | `mflux-qwen/`, `models/research/qwen-image-2.1/`, `models/qwen/` (optional image-edit backend, Phase 4) | §5 |
| — | `models/diffusion_models`, `models/text_encoders`, `models/vae`, `sdcpp/`, `outputs/` (Pass-1 sd.cpp/Qwen comparison and the Phase 4 sd.cpp comparator; not used by photo-gen) | pins in [`research/model-pins.txt`](../research/model-pins.txt), [`research/z-image-model-pins.txt`](../research/z-image-model-pins.txt) |

## 1. Machine and location
- MacBook Air M5, 16 GB, macOS 27.0 (26A428), on AC power.
- **Clone to `~/Dev/photo-gen`.** The application itself is path-independent: `bin/photo-gen` derives `PHOTOGEN_ROOT` from its own location. But the toolchain file `mflux/env.sh` and the research harnesses (`research/*.sh`, `research/experiments/*.py` / `*.sh`) hard-code `~/Dev/photo-gen`, as they did when the evidence was produced. They are left unchanged on purpose, so they match the recorded runs.

```sh
mkdir -p ~/Dev && git clone git@github.com:nckandrw/photo-gen.git ~/Dev/photo-gen
cd ~/Dev/photo-gen && git checkout photo-gen-m5-16gb-v2     # latest validated tag (v1 = earlier state)
```

## 2. Toolchain (project-local; nothing installed globally, no sudo)
Recorded pins (`research/mflux-versions.md`):
- **uv 0.12.18**, asset `uv-aarch64-apple-darwin.tar.gz`, sha256 `cf40e0c6a202190ccd9e0406dcfdd5b2d6668a9a5c779b17948963df32aafe5b`, placed at `mflux/tools/uv`.
- **CPython 3.12.14** (python-build-standalone `cpython-3.12.14-macos-aarch64-none`), installed by uv into `mflux/python/`.
- Packages from PyPI, **wheels only**. The exact 56-package set is [`config/python-requirements.lock.txt`](../config/python-requirements.lock.txt).
  - Key pins: mflux 0.20.0, mlx 0.32.2, mlx-metal 0.32.2, pillow 12.3.0, numpy 2.5.3.
  - mflux 0.20.0 wheel sha256 `5d60a278d67289be0da2e4ba0e8dcf938dd3c676a01c9064f64e3fb10e30767d`.

```sh
cd ~/Dev/photo-gen
mkdir -p mflux/tools mflux/dl
# download uv 0.12.18 for aarch64-apple-darwin into mflux/dl/, then verify:
shasum -a 256 mflux/dl/uv-aarch64-apple-darwin.tar.gz      # must equal cf40e0c6…fe5b
tar -xzf mflux/dl/uv-aarch64-apple-darwin.tar.gz -C mflux/tools --strip-components 1
source mflux/env.sh                                          # keeps uv/python/HF caches inside mflux/
uv python install 3.12.14
uv venv --python 3.12.14 mflux/.venv
uv pip install --python mflux/.venv/bin/python3.12 --only-binary :all: -r config/python-requirements.lock.txt
```

> `mflux/requirements.lock.txt` is the original lock captured on 2026-09-24. It contains terminal colour codes, so use `config/python-requirements.lock.txt`: same 56 packages and versions (verified identical 2026-09-25), clean format.

## 3. Model (5.9 GB, external, Apache-2.0)
`mflux-community/z-image-turbo-mflux-q4` @ **`d2d30500c4bc0d19770bd952951df3e7c635ae9e`**. Expected location: `models/mflux/z-image-turbo-mflux-q4/`. It is based on Tongyi-MAI Z-Image-Turbo (Apache-2.0) and pre-quantized by mflux-community (MLX affine 4-bit, group 64).

| file | algo | digest | bytes |
|---|---|---|---:|
| text_encoder/0.safetensors | sha256 | ecf4b7e89098b92e79e8910ff6ddef8e7fbc1c5d6dffc930faf903bde06c9d07 | 2135435241 |
| text_encoder/1.safetensors | sha256 | 8b32bbec7881a83ca6f9de71c131c20881447e31f1d46cebb2d3720591026be8 | 127582075 |
| text_encoder/model.safetensors.index.json | git-sha1 | cc4b89edc0ce82cda966bc89f67896edeefa749e | 51332 |
| tokenizer/chat_template.jinja | git-sha1 | 01be9b307daa2d425f7c168c9fb145a286e0afb4 | 4168 |
| tokenizer/tokenizer.json | sha256 | be75606093db2094d7cd20f3c2f385c212750648bd6ea4fb2bf507a6a4c55506 | 11422650 |
| tokenizer/tokenizer_config.json | git-sha1 | 9a87e3822403fb40a9524bb75edb66c6f0585750 | 692 |
| transformer/0.safetensors | sha256 | 6dd1c55ab672d2148171b13b9c6e719465aecf12743ccb6d97d5ee1978f7e9ba | 2140225820 |
| transformer/1.safetensors | sha256 | 135062103c799495abe92f9966b163f39498b590a2244954679c0d709acb8b61 | 1323528823 |
| transformer/model.safetensors.index.json | git-sha1 | 1455bc3cbf51198d9b5fbf50eb2d9e0b6d43e995 | 61606 |
| vae/0.safetensors | sha256 | 531f8197f218382e2f5d300bee1a0b42edbc50ad7f181e37e994b9d1ca471a58 | 164654177 |
| vae/model.safetensors.index.json | git-sha1 | 33dfe32850bad435088bd6cfb11aa6adfdbaa585 | 17378 |

The authoritative copy of this table is [`config/backend-zimage-mflux.json`](../config/backend-zimage-mflux.json), which the app verifies on every startup. `git-sha1` is the git blob id the HF API publishes for non-LFS files.

```sh
source mflux/env.sh
mflux/.venv/bin/hf download mflux-community/z-image-turbo-mflux-q4 \
    --revision d2d30500c4bc0d19770bd952951df3e7c635ae9e \
    --local-dir models/mflux/z-image-turbo-mflux-q4
bin/photo-gen verify --full          # re-hashes all 11 files against the manifest; must print "ok": true
```

This is the only network step. photo-gen itself never downloads anything and runs with `HF_HUB_OFFLINE=1`. The mflux-community org has had a corrupt-download incident (mflux #748), which is why `verify --full` is mandatory after any download.

## 4. Verify the build
```sh
bin/photo-gen verify                                   # versions, 11 model digests, mflux capability cross-check
cd app/tests && PHOTOGEN_ROOT=../.. PYTHONPATH=..:. ../../mflux/.venv/bin/python3.12 -m unittest -v   # 72 tests (2026-10-07)
cd ../..
P="a red apple on a wooden table, soft window light"
bin/photo-gen generate -p "$P" --seed 42 --width 512 --height 512      # REFERENCE → 9ae59f59…
bin/photo-gen generate -p "$P" --seed 42 --profile fast                # FAST 1024² → 7b45cfbe…
bin/photo-gen generate -p "$P" --seed 42                               # REFERENCE 1024² → fe47d88d…
```

**Reference pixel hashes** (SHA-256 of decoded 8-bit RGB; the CLI prints them as `pixel_sha256`):
| configuration | hash |
|---|---|
| REFERENCE fp32/9, 1024² | `fe47d88dfb4bec549060c29c527eeff280d863e8e12176cdc1c28d3d8003a118` |
| REFERENCE fp32/9, 768² | `94a023d366cf8527aceb178ef42a676c0446ff8d93f08f32407575a6a369265a` |
| REFERENCE fp32/9, 512² | `9ae59f590e8c0b3ad067448cbed61f2969ec759918339626f76157f8b6529c9c` |
| FAST bf16/8, 1024² | `7b45cfbe2eed1cd1f732df87196b93e746dd422e0e9f5b64631ddbbea2ad9342` |
| FAST bf16/8, 768² | `20ff9e2c8d171f12b7411acf375e7bc644f4a06cfb56fdd73de7f52cf3787aae` |
| FAST bf16/8, 512² | `0b9cc20a6508e74f6285672dd700c43240e040068c2b9da0af2f68658e0be8d8` |
| bf16/9, 1024² (validated; not a profile) | `11b19277f7fd077d528d4e282a77bd9c90f3af3adf26555cf11d2f02760d520a` |
| BALANCED bf16/5, 1024² | `befe1b3c8af5424cc5f65868fec96938bfac782238f46c18652244fada3bdd42` |
| ULTRA bf16/4, 512² | `6aa2b8422c7213e7ad17d6113aaef7d41f009be185361c9ea5d2023adcf3c2a9` |

**A matching hash is the proof of reproduction.** A different hash on the validated machine means something in §2/§3 differs; `verify` should say what. On other hardware, a different hash is expected and is not evidence of a bug.

## 5. Optional: the image-edit backend (Qwen-Image-2.1; research opt-in, G2 REJECTED; Qwen Research License, non-commercial)
The edit backend is **not a production feature**: the real-photograph gate G2 rejected both gated configurations (`research/editing/real-world/results.md`). Rebuild it only for research. Z-Image generation (§1–§4) does not need any of this. Without it, `photo-gen edit` and `POST /edit` report the backend as unavailable (503), and everything else is unaffected.

| not in Git | size | how to get it back |
|---|---:|---|
| `mflux-qwen/.venv` (separate venv: mflux **0.21.0**, MLX 0.32.2) | ≈ 1.5 GB | §5.1 |
| `models/research/qwen-image-2.1/` (official checkpoint; post-G2 disposition RETAIN LOCALLY, `research/qwen/QWEN-ASSET-PROVENANCE.md` §6) | 33.13 GB | §5.2 |
| `models/qwen/qwen-image-2.1-edit-mflux-q4/` (local q4 export) | 10.64 GB | §5.3 |
| `data/inputs/` (staged input images, content-addressed) | — | created by the app |

**Never install mflux 0.21.0 into `mflux/.venv`.** 0.21.0 makes the Z-Image bf16 hidden stream the default (upstream #803) and changes the transformer lifetime (#802), so the REFERENCE hashes in §4 would change.

### 5.1 Venv (project-local; same uv/Python as §2)
```sh
source mflux/env.sh
uv venv mflux-qwen/.venv --python 3.12.14
# mflux-0.21.0-py3-none-any.whl from PyPI; verify: sha256 b2e38fd3cd4e50d497cc226e01555b8fc7856181c9421bde2e043bc53ac12d2e
uv pip install --python mflux-qwen/.venv/bin/python3.12 mflux-0.21.0-py3-none-any.whl -c config/qwen-venv-constraints.txt
```
- `config/qwen-venv-constraints.txt` pins every package to mflux 0.21.0's own `uv.lock` (CPython 3.12, darwin), **except MLX**: pinned to 0.32.2, production's M5-verified MLX, instead of the lock's 0.32.0. Both are within mflux's declared `mlx>=0.32.0,<0.33`.
- The resulting environment is frozen in `config/qwen-python-requirements.lock.txt`.
- **Known security advisories** (GitHub Dependabot, seen 2026-10-08; recorded in Phase 7): 4 open alerts on `config/qwen-python-requirements.lock.txt`: **fsspec** (high: server-side template injection in ReferenceFileSystem), and **urllib3** (one medium: chunked-deflate infinite loop; two high: unbounded chunk-size line buffering, HTTPS proxy TLS configuration possibly ignored). The edit venv is intentionally pinned and runs offline (`HF_HUB_OFFLINE=1`, loopback-only API, no remote filesystems), and the lock is **not** changed for these alerts. Upgrading would change the pinned edit environment, so it needs its own security assessment and a parity re-check (`research/qwen/PHASE6-INDEX.md` §7). It is not part of any research phase so far.

### 5.2 Checkpoint (33.13 GB; pinned)
```sh
zsh research/qwen/qwen-download.sh            # Qwen/Qwen-Image-2.1 @ d26bb61 (+ the sd.cpp comparator TE/mmproj)
mflux/.venv/bin/python3.12 research/qwen/verify_downloads.py   # every file vs research/qwen/upstream-file-manifest.json
```

### 5.3 q4 export (one-time; deterministic)
```sh
RUN=run3 zsh research/qwen/export-q4.sh       # QwenImage21Edit(quantize=4).save_model; ~75 s; monitored, with abort thresholds
bin/photo-gen verify --edit --full            # 18 files vs config/backend-qwen21-edit-mflux.json; must print "ok": true
```
- Two independent exports (2026-10-07) were **byte-identical in all 18 files**, so a re-export reproduces the pinned digests.
- The export holds about 11–12 GB while saving. Close large apps first: with other apps open, it pushed the machine into brief critical memory pressure (`research/qwen/INCIDENTS.md`).

### 5.4 Verify an edit
```sh
bin/photo-gen generate -p "a red apple on a wooden table, soft window light" --seed 42 --profile balanced   # befe1b3c… (the input)
bin/photo-gen edit --image data/outputs/<that job>.png -p "Change the background to a sunset beach" \
    --seed 42 --output-resolution 512 --allow-experimental
```
Expected on the validated machine: pixel sha256 `f7aa22f650100d7858c16f6c67c487c81ee7f5b40803d9b7f9e0c105240f106a` (RGB). The output PNG is RGBA; its RGBA sha256 is `49a202cb…`. The plain mflux CLI with the same arguments gives the same pixels (`research/qwen/QWEN-EDITING-BASELINE.md`).
The Phase 5 memory policy P2 is pixel-identical (exact parity on 5/5 pairs, `research/qwen/QWEN-MEMORY-LIFETIME.md` §2), so it doesn't change this hash.

### 5.5 Reproduce the real-photograph gate G2 (research)
```sh
mflux/.venv/bin/python3.12 -I research/editing/real-world/fetch_sources.py research/editing/real-world/selection.json
#   CC0/PD Wikimedia Commons originals -> data/benchmark/real-world/originals/ (gitignored); file and pixel
#   sha256 must match research/editing/real-world/source-manifest.json
nohup zsh research/editing/real-world/g2-chain.sh > g2-chain.log 2>&1 < /dev/null & disown   # 45 edits, ~4.5 h
```
- `run_edit.sh` refuses to overwrite an existing run directory, and the committed `research/qwen/runs/G2-*` records are evidence. To re-run, use a fresh checkout or change the run ids in a copy of the chain. Never delete the committed records.
- Every run's expected output `pixel_sha256` is recorded in `research/editing/real-world/benchmark.csv`. The repeats show the configuration is deterministic on this machine.
- Rating is provenance-blind. Follow the order `g2_blind.py prepare` → rater → `check_scores_format.py` → `freeze` → `unblind` → `analyze_g2.py` (`protocol.md` §5 and amendment 2).

### 5.6 Reproduce the Q-Q diagnostic (Phase 6, research)
```sh
nohup zsh research/qwen/qq/export-q8.sh > export-chain.log 2>&1 < /dev/null & disown    # q8 export from the retained source, per component (~2 min)
mflux/.venv/bin/python3.12 research/qwen/qq/merge_q8.py models/research/qq-staging/q8-part-vae-transformer \
    models/research/qq-staging/q8-part-text_encoder models/research/qwen-image-2.1-edit-mflux-q8 models/qwen/qwen-image-2.1-edit-mflux-q4 merge.json
nohup zsh research/qwen/qq/qq-chain.sh > qq-chain.log 2>&1 < /dev/null & disown          # 18 edits, ~2.2 h
```
- The export is exact. Every file's sha256 must equal `research/qwen/qq/export/merge-q8.json`, and gate E checks the procedure against the canonical q4 tensors.
- **Run directories:** `export-q8.sh` writes its records into `research/qwen/qq/export/` and `run_edit.sh` refuses existing run directories, so use a fresh checkout, or copies with new names, to re-run.
- **Expected pixels:**
  - every q4 run must reproduce its G2 run's pixels (gate Q);
  - q8 pixels are in `research/qwen/runs/QQ-*/worker/identity.json`.
- **Rating:** `make_pairs.py` → `qq_blind.py prepare` → fresh rater → `qq_blind.py check` → `freeze` → `unblind` → `analyze_qq.py` (`research/qwen/qq/PROTOCOL.md`).

## 6. Offline and privacy
- The API binds to `127.0.0.1`. There is no telemetry.
- Workers run with `HF_HUB_OFFLINE=1`, `HF_HUB_DISABLE_TELEMETRY=1`, `HF_HOME=mflux/hf`.
- No credentials are needed or stored anywhere in the project.
