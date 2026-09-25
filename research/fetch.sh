#!/bin/zsh
# Pinned, hash-verified download from Hugging Face.
# Usage: zsh research/fetch.sh <repo> <revision-sha> <path-in-repo> <expected-size> <expected-sha256> <dest-dir>
set -euo pipefail
repo=$1 rev=$2 file=$3 size=$4 want=$5 dest=$6
mkdir -p "$dest"
out="$dest/${file:t}"
log=~/Dev/photo-gen/research/downloads.log
url="https://huggingface.co/$repo/resolve/$rev/$file"
print "$(date -u +%FT%TZ) START $repo@$rev $file expect_size=$size" >> $log
curl -fL --retry 5 -C - -o "$out.part" "$url"
got_size=$(stat -f %z "$out.part")
got=$(shasum -a 256 "$out.part" | cut -d' ' -f1)
if [[ $got_size == $size && $got == $want ]]; then
  mv "$out.part" "$out"
  chmod a-w "$out"
  print "$(date -u +%FT%TZ) OK    $out size=$got_size sha256=$got" | tee -a $log
else
  print "$(date -u +%FT%TZ) FAIL  $out.part size=$got_size (want $size) sha256=$got (want $want)" | tee -a $log
  exit 1
fi
