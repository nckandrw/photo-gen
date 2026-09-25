#!/usr/bin/env python3
"""Chain P3B job files (block-sensitivity-map.md, kernel-profile.md, ffn-reduction-design.md)."""
import json
P = json.load(open("prompts.json")); C = json.load(open("p3b/calib-prompts.json"))
BLOCKS = [f"nr{i}" for i in range(2)] + [f"cr{i}" for i in range(2)] + [f"L{i}" for i in range(30)]
def req(prompt, res, prec, steps, seed, **extra):
    return {"prompt": prompt, "width": res, "height": res, "steps": steps, "seed": seed, "precision": prec,
            "release_transformer": True, **extra}
import os; W = os.path.abspath("p3b")
jobs = {}
# timing + stats at 1024² (instrumented, uncompiled)
jobs["probe-1024"] = [
    {"tag": "time-1024-bf16-st8-p01", "meta": {"mode": "time"}, "req": req(P["p01"], 1024, "bf16", 8, 42, probe={"mode": "time", "out": f"{W}/time-1024-bf16.json"})},
    {"tag": "time-1024-fp32-st9-p01", "meta": {"mode": "time"}, "req": req(P["p01"], 1024, "fp32", 9, 42, probe={"mode": "time", "out": f"{W}/time-1024-fp32.json"})},
    {"tag": "none-1024-bf16-st8-p01", "meta": {"mode": "none"}, "req": req(P["p01"], 1024, "bf16", 8, 42, probe={"mode": "none"})},
] + [{"tag": f"stats-1024-bf16-st8-{p}", "meta": {"mode": "stats", "pid": p}, "req": req(P[p], 1024, "bf16", 8, 42, probe={"mode": "stats", "out": f"{W}/stats-1024-bf16-{p}.json"})} for p in ("p01", "p06", "p09")]
# perturbation sensitivity at 512² (uncompiled; baselines first)
sens = []
for p in ("p01", "p06", "p09"):
    sens.append({"tag": f"sens-512-{p}-base", "meta": {"mode": "none", "pid": p}, "req": req(P[p], 512, "bf16", 8, 42, probe={"mode": "none"})})
for b in BLOCKS:
    for p in ("p01", "p06", "p09"):
        sens.append({"tag": f"sens-512-{p}-skip-{b}", "meta": {"mode": "perturb", "kind": "skip", "block": b, "pid": p},
                     "req": req(P[p], 512, "bf16", 8, 42, probe={"mode": "perturb", "kind": "skip", "block": b})})
    sens.append({"tag": f"sens-512-p01-scale09-{b}", "meta": {"mode": "perturb", "kind": "scale", "block": b, "pid": "p01"},
                 "req": req(P["p01"], 512, "bf16", 8, 42, probe={"mode": "perturb", "kind": "scale", "scale": 0.9, "block": b})})
jobs["sens-512"] = sens
jobs["sens-1024"] = [{"tag": "sens-1024-p01-base", "meta": {"mode": "none", "pid": "p01"}, "req": req(P["p01"], 1024, "bf16", 8, 42, probe={"mode": "none"})}] + \
    [{"tag": f"sens-1024-p01-skip-{b}", "meta": {"mode": "perturb", "kind": "skip", "block": b, "pid": "p01"},
      "req": req(P["p01"], 1024, "bf16", 8, 42, probe={"mode": "perturb", "kind": "skip", "block": b})} for b in BLOCKS]
# FFN calibration (calibration prompts only; disjoint from the evaluation suite), 512², bf16/8
jobs["ffn-calib"] = [{"tag": f"calib-512-{c}", "meta": {"mode": "ffn_calib", "pid": c},
                      "req": req(C[c], 512, "bf16", 8, 42, probe={"mode": "ffn_calib", "calib_out": f"{W}/calib-{c}.npz"})} for c in C]
# FFN pruning sweep (compiled, production-like): 512² x 12 suite prompts, + 1024² p01 timing
sweep = []
for kf in (1.0, 0.9, 0.8, 0.7, 0.6):
    for p in P:
        sweep.append({"tag": f"ffn-512-k{int(kf*100)}-{p}", "meta": {"keep": kf, "pid": p, "res": 512},
                      "req": req(P[p], 512, "bf16", 8, 42, ffn_prune={"keep_frac": kf, "scores": f"{W}/ffn-scores.npz"})})
for kf in (1.0, 0.9, 0.8, 0.7, 0.6):
    sweep.append({"tag": f"ffn-1024-k{int(kf*100)}-p01", "meta": {"keep": kf, "pid": "p01", "res": 1024},
                  "req": req(P["p01"], 1024, "bf16", 8, 42, ffn_prune={"keep_frac": kf, "scores": f"{W}/ffn-scores.npz"})})
jobs["ffn-sweep"] = sweep
# NAX end-to-end check: REFERENCE fp32/9 512² p01 s42 with MLX_ENABLE_TF32=0 (env set by the chain)
jobs["nax-e2e"] = [{"tag": "nax-e2e-512-fp32-st9-tf32off", "meta": {"MLX_ENABLE_TF32": "0"}, "req": req(P["p01"], 512, "fp32", 9, 42)}]
for k, v in jobs.items():
    json.dump(v, open(f"{W}/jobs-{k}.json", "w"), indent=1); print(k, len(v))
