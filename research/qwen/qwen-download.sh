#!/bin/zsh
# Pinned Phase 4 acquisition (QWEN-SOURCE-AUDIT.md §10; approved by the user 2026-10-06).
# Marker: QWEN_DOWNLOAD_DONE (or QWEN_DOWNLOAD_FAILED). Verification: research/qwen/verify_downloads.py.
# Qwen/Qwen-Image-2.1 is under the Qwen Research License (non-commercial); never commit or redistribute.
cd ~/Dev/photo-gen && source mflux/env.sh
unset HF_HUB_OFFLINE
HF=mflux/.venv/bin/hf   # the downloader CLI only; nothing is installed into the production venv
echo "[$(date +%T)] comparator TE: Qwen/Qwen3-VL-8B-Instruct-GGUF @ f982a07 (Apache-2.0)"
$HF download Qwen/Qwen3-VL-8B-Instruct-GGUF Qwen3VL-8B-Instruct-Q4_K_M.gguf mmproj-Qwen3VL-8B-Instruct-F16.gguf \
  --revision f982a07559d4a2f6c8744d840bf6fccab30eea96 --local-dir models/text_encoders || { echo QWEN_DOWNLOAD_FAILED; exit 1; }
echo "[$(date +%T)] Qwen/Qwen-Image-2.1 @ d26bb61 (complete checkpoint, 33.13 GB)"
$HF download Qwen/Qwen-Image-2.1 --revision d26bb61231c349cf6b7896fa83353113880e1ba3 \
  --local-dir models/research/qwen-image-2.1 || { echo QWEN_DOWNLOAD_FAILED; exit 1; }
echo "[$(date +%T)] QWEN_DOWNLOAD_DONE"
