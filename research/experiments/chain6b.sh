#!/bin/zsh
# Re-sequenced after D5 (blind contamination of seed 42): wait for the running gate8 runner (pid 75369),
# then the seed-1234 block, then cold runs (each after 600 s idle), sustained map, E10 dtype ablation.
E=~/Dev/photo-gen/research/experiments; PY=~/Dev/photo-gen/mflux/.venv/bin/python3.12; cd $E
while kill -0 75369 2>/dev/null; do sleep 15; done
echo "[$(date +%T)] gate8 seeds 42/7 runner finished; seed-1234 block"
$PY prod_runner.py gate8/jobs-s1234.json gate8/results.jsonl gate8/work
echo "[$(date +%T)] cold runs"
n=$($PY -c "import json;print(len(json.load(open('perfmap/cold-jobs.json'))))")
for i in $(seq 0 $((n-1))); do
  echo "[$(date +%T)] idle 600 s before cold job $i"; sleep 600
  $PY -c "import json;j=json.load(open('perfmap/cold-jobs.json'));json.dump([j[$i]],open('perfmap/cold-one.json','w'))"
  $PY prod_runner.py perfmap/cold-one.json perfmap/cold-results.jsonl perfmap/work
done
echo "[$(date +%T)] sustained map"
$PY prod_runner.py perfmap/sustained-jobs.json perfmap/sustained-results.jsonl perfmap/work
echo "[$(date +%T)] E10 promotion ablation"
for v in none pad temb rope temb+rope pad+temb+rope; do
  HF_HUB_OFFLINE=1 HF_HOME=~/Dev/photo-gen/mflux/hf $PY e10_promotion_ablation.py $v e10/$v.json 2>e10/$v.stderr | tail -1
done
echo CHAIN6B_DONE
