#!/bin/zsh
# Smoke chain 1 (512): S2 plain-CLI parity control, S3 production-path repeat (determinism). Marker: SMOKE1_DONE
cd ~/Dev/photo-gen
STAGED=$PWD/data/inputs/befe1b3c8af5424cc5f65868fec96938bfac782238f46c18652244fada3bdd42.png
P="Change the background to a sunset beach"
zsh research/qwen/run_edit.sh S2-plain-512 plain $STAGED 512 42 "$P"
sleep 20
zsh research/qwen/run_edit.sh S3-app-512-repeat app $STAGED 512 42 "$P"
echo SMOKE1_DONE
