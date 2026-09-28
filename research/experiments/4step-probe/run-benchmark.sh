#!/bin/zsh
# 4-step probe benchmark: cold A, B, C (each after 600 s idle), then 72 sustained runs (6-permutation rotation).
# Marker: PROBE_BENCH_DONE. Resumable (prod_runner skips done tags).
E=~/Dev/photo-gen/research/experiments; PY=~/Dev/photo-gen/mflux/.venv/bin/python3.12; cd $E
export PRODRUNNER_WORKER_SCRIPT=$E/4step-probe/probe_worker.py
echo "[$(date +%T)] PROBE start"; pmset -g batt | head -1
n=$($PY -c "import json;print(len(json.load(open('4step-probe/jobs-cold.json'))))")
for i in $(seq 0 $((n-1))); do
  echo "[$(date +%T)] idle 600 s before cold job $i"; sleep 600
  $PY -c "import json;j=json.load(open('4step-probe/jobs-cold.json'));json.dump([j[$i]],open('4step-probe/cold-one.json','w'))"
  $PY prod_runner.py 4step-probe/cold-one.json 4step-probe/results-cold.jsonl 4step-probe/work-cold
done
echo "[$(date +%T)] sustained benchmark"
$PY prod_runner.py 4step-probe/jobs-bench.json 4step-probe/results-bench.jsonl 4step-probe/work-bench
echo "[$(date +%T)] PROBE_BENCH_DONE"
