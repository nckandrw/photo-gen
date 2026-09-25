# Pinned versions — Qwen-Image-2.1 validation

Recorded 2026-09-24. Updated as components are added.

## Machine
- MacBook Air, Apple M5, 10 CPU (4P+6E), 8-core GPU, Metal 4 (MTLGPUFamilyApple10), 16 GiB unified (17179869184 B)
- macOS 27.0 (26A428), arm64
- Metal recommendedMaxWorkingSetSize 12713.12 MB; maxBufferLength 9.53 GB; ggml reports `has tensor = true`, `has bfloat = true`, shared buffers + residency sets
- Xcode at /Applications/Xcode.app; Apple clang 21.0.0 (clang-2100.3.34.2); system Python 3.9.6 (unused)

## stable-diffusion.cpp
- Release `master-908-88411ef` (published 2026-09-23T22:10:47Z by github-actions[bot]), commit `88411ef1e0688ff2df1010aeeb5d92b2d8cea2be`
- Asset `sd-master-88411ef-bin-Darwin-macOS-26.6.2-arm64.zip`, 34389489 B, sha256 `acf9cd2219e69bdfc0faa0d6daaafa696d9551c723b74d6e37f2cd78da386d5a` (matches GitHub asset digest)
- Universal Mach-O (x86_64+arm64), ad-hoc linker-signed, links Metal/MetalKit/Accelerate; ggml submodule `4bf5f60` (leejet/ggml); embedded metal library
- Location: `~/Dev/photo-gen/sdcpp/master-908-88411ef/`; `sd-cli --version` → "stable-diffusion.cpp version unknown, commit 88411ef"
- `sd-cli -h` saved to `sdcpp/sd-cli-help.txt`; `--list-devices` → MTL0 (Apple M5), BLAS (Accelerate), CPU

## Models (store: `~/Dev/photo-gen/models/`, files made read-only after sha256 verification)
| Role | Repo @ revision | File | Size (B) | SHA256 | Status |
|---|---|---|---:|---|---|
| TE (Heretic) | pottokao/Qwen-Image-2.1-Text-Encoder-Heretic-GGUF @ e21acf0ee1ce58bb6d9db4c1975639a0b6df4413 | qwen3vl_8b_heretic-Q4_K_M.gguf | 5027785376 | 1338274ac7a6344f262a16c7a52d1bd7fe789307d252733b23ea421126e5d343 | pending |
| mmproj (Heretic) | same | mmproj-qwen3vl_8b_heretic-f16.gguf | 1159030464 | 4649839491c8df1ebc9bed2de158ad2a45b53ed1d3b311d92a69056b6764f101 | pending |
| DiT | leejet/Qwen-Image-2.1-GGUF @ cc11433936a06e9765f7c0c0b1f0436cfd2b9856 | qwen_image_2.1-Q4_K.gguf | 4197494816 | 29f9c83c249ff0292fb2943fceddfa2319b446601866c82a4f8be062abea72c2 | pending |
| VAE | Comfy-Org/Qwen-Image-2.1 @ 9a44dbdb47cefd046be9c0a13476192f34c8db8e | vae/qwen_image_2.1_vae_bf16.safetensors | 675509688 | bb21f7473051e1ac368515dd3f2e15cd44d7a11748ee8823e1ddca3e4876b7c9 | pending |
| TE (stock, A/B) | Qwen/Qwen3-VL-8B-Instruct-GGUF @ f982a07559d4a2f6c8744d840bf6fccab30eea96 | Qwen3VL-8B-Instruct-Q4_K_M.gguf | 5027784800 | 67d1659bfe71b89d50b45a4ad1a9e5b997e5bb16ce5da66a6a6167abd569e9e2 | not yet needed |
| DiT fallback | leejet @ cc11433 | qwen_image_2.1-Q4_0.gguf | 4197494816 | 8d992dc95dcbf13196a4aca893697fb56a5c9263e19e7b40c898be2cf29e9147 | only if needed |

## ComfyUI (Candidate 2) — not installed yet
