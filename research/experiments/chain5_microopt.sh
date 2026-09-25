#!/bin/zsh
# After chain4: micro-opt attribution — SDPA mask=None vs the model's all-zeros additive mask, bf16 stream, ABBA.
cd ~/Dev/photo-gen/research/experiments
until grep -q CHAIN4_DONE chain4-console.log 2>/dev/null; do sleep 30; done
echo "[$(date +%T)] micro-opt mask-none"
python3 ab_runner.py microopt/jobs.json microopt/results.jsonl
echo CHAIN5_DONE
