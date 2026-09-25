#!/bin/zsh
# Samples system + target-process memory every INTERVAL seconds into a CSV until killed.
# Usage: zsh research/monitor.sh <out.csv> <exact-process-name> [interval=1]
# Columns:
#   pressure_level  kern.memorystatus_vm_pressure_level (1=normal/green, 2=warn/yellow, 4=critical/red)
#   free_pct        memory_pressure "System-wide memory free percentage"
#   swap_used_mb    vm.swapusage used
#   compressed_gb   pages occupied by compressor * 16 KiB
#   wired_gb        pages wired down * 16 KiB
#   proc_rss_gb     sum RSS of matching processes (ps)
#   proc_mem_gb     top's MEM (phys footprint, includes Metal shared buffers) of matching processes
#   cpu_speed_limit pmset -g therm CPU_Speed_Limit (100 = no throttling; blank = not reported)
out=$1 pat=$2 iv=${3:-1}
print "ts,epoch,pressure_level,free_pct,swap_used_mb,compressed_gb,wired_gb,proc_rss_gb,proc_mem_gb,cpu_speed_limit" > $out
while true; do
  ts=$(date +%T); ep=$(date +%s)
  pl=$(sysctl -n kern.memorystatus_vm_pressure_level)
  fp=$(memory_pressure 2>/dev/null | awk -F': ' '/free percentage/{gsub("%","",$2);print $2}')
  sw=$(sysctl -n vm.swapusage | awk '{gsub("M","",$6);print $6}')
  vs=$(vm_stat)
  cg=$(print "$vs" | awk '/occupied by compressor/{gsub("\\.","",$5);printf "%.2f",$5*16384/1e9}')
  wg=$(print "$vs" | awk '/wired down/{gsub("\\.","",$4);printf "%.2f",$4*16384/1e9}')
  pids=(${(f)"$(pgrep -x "$pat")"})
  rss=0; mem=0
  if [[ -n ${pids[1]:-} ]]; then
    rss=$(ps -o rss= -p ${(j:,:)pids} 2>/dev/null | awk '{s+=$1} END{printf "%.2f",s/1048576}')
    mem=$(for p in $pids; do top -l 1 -pid $p -stats mem 2>/dev/null | tail -1; done | awk '
      {v=$1; u=substr(v,length(v)); n=v+0; if(u=="G")n*=1024; else if(u=="K")n/=1024; else if(u=="B")n/=1048576; s+=n}
      END{printf "%.2f",s/1024}')
  fi
  th=$(pmset -g therm 2>/dev/null | awk -F'= ' '/CPU_Speed_Limit/{print $2}')
  print "$ts,$ep,$pl,$fp,$sw,$cg,$wg,$rss,$mem,$th" >> $out
  sleep $iv
done
