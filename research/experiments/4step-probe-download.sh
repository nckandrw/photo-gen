#!/bin/zsh
# Pinned acquisition for the 4-step probe (4step-probe-acquisition.md). Marker: PROBE_DOWNLOAD_DONE
cd ~/Dev/photo-gen && source mflux/env.sh
unset HF_HUB_OFFLINE
echo "[$(date +%T)] base q4"
mflux/.venv/bin/hf download mflux-community/z-image-base-mflux-q4 --revision 087eaf40738482a1a99394ce1b490ab12738c1f6 --local-dir models/research/z-image-base-mflux-q4 || { echo PROBE_DOWNLOAD_FAILED; exit 1; }
echo "[$(date +%T)] 4-step LoRA"
mflux/.venv/bin/hf download alibaba-pai/Z-Image-Fun-Lora-Distill Z-Image-Fun-Lora-Distill-4-Steps-2603-ComfyUI.safetensors --revision f9a4db417ab7d8c1c5ffa9c0f03bdd72ae4a070c --local-dir models/research/loras || { echo PROBE_DOWNLOAD_FAILED; exit 1; }
echo "[$(date +%T)] PROBE_DOWNLOAD_DONE"
