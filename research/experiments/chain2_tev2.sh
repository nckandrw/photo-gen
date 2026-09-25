#!/bin/zsh
# After the GPU chain and the V2 download finish: convert heretic V2 -> MLX q4 (validated vs stock), then TE drift.
R=~/Dev/photo-gen; E=$R/research/experiments; PY=$R/mflux/.venv/bin/python3.12; cd $E
source $R/mflux/env.sh; export HF_HUB_OFFLINE=1
until grep -q CHAIN_DONE chain-console.log 2>/dev/null; do sleep 30; done
until [ -f $R/models/mflux/text-encoders/heretic-v2-src/model-00002-of-00002.safetensors ] && [ -f $R/models/mflux/text-encoders/heretic-v2-src/tokenizer_config.json ] && ! ls $R/models/mflux/text-encoders/heretic-v2-src/*.part >/dev/null 2>&1; do sleep 30; done
echo "[$(date +%T)] converting heretic V2 -> q4"
/usr/bin/time -l $PY convert_te_q4.py $R/models/mflux/text-encoders/heretic-v2-src $R/models/mflux/text-encoders/heretic-v2-q4 $R/models/mflux/z-image-turbo-mflux-q4/text_encoder tev2/convert-report.json 2> tev2/convert.stderr
grep "peak memory footprint" tev2/convert.stderr
echo "[$(date +%T)] TE drift"
$PY te_drift.py $R/models/mflux/z-image-turbo-mflux-q4 $R/models/mflux/text-encoders/heretic-v2-q4 tev2/drift-prompts.json tev2/drift.json 2>&1 | tail -14
echo CHAIN2_DONE
