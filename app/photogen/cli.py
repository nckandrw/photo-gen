"""photo-gen command line. Uses the same service/job/runtime layer as the HTTP API."""
from __future__ import annotations

import argparse
import json
import os
import sys

from .api import public_job, serve
from .config import AppConfig
from .errors import PhotoGenError
from .service import PhotoGenService, setup_logging
from .tasks import IMAGE_EDIT, TEXT_TO_IMAGE


def _seed(v: str):
    if v == "random":
        return "random"
    try:
        s = int(v)
    except ValueError:
        raise argparse.ArgumentTypeError("seed must be an integer or 'random'") from None
    return s


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="photo-gen", description="Local image generation (Z-Image-Turbo on mflux/MLX) and "
                                "experimental image editing (Qwen-Image-2.1 on mflux/MLX).")
    p.add_argument("--config", help="path to photogen.toml (default: config/photogen.toml)")
    p.add_argument("-v", "--verbose", action="store_true", help="DEBUG logging")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("serve", help="run the local HTTP API (127.0.0.1 by default)")
    s.add_argument("--full-verify", action="store_true", help="re-hash every model file at startup")

    g = sub.add_parser("generate", help="generate one image now (waits for the GPU if the server is busy)")
    g.add_argument("--prompt", "-p", required=True)
    g.add_argument("--width", type=int)
    g.add_argument("--height", type=int)
    g.add_argument("--steps", type=int)
    g.add_argument("--seed", type=_seed, help="integer or 'random' (default from config)")
    g.add_argument("--output-name", help="optional name suffix for the output file")
    g.add_argument("--precision", choices=["fp32", "bf16"],
                   help="DiT activation dtype: fp32 (default, reference) or bf16 (opt-in, ~30%% faster denoise, "
                        "not pixel-identical to fp32; see research/experiments/bf16-quality-report.md)")
    g.add_argument("--profile", choices=["reference", "fast", "balanced", "ultra"],
                   help="reference = fp32 + 9 steps (default behaviour, canonical); fast = bf16 + 8 steps (gated at "
                        "512x512, 768x768 and 1024x1024; ~35%% less denoise than reference); balanced = bf16 + 5 steps "
                        "(gated at 1024x1024 ONLY; ~0.63x FAST denoise); ultra = bf16 + 4 steps "
                        "(gated at 512x512 ONLY); other sizes need --allow-experimental")
    g.add_argument("--text-encoder", help="'stock' (default) or a registered substitute from config/text-encoders.json")
    g.add_argument("--allow-experimental", action="store_true",
                   help="permit non-validated resolutions/step counts (still bounded to ≤1024² pixels)")
    g.add_argument("--json", action="store_true", help="print the full job record as JSON")

    e = sub.add_parser("edit", help="edit one image now with Qwen-Image-2.1 (RESEARCH/EXPERIMENTAL; Qwen Research "
                                    "License, non-commercial)")
    e.add_argument("--image", "-i", required=True, help="input image: PNG, JPEG or WebP, opaque, 64..8192 px per side")
    e.add_argument("--prompt", "-p", required=True, help="the edit instruction")
    e.add_argument("--seed", type=_seed, help="integer or 'random' (default from config)")
    e.add_argument("--steps", type=int, help="denoising steps (default 40, the upstream recommendation)")
    e.add_argument("--output-resolution", type=int,
                   help="pixel-area budget as a side length, multiple of 32 (default 1024); the output keeps the "
                        "input's aspect ratio")
    e.add_argument("--output-name", help="optional name suffix for the output file")
    e.add_argument("--allow-experimental", action="store_true",
                   help="required: no edit configuration has passed a quality gate yet")
    e.add_argument("--json", action="store_true", help="print the full job record as JSON")

    j = sub.add_parser("jobs", help="list jobs")
    j.add_argument("--status", choices=["queued", "running", "completed", "failed", "cancelled"])
    j.add_argument("--limit", type=int, default=20)
    j.add_argument("--json", action="store_true")

    one = sub.add_parser("job", help="show one job")
    one.add_argument("job_id")

    c = sub.add_parser("cancel", help="cancel a queued job (running API jobs: use POST /jobs/{id}/cancel)")
    c.add_argument("job_id")

    st = sub.add_parser("status", help="queue, recent durations, memory/thermal telemetry")
    st.add_argument("--json", action="store_true")

    v = sub.add_parser("verify", help="verify runtime versions and model integrity")
    v.add_argument("--full", action="store_true", help="re-hash every model file (ignores the cache)")
    v.add_argument("--edit", action="store_true", help="verify the image-edit backend (Qwen) instead of text-to-image")

    sub.add_parser("capabilities", help="print runtime capabilities (and every task's backend)")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        cfg = AppConfig.load(args.config)
        setup_logging(cfg, verbose=args.verbose)
        svc = PhotoGenService(cfg)

        if args.cmd == "serve":
            svc.require_healthy(full=args.full_verify)
            serve(svc)
            return 0

        if args.cmd == "verify":
            h = svc.verify_edit(full=args.full) if args.edit else svc.verify(full=args.full)
            print(json.dumps(h.to_dict(), indent=1))
            return 0 if h.ok else 2

        if args.cmd == "capabilities":
            print(json.dumps(svc.capabilities(), indent=1))
            return 0

        if args.cmd == "generate":
            svc.require_healthy()
            params = {"prompt": args.prompt}
            for k in ("width", "height", "steps", "seed"):
                if getattr(args, k) is not None:
                    params[k] = getattr(args, k)
            if args.output_name:
                params["output_name"] = args.output_name
            if args.precision:
                params["precision"] = args.precision
            if args.profile:
                params["profile"] = args.profile
            if args.text_encoder:
                params["text_encoder"] = args.text_encoder
            if args.allow_experimental:
                params["allow_experimental"] = True
            return _run_and_report(svc, params, args.json)

        if args.cmd == "edit":
            svc.require_edit_healthy()
            params = {"task": IMAGE_EDIT, "prompt": args.prompt, "image": os.path.abspath(args.image)}
            for k in ("seed", "steps", "output_resolution", "output_name"):
                if getattr(args, k) is not None:
                    params[k] = getattr(args, k)
            if args.allow_experimental:
                params["allow_experimental"] = True
            return _run_and_report(svc, params, args.json)

        if args.cmd == "jobs":
            jobs = [public_job(j) for j in svc.jobs.store.list(status=args.status, limit=args.limit)]
            if args.json:
                print(json.dumps(jobs, indent=1))
            else:
                for jb in jobs:
                    r = jb["request"]
                    tag = "" if jb["task"] == TEXT_TO_IMAGE else f"[{jb['task']}] "
                    print(f"{jb['job_id']}  {jb['status']:<9}  {r['width']}x{r['height']}  seed={jb['seed']:<10}  "
                          f"{(str(jb['generation_seconds']) + 's') if jb['generation_seconds'] else '':>8}  "
                          f"{tag}{r['prompt'][:50]}")
            return 0

        if args.cmd == "job":
            print(json.dumps(public_job(svc.jobs.store.get(args.job_id)), indent=1))
            return 0

        if args.cmd == "cancel":
            print(json.dumps(public_job(svc.jobs.cancel(args.job_id)), indent=1))
            return 0

        if args.cmd == "status":
            svc.verify()
            st = svc.status()
            if args.json:
                print(json.dumps(st, indent=1))
            else:
                mem, th = st["memory"], st["thermal"]
                print(f"service: {st['service']}  runtime: {st['runtime']} {st['runtime_version']}  "
                      f"model: {st['model']}@{st['model_revision'][:7]}  low_ram: {st['low_ram']}")
                print(f"active: {[a['job_id'] for a in st['active_jobs']] or 'none'}  queued: {st['queue_length']}")
                print(f"last generation: {st['last_generation_seconds']}s  recent: {st['recent_generation_seconds']}")
                print(f"memory: pressure={mem.get('pressure_level')} free={mem.get('free_percent')}% "
                      f"swap_used={mem.get('swap_used_gb')}GB  thermal warning recorded: "
                      f"{th.get('thermal_warning_recorded')}  power: {st['power_source']}")
            return 0
    except PhotoGenError as e:
        print(json.dumps(e.to_dict(), indent=1), file=sys.stderr)
        return 2
    return 1


def _run_and_report(svc: PhotoGenService, params: dict, as_json: bool) -> int:
    """Submit one job, run it in this process (waiting for the GPU lock), and report it."""
    job = svc.jobs.submit(params, source="cli")
    print(f"job {job['id']}: {job['width']}x{job['height']} steps={job['steps']} seed={job['seed']}", file=sys.stderr)
    job = public_job(svc.jobs.run_sync(job["id"]))
    if as_json:
        print(json.dumps(job, indent=1))
    elif job["status"] == "completed":
        print(f"{job['output_path']}\n  seed={job['seed']}  time={job['generation_seconds']}s  "
              f"pixel_sha256={job['pixel_sha256']}\n  metadata={job['metadata_path']}")
    else:
        print(f"job {job['job_id']} {job['status']}: {(job['error'] or {}).get('message')}", file=sys.stderr)
    return 0 if job["status"] == "completed" else 1
