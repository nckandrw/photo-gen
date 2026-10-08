#!/bin/zsh
# Phase 8 Q-VR conditional arms (PROTOCOL.md section 8; gate held: all section 5.1 gates pass, no item MATERIAL).
# Sequential: Texture-Fix weight diff + 6 decodes on CPU (run_ref.sh watchdog), then the R15-512 identity-edit probe on
# the GPU through the production app path (research/qwen/run_edit.sh mode app: job system, gpu.lock, edit worker).
# Start: nohup zsh research/qwen/qv-reference/qvr-cond-chain.sh > research/qwen/qv-reference/qvr-cond-chain.log 2>&1 < /dev/null & disown
# Markers: QVR_COND_DONE / QVR_COND_STOPPED <step>. The body is one function, parsed in full before it runs.
main() {
cd ~/Dev/photo-gen
local R=research/qwen/qv-reference TF=models/research/texture-fix-vae-qwen-image-2.1
local -a REF=(env HF_HUB_OFFLINE=1 torch-ref/.venv/bin/python3.12 -I)
step() { local id=$1; shift; echo "STEP $id $(date +%T)"; zsh $R/run_ref.sh $R/runs/$id "$@" || { echo "QVR_COND_STOPPED $id $(date +%T)"; return 1; }; }
echo "QVR_COND_START $(date) head=$(git rev-parse --short HEAD)"
step TF-weights $REF[@] $R/ref_side.py weights-diff $TF $R/runs/TF-weights/weights-diff.json || return 1
for b t in 512 R02 512 R12 512 R15 1024 R02 1024 R12 1024 R15; do
  step TF-$b-$t $REF[@] $R/ref_side.py texturefix $R/runs/A2-$b-$t/data $TF $R/runs/TF-$b-$t/data || return 1
done
echo "STEP QVR-ID-512-R15 $(date +%T)"
zsh research/qwen/run_edit.sh QVR-ID-512-R15 app \
  $PWD/data/inputs/d3c22ffaae47572c1515a0d7f58231cc1ce88055b344c11e7d58c5561442335e.png 512 2510715 \
  "Preserve this image exactly. Do not change anything." 40 || { echo "QVR_COND_STOPPED QVR-ID-512-R15 $(date +%T)"; return 1; }
echo "QVR_COND_DONE $(date)"
}
main "$@"
