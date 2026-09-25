#!/bin/zsh
# Z-Image-Turbo PRIMARY + #1990 WORKAROUND run. Usage: zsh research/zrun.sh <run-id> <W> <H> <prompt> [extra sd-cli args...]
id=$1 W=$2 H=$3 P=$4; shift 4
M=~/Dev/photo-gen/models
export GGML_METAL_TENSOR_DISABLE=1
zsh ~/Dev/photo-gen/research/run.sh $id --diffusion-model $M/diffusion_models/z_image_turbo-Q4_K.gguf --vae $M/vae/ae.safetensors \
  --llm $M/text_encoders/Qwen3-4B-Q4_K_M.gguf -p "$P" -W $W -H $H --steps 9 --cfg-scale 1 --sampling-method euler -s 42 -v \
  -o ~/Dev/photo-gen/outputs/$id.png "$@"
echo "ENV: GGML_METAL_TENSOR_DISABLE=1 (process-scoped; sd.cpp #1990 workaround) | Metal tensor API = disabled" > ~/Dev/photo-gen/research/runs/$id/env.txt
cp ~/Dev/photo-gen/research/runs/$id/monitor.csv ~/Dev/photo-gen/research/z-image-monitor-$id.log
python3 ~/Dev/photo-gen/research/imgcheck.py ~/Dev/photo-gen/outputs/$id.png
