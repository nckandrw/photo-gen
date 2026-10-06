#!/bin/zsh
# One-time q4 export (QWEN-SOURCE-AUDIT.md §10). Marker: QWEN_EXPORT_DONE / QWEN_EXPORT_FAILED / QWEN_EXPORT_ABORTED.
# Abort thresholds (declared before the run): swap grows by > 6144 MB over its starting value, OR the kernel memory
# pressure level is critical (4) for 20 consecutive 1 s samples. On abort the export (time + its python child) is killed.
cd ~/Dev/photo-gen && source mflux/env.sh
export HF_HUB_OFFLINE=1
SRC=models/research/qwen-image-2.1
DST=models/qwen/qwen-image-2.1-edit-mflux-q4
OUT=research/qwen/export/${RUN:-run2}   # each run keeps its own logs (never overwritten)
mkdir -p models/qwen $OUT
zsh research/monitor.sh $OUT/export-monitor.csv python3.12 1 &
MON=$!
swap0=$(sysctl -n vm.swapusage | awk '{gsub("M","",$6);print int($6)}')
echo "[$(date +%T)] start export; swap0=${swap0}MB; $(pmset -g batt | head -1)"
/usr/bin/time -l mflux-qwen/.venv/bin/python3.12 research/qwen/export_q4.py $SRC $DST > $OUT/export-stdout.log 2> $OUT/export-time.txt &
PID=$!
crit=0; aborted=0
while kill -0 $PID 2>/dev/null; do
  sw=$(sysctl -n vm.swapusage | awk '{gsub("M","",$6);print int($6)}')
  pl=$(sysctl -n kern.memorystatus_vm_pressure_level)
  if (( pl == 4 )); then (( crit++ )); else crit=0; fi
  if (( sw - swap0 > 6144 || crit >= 20 )); then
    echo "[$(date +%T)] ABORT: swap ${sw}MB (start ${swap0}MB), critical streak ${crit}"
    # kill the python child too: PID is /usr/bin/time, and signalling only it orphans the export (incident
    # 2026-10-07 00:05, research/qwen/INCIDENTS.md)
    pkill -TERM -P $PID; kill -TERM $PID; sleep 5; pkill -KILL -P $PID 2>/dev/null; kill -KILL $PID 2>/dev/null
    aborted=1; break
  fi
  sleep 1
done
wait $PID; rc=$?
kill $MON 2>/dev/null
echo "[$(date +%T)] exit rc=$rc; swap now $(sysctl -n vm.swapusage | awk '{print $6}')"
if (( aborted )); then echo QWEN_EXPORT_ABORTED; elif (( rc == 0 )); then echo QWEN_EXPORT_DONE; else echo QWEN_EXPORT_FAILED; fi
