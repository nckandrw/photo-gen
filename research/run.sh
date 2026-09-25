#!/bin/zsh
# Runs one sd-cli test with monitoring. Everything is logged under research/runs/<id>/.
# Usage: zsh research/run.sh <run-id> <sd-cli args...>
set -uo pipefail
id=$1; shift
root=~/Dev/photo-gen
dir=$root/research/runs/$id
mkdir -p $dir
bin=$root/sdcpp/master-908-88411ef/sd-cli
print -r -- "$bin ${(q)@}" > $dir/cmd.txt
zsh $root/research/monitor.sh $dir/monitor.csv sd-cli 1 &
mon=$!
{ print "START $(date +%FT%T)"; pmset -g therm; sysctl vm.swapusage; memory_pressure | tail -1; } > $dir/pre.txt 2>&1
start=$(date +%s.%N 2>/dev/null || python3 -c 'import time;print(time.time())')
/usr/bin/time -l $bin "$@" > $dir/sd-cli.log 2> $dir/stderr.log
rc=$?
end=$(python3 -c 'import time;print(time.time())')
sleep 2; kill $mon 2>/dev/null
{ print "END $(date +%FT%T) rc=$rc"; pmset -g therm; sysctl vm.swapusage; memory_pressure | tail -1; } > $dir/post.txt 2>&1
python3 - "$dir" "$rc" <<'EOF'
import csv,sys,re,os
d,rc=sys.argv[1],sys.argv[2]
rows=list(csv.DictReader(open(f"{d}/monitor.csv")))
def mx(k):
    v=[float(r[k]) for r in rows if r[k] not in ("",None)]
    return max(v) if v else None
def mn(k):
    v=[float(r[k]) for r in rows if r[k] not in ("",None)]
    return min(v) if v else None
err=open(f"{d}/stderr.log").read()
m=re.search(r"(\d+)\s+maximum resident set size",err)
pf=re.search(r"(\d+)\s+peak memory footprint",err)
real=re.search(r"([\d.]+) real",err)
s={"rc":rc,"samples":len(rows),
   "wall_s":real and float(real.group(1)),
   "time_l_max_rss_gb":m and round(int(m.group(1))/1e9,2),
   "time_l_peak_footprint_gb":pf and round(int(pf.group(1))/1e9,2),
   "mon_peak_proc_mem_gb":mx("proc_mem_gb"),"mon_peak_proc_rss_gb":mx("proc_rss_gb"),
   "peak_pressure_level":mx("pressure_level"),"min_free_pct":mn("free_pct"),
   "swap_start_mb":rows and rows[0]["swap_used_mb"],"peak_swap_mb":mx("swap_used_mb"),
   "compressed_start_gb":rows and rows[0]["compressed_gb"],"peak_compressed_gb":mx("compressed_gb"),
   "min_cpu_speed_limit":mn("cpu_speed_limit")}
open(f"{d}/summary.txt","w").write("\n".join(f"{k}={v}" for k,v in s.items())+"\n")
print("\n".join(f"{k}={v}" for k,v in s.items()))
EOF
