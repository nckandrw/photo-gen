# Z-Image-Turbo experiment — pinned versions (2026-09-24)

Machine: MacBook Air M5, 8-core GPU (Apple10 / Metal 4), 16 GiB, macOS 27.0 (26A428). Metal recommendedMaxWorkingSetSize 12713.12 MB, maxBufferLength 9.53 GB.

Runtime: stable-diffusion.cpp release `master-908-88411ef` (commit 88411ef1e0688ff2df1010aeeb5d92b2d8cea2be); zip sha256 acf9cd2219e69bdfc0faa0d6daaafa696d9551c723b74d6e37f2cd78da386d5a; sd-cli sha256 40ae4010a32e428ca9f5095376d68a8db462e9655d5c1d826f1f8e236e8c2ab3; libstable-diffusion.dylib sha256 1c8b2f9db1cb9d93f5e1594e38ac67330e606e633e19ba0da4fda577b3f4c972. Metal backend MTL0 (Apple M5), `has tensor = true`. Help output identical to Qwen phase (only argv[0] differs).

| Role | Repo @ revision | File | Size (B) | SHA256 (verified after download) |
|---|---|---|---:|---|
| DiT | leejet/Z-Image-Turbo-GGUF @ c61c0e422dc8b541b7548cf33a4ef8302b0f8085 | z_image_turbo-Q4_K.gguf | 3864250304 | 14b375ab4f226bc5378f68f37e899ef3c2242b8541e61e2bc1aff40976086fbd |
| TE | Qwen/Qwen3-4B-GGUF @ bc640142c66e1fdd12af0bd68f40445458f3869b | Qwen3-4B-Q4_K_M.gguf | 2497280256 | 7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5 |
| VAE | Comfy-Org/z_image_turbo @ 6fc90a3b1b653e935a0d175e260736de25b84df5 | split_files/vae/ae.safetensors | 335304388 | afc8e28272cd15db3919bacdb6918ce9c1ed22e96cb12c4d5ed0fba823529e38 |

Qwen control artifacts: unchanged, re-verified 2026-09-24 11:0x (see versions.md).

Inference config (PRIMARY CONFIGURATION): `--steps 9 --cfg-scale 1 --sampling-method euler -s 42`, scheduler = sd.cpp model default (recorded per run). cfg-scale 1 ≡ official guidance_scale 0 (see z-image-tests.md, Directive improvement 1).
