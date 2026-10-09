#!/bin/zsh
# usage: crop.sh SHEET fx fy fw fh tag [maxdim] [files...]
# fractional crop region (0..1) applied to each file of the sheet
B=/Users/nckandrw/Dev/photo-gen/research/editing/compositing/review/blind
S=/private/tmp/claude-501/-Users-nckandrw-Dev-photo-gen/a0de6674-7bd8-464e-ba17-f8acc44526b3/scratchpad/cmpf-rater
sheet=$1; fx=$2; fy=$3; fw=$4; fh=$5; tag=$6; maxd=${7:-0}
shift 7 2>/dev/null
labels=("$@")
if [ ${#labels[@]} -eq 0 ]; then labels=(ORIGINAL-FULL A B C D E); fi
for l in $labels; do
  f=$B/$sheet-$l.png; [ -f $f ] || f=$S/$sheet-$l.png
  W=$(sips -g pixelWidth $f | tail -1 | awk '{print $2}')
  H=$(sips -g pixelHeight $f | tail -1 | awk '{print $2}')
  x=$(printf "%.0f" $(( fx * W ))); y=$(printf "%.0f" $(( fy * H )))
  w=$(printf "%.0f" $(( fw * W ))); h=$(printf "%.0f" $(( fh * H )))
  out=$S/$sheet-$tag-$l.png
  sips -c $h $w --cropOffset $y $x $f --out $out >/dev/null 2>&1
  if [ "$maxd" != "0" ]; then
    cw=$w; ch=$h; m=$(( cw > ch ? cw : ch ))
    if [ $m -gt $maxd ]; then sips -Z $maxd $out >/dev/null 2>&1; fi
  fi
  echo "$out ${w}x${h} @ $x,$y"
done
