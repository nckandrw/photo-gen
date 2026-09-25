#!/bin/zsh
# E02 controlled A/B: each timed run starts after a 10-min idle cooldown. Same harness for both arms.
R=~/Dev/photo-gen; E=$R/research/experiments; source $R/mflux/env.sh; PY=$R/mflux/.venv/bin/python3.12
P="a red apple on a wooden table, soft window light"
run() { local tag=$1; shift; echo "[$(date +%T)] start $tag"; /usr/bin/time -l $PY $E/e02_bf16_hidden_stream.py "$@" 2> $E/e02ab-$tag.stderr | grep E02RESULT > $E/e02ab-$tag.json; grep "peak memory footprint" $E/e02ab-$tag.stderr; tr '\r' '\n' < $E/e02ab-$tag.stderr | grep -oE "[0-9.]+s/it\]" | tr '\n' ' ' > $E/e02ab-$tag.steps; cat $E/e02ab-$tag.json; echo; }
run neon-bf16 $E/e02ab-neon-bf16.png 'A neon sign in a dark cyberpunk alley reading "QWEN IMAGE 2.1", clearly legible.' --rope-cast
echo "[$(date +%T)] cooldown 600s"; sleep 600; pmset -g therm | head -1
run apple-fp32-baseline $E/e02ab-apple-fp32.png "$P" --baseline
echo "[$(date +%T)] cooldown 600s"; sleep 600; pmset -g therm | head -1
run apple-bf16 $E/e02ab-apple-bf16.png "$P" --rope-cast
echo E02AB_DONE
