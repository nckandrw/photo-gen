#!/bin/zsh
# One monitored Qwen-Image-2.1 edit run (Phase 4 research harness). Never shares the GPU: run sequentially only.
# Usage: zsh research/qwen/run_edit.sh <run_id> <app|plain> <image> <output_resolution> <seed> <instruction> [steps=40]
#   app   = the production path: bin/photo-gen edit (job system, staging, edit worker with passive probes)
#   plain = the unmodified mflux 0.21.0 CLI on the same staged input and arguments (parity control for the probes)
#   worker0/worker1 = the production edit worker run directly (worker_run.py) with defer_transformer_load off/on
#   mem:<P0|P1|PV|P2> = the production edit worker with a named Phase 5 lifetime policy (research/qwen/memory/mem_run.py)
#   sdcpp = comparator: sd.cpp master-908 (the 2026-09-24 baseline configuration: auto-fit, no memory flags, euler,
#           cfg 1) + official Qwen3-VL-8B-Instruct Q4_K_M + mmproj F16, reference via -r; output = res x res
# Abort thresholds (declared before any run): swap grows by > 6144 MB over its starting value, OR the kernel memory
# pressure level is critical (4) for 20 consecutive 1 s samples -> the edit process(es) are killed.
# Evidence: research/qwen/runs/<run_id>/ (monitor.csv, console.log, result.json, conditions.txt). Marker: EDIT_RUN_END.
# The body is one function, parsed in full before it runs, so editing this file during a chain cannot shift
# what a running instance executes (incident 2026-10-07 00:19, INCIDENTS.md).
main() {
set -u
cd ~/Dev/photo-gen
RID=$1 MODE=$2 IMG=$3 RES=$4 SEED=$5 PROMPT=$6 STEPS=${7:-40}
OUT=research/qwen/runs/$RID
if [[ -e $OUT ]]; then echo "refusing to overwrite $OUT"; return 3; fi
mkdir -p $OUT
{ echo "run_id=$RID mode=$MODE res=$RES seed=$SEED steps=$STEPS"; echo "image=$IMG"; echo "prompt=$PROMPT"
  date; pmset -g batt | head -2; sysctl vm.swapusage kern.memorystatus_vm_pressure_level
  memory_pressure | grep "free percentage"; pmset -g therm | grep -i -E "warning|limit"
  ps -axo rss,comm | sort -rn | head -6
  echo "git_head=$(git rev-parse HEAD)"; echo "git_dirty(app,config,research/qwen):"
  git status --porcelain app config research/qwen/run_edit.sh research/qwen/worker_run.py research/qwen/memory; } > $OUT/conditions.txt 2>&1
local PROC=python3.12; [[ $MODE == sdcpp ]] && PROC=sd-cli
zsh research/monitor.sh $OUT/monitor.csv $PROC 1 &
MON=$!
swap0=$(sysctl -n vm.swapusage | awk '{gsub("M","",$6);print int($6)}')
t0=$(date +%s)
if [[ $MODE == app ]]; then
  bin/photo-gen edit --image "$IMG" --prompt "$PROMPT" --seed $SEED --steps $STEPS --output-resolution $RES \
    --allow-experimental --json > $OUT/result.json 2> $OUT/console.log &
elif [[ $MODE == plain ]]; then
  env -i PATH=/usr/bin:/bin HOME=$HOME HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 HF_HOME=$PWD/mflux/hf \
    /usr/bin/time -l mflux-qwen/.venv/bin/mflux-generate-qwen-2.1-edit \
    --model models/qwen/qwen-image-2.1-edit-mflux-q4 --base-model qwen-image-2.1 "--prompt=$PROMPT" \
    --image-paths "$IMG" --seed $SEED --steps $STEPS --output-resolution $RES --low-ram \
    --output $OUT/plain.png > $OUT/console.log 2>&1 &
elif [[ $MODE == worker0 || $MODE == worker1 ]]; then   # production worker directly; defer_transformer_load 0/1
  mflux/.venv/bin/python3.12 research/qwen/worker_run.py $OUT/worker "$IMG" $RES $SEED "$PROMPT" ${MODE#worker} $STEPS \
    > $OUT/result.json 2> $OUT/console.log &
elif [[ $MODE == mem:* ]]; then   # Phase 5 memory-lifetime A/B: production worker with a named policy (mem_run.py)
  mflux/.venv/bin/python3.12 research/qwen/memory/mem_run.py $OUT/worker "$IMG" $RES $SEED "$PROMPT" ${MODE#mem:} $STEPS \
    > $OUT/result.json 2> $OUT/console.log &
elif [[ $MODE == sdcpp ]]; then
  local M=$PWD/models
  env -i PATH=/usr/bin:/bin HOME=$HOME /usr/bin/time -l sdcpp/master-908-88411ef/sd-cli \
    --diffusion-model $M/diffusion_models/qwen_image_2.1-Q4_K.gguf --vae $M/vae/qwen_image_2.1_vae_bf16.safetensors \
    --llm $M/text_encoders/Qwen3VL-8B-Instruct-Q4_K_M.gguf --llm_vision $M/text_encoders/mmproj-Qwen3VL-8B-Instruct-F16.gguf \
    -r "$IMG" -p "$PROMPT" -W $RES -H $RES --steps $STEPS --cfg-scale 1 --sampling-method euler -s $SEED -v \
    -o $OUT/sdcpp.png > $OUT/console.log 2>&1 &
else
  echo "unknown mode $MODE"; kill $MON; return 2
fi
PID=$!
crit=0; aborted=0
while kill -0 $PID 2>/dev/null; do
  sw=$(sysctl -n vm.swapusage | awk '{gsub("M","",$6);print int($6)}')
  pl=$(sysctl -n kern.memorystatus_vm_pressure_level)
  if (( pl == 4 )); then (( crit++ )); else crit=0; fi
  if (( sw - swap0 > 6144 || crit >= 20 )); then
    echo "ABORT $(date +%T): swap ${sw}MB (start ${swap0}MB), critical streak ${crit}" | tee -a $OUT/conditions.txt
    pkill -TERM -f "mflux_qwen_edit_worker|mflux-generate-qwen-2.1-edit|sd-cli"; pkill -TERM -P $PID; kill -TERM $PID
    sleep 5; pkill -KILL -f "mflux_qwen_edit_worker|mflux-generate-qwen-2.1-edit|sd-cli"; kill -KILL $PID 2>/dev/null
    aborted=1; break
  fi
  sleep 1
done
wait $PID; rc=$?
kill $MON 2>/dev/null
echo "wall_s=$(( $(date +%s) - t0 )) rc=$rc aborted=$aborted swap_end=$(sysctl -n vm.swapusage | awk '{print $6}')" \
  | tee -a $OUT/conditions.txt
echo "EDIT_RUN_END $RID rc=$rc aborted=$aborted"
}
main "$@"; exit $?   # exit here: never read past this line, even if the file grows mid-run
