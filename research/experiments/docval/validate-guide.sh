#!/bin/zsh
# Runs the generating commands documented in docs/photo-gen-guide.html, verbatim, and checks pixel hashes
# against the regression hashes. Run only while no research chain is using the GPU.
cd ~/Dev/photo-gen
P="a red apple on a wooden table, soft window light"
echo "== [1] CLI FAST (First image section) $(date +%T)"
bin/photo-gen generate -p "$P" --profile fast --seed 42 2>&1 | tail -4
echo "== [2] CLI REFERENCE, no profile flags, 512² $(date +%T)"
bin/photo-gen generate -p "$P" --width 512 --height 512 --seed 42 2>&1 | tail -4
echo "== [3] HTTP: serve, POST /generate, GET /jobs/{id}?wait, GET /outputs/{id} $(date +%T)"
bin/photo-gen serve > research/experiments/docval/serve.log 2>&1 &
for i in $(seq 1 60); do curl -s -o /dev/null http://127.0.0.1:8765/health && break; sleep 0.5; done
R=$(curl -s -X POST http://127.0.0.1:8765/generate -H 'Content-Type: application/json' \
     -d "{\"prompt\":\"$P\",\"profile\":\"reference\",\"width\":512,\"height\":512,\"seed\":42}")
echo "$R" | python3 -c "import sys,json;j=json.load(sys.stdin);print('POST ->', j['status'], j['job_id'], j['request']['profile'], j['request']['precision'], j['request']['steps'])"
JID=$(echo "$R" | python3 -c "import sys,json;print(json.load(sys.stdin)['job_id'])")
curl -s "http://127.0.0.1:8765/jobs/$JID?wait=300" | python3 -c "import sys,json;j=json.load(sys.stdin);print('GET wait ->', j['status'], j['pixel_sha256'], j['generation_seconds'], j['output_path'])"
curl -s -o research/experiments/docval/api-output.png -w "GET /outputs -> HTTP %{http_code} %{content_type} %{size_download}B\n" http://127.0.0.1:8765/outputs/$JID
kill -TERM %1; sleep 2
echo "== done $(date +%T)"
echo "expected: [1] 7b45cfbe…  [2] 9ae59f59…  [3] 9ae59f59…"
