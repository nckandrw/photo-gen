#!/bin/zsh
# Waits for the bf16 A/B runner to finish, then runs the queued GPU experiments sequentially.
cd ~/Dev/photo-gen/research/experiments
while pgrep -f "ab_runner.py bf16ab" >/dev/null; do sleep 20; done
echo "[$(date +%T)] A/B finished; starting VAE lifecycle"
python3 ab_runner.py vaelc/jobs.json vaelc/results.jsonl
echo "[$(date +%T)] starting cache audit"
python3 ab_runner.py audit/jobs.json audit/results.jsonl
echo "[$(date +%T)] starting E09 proxy"
~/Dev/photo-gen/mflux/.venv/bin/python3.12 e09_pruning_proxy.py > e09_pruning_proxy.json
cat e09_pruning_proxy.json
echo CHAIN_DONE
