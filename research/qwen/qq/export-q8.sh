#!/bin/zsh
# Phase 6 Q-Q export chain (research/qwen/qq/PROTOCOL.md §3). Sequential steps, each under the 1 Hz monitor and the
# Phase 4 watchdog (abort if swap grows by > 6144 MB over its start, or 20 consecutive critical-pressure samples; the
# python child is signalled too, incident 2026-10-07 00:05). Stops at the first failed step.
# Markers: QQ_EXPORT_DONE / QQ_EXPORT_FAILED <step> / QQ_EXPORT_ABORTED <step>.
# Run as a top-level: nohup zsh research/qwen/qq/export-q8.sh > research/qwen/qq/export/export-chain.log 2>&1 < /dev/null & disown
main() {
set -u
cd ~/Dev/photo-gen && source mflux/env.sh
export HF_HUB_OFFLINE=1
SRC=models/research/qwen-image-2.1
CANON=models/qwen/qwen-image-2.1-edit-mflux-q4
STAGE=models/research/qq-staging
OUT=research/qwen/qq/export
PY=mflux-qwen/.venv/bin/python3.12
T=research/qwen/qq/export_q8_split.py
mkdir -p $OUT $STAGE
echo "QQ_EXPORT_START $(date) git=$(git rev-parse HEAD) $(pmset -g batt | head -1)"
step() {  # step <name> <args...>
  local name=$1; shift
  if [[ -e $OUT/$name.json ]]; then echo "[$(date +%T)] step $name already recorded ($OUT/$name.json); skipped"; return 0; fi
  if [[ -e $OUT/$name-stdout.log ]]; then echo "refusing: $OUT/$name-stdout.log exists (move an earlier attempt's logs aside)"; return 3; fi
  zsh research/monitor.sh $OUT/$name-monitor.csv python3.12 1 &
  local MON=$!
  local swap0=$(sysctl -n vm.swapusage | awk '{gsub("M","",$6);print int($6)}')
  echo "[$(date +%T)] step $name start; swap0=${swap0}MB"
  /usr/bin/time -l $PY $T "$@" $OUT/$name.json > $OUT/$name-stdout.log 2> $OUT/$name-time.txt &
  local PID=$! crit=0 aborted=0 sw pl
  while kill -0 $PID 2>/dev/null; do
    sw=$(sysctl -n vm.swapusage | awk '{gsub("M","",$6);print int($6)}')
    pl=$(sysctl -n kern.memorystatus_vm_pressure_level)
    if (( pl == 4 )); then (( crit++ )); else crit=0; fi
    if (( sw - swap0 > 6144 || crit >= 20 )); then
      echo "[$(date +%T)] ABORT $name: swap ${sw}MB (start ${swap0}MB), critical streak ${crit}"
      pkill -TERM -P $PID; kill -TERM $PID; sleep 5; pkill -KILL -P $PID 2>/dev/null; kill -KILL $PID 2>/dev/null
      aborted=1; break
    fi
    sleep 1
  done
  wait $PID; local rc=$?
  kill $MON 2>/dev/null
  echo "[$(date +%T)] step $name rc=$rc aborted=$aborted swap_end=$(sysctl -n vm.swapusage | awk '{print $6}')"
  if (( aborted )); then echo "QQ_EXPORT_ABORTED $name"; return 1; fi
  if (( rc != 0 )); then echo "QQ_EXPORT_FAILED $name"; return 1; fi
  sleep 20
  return 0
}
step qerr-transformer qerr $SRC transformer 8 || return 1
step qerr-text_encoder qerr $SRC text_encoder 8 || return 1
step check-q4-vae-transformer check $SRC $CANON 4 vae,transformer || return 1
step check-q4-text_encoder check $SRC $CANON 4 text_encoder || return 1
step export-q8-vae-transformer export $SRC $STAGE/q8-part-vae-transformer 8 vae,transformer || return 1
step export-q8-text_encoder export $SRC $STAGE/q8-part-text_encoder 8 text_encoder || return 1
echo "QQ_EXPORT_DONE $(date)"
}
main "$@"; exit $?   # exit here: never read past this line, even if the file grows mid-run
