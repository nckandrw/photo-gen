#!/bin/zsh
# Stage B: 3 cold runs (5-step) (each after 600 s idle), then 3 sustained ABBA blocks (512, 768, 1024). Marker: STAGE_B_GEN_DONE
E=~/Dev/photo-gen/research/experiments; PY=~/Dev/photo-gen/mflux/.venv/bin/python3.12; G=step-count-quality-gate; cd $E
echo "[$(date '+%F %T')] STAGE B start"; pmset -g batt | head -1
n=$($PY -c "import json;print(len(json.load(open('$G/jobs-B-cold.json'))))")
for i in $(seq 0 $((n-1))); do
  tag=$($PY -c "import json;print(json.load(open('$G/jobs-B-cold.json'))[$i]['tag'])")
  if grep -q "\"$tag\"" $G/results-B-cold.jsonl 2>/dev/null; then echo "skip $tag"; continue; fi
  echo "[$(date +%T)] idle 600 s before $tag"; sleep 600
  $PY -c "import json;j=json.load(open('$G/jobs-B-cold.json'));json.dump([j[$i]],open('$G/cold-one.json','w'))"
  $PY prod_runner.py $G/cold-one.json $G/results-B-cold.jsonl $G/work-B-cold
done
for r in 512 768 1024; do
  echo "[$(date +%T)] Stage B sustained $r"
  $PY prod_runner.py $G/jobs-B-$r.json $G/results-B-$r.jsonl $G/work-B-$r
done
echo "[$(date '+%F %T')] STAGE_B_GEN_DONE"
