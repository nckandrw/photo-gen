#!/bin/zsh
# 768² BALANCED confirmation: 32 pairs (16 prompts x seeds 3141/9091), ABBA, sustained. Marker: CONFIRM768_GEN_DONE
E=~/Dev/photo-gen/research/experiments; PY=~/Dev/photo-gen/mflux/.venv/bin/python3.12; G=step-count-quality-gate; cd $E
echo "[$(date '+%F %T')] CONFIRM768 start"; pmset -g batt | head -1
$PY prod_runner.py $G/jobs-K768.json $G/results-K768.jsonl $G/work-K768
echo "[$(date '+%F %T')] CONFIRM768_GEN_DONE"
