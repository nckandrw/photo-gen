#!/bin/zsh
# Cold Z-Image BALANCED check (performance-regression evidence for the refactor), then the frozen G0 chain.
# Marker: G0_CHAIN_DONE (from g0-chain.sh). Log: research/qwen/g0-launch.log
main() {
cd ~/Dev/photo-gen
echo "idle cooldown start $(date +%T)"; sleep 600
{ date; pmset -g batt | head -1; sysctl vm.swapusage; } > research/qwen/zimage-regression/cold-balanced-conditions.txt
bin/photo-gen generate -p "a red apple on a wooden table, soft window light" --seed 42 --profile balanced --json \
  > research/qwen/zimage-regression/cold-balanced-1024.json 2> research/qwen/zimage-regression/cold-balanced-1024.log
echo "cold balanced done $(date +%T)"; sleep 30
zsh research/qwen/g0-chain.sh
}
main "$@"; exit $?
