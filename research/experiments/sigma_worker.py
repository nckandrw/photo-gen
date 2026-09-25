"""Research wrapper: runs the UNMODIFIED production worker (photogen.runtimes.mflux_zimage_worker.main) but
appends `--scheduler sigma_sched.<Class>` to the mflux argv when the request carries
"research_scheduler". Everything else (bf16 patch, transformer release, probes, argv) is the production path.

Usage: python sigma_worker.py <request.json> <result.json>
The result JSON gains: research_scheduler, sigmas_used (from SIGMA_DUMP).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from mflux.models.z_image.cli import z_image_turbo_generate as cli  # noqa: E402
from photogen.runtimes import mflux_zimage_worker as worker  # noqa: E402


def run(req_path, res_path):
    req = json.load(open(req_path))
    sched = req.pop("research_scheduler", None)
    dump = res_path + ".sigmas.json"
    if sched:
        os.environ["SIGMA_DUMP"] = dump
        orig = cli.main

        def main_with_scheduler(*a, **k):
            sys.argv = sys.argv + ["--scheduler", f"sigma_sched.{sched}"]
            return orig(*a, **k)

        cli.main = main_with_scheduler
    clean = res_path + ".request-clean.json"
    json.dump(req, open(clean, "w"), indent=1)
    rc = worker.main(clean, res_path)
    res = json.load(open(res_path))
    res["research_scheduler"] = sched
    res["sigmas_used"] = json.load(open(dump)) if sched and os.path.exists(dump) else None
    json.dump(res, open(res_path, "w"), indent=1)
    return rc


if __name__ == "__main__":
    sys.exit(run(sys.argv[1], sys.argv[2]))
