#!/bin/zsh
for R in 768 1024; do
  zsh ~/Dev/photo-gen/research/qrun.sh qw-p-$R $R $R "a red apple on a wooden table, soft window light" on
  python3 ~/Dev/photo-gen/research/record.py qw-p-$R ~/Dev/photo-gen/research/qwen-bench-clean.csv qwen ${R}x${R} 25 1 1 apple "PENDING" "Qwen PRIMARY CONTROL (Metal tensor API = enabled); clean conditions"
  python3 - $R <<'PY'
import csv,sys
r="qw-p-"+sys.argv[1]; rows=list(csv.DictReader(open(f"/Users/nckandrw/Dev/photo-gen/research/runs/{r}/monitor.csv"))); lv=[int(float(x['pressure_level'])) for x in rows]
print(r,"n",len(rows),"L1",lv.count(1),"L2",lv.count(2),"L4",lv.count(4),"wired max",max(float(x['wired_gb']) for x in rows),"swap",rows[0]['swap_used_mb'],"->",max(float(x['swap_used_mb']) for x in rows))
PY
done
echo QWEN_DONE
