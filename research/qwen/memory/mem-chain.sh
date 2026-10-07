#!/bin/zsh
# Phase 5 memory-lifetime A/B chain (pre-registered in research/qwen/memory/PROTOCOL.md). Frozen in a commit before
# launch. Launch: nohup zsh research/qwen/memory/mem-chain.sh > research/qwen/memory/mem-chain.log 2>&1 < /dev/null & disown
# Marker: MEMCHAIN_DONE. Research harness runs bypass data/gpu.lock: run no photo-gen jobs while this chain runs.
main() {
set -u
cd ~/Dev/photo-gen
echo "MEMCHAIN_START $(date) git=$(git rev-parse HEAD)"
PF=research/qwen/memory/preflight
mkdir -p $PF
P="a red apple on a wooden table, soft window light"
# ---- preflight: Z-Image regression + one production edit through the real CLI on the Phase 5 code ----
for spec in "reference 1024" "fast 1024" "balanced 1024" "ultra 512" "reference 512"; do
  prof=${spec% *} res=${spec#* }
  bin/photo-gen generate -p "$P" --seed 42 --profile $prof --width $res --height $res --json \
    > $PF/zimage-$prof-$res.json 2> $PF/zimage-$prof-$res.log
  echo "ZREG $prof $res rc=$? $(python3 -c "import json;d=json.load(open('$PF/zimage-$prof-$res.json'));print(d.get('pixel_sha256'), d.get('generation_seconds'), d.get('backend_id'))" 2>&1)"
  sleep 20
done
E05=$(python3 -c "import json;print(json.load(open('research/qwen/memory/inputs.json'))['E05']['staged_path'])")
E08C=$(python3 -c "import json;print(json.load(open('research/qwen/memory/inputs.json'))['E08c']['staged_path'])")
I05="Change the background to a sunset beach"
I08="Replace the bananas with pineapples. Do not change anything else."
bin/photo-gen edit --image "$E05" -p "$I05" --seed 42 --output-resolution 512 --allow-experimental --json \
  > $PF/edit-E05-512.json 2> $PF/edit-E05-512.log
echo "EDITPRE rc=$? $(python3 -c "import json;d=json.load(open('$PF/edit-E05-512.json'));print(d.get('pixel_sha256'), d.get('generation_seconds'), d.get('backend_id'))" 2>&1)"
sleep 20
# ---- A/B 512 ----
zsh research/qwen/run_edit.sh M5-512-E05-P0 mem:P0 "$E05" 512 42 "$I05"; sleep 20
zsh research/qwen/run_edit.sh M5-512-E05-P2 mem:P2 "$E05" 512 42 "$I05"; sleep 20
zsh research/qwen/run_edit.sh M5-512-E08c-P0 mem:P0 "$E08C" 512 42 "$I08"; sleep 20
zsh research/qwen/run_edit.sh M5-512-E08c-P2 mem:P2 "$E08C" 512 42 "$I08"
echo "COOLDOWN $(date +%T)"; sleep 120
# ---- A/B 1024 (ABBA on E05, then E08c) ----
zsh research/qwen/run_edit.sh M5-1024-E05-P0a mem:P0 "$E05" 1024 42 "$I05"; sleep 20
zsh research/qwen/run_edit.sh M5-1024-E05-P2a mem:P2 "$E05" 1024 42 "$I05"; sleep 20
zsh research/qwen/run_edit.sh M5-1024-E05-P2b mem:P2 "$E05" 1024 42 "$I05"; sleep 20
zsh research/qwen/run_edit.sh M5-1024-E05-P0b mem:P0 "$E05" 1024 42 "$I05"; sleep 20
zsh research/qwen/run_edit.sh M5-1024-E08c-P2 mem:P2 "$E08C" 1024 42 "$I08"; sleep 20
zsh research/qwen/run_edit.sh M5-1024-E08c-P0 mem:P0 "$E08C" 1024 42 "$I08"
echo "MEMCHAIN_DONE $(date)"
}
main "$@"; exit $?   # exit here: never read past this line, even if the file grows mid-run
