#!/bin/zsh
# Qwen-Image-2.1 control run, exact configuration validated in the Qwen project
# (sd.cpp master-908, leejet Q4_K DiT + Heretic Q4_K_M TE + official VAE, euler, model-default scheduler, cfg 1, 25 steps).
# Usage: zsh research/qrun.sh <run-id> <W> <H> <prompt> <tensor: on|off> [steps=25]
id=$1 W=$2 H=$3 P=$4 T=$5 S=${6:-25}
M=~/Dev/photo-gen/models
if [[ $T == off ]]; then export GGML_METAL_TENSOR_DISABLE=1; lbl="GGML_METAL_TENSOR_DISABLE=1 | Metal tensor API = disabled (BACKEND DIAGNOSTIC)"; else unset GGML_METAL_TENSOR_DISABLE; lbl="none | Metal tensor API = enabled (PRIMARY CONTROL)"; fi
zsh ~/Dev/photo-gen/research/run.sh $id --diffusion-model $M/diffusion_models/qwen_image_2.1-Q4_K.gguf --vae $M/vae/qwen_image_2.1_vae_bf16.safetensors \
  --llm $M/text_encoders/qwen3vl_8b_heretic-Q4_K_M.gguf -p "$P" -W $W -H $H --steps $S --cfg-scale 1 --sampling-method euler -s 42 -v \
  -o ~/Dev/photo-gen/outputs/$id.png
echo "ENV: $lbl" > ~/Dev/photo-gen/research/runs/$id/env.txt
cp ~/Dev/photo-gen/research/runs/$id/monitor.csv ~/Dev/photo-gen/research/qwen-monitor-$id.log
python3 ~/Dev/photo-gen/research/imgcheck.py ~/Dev/photo-gen/outputs/$id.png
