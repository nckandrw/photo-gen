#!/usr/bin/env python3
"""Generates Phase 3 job files (pre-registered in sigma-schedule-audit.md / fast-resolution-gates-report.md)."""
import json
P = json.load(open("prompts.json"))
def req(prompt, res, prec, steps, seed, sched=None):
    r = {"prompt": prompt, "width": res, "height": res, "steps": steps, "seed": seed, "precision": prec,
         "release_transformer": True}
    if sched: r["research_scheduler"] = sched
    return r
def abba(pairs):  # pairs: list of (A_job, B_job); pair i even -> A,B ; odd -> B,A
    out = []
    for i, (a, b) in enumerate(pairs): out += [a, b] if i % 2 == 0 else [b, a]
    return out
# sigma audit: M (mflux default) vs S (OfficialStatic3), bf16/8
def sigma(res, seeds):
    pairs = []
    for s in seeds:
        for pid, pr in P.items():
            m = {"tag": f"sa-{res}-{pid}-s{s}-M", "meta": {"exp": "sigma", "arm": "M", "res": res, "pid": pid, "seed": s}, "req": req(pr, res, "bf16", 8, s)}
            S = {"tag": f"sa-{res}-{pid}-s{s}-S", "meta": {"exp": "sigma", "arm": "S", "res": res, "pid": pid, "seed": s}, "req": req(pr, res, "bf16", 8, s, "OfficialStatic3")}
            pairs.append((m, S))
    return abba(pairs)
def gate(res, seeds):
    pairs = []
    for s in seeds:
        for pid, pr in P.items():
            a = {"tag": f"g{res}-{pid}-s{s}-ref", "meta": {"exp": f"G{res}", "arm": "REFERENCE", "res": res, "pid": pid, "seed": s}, "req": req(pr, res, "fp32", 9, s)}
            b = {"tag": f"g{res}-{pid}-s{s}-fast", "meta": {"exp": f"G{res}", "arm": "FAST", "res": res, "pid": pid, "seed": s}, "req": req(pr, res, "bf16", 8, s)}
            pairs.append((a, b))
    return abba(pairs)
p01 = P["p01"]
json.dump([{"tag": "cold-768-fp32-st9", "meta": {"tier": "REFERENCE"}, "req": req(p01, 768, "fp32", 9, 42)}], open("perfmap/jobs-cold768-ref.json", "w"), indent=1)
json.dump([{"tag": "cold-768-bf16-st8", "meta": {"tier": "FAST"}, "req": req(p01, 768, "bf16", 8, 42)}], open("perfmap/jobs-cold768-fast.json", "w"), indent=1)
json.dump(sigma(512, [2718, 31415]), open("sigma/jobs-512.json", "w"), indent=1)
json.dump(sigma(768, [2718, 31415]), open("sigma/jobs-768.json", "w"), indent=1)
json.dump(sigma(1024, [2718]), open("sigma/jobs-1024.json", "w"), indent=1)
for r in (512, 768, 1024):
    json.dump(gate(r, [1618, 8128]), open(f"fastgate/jobs-{r}.json", "w"), indent=1)
print("ok")
