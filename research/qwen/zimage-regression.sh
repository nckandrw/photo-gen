#!/bin/zsh
# Phase 4 Z-Image regression through the REFACTORED app (task router, runtime-owned sidecar, edit backend wired in).
# Expected pixel sha256 (CLAUDE.md, p01 "a red apple on a wooden table, soft window light", seed 42):
#   REFERENCE 1024 fe47d88d, FAST 1024 7b45cfbe, BALANCED 1024 befe1b3c, ULTRA 512 6aa2b842; API REFERENCE 512 9ae59f59.
# Evidence: research/qwen/zimage-regression/. Marker: ZREG_DONE
main() {
cd ~/Dev/photo-gen
local OUT=research/qwen/zimage-regression P="a red apple on a wooden table, soft window light"
mkdir -p $OUT
{ date; pmset -g batt | head -1; sysctl vm.swapusage; echo "git_head=$(git rev-parse HEAD)"; git status --porcelain app config; } > $OUT/conditions.txt
bin/photo-gen generate -p "$P" --seed 42 --profile reference --json > $OUT/cli-reference-1024.json 2> $OUT/cli-reference-1024.log; sleep 10
bin/photo-gen generate -p "$P" --seed 42 --profile fast --json > $OUT/cli-fast-1024.json 2> $OUT/cli-fast-1024.log; sleep 10
bin/photo-gen generate -p "$P" --seed 42 --profile balanced --json > $OUT/cli-balanced-1024.json 2> $OUT/cli-balanced-1024.log; sleep 10
bin/photo-gen generate -p "$P" --seed 42 --profile ultra --width 512 --height 512 --json > $OUT/cli-ultra-512.json 2> $OUT/cli-ultra-512.log; sleep 10
bin/photo-gen serve > $OUT/serve.log 2>&1 &
local SRV=$!
for i in {1..120}; do curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8765/health | grep -q 200 && break; sleep 1; done
curl -s http://127.0.0.1:8765/health > $OUT/api-health.json
curl -s http://127.0.0.1:8765/capabilities > $OUT/api-capabilities.json
local JOB=$(curl -s -X POST http://127.0.0.1:8765/generate -H 'Content-Type: application/json' \
  -d "{\"prompt\": \"$P\", \"width\": 512, \"height\": 512, \"seed\": 42}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["job_id"])')
curl -s "http://127.0.0.1:8765/jobs/$JOB?wait=600" > $OUT/api-reference-512.json
kill -TERM $SRV; wait $SRV
echo "ZREG_DONE $(date +%T)"
}
main "$@"; exit $?
