#!/bin/zsh
# usage: vmont.sh SHEET tag scale labels...   (vstack, nearest-neighbour scaled)
S=/private/tmp/claude-501/-Users-nckandrw-Dev-photo-gen/a0de6674-7bd8-464e-ba17-f8acc44526b3/scratchpad/cmpf-rater
sheet=$1; tag=$2; k=$3; shift 3
ins=(); fl=""; st=""; i=0
for l in "$@"; do
  ins+=(-i "$S/${sheet}-${tag}-${l}.png")
  fl="${fl}[${i}]scale=iw*${k}:ih*${k}:flags=neighbor,pad=iw:ih+6:0:0:white[v${i}];"
  st="${st}[v${i}]"
  i=$((i+1))
done
ffmpeg -loglevel error -y "${ins[@]}" -filter_complex "${fl}${st}vstack=inputs=${i}" "$S/${sheet}-${tag}-V.png"
sips -g pixelWidth -g pixelHeight "$S/${sheet}-${tag}-V.png" | tail -2 | tr '\n' ' '; echo
