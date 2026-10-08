# Texture-Fix VAE: acquisition audit (Phase 8, PROTOCOL.md §8.1), written before the download

**Gate (§8):** every §5.1 gate passed and no item is MATERIAL (`qvr-summary.json`, commit `134a618`), so the conditional
Texture-Fix arm may run.

| | |
|---|---|
| repository | `madebyollin/texture-fix-vae-for-qwen-image-2.1` (Hugging Face, not gated) |
| revision | `702909b4d408912c7a28fadea06e8b7fdb38ef0c` (last modified 2026-10-06; the "2026-10-05 updated release") |
| what it is (model card, primary-source claim) | the Qwen-Image-2.1 VAE with a fine-tuned **decoder** (adversarial TAESD-style recipe; first the two highest-resolution decoder stages + head, then per-conv scale/bias and RMSNorm gains for fp16 headroom); encoder weights "only rescaled by exact powers of two … computes the same function". Reported reconstruction: PSNR 32.35 vs 32.85 dB (DIV2K 1024² crops), LPIPS 0.0490 vs 0.0460, rFID better. Not developed for text fidelity. |
| files downloaded | `config.json` (2,079 B, sha256 `9785d527…a589ac`; diffs empty against the original VAE config) and `diffusion_pytorch_model.safetensors` (fp32, 1,350,989,544 B, LFS sha256 `9c4a3e6b970fe82e99fae227b70529646427333c4378a51b2e853c93f492a6a8`). Not downloaded: the bf16 file, the demo images and latents. |
| licence | `license: other`, `qwen-research`. The repository's `LICENSE` (sha256 `8dc973f0…72b28d`) is **byte-identical** to the Qwen-Image-2.1 `LICENSE` we already hold. `NOTICE`: modified decoder weights by madebyollin, 2026. Non-commercial / research use only, the same terms as the base model; this research-only diagnostic matches them. |
| destination | `models/research/texture-fix-vae-qwen-image-2.1/` (gitignored by `models/**`); never committed or redistributed |
| disk | +1.35 GB (181 GiB free before) |
| method | `curl` of the two files at the pinned revision; the sha256 is verified before any use, and the file is used read-only by `ref_side.py` (CPU, Diffusers `AutoencoderKLQwenImage21`, strict load) |
| use | §8.1 only: a decoder comparison on identical latents, encoder-equivalence check, per-tensor weight diff. Never a default, never in `app/` or `config/`. |
| deletion trigger | delete when Phase 8 closes unless the user decides to keep it; it is re-acquirable exactly from the pinned revision and hash above |
| **disposition at Phase 8 close (2026-10-09)** | **trigger met; kept pending your decision** (deletion is yours to authorise; re-acquirable exactly). Result: no text rescue (`research/qwen/QWEN-QVR-REFERENCE.md` §5.1). |
