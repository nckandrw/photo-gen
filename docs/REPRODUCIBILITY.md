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
| — | `models/diffusion_models`, `models/text_encoders`, `models/vae`, `sdcpp/`, `outputs/` (Pass-1 sd.cpp/Qwen comparison only; not used by photo-gen) | pins in [`research/model-pins.txt`](../research/model-pins.txt), [`research/z-image-model-pins.txt`](../research/z-image-model-pins.txt) |

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
cd app/tests && PHOTOGEN_ROOT=../.. PYTHONPATH=..:. ../../mflux/.venv/bin/python3.12 -m unittest -v   # 39 tests
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

**A matching hash is the proof of reproduction.** A different hash on the validated machine means something in §2/§3 differs; `verify` should say what. On other hardware, a different hash is expected and is not evidence of a bug.

## 5. Offline and privacy
- The API binds to `127.0.0.1`. There is no telemetry.
- Workers run with `HF_HUB_OFFLINE=1`, `HF_HUB_DISABLE_TELEMETRY=1`, `HF_HOME=mflux/hf`.
- No credentials are needed or stored anywhere in the project.
