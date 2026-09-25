#!/bin/zsh
# 3 consecutive identical Z-Image 1024² runs, no cooldown between runs.
for i in 1 2 3; do
  zsh ~/Dev/photo-gen/research/zrun.sh zi-th3-r$i 1024 1024 "a red apple on a wooden table, soft window light" > /dev/null 2>&1
  python3 ~/Dev/photo-gen/research/record.py zi-th3-r$i ~/Dev/photo-gen/research/z-image-bench.csv zimage 1024x1024 9 0 1 apple "THERMAL-3 run $i" "Z-Image PRIMARY + #1990 WORKAROUND; consecutive, no cooldown"
  pmset -g therm | tr '\n' ' '; echo
done
echo THERMAL3_DONE
