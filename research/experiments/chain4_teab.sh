#!/bin/zsh
# After chain3: align inv_freq in the heretic-v2 q4 TE, then the stock vs heretic-v2 image A/B (bf16, 512/1024, seed 42).
R=~/Dev/photo-gen; E=$R/research/experiments; PY=$R/mflux/.venv/bin/python3.12; cd $E
until grep -q CHAIN3_DONE chain3-console.log 2>/dev/null; do sleep 30; done
echo "[$(date +%T)] align inv_freq"
$PY align_inv_freq.py $R/models/mflux/z-image-turbo-mflux-q4/text_encoder $R/models/mflux/text-encoders/heretic-v2-q4
echo "[$(date +%T)] TE image A/B"
python3 ab_runner.py teab/jobs.json teab/results.jsonl
echo CHAIN4_DONE
