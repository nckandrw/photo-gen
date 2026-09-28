# Blind protocol: 4-step probe

- **Tool:** `research/experiments/blind_stage.py` (prepare → freeze → unblind), following `BLIND-PROTOCOL.md`.
- **Generation is separate from identity:**
  - Image files are named by tag (`<cand>-<pid>-s<seed>`) and are never opened directly by the rater.
  - The rater sees only `Cnn.png` composites. Each composite's L/R assignment is random, and the key is written atomically before any composite exists.
- **Three pairwise directories, separate RNG seeds, reviewed in this order:**
  1. `blind-CvsB` (rng 2809281): 24 composites, C vs B. Answers Q2.
  2. `blind-CvsA` (rng 2809282): 24 composites, C vs A. Answers Q3.
  3. `blind-AvsB` (rng 2809283): 24 composites, A vs B. A calibration control: how much plain step reduction costs.
  - Each directory is scored and frozen before the next is prepared.
  - All keys stay sealed until all three score files are frozen, so no directory's key can inform another's scores.
- **Disclosed limitation:** each C, A and B image appears in two directories. The rater may recognise an image seen earlier, but not its identity, because keys are sealed until all scoring is done.
- **Seeds 4242 and 6174 have never been used in this project.** The rater has seen no image from them.
- **Scoring per composite, in the directive's priority order:**
  1. prompt adherence (incl. object count, spatial relations);
  2. composition;
  3. visual quality (detail, texture, realism, lighting, artifacts).

  Plus text correctness for p03/p05/p07, and an artifact type if any. **Overall preference is lexicographic:** a prompt-adherence difference decides; otherwise composition; otherwise visual quality; otherwise "=". A prettier but less prompt-faithful image does not win.
- Pixel identity and PSNR/SSIM are **not** quality criteria. They are reported descriptively only.
- **Artifacts preserved:** per directory, the key, `MANIFEST.json`, the frozen scores with hashes, and the unblinded key.
