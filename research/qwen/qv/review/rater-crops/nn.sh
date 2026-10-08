#!/bin/zsh
# usage: nn.sh in.png h w y x scale out.png  (crop at native res, then nearest-neighbour enlarge)
C=/private/tmp/claude-501/-Users-nckandrw-Dev-photo-gen/402b96d5-87ed-48b5-9f7c-27d6595006a4/scratchpad/qv-rater-crops
rm -f ${C}/_tmp.png
sips -c ${2} ${3} --cropOffset ${4} ${5} "${1}" --out ${C}/_tmp.png >/dev/null
W=$(sips -g pixelWidth ${C}/_tmp.png | awk '/pixelWidth/{print $2}')
H=$(sips -g pixelHeight ${C}/_tmp.png | awk '/pixelHeight/{print $2}')
if [[ "$W" != "${3}" || "$H" != "${2}" ]]; then echo "CROP SIZE MISMATCH ${W}x${H} for ${7}"; exit 1; fi
ffmpeg -loglevel error -y -i ${C}/_tmp.png -vf "scale=iw*${6}:ih*${6}:flags=neighbor" "${7}"
