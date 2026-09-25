#!/bin/zsh
# Phase 3 chain B (phase3-plan.md): NAX capture, op profile, quantization microbench, NAX e2e check,
# instrumented block probes, FFN calibration + group-aligned pruning sweep, block-sensitivity ablations.
# Sequential; nothing else uses the GPU. Resumable per prod_runner tag. Completion marker: PHASE3B_DONE
E=~/Dev/photo-gen/research/experiments; PY=~/Dev/photo-gen/mflux/.venv/bin/python3.12; cd $E
export HF_HUB_OFFLINE=1 HF_HOME=~/Dev/photo-gen/mflux/hf
mkdir -p p3b/cap
echo "[$(date +%T)] PHASE3B start"; pmset -g batt | head -1
if [ ! -f p3b/nax-fp32-tf32off.json ]; then
  echo "[$(date +%T)] NAX probe"
  MTL_CAPTURE_ENABLED=1 $PY nax_probe.py bf16 p3b/nax-bf16.json p3b/cap/nax-bf16.gputrace
  MTL_CAPTURE_ENABLED=1 $PY nax_probe.py fp32 p3b/nax-fp32.json p3b/cap/nax-fp32.gputrace
  MLX_ENABLE_TF32=0 MTL_CAPTURE_ENABLED=1 $PY nax_probe.py fp32 p3b/nax-fp32-tf32off.json p3b/cap/nax-fp32-tf32off.gputrace
fi
if [ ! -f p3b/op-bf16-L1056.json ]; then
  echo "[$(date +%T)] op profile"
  MTL_CAPTURE_ENABLED=1 $PY op_profile.py fp32 4128 p3b/op-fp32-L4128.json p3b/cap
  MTL_CAPTURE_ENABLED=1 $PY op_profile.py bf16 4128 p3b/op-bf16-L4128.json p3b/cap
  $PY op_profile.py bf16 1056 p3b/op-bf16-L1056.json
fi
if [ ! -f p3b/quant-fp32-L4128.json ]; then
  echo "[$(date +%T)] quantization microbench"
  $PY quant_microbench.py bf16 4128 p3b/quant-bf16-L4128.json
  $PY quant_microbench.py bf16 1056 p3b/quant-bf16-L1056.json
  $PY quant_microbench.py fp32 4128 p3b/quant-fp32-L4128.json
fi
echo "[$(date +%T)] NAX e2e (REFERENCE 512² with MLX_ENABLE_TF32=0)"
PRODRUNNER_WORKER_ENV=MLX_ENABLE_TF32=0 $PY prod_runner.py p3b/jobs-nax-e2e.json p3b/results-nax-e2e.jsonl p3b/work-nax
echo "[$(date +%T)] instrumented probes 1024²"
PRODRUNNER_WORKER_SCRIPT=$E/p3_block_probe.py $PY prod_runner.py p3b/jobs-probe-1024.json p3b/results-probe-1024.jsonl p3b/work-probe
echo "[$(date +%T)] FFN calibration"
PRODRUNNER_WORKER_SCRIPT=$E/p3_block_probe.py $PY prod_runner.py p3b/jobs-ffn-calib.json p3b/results-ffn-calib.jsonl p3b/work-calib
$PY p3b_merge_calib.py
echo "[$(date +%T)] FFN pruning sweep"
PRODRUNNER_WORKER_SCRIPT=$E/ffn_prune_worker.py $PY prod_runner.py p3b/jobs-ffn-sweep.json p3b/results-ffn-sweep.jsonl p3b/work-ffn
echo "[$(date +%T)] block sensitivity 512²"
PRODRUNNER_WORKER_SCRIPT=$E/p3_block_probe.py $PY prod_runner.py p3b/jobs-sens-512.json p3b/results-sens-512.jsonl p3b/work-sens512
echo "[$(date +%T)] block sensitivity 1024² (p01)"
PRODRUNNER_WORKER_SCRIPT=$E/p3_block_probe.py $PY prod_runner.py p3b/jobs-sens-1024.json p3b/results-sens-1024.jsonl p3b/work-sens1024
echo "[$(date +%T)] PHASE3B_DONE"
