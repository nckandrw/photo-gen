# models/ (not versioned)

Model weights are **not** stored in Git. photo-gen needs exactly one model:

`models/mflux/z-image-turbo-mflux-q4/`: `mflux-community/z-image-turbo-mflux-q4` @ `d2d30500c4bc0d19770bd952951df3e7c635ae9e` (Apache-2.0, 5.9 GB, 11 files).

- Download and verification steps: [`docs/REPRODUCIBILITY.md`](../docs/REPRODUCIBILITY.md) §3.
- Pinned digests (verified on every startup): [`config/backend-zimage-mflux.json`](../config/backend-zimage-mflux.json).

Other subdirectories that may exist locally (`diffusion_models/`, `text_encoders/`, `vae/`) hold the Pass-1 sd.cpp/Qwen comparison models. photo-gen does not use them. Their pins are in `research/model-pins.txt` and `research/z-image-model-pins.txt`.
