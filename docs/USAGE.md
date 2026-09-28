# photo-gen usage reference (markdown)

> This was the project README until 2026-09-25. It is kept as a plain-markdown reference; [photo-gen-guide.html](photo-gen-guide.html) is the fuller guide. Paths in `code` are relative to the project root.

## What it does
- Text-to-image with Z-Image-Turbo, one generation at a time, queued.
- Every image gets a JSON metadata record: prompt, seed, resolution, steps, model and revision, runtime versions, per-phase and per-step timings, peak memory, and both **pixel SHA-256** (canonical identity) and file SHA-256.
- The same seed + prompt + settings reproduces the same pixels. This is verified against the research reference.
- Startup verifies runtime versions, model file hashes and mflux's own capability declarations, and **refuses to run on drift**. Nothing is ever downloaded or repaired automatically.

## Prerequisites (already present on this machine)
- `mflux/.venv`: project-local Python 3.12.14 with mflux 0.20.0 / mlx 0.32.2. photo-gen **installs nothing** into it; the app is loaded through `PYTHONPATH`.
- `models/mflux/z-image-turbo-mflux-q4/`: the hash-verified model.
- photo-gen itself adds **no packages**: Python stdlib (http.server, sqlite3, tomllib) plus Pillow (already in the venv).

## Start
```sh
bin/photo-gen verify            # versions + model integrity + mflux capability cross-check
bin/photo-gen serve             # API on http://127.0.0.1:8765 (localhost only)
```
The first verification hashes every model file (a few seconds when cached by the OS, up to ~20 s cold). Later startups trust an inode/size/mtime cache; use `bin/photo-gen verify --full` to force a re-hash.

## CLI
```sh
bin/photo-gen generate --prompt "a red apple on a wooden table, soft window light" --width 1024 --height 1024 --seed 42
bin/photo-gen generate -p "a lighthouse at dawn" --seed random --json     # full machine-readable record
bin/photo-gen generate -p "a lighthouse at dawn" --seed 42 --precision bf16  # opt-in faster path (see below)
bin/photo-gen jobs --limit 10
bin/photo-gen job <job_id>
bin/photo-gen status            # queue, recent durations, memory/thermal telemetry
bin/photo-gen capabilities
```
The CLI runs the job in its own process through the same job layer as the API. If the server is generating, the CLI waits for the machine-wide GPU lock, so there's never more than one generation at a time.

## HTTP API (127.0.0.1 only)
| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | service status + startup verification checks (503 if degraded) |
| GET | `/status` | active job, queue length, recent durations and step timing, memory/swap/pressure, thermal warning flags, capabilities |
| GET | `/capabilities` | what the backend actually supports |
| POST | `/generate` | submit → `202` with the job record |
| GET | `/jobs?status=&limit=&pixel_sha256=` | history / search |
| GET | `/jobs/{id}?wait=SECONDS` | job record; `wait` long-polls until the job finishes (max 900) |
| POST | `/jobs/{id}/cancel` | cancel a queued or running job |
| GET | `/outputs/{id}` | PNG bytes of a completed job |

```sh
curl -s -X POST http://127.0.0.1:8765/generate -H 'Content-Type: application/json' \
     -d '{"prompt":"a red apple on a wooden table, soft window light","width":1024,"height":1024,"seed":42}'
curl -s "http://127.0.0.1:8765/jobs/<job_id>?wait=300"
```
Request fields: `prompt` (required), `width`, `height`, `steps`, `seed` (int or `"random"`), `profile` (`"reference"` | `"fast"`), `precision` (`"fp32"` default | `"bf16"`), `output_name`, `allow_experimental`, `text_encoder` (`"stock"` default | an enabled entry in `config/text-encoders.json`), `task` (`"text-to-image"` only), `output_format` (`"png"` only).
A local agent can call `POST /generate`, then `GET /jobs/{id}?wait=…`, and gets back `job_id`, `status`, `output_path`, `pixel_sha256`, `seed` and the full generation metadata.

**Rejected on purpose.** These fields return HTTP 400 instead of being silently ignored:
- `negative_prompt` and `guidance`/`cfg` — Turbo runs without CFG; mflux itself declares both as ignored;
- `scheduler`, `model`, `quantize`;
- `low_ram: false`;
- `lora`, `image` / `strength` (not validated);
- unknown fields.

**Browser protection.** Requests with a non-local `Host`, cross-origin `Origin`, or non-JSON POST bodies are refused (403/415), so web pages can't drive the local API.

## Resolutions and steps
- **Validated:** 512×512, 768×768, 1024×1024 at 9 steps, guidance 0.
  - In mflux every step is one DiT evaluation, so 9 steps = **9 NFE**.
  - The official Turbo recipe is 8 NFE. The model card's "9 steps → 8 forwards" was an old diffusers artifact; diffusers now defaults to 8 steps.
  - Details: `research/experiments/scheduler-nfe-note.md`.
- **Anything else needs `allow_experimental: true`** and must meet all of these:
  - dimensions are multiples of 16;
  - each side is between 256 and 1536;
  - total pixels are no more than 1024×1024 (the largest validated size).

  These results are labelled `validated_configuration: false` and logged as warnings.
- 2048² is refused: it's outside Z-Image's documented range and unmeasured on 16 GB.

## Configurations (profiles)
| profile | precision | steps | status | use |
|---|---|---|---|---|
| **reference** (default when no profile is given) | fp32 | 9 (= 9 NFE in mflux) | permanent research reference; pixel hash 1024² `fe47d88d…` (apple, seed 42) | reproducibility, comparisons |
| **fast** | bf16 | 8 | gated at **512², 768² and 1024²** by direct blinded REFERENCE-vs-FAST gates (2026-09-25; 72 pairs: 2 / 1 / 69 ties; `research/experiments/fast-resolution-gates-report.md`). 8 steps = 8 NFE, the official Turbo count | normal use |
| (no profile) | bf16 | 9 | validated at 1024² only (bf16 gate); needs `allow_experimental` at 512²/768² | explicit precision request |
| experimental | bf16 | 7 / 6 / 5 / 4 | research only; **not quality-equivalent** (7–6 draft, 5–4 preview) | needs `allow_experimental` |

- `--profile fast` (CLI) or `"profile": "fast"` (API). A profile fixes precision and steps; conflicting explicit values are rejected.
- Requests without a profile behave exactly as before: fp32 + 9 steps unless you pass other parameters. Existing jobs are never changed.
- `fast` at sizes other than 512², 768² and 1024² requires `allow_experimental`; results are labelled `validated_configuration: false`.
- Metadata records `profile`, `precision`, `steps`, runtime, model, scheduler, resolution and seed.
- Measured times per profile: `research/experiments/PERFORMANCE-MAP.md`.

## Precision (opt-in bf16)
- **`fp32` is the default and the reference.** It is the unmodified mflux 0.20.0 behaviour: the DiT activations are float32, and the output is pixel-identical to the validated research runs.
- **`bf16` is opt-in.** It keeps the DiT hidden stream in bfloat16 through four in-process casts in the worker. No mflux file, weight, quantization or scheduler changes.
- **Speed:** ≈30% less denoise time than fp32 (≈1.4×), measured in the same session at 1024² (sustained: ≈10.6 vs 15.0 s/step), with the same memory.
- **Output:** deterministic, but **not pixel-identical** to fp32. The same seed gives a closely similar image with small content differences.
- **Quality gate:** passed on 24 blinded pairs, with no text regression (`research/experiments/bf16-quality-report.md`). The gate covered 1024² at 9 steps only; other sizes and step counts are unmeasured in bf16.
- **Recording:** metadata records `precision` (and the observed DiT dtypes under the result's effective parameters), and `reproduce.cli` includes `--precision bf16`.

## Text encoder substitution (opt-in, registry-gated)
- **`text_encoder: stock` is the default.** It is the validated pack, unchanged.
- **Other names must be registered** in `config/text-encoders.json` with pinned file digests and `enabled: true`. Anything else is rejected.
- **How a substitute runs:** through a composite model directory. Its `transformer/`, `vae/` and `tokenizer/` are symlinks to the validated stock pack; `text_encoder/` is the substitute.
- **Checks before every job:** the composite layout and the substitute's file hashes. A failure refuses the job.
- **Recording:** metadata records the text encoder's name, source and file digests.
- **No downloads or conversions happen at runtime.** Conversion is a research step: `research/experiments/convert_te_q4.py`.
- **Current state:** the registry is **empty**, so only `stock` is available. `heretic-v2` was evaluated and **closed** 2026-09-25 (`research/experiments/te-heretic-v2-report.md`).
- **Removal:** delete its registry entry and composite directory. The stock pack is never touched.

## Output structure
```
data/
  outputs/YYYY/MM/DD/<job_id>.png     image (mflux embeds its own PNG metadata)
  outputs/YYYY/MM/DD/<job_id>.json    photo-gen metadata (schema photogen.generation/1), incl. reproduce command
  jobs/<job_id>/worker.log            worker output (debug)
  photogen.sqlite3                    job history
  logs/photogen.log                   application log (rotated)
  gpu.lock                            machine-wide one-generation lock
  integrity-cache.json                model-hash verification cache
```
Job IDs are UTC timestamps plus a random suffix; the dated folders use the UTC date.

## Performance and thermal behaviour (measured, 1024²)
> These are the original **REFERENCE (fp32 + 9 steps)** figures, from before the transformer-release fix. Current cold figures: REFERENCE 83.4 s wall, FAST 54.2 s wall (`research/experiments/PERFORMANCE-MAP.md`; summarized in the guide's Performance section).

| Regime | Time per image | Notes |
|---|---:|---|
| Cold (first image after idle) | ≈85 s | ≈8.5–9 s/step |
| Sustained (after ~5 consecutive images) | ≈134 s | fanless throttling, ≈13.7–14.4 s/step; ≈27 images/hour |

The Air throttles after 1–2 images and recovers after about 10 minutes idle. Between sessions the sustained figure varied about 131–156 s. `GET /status` shows recent durations and per-step timing; these are performance observations, **not temperatures**, which this Mac doesn't expose without sudo.

## Memory
- `--low-ram` is always on: the text encoder is freed before denoising, the MLX cache is capped at 1 GB, and VAE decode is tiled.
- **Transformer release before VAE decode** (production since 2026-09-25). mflux's `--low-ram` sets `model.transformer = None`, but its compiled `predict` closure kept the DiT alive through VAE decode. photo-gen's worker clears that closure's holder, so the ~3.47 GB DiT is reclaimable before decode.
  - Output is pixel-identical; no runtime cost.
  - Peak footprint at 1024²: fp32 7.3 → **6.56 GB**, bf16 7.3 → **5.84 GB**. At 512²: fp32 **5.93 GB**, bf16 **5.41 GB**.
  - No swap growth, normal memory pressure.
  - Evidence: `research/experiments/production-memory-fix-report.md`.
- Without it, this machine hit 12.8 GB, critical pressure and 2 GB of swap, so it can't be disabled from the API or CLI.
- Inference runs in a fresh worker process per job. Its memory is fully returned afterwards, and the server stays around 0.1 GB.

## Troubleshooting
| Symptom | Meaning / action |
|---|---|
| `runtime_unavailable` at startup | version drift or model hash mismatch. Details are in the error. photo-gen won't repair it; investigate before changing anything. |
| `unsupported_parameter` | the backend doesn't honour that field (see above) |
| `invalid_request` for a size | use a validated size or `allow_experimental: true` (still bounded to ≤1024² pixels) |
| job `failed` with `output_corrupted` | the image was blank/uniform or the wrong size (the class of silent failure seen in research) |
| job `failed`: "worker killed by signal" | likely out-of-memory or crash; see `data/jobs/<id>/worker.log` |
| job `failed` on battery | mflux stops generating when battery ≤5% (`--battery-percentage-stop-limit`) |
| `queue_full` (429) | 20 queued/running jobs by default (`config/photogen.toml`) |
| CLI "waiting: another process is generating" | the API server holds the GPU lock; the CLI starts when it's released |

## Limitations
- One backend, one model, text-to-image only. No editing, img2img, LoRA, ControlNet or negative prompts.
- One generation at a time. Concurrency isn't validated on this hardware.
- No progress streaming (use `?wait=` long-polling). No GUI.
- Each job pays ≈2.6 s of worker start-up (≈3% at 1024²) in exchange for the validated memory profile.
- Thermal state is inferred from timings; there's no temperature telemetry.

## Layout
```
app/photogen/        application (config, models, runtimes/, jobs, store, api, cli, integrity, imaging, system)
app/tests/           unit + API tests (stdlib unittest)
bin/photo-gen        launcher (uses the validated interpreter, sets offline env)
config/              photogen.toml (user) + backend-zimage-mflux.json (immutable backend identity)
research/            research evidence (read-only for the application)
```
Run the tests with:
```sh
cd app/tests && PHOTOGEN_ROOT=../.. PYTHONPATH=..:. ../../mflux/.venv/bin/python3.12 -m unittest -v
```
