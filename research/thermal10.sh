#!/bin/zsh
for i in $(seq 1 10); do
  zsh ~/Dev/photo-gen/research/zrun.sh zi-th10-r$i 1024 1024 "a red apple on a wooden table, soft window light" > /dev/null 2>&1
  python3 ~/Dev/photo-gen/research/record.py zi-th10-r$i ~/Dev/photo-gen/research/z-image-bench.csv zimage 1024x1024 9 0 1 apple "THERMAL-10 run $i" "Z-Image PRIMARY + #1990 WORKAROUND; consecutive, no cooldown; VAE-OOM-fallback expected"
  cmp -s ~/Dev/photo-gen/outputs/zi-th10-r$i.png ~/Dev/photo-gen/outputs/zi-p-1024.png && echo "r$i identical" || echo "r$i DIFFERS"
done
echo THERMAL10_DONE
