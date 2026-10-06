"""Generate editing-benchmark sources with PHOTO-GEN itself (Z-Image REFERENCE, 1024²), sequentially.

Usage (repo root): mflux/.venv/bin/python3.12 research/editing/gen_sources.py <suite.json> <id[:seed_offset]> ...
Every attempt is appended to research/editing/source-attempts.jsonl (never rewritten). Acceptance against each
test's 'must_show' list is a separate, recorded visual decision (sources.json), per the suite's selection rule."""
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
suite = json.loads(Path(sys.argv[1]).read_text())
tests = {t["id"]: t for t in suite["tests"]}
log = ROOT / "research" / "editing" / "source-attempts.jsonl"
for spec in sys.argv[2:]:
    tid, _, off = spec.partition(":")
    t = tests[tid]
    seed = t["source"]["seed"] + int(off or 0)
    cmd = [str(ROOT / "bin" / "photo-gen"), "generate", "--profile", "reference", "--width", "1024", "--height", "1024",
           "--seed", str(seed), "-p", t["source"]["prompt"], "--output-name", f"editsrc-{tid}-s{seed}", "--json"]
    t0 = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True)
    try:
        job = json.loads(p.stdout)
    except ValueError:
        job = {"status": "no-json", "stderr": p.stderr[-2000:]}
    rec = {"id": tid, "seed": seed, "prompt": t["source"]["prompt"], "rc": p.returncode, "status": job.get("status"),
           "job_id": job.get("job_id"), "output_path": job.get("output_path"), "pixel_sha256": job.get("pixel_sha256"),
           "file_sha256": job.get("file_sha256"), "validated": (job.get("request") or {}).get("validated"),
           "generation_seconds": job.get("generation_seconds"), "wall_seconds": round(time.time() - t0, 1),
           "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")}
    with log.open("a") as f:
        f.write(json.dumps(rec) + "\n")
    print(json.dumps(rec), flush=True)
print("SOURCES_GEN_DONE", flush=True)
