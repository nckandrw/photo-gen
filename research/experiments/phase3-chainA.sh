#!/bin/zsh
# Phase 3 chain A (phase3-plan.md): 768² cold REFERENCE/FAST (each after 600 s idle) -> sigma audit A/B
# (512, 768, 1024 sanity) -> FAST gates G512, G768 -> G1024-direct. Sequential; nothing else uses the GPU.
# Resumable: prod_runner skips tags already in the results JSONL. Completion marker: PHASE3A_DONE
E=~/Dev/photo-gen/research/experiments; PY=~/Dev/photo-gen/mflux/.venv/bin/python3.12; cd $E
echo "[$(date +%T)] PHASE3A start"; pmset -g batt | head -2
for t in ref fast; do
  if ! grep -q "cold-768" perfmap/cold768-results.jsonl 2>/dev/null || ! grep -q "\"cold-768-$([ $t = ref ] && echo fp32-st9 || echo bf16-st8)\"" perfmap/cold768-results.jsonl; then
    echo "[$(date +%T)] idle 600 s before cold 768 $t"; sleep 600
    $PY prod_runner.py perfmap/jobs-cold768-$t.json perfmap/cold768-results.jsonl perfmap/work-cold768
  fi
done
for r in 512 768 1024; do
  echo "[$(date +%T)] sigma audit $r"
  PRODRUNNER_WORKER_SCRIPT=$E/sigma_worker.py $PY prod_runner.py sigma/jobs-$r.json sigma/results-$r.jsonl sigma/work-$r
done
echo SIGMA_AB_DONE
for r in 512 768 1024; do
  echo "[$(date +%T)] FAST gate $r"
  $PY prod_runner.py fastgate/jobs-$r.json fastgate/results-$r.jsonl fastgate/work-$r
  echo "GATE_${r}_GEN_DONE"
done
echo "[$(date +%T)] PHASE3A_DONE"
