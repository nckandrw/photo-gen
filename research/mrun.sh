#!/bin/zsh
# MFLUX Z-Image-Turbo run with the same monitoring as sd.cpp runs.
# Usage: zsh research/mrun.sh <run-id> <W> <H> <prompt> [extra mflux args...]
set -uo pipefail
id=$1 W=$2 H=$3 P=$4; shift 4
root=~/Dev/photo-gen; dir=$root/research/runs/$id; mkdir -p $dir
source $root/mflux/env.sh
export HF_HUB_OFFLINE=1 ZI_PHASES=$dir/phases.json
PY=$root/mflux/.venv/bin/python3.12
args=(--model $root/models/mflux/z-image-turbo-mflux-q4 --base-model z-image-turbo --prompt "$P" --width $W --height $H --steps 9 --seed 42 ${LOWRAM_FLAG---low-ram} --output $root/outputs/$id.png "$@")
print -r -- "$PY $root/mflux/zi_driver.py ${(q)args[@]}" > $dir/cmd.txt
zsh $root/research/monitor.sh $dir/monitor.csv python3.12 1 &
mon=$!
{ print "START $(date +%FT%T)"; pmset -g therm; sysctl vm.swapusage; memory_pressure | tail -1; pmset -g batt | head -1; } > $dir/pre.txt 2>&1
/usr/bin/time -l $PY $root/mflux/zi_driver.py "${args[@]}" > $dir/mflux.log 2> $dir/stderr.log
rc=$?
sleep 2; kill $mon 2>/dev/null
{ print "END $(date +%FT%T) rc=$rc"; pmset -g therm; sysctl vm.swapusage; memory_pressure | tail -1; } > $dir/post.txt 2>&1
python3 - "$dir" "$rc" <<'PY'
import csv,sys,re,json
d,rc=sys.argv[1],sys.argv[2]
rows=list(csv.DictReader(open(f"{d}/monitor.csv"))); err=open(f"{d}/stderr.log").read()
f=lambda k:[float(r[k]) for r in rows if r[k] not in ("",None)]
lv=[int(float(x)) for x in f("pressure_level")]
m=lambda p:(re.search(p,err) or [None,None])[1]
ph=json.load(open(f"{d}/phases.json")) if rc=="0" else {}
s={"rc":rc,"samples":len(rows),"wall_s":m(r"([\d.]+) real"),"time_l_peak_footprint_gb":round(int(m(r"(\d+)\s+peak memory footprint") or 0)/1e9,2),
   "time_l_max_rss_gb":round(int(m(r"(\d+)\s+maximum resident set size") or 0)/1e9,2),
   "pressure_L2":lv.count(2),"pressure_L4":lv.count(4),"min_free_pct":min(f("free_pct")),
   "swap_start_mb":rows[0]["swap_used_mb"],"peak_swap_mb":max(f("swap_used_mb")),"wired_max_gb":max(f("wired_gb")),"peak_compressed_gb":max(f("compressed_gb"))}
for k,v in ph.get("phases",{}).items(): s[k]=v[0]
for k in ("denoise_sec_derived","process_wall_sec","torch_imported","torch_mps_allocated_bytes","mlx_version","device"): s[k]=ph.get(k)
open(f"{d}/summary.txt","w").write("\n".join(f"{k}={v}" for k,v in s.items())+"\n")
print("\n".join(f"{k}={v}" for k,v in s.items()))
PY
python3 $root/research/imgcheck.py $root/outputs/$id.png 2>&1
