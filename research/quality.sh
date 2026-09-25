#!/bin/zsh
R=~/Dev/photo-gen/research
typeset -A P
P[desk]='A wooden desk with five distinct objects: a red notebook on the left, a black fountain pen in the center, a white ceramic mug behind the notebook, a small brass clock on the right, and a green plant in the far background. Soft morning light from the left.'
P[neon]='A neon sign in a dark cyberpunk alley reading "QWEN IMAGE 2.1", clearly legible.'
P[cebu]='A realistic Cebu city street at dusk after light rain, photographed with a 35mm lens, wet pavement reflecting warm storefront lights.'
P[portrait]='A cinematic portrait positioned according to the rule of thirds, with a softly blurred urban background and warm evening light.'
P[glass]='Two human hands holding a transparent glass containing water, with realistic fingers, refraction, reflections and readable text appearing through the glass.'
for k in desk neon cebu portrait glass; do
  zsh $R/zrun.sh zi-q-$k 1024 1024 "$P[$k]" > /dev/null 2>&1
  python3 $R/record.py zi-q-$k $R/z-image-bench.csv zimage 1024x1024 9 0 1 $k "QUALITY" "Z-Image PRIMARY + #1990 WORKAROUND (Metal tensor API = disabled); quality benchmark"
  zsh $R/qrun.sh qw-q-$k 1024 1024 "$P[$k]" on > /dev/null 2>&1
  python3 $R/record.py qw-q-$k $R/qwen-bench-clean.csv qwen 1024x1024 25 1 1 $k "QUALITY" "Qwen PRIMARY CONTROL (Metal tensor API = enabled); quality benchmark"
  grep -h "ran out of memory" $R/runs/zi-q-$k/sd-cli.log $R/runs/qw-q-$k/sd-cli.log
  python3 $R/imgcheck.py ~/Dev/photo-gen/outputs/zi-q-$k.png ~/Dev/photo-gen/outputs/qw-q-$k.png
done
echo QUALITY_DONE
