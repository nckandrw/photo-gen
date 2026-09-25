# MFLUX phase — pinned versions (2026-09-24)

## Toolchain (project-local; nothing outside ~/Dev/photo-gen/mflux except as noted)
- uv 0.12.18 (01cb90c1a 2026-09-22), `uv-aarch64-apple-darwin.tar.gz` sha256 cf40e0c6a202190ccd9e0406dcfdd5b2d6668a9a5c779b17948963df32aafe5b (matches GitHub asset digest); Mach-O arm64, hardened runtime, TeamIdentifier 2DC432GLL2. Location `mflux/tools/uv`.
- Environment file `mflux/env.sh` pins UV_PYTHON_INSTALL_DIR, UV_PYTHON_BIN_DIR, UV_CACHE_DIR, UV_TOOL_DIR, HF_HOME to `mflux/`; UV_PYTHON_PREFERENCE=only-managed; UV_NO_CONFIG=1; UV_PYTHON_INSTALL_REGISTRY=0.
- **Incident (resolved):** the first `uv python install` also created `~/.local/bin/python3.12` (symlink into mflux/python) because UV_PYTHON_BIN_DIR was not yet set. It was removed within a minute (verified target before `rm`) and UV_PYTHON_BIN_DIR added to env.sh. No other files outside the project were created by uv.
- CPython 3.12.14 (python-build-standalone, `cpython-3.12.14-macos-aarch64-none`), arm64, at `mflux/python/`. venv `mflux/.venv`.

## Packages (installed with `uv pip install --only-binary :all: mflux==0.20.0 mlx==0.32.2`; wheels only, no build scripts)
- mflux 0.20.0 — PyPI wheel sha256 5d60a278d67289be0da2e4ba0e8dcf938dd3c676a01c9064f64e3fb10e30767d; sdist sha256 8fec3407bbc821cfba9cebd8ae55e35450b9429ec9b5445c9557aaeb78087de0. Installed source tree **byte-identical** (`diff -r`) to the audited sdist.
- mlx 0.32.2 + mlx-metal 0.32.2 (`py3-none-macosx_26_0_arm64` wheel; metallib contains NAX kernels, e.g. `qmm_t_nax`, `steel_gemm_fused_nax_`).
- Declared hard deps pulled in (per decision A): torch 2.14.0, transformers 5.17.0, opencv-python 4.14.0.94, tokenizers 0.23.2, and others. torch is imported at runtime (top-level import in mflux weight_loader) but `torch.mps.current_allocated_memory()` = 0 after generation → not used for compute on this path.
- Full lock (56 packages): `mflux/requirements.lock.txt`:
```
[1mannotated-doc[0m==0.0.5
[1manyio[0m==4.15.1
[1mcertifi[0m==2026.7.22
[1mcharset-normalizer[0m==3.5.1
[1mclick[0m==8.5.0
[1mcontourpy[0m==1.4.0
[1mcycler[0m==0.12.1
[1mfilelock[0m==4.0.3
[1mfonttools[0m==4.66.0
[1mfsspec[0m==2026.9.0
[1mh11[0m==0.16.0
[1mhf-transfer[0m==0.1.9
[1mhf-xet[0m==1.6.0
[1mhttpcore[0m==1.0.9
[1mhttpx[0m==0.28.1
[1mhuggingface-hub[0m==1.32.0
[1midna[0m==3.20
[1mjinja2[0m==3.1.6
[1mkiwisolver[0m==1.5.1
[1mmarkdown-it-py[0m==4.2.0
[1mmarkupsafe[0m==3.0.3
[1mmatplotlib[0m==3.11.2
[1mmdurl[0m==0.1.2
[1mmflux[0m==0.20.0
[1mmlx[0m==0.32.2
[1mmlx-metal[0m==0.32.2
[1mmpmath[0m==1.3.0
[1mnetworkx[0m==3.7
[1mnumpy[0m==2.5.3
[1mopencv-python[0m==4.14.0.94
[1mpackaging[0m==26.3
[1mpiexif[0m==1.1.3
[1mpillow[0m==12.3.0
[1mplatformdirs[0m==4.11.12
[1mprotobuf[0m==7.36.2
[1mpygments[0m==2.21.0
[1mpyparsing[0m==3.3.3
[1mpython-dateutil[0m==2.9.0.post0
[1mpyyaml[0m==6.0.3
[1mregex[0m==2026.9.10
[1mrequests[0m==2.34.2
[1mrich[0m==15.0.0
[1msafetensors[0m==0.8.0
[1msentencepiece[0m==0.2.2
[1msetuptools[0m==84.0.0
[1mshellingham[0m==1.5.4
[1msix[0m==1.17.0
[1msympy[0m==1.14.0
[1mtokenizers[0m==0.23.2
[1mtoml[0m==0.10.2
[1mtorch[0m==2.14.0
[1mtqdm[0m==4.70.1
[1mtransformers[0m==5.17.0
[1mtyper[0m==0.27.2
[1mtyping-extensions[0m==4.16.0
[1murllib3[0m==2.8.0
```

## Model (store: `models/mflux/z-image-turbo-mflux-q4/`, read-only after verification)
`mflux-community/z-image-turbo-mflux-q4` @ d2d30500c4bc0d19770bd952951df3e7c635ae9e (lastModified 2026-08-03), 5,902,985,542 B total.
| File | Verification |
|---|---|
| text_encoder/0.safetensors | sha256 ecf4b7e89098b92e79e8910ff6ddef8e7fbc1c5d6dffc930faf903bde06c9d07 |
| text_encoder/1.safetensors | sha256 8b32bbec7881a83ca6f9de71c131c20881447e31f1d46cebb2d3720591026be8 |
| transformer/0.safetensors | sha256 6dd1c55ab672d2148171b13b9c6e719465aecf12743ccb6d97d5ee1978f7e9ba |
| transformer/1.safetensors | sha256 135062103c799495abe92f9966b163f39498b590a2244954679c0d709acb8b61 |
| vae/0.safetensors | sha256 531f8197f218382e2f5d300bee1a0b42edbc50ad7f181e37e994b9d1ca471a58 |
| tokenizer/tokenizer.json | sha256 be75606093db2094d7cd20f3c2f385c212750648bd6ea4fb2bf507a6a4c55506 |
| text_encoder/model.safetensors.index.json | git-sha1 cc4b89edc0ce82cda966bc89f67896edeefa749e |
| transformer/model.safetensors.index.json | git-sha1 1455bc3cbf51198d9b5fbf50eb2d9e0b6d43e995 |
| vae/model.safetensors.index.json | git-sha1 33dfe32850bad435088bd6cfb11aa6adfdbaa585 |
| tokenizer/chat_template.jinja | git-sha1 01be9b307daa2d425f7c168c9fb145a286e0afb4 |
| tokenizer/tokenizer_config.json | git-sha1 9a87e3822403fb40a9524bb75edb66c6f0585750 |

## Run configuration
`mflux/zi_driver.py` (instrumentation wrapper around the unmodified CLI `main()`), launched by `research/mrun.sh`:
`--model models/mflux/z-image-turbo-mflux-q4 --base-model z-image-turbo --width W --height H --steps 9 --seed 42 --low-ram` with `HF_HUB_OFFLINE=1`. Guidance forced to 0.0 by the Turbo CLI (official semantics). Scheduler: mflux default for Turbo (`linear` + resolution-dependent shift).
