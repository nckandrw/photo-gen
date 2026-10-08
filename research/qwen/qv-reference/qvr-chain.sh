#!/bin/zsh
# Phase 8 Q-VR chain (PROTOCOL.md sections 5 and 9): gates and probes, then the staged A1/A2 runs (R12-512 -> R12-1024
# -> the rest), then A1T. Strictly sequential; every step is monitored by run_ref.sh (watchdog 2 GB swap growth /
# 10 critical samples / 11 GB footprint). Any failed or aborted step stops the chain.
# Start: nohup zsh research/qwen/qv-reference/qvr-chain.sh > research/qwen/qv-reference/qvr-chain.log 2>&1 < /dev/null & disown
# Markers: QVR_CHAIN_DONE / QVR_CHAIN_STOPPED <step>. The body is one function, parsed in full before it runs.
main() {
cd ~/Dev/photo-gen
local R=research/qwen/qv-reference
local PY=mflux/.venv/bin/python3.12
local -a REF=(env HF_HUB_OFFLINE=1 torch-ref/.venv/bin/python3.12 -I)
local -A STAGED=(
  R02 data/inputs/73670d26a44b0281bab6f60d37d4adb69f77a1a836ea9dea0cb306a7a21239e9.png
  R12 data/inputs/6766f9603ea0a60bf338e6bd40308d3bdce19b0566379b2f0fab8b94e228e301.png
  R15 data/inputs/d3c22ffaae47572c1515a0d7f58231cc1ce88055b344c11e7d58c5561442335e.png
)
step() { local id=$1; shift; echo "STEP $id $(date +%T)"; zsh $R/run_ref.sh $R/runs/$id "$@" || { echo "QVR_CHAIN_STOPPED $id $(date +%T)"; return 1; }; }
a1() { step A1-$1-$2 $PY $R/mlx_run.py capture $PWD/$STAGED[$2] $1 $R/runs/A1-$1-$2/data ${3:-}; }
a2() { step ${3:-A2}-$1-$2 $REF[@] $R/ref_side.py run $R/runs/A1-$1-$2/data $R/runs/${3:-A2}-$1-$2/data; }
a1t() { step A1T-$1-$2 $PY $R/mlx_run.py --tf32-off capture $PWD/$STAGED[$2] $1 $R/runs/A1T-$1-$2/data; }
echo "QVR_CHAIN_START $(date) head=$(git rev-parse --short HEAD)"
step GATE-weights $REF[@] $R/weight_identity.py $R/runs/GATE-weights/data/weight-identity.json || return 1
step PROBE-mlx $PY $R/mlx_run.py probe $R/runs/PROBE-mlx/data || return 1
step PROBE-mps $REF[@] $R/ref_side.py mps-probe $R/runs/PROBE-mlx/data/probe.json $R/runs/PROBE-mps/data \
  || echo "PROBE-mps failed: positive control only, the chain continues"
step GATE-conv $REF[@] $R/ref_side.py conv-gate $R/runs/GATE-conv/data || return 1
# feasibility stage 1 (512) and A2 determinism
a1 512 R12 --tiler-gate || return 1
a2 512 R12 || return 1
a2 512 R12 A2b || return 1
# feasibility stage 2 (1024)
a1 1024 R12 --tiler-gate || return 1
a2 1024 R12 || return 1
# the rest
for b t in 512 R02 512 R15 1024 R02 1024 R15; do a1 $b $t || return 1; a2 $b $t || return 1; done
for b t in 512 R02 512 R12 512 R15 1024 R02 1024 R12 1024 R15; do a1t $b $t || return 1; done
echo "QVR_CHAIN_DONE $(date)"
}
main "$@"
