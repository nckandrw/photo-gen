#!/bin/zsh
# One monitored Phase 8 Q-VR step (PROTOCOL.md section 9). Never run two at once.
# Usage: zsh research/qwen/qv-reference/run_ref.sh <run_dir> <command...>
#   The command writes its own outputs into <run_dir>/data (the tools refuse an existing directory); this wrapper writes
#   <run_dir>/{conditions.txt, monitor.csv, console.log, wrap.txt}.
# Watchdog (declared in PROTOCOL.md section 9 before any run): kill and stop if swap grows by > 2048 MB over its value
# at the start of this step, OR the kernel memory-pressure level is critical (4) for 10 consecutive samples, OR the
# monitored python3.12 footprint (top MEM, the monitor's proc_mem_gb) exceeds 11 GB.
# Marker: REF_RUN_END <run_dir> rc=<rc> aborted=<0|1>. The body is one function, parsed in full before it runs.
main() {
set -u
cd ~/Dev/photo-gen
local OUT=$1; shift
if [[ -e $OUT ]]; then echo "refusing to overwrite $OUT"; return 3; fi
mkdir -p $OUT
{ echo "run_dir=$OUT"; echo "command=$*"; date; pmset -g batt | head -2
  sysctl vm.swapusage kern.memorystatus_vm_pressure_level; memory_pressure | grep "free percentage"
  pmset -g therm | grep -i -E "warning|limit"; ps -axo rss,comm | sort -rn | head -6
  echo "git_head=$(git rev-parse HEAD)"; echo "git_dirty(qv-reference tools, app, config):"
  git status --porcelain app config research/qwen/qv research/qwen/qv-reference/*.py research/qwen/qv-reference/*.sh
} > $OUT/conditions.txt 2>&1
zsh research/monitor.sh $OUT/monitor.csv python3.12 1 &
local MON=$!
local swap0=$(sysctl -n vm.swapusage | awk '{gsub("M","",$6);print int($6)}')
local t0=$(date +%s)
"$@" > $OUT/console.log 2>&1 &
local PID=$!
local crit=0 aborted=0 sw pl mem
while kill -0 $PID 2>/dev/null; do
  sw=$(sysctl -n vm.swapusage | awk '{gsub("M","",$6);print int($6)}')
  pl=$(sysctl -n kern.memorystatus_vm_pressure_level)
  mem=$(tail -1 $OUT/monitor.csv | awk -F, '{print $9+0}')
  if (( pl == 4 )); then (( crit++ )); else crit=0; fi
  if (( sw - swap0 > 2048 || crit >= 10 || mem > 11.0 )); then
    echo "ABORT $(date +%T): swap ${sw}MB (start ${swap0}MB), critical streak ${crit}, footprint ${mem} GB" | tee -a $OUT/conditions.txt
    kill $PID 2>/dev/null; pkill -f "qv-reference/(mlx_side|ref_side)\.py" 2>/dev/null
    aborted=1; break
  fi
  sleep 1
done
wait $PID 2>/dev/null; local rc=$?
kill $MON 2>/dev/null
local n=$(( $(wc -l < $OUT/monitor.csv) - 1 )) dt=$(( $(date +%s) - t0 ))
echo "wall_s=$dt rc=$rc aborted=$aborted swap_start_mb=$swap0 swap_end=$(sysctl -n vm.swapusage | awk '{print $6}') monitor_samples=$n" > $OUT/wrap.txt
echo "REF_RUN_END $OUT rc=$rc aborted=$aborted"
return $(( rc != 0 || aborted ))
}
main "$@"
