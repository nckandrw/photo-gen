# photo-gen parity gate — application vs research reference (2026-09-24)

Purpose (architecture addendum §14/§22 step 7): confirm the photo-gen runtime adapter reproduces the validated MFLUX configuration without regressions.
Conditions: AC power; Finder/Terminal/Claude Code only; photo-gen 0.1.0; mflux 0.20.0, mlx 0.32.2, Python 3.12.14; model q4 @ d2d3050 (hash-verified).
Path: 512² via CLI (`bin/photo-gen generate`), 1024² via HTTP API (`POST /generate` → `GET /jobs/{id}?wait=`).

| Res | Job | Pixel sha256 | vs research | Worker wall (s) | Load | TE | Denoise | VAE | Peak footprint (GB) | MLX peak (GB) | Research reference |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 512² | `20260924T102116Z-444c59` | 9ae59f590e8c0b3a… | **identical** | 21.658 | 1.232 | 0.668 | 17.936 | 0.425 | 6.819 | 5.627 | mf-512 / mf-512-probe: 22.0–30.4 s wall, 18.1–21.3 s denoise, 6.54–7.02 GB |
| 1024² | `20260924T102610Z-cb09d4` | fe47d88dfb4bec54… | **identical** | 86.648 | 1.073 | 0.646 | 81.535 | 2.024 | 7.266 | 5.697 | cool-chip 1024²: 84.6–103.8 s wall, 78.6–97.2 s denoise, 7.23–7.36 GB |

Per-step (1024²): [9.011, 8.743, 8.665, 9.062, 8.991, 8.982, 9.077, 9.233, 9.55] s — cool-chip regime (8.7–9.6 s/step), matching research cold runs.
Server process (API, idle→after job): 107 MB → 131 MB RSS; inference memory lives only in the per-job worker process.

**Result: PASS.** Output is pixel-identical to the research reference at both resolutions; time, memory and per-step profile fall within the research ranges for the same thermal state. The subprocess-per-job design adds ≈2.6 s per job (interpreter start + imports + lazy weight load; measured at 512² as worker wall 21.66 s vs in-process generate 19.03 s), ≈3% of a cool 1024² job.
