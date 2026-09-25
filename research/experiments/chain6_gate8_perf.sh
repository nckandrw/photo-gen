#!/bin/zsh
# After the memfix gate: (1) 8-step blinded-gate generation (bf16 9 vs 8, production worker, ABBA);
# (2) cold runs, each after 10 min idle; (3) sustained performance map. Nothing else should use the GPU meanwhile.
E=~/Dev/photo-gen/research/experiments; PY=~/Dev/photo-gen/mflux/.venv/bin/python3.12; cd $E
until grep -q RUNNER_DONE memfix-console.log 2>/dev/null; do sleep 20; done
echo "[$(date +%T)] gate8 generation"
$PY prod_runner.py gate8/jobs.json gate8/results.jsonl gate8/work
echo "[$(date +%T)] cold runs"
n=$($PY -c "import json;print(len(json.load(open('perfmap/cold-jobs.json'))))")
for i in $(seq 0 $((n-1))); do
  echo "[$(date +%T)] idle 600 s before cold job $i"; sleep 600
  $PY -c "import json;j=json.load(open('perfmap/cold-jobs.json'));json.dump([j[$i]],open('perfmap/cold-one.json','w'))"
  $PY prod_runner.py perfmap/cold-one.json perfmap/cold-results.jsonl perfmap/work
done
echo "[$(date +%T)] sustained map"
$PY prod_runner.py perfmap/sustained-jobs.json perfmap/sustained-results.jsonl perfmap/work
echo CHAIN6_DONE
