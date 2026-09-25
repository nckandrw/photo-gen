#!/bin/zsh
# After chain2: (1) photo-gen parity for the new opt-in bf16 path + fp32 default regression check,
# (2) bf16 step sweep 8..4 (12 prompts x seed 42; 9-step bf16 references are bf16ab/pXX-s42-bf16.png).
R=~/Dev/photo-gen; E=$R/research/experiments; cd $E
until grep -q CHAIN2_DONE chain2-console.log 2>/dev/null; do sleep 30; done
mkdir -p parity-bf16
P01='a red apple on a wooden table, soft window light'
P05='A neon sign in a dark cyberpunk alley reading "QWEN IMAGE 2.1", clearly legible.'
echo "[$(date +%T)] photo-gen parity"
$R/bin/photo-gen generate --prompt "$P01" --seed 42 --precision bf16 --output-name parity-bf16-p01 --json > parity-bf16/p01-bf16.json 2> parity-bf16/p01-bf16.err
$R/bin/photo-gen generate --prompt "$P05" --seed 42 --precision bf16 --output-name parity-bf16-p05 --json > parity-bf16/p05-bf16.json 2> parity-bf16/p05-bf16.err
$R/bin/photo-gen generate --prompt "$P01" --seed 42 --output-name parity-fp32-default-p01 --json > parity-bf16/p01-fp32-default.json 2> parity-bf16/p01-fp32-default.err
python3 - <<'PY'
import json
exp={"p01-bf16":"11b19277f7fd077d528d4e282a77bd9c90f3af3adf26555cf11d2f02760d520a",
     "p05-bf16":"7bfd59cad5aca39070d0fe00e794fe04af280546469b25b0d48dc3bc737abf54",
     "p01-fp32-default":"fe47d88dfb4bec549060c29c527eeff280d863e8e12176cdc1c28d3d8003a118"}
out={}
for k,v in exp.items():
    try:
        j=json.load(open(f"parity-bf16/{k}.json")); got=j.get("pixel_sha256")
    except Exception as e:
        got=f"ERROR {e}"; j={}
    out[k]={"expected":v,"got":got,"match":got==v,"status":j.get("status"),"generation_seconds":j.get("generation_seconds")}
json.dump(out,open("parity-bf16/summary.json","w"),indent=1); print(json.dumps(out,indent=1))
PY
echo "[$(date +%T)] step sweep"
python3 ab_runner.py stepsweep/jobs.json stepsweep/results.jsonl
echo CHAIN3_DONE
