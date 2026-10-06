#!/bin/zsh
# Real end-to-end API check of the edit task through serve (Phase 4 closure). Marker: APICHECK_DONE
main() {
cd ~/Dev/photo-gen
local OUT=research/qwen/api-check; mkdir -p $OUT
{ date; pmset -g batt | head -1; sysctl vm.swapusage; echo "git_head=$(git rev-parse HEAD)"; git status --porcelain app config; } > $OUT/conditions.txt
bin/photo-gen serve > $OUT/serve.log 2>&1 &
local SRV=$!
for i in {1..120}; do curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8765/health | grep -q 200 && break; sleep 1; done
curl -s http://127.0.0.1:8765/health > $OUT/health.json
# 1) real POST /edit: must reproduce G0-512-E05 (bd548f1b...)
local J1=$(curl -s -X POST http://127.0.0.1:8765/edit -H 'Content-Type: application/json' -d '{"image": "/Users/nckandrw/Dev/photo-gen/data/outputs/2026/10/06/20261006T170025Z-9f37b9-editsrc-E05-s1505.png", "prompt": "Change the background to a sunset beach", "output_resolution": 512, "seed": 42, "allow_experimental": true}' | tee $OUT/edit-submit.json | python3 -c 'import json,sys; print(json.load(sys.stdin)["job_id"])')
curl -s "http://127.0.0.1:8765/jobs/$J1?wait=900" > $OUT/edit-job.json
curl -s -o $OUT/edit-output.png "http://127.0.0.1:8765/outputs/$J1"
# 2) real cancel of a running edit
local J2=$(curl -s -X POST http://127.0.0.1:8765/edit -H 'Content-Type: application/json' -d '{"image": "/Users/nckandrw/Dev/photo-gen/data/outputs/2026/10/06/20261006T165054Z-9afd59-editsrc-E01-s1101.png", "prompt": "Change the red car to a blue motorcycle while preserving the street, lighting, perspective, and all other objects.", "output_resolution": 512, "seed": 42, "allow_experimental": true}' | python3 -c 'import json,sys; print(json.load(sys.stdin)["job_id"])')
for i in {1..60}; do curl -s "http://127.0.0.1:8765/jobs/$J2" | grep -q '"status": "running"' && break; sleep 1; done
sleep 20
{ echo "before cancel: $(date +%T)"; pgrep -fl mflux_qwen_edit_worker; } > $OUT/cancel-trace.txt
curl -s -X POST "http://127.0.0.1:8765/jobs/$J2/cancel" -H 'Content-Type: application/json' -d '{}' > $OUT/cancel-response.json
sleep 3
{ echo "after cancel: $(date +%T)"; echo "worker processes:"; pgrep -fl mflux_qwen_edit_worker || echo "(none)"; } >> $OUT/cancel-trace.txt
curl -s "http://127.0.0.1:8765/jobs/$J2" > $OUT/cancel-job.json
curl -s http://127.0.0.1:8765/status > $OUT/status-after-cancel.json
# 3) the queue still works: ULTRA 512 p01 (6aa2b842...)
local J3=$(curl -s -X POST http://127.0.0.1:8765/generate -H 'Content-Type: application/json' -d '{"prompt": "a red apple on a wooden table, soft window light", "profile": "ultra", "width": 512, "height": 512, "seed": 42}' | python3 -c 'import json,sys; print(json.load(sys.stdin)["job_id"])')
curl -s "http://127.0.0.1:8765/jobs/$J3?wait=600" > $OUT/ultra-job.json
kill -TERM $SRV; wait $SRV
echo "APICHECK_DONE $(date +%T)"
}
main "$@"; exit $?
