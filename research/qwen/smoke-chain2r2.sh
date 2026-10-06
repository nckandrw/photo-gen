#!/bin/zsh
# Smoke chain 2: defer_transformer_load A/B (parity + memory) at 512, then the first 1024² edits. Marker: SMOKE2_DONE (rerun r2 after the worker_run.py relative-path bug; failed r1 dirs kept)
main() {
cd ~/Dev/photo-gen
local STAGED=$PWD/data/inputs/befe1b3c8af5424cc5f65868fec96938bfac782238f46c18652244fada3bdd42.png
local P="Change the background to a sunset beach"
zsh research/qwen/run_edit.sh A0r2-worker-512-stock worker0 $STAGED 512 42 "$P"; sleep 30
zsh research/qwen/run_edit.sh A1r2-worker-512-defer worker1 $STAGED 512 42 "$P"; sleep 30
zsh research/qwen/run_edit.sh B1r2-worker-1024-defer worker1 $STAGED 1024 42 "$P"; sleep 45
zsh research/qwen/run_edit.sh B0r2-worker-1024-stock worker0 $STAGED 1024 42 "$P"
echo SMOKE2_DONE
}
main "$@"
