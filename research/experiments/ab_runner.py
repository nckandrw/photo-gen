#!/usr/bin/env python3
"""Generic runner: executes exp_zimage.py jobs sequentially with the 1 Hz system monitor; one JSONL row per run.
Usage: ab_runner.py <jobs.json> <out.jsonl>   (jobs: list of {tag, args:[...]})"""
import json, os, subprocess, sys, time
R = os.path.expanduser("~/Dev/photo-gen"); E = f"{R}/research/experiments"
PY = f"{R}/mflux/.venv/bin/python3.12"
env = {**os.environ, "HF_HUB_OFFLINE": "1", "HF_HUB_DISABLE_TELEMETRY": "1", "HF_HOME": f"{R}/mflux/hf"}
jobs = json.load(open(sys.argv[1])); out = open(sys.argv[2], "a")
done = set()
if os.path.exists(sys.argv[2]):
    for l in open(sys.argv[2]):
        try: done.add(json.loads(l)["tag"])
        except Exception: pass
for j in jobs:
    if j["tag"] in done: continue
    mon_csv = f"{E}/{os.path.basename(sys.argv[2]).split('.')[0]}-mon-{j['tag']}.csv"
    mon = subprocess.Popen(["zsh", f"{R}/research/monitor.sh", mon_csv, "python3.12", "1"])
    t = time.time()
    p = subprocess.run([PY, f"{E}/exp_zimage.py", *j["args"]], capture_output=True, text=True, env=env)
    wall = round(time.time() - t, 2); time.sleep(1.5); mon.terminate()
    res = next((json.loads(l[10:]) for l in p.stdout.splitlines() if l.startswith("EXPRESULT ")), None)
    rows = []
    try:
        import csv
        rows = list(csv.DictReader(open(mon_csv)))
    except Exception: pass
    f = lambda k: [float(r[k]) for r in rows if r.get(k) not in (None, "")]
    sysm = {"swap_start_mb": f("swap_used_mb")[0] if rows else None, "swap_max_mb": max(f("swap_used_mb"), default=None),
            "pressure_max": max(f("pressure_level"), default=None), "free_min_pct": min(f("free_pct"), default=None),
            "wired_max_gb": max(f("wired_gb"), default=None)}
    row = {"tag": j["tag"], "meta": j.get("meta", {}), "rc": p.returncode, "wall_s": wall, "start": time.strftime("%H:%M:%S", time.localtime(t)),
           "sys": sysm, "res": res, "stderr_tail": p.stderr[-400:] if p.returncode else ""}
    out.write(json.dumps(row) + "\n"); out.flush()
    print(f"{row['start']} {j['tag']:32} rc={p.returncode} wall={wall} denoise={res and res['denoise_s']} fp={res and res['peak_footprint_gb']}", flush=True)
print("RUNNER_DONE", flush=True)
