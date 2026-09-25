#!/usr/bin/env python3
"""Extract metrics from research/runs/<id>/ and append one row to a bench CSV.

Usage: record.py <run-id> <bench.csv> <model-set: zimage|qwen> <resolution> <steps> <guidance> <cfg> <prompt_id> <result> <notes>
Prints the extracted metrics. Times come from sd-cli's own log lines; memory/swap/pressure
from /usr/bin/time -l and the 1 Hz monitor (see run.sh).
"""
import csv, os, re, sys

run_id, bench, mset, res, steps, guid, cfg, pid, result, notes = sys.argv[1:11]
d = os.path.expanduser(f"~/Dev/photo-gen/research/runs/{run_id}")
log = open(f"{d}/sd-cli.log").read()
summ = dict(l.strip().split("=", 1) for l in open(f"{d}/summary.txt") if "=" in l)
pre = open(f"{d}/pre.txt").read()
env = open(f"{d}/env.txt").read().strip() if os.path.exists(f"{d}/env.txt") else "none"

loads = [float(x) for x in re.findall(r"loading tensors completed, taking ([\d.]+)s", log)]
def one(p):
    m = re.search(p, log)
    return float(m.group(1)) if m else ""
te = one(r"get_learned_condition completed, taking ([\d.]+)s")
dit = one(r"sampling completed, taking ([\d.]+)s")
vae = one(r"decode_first_stage completed, taking ([\d.]+)s")
gen = one(r"generate_image completed in ([\d.]+)s")
sched = re.search(r"get_sigmas with (\w+) scheduler", log)
ok_save = "(success)" in log
swap_delta = round((float(summ["peak_swap_mb"]) - float(summ["swap_start_mb"])) / 1024, 2)
power = "AC" if "AC Power" in os.popen("pmset -g batt").read() else "BATTERY"
therm = "no warnings" if "No thermal warning level has been recorded" in pre else "WARNING (see pre.txt)"

M = {
 "zimage": ("z_image_turbo-Q4_K.gguf","14b375ab4f226bc5378f68f37e899ef3c2242b8541e61e2bc1aff40976086fbd",
            "Qwen3-4B-Q4_K_M.gguf","7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5",
            "ae.safetensors","afc8e28272cd15db3919bacdb6918ce9c1ed22e96cb12c4d5ed0fba823529e38"),
 "qwen":   ("qwen_image_2.1-Q4_K.gguf","29f9c83c249ff0292fb2943fceddfa2319b446601866c82a4f8be062abea72c2",
            "qwen3vl_8b_heretic-Q4_K_M.gguf","1338274ac7a6344f262a16c7a52d1bd7fe789307d252733b23ea421126e5d343",
            "qwen_image_2.1_vae_bf16.safetensors","bb21f7473051e1ac368515dd3f2e15cd44d7a11748ee8823e1ddca3e4876b7c9"),
}[mset]
row = [os.popen(f"head -1 {d}/pre.txt").read().split()[1], "sd.cpp", "master-908-88411ef", "macOS 27.0 (26A428)",
       "MBA M5 8-GPU 16GB", power, *M, res, steps, guid, cfg, "42", pid,
       round(sum(loads), 2), te, dit, vae, summ["wall_s"], summ["time_l_peak_footprint_gb"], swap_delta,
       summ["peak_pressure_level"], therm, result,
       f"{notes}; env={env}; scheduler={sched.group(1) if sched else '?'}; generate_image={gen}s; max_rss={summ['time_l_max_rss_gb']}GB; min_free={summ['min_free_pct']}%; peak_compressed={summ['peak_compressed_gb']}GB; saved={ok_save}"]
with open(bench, "a", newline="") as f:
    csv.writer(f).writerow(row)
print(dict(loads=loads, te=te, dit=dit, vae=vae, gen=gen, wall=summ["wall_s"], peak_fp=summ["time_l_peak_footprint_gb"],
           swap_delta_gb=swap_delta, pressure=summ["peak_pressure_level"], min_free=summ["min_free_pct"], env=env, power=power))
