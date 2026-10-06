# Phase 4 incident log (append-only)

## 2026-10-07 00:05 — q4 export: watchdog abort did not stop the export
- **What happened.** `research/qwen/export-q4.sh` (first run) logged `ABORT: swap 8200MB (start 1977MB)` at 00:05:00 and `QWEN_EXPORT_ABORTED`. The declared threshold was swap growth > 6144 MB; kernel pressure stayed at level 2 (warn) and never reached critical.
- **Root cause (watchdog bug).** `$PID` was the `/usr/bin/time -l` wrapper. `kill -TERM/-KILL $PID` terminated only the wrapper (rc 143); its Python child was orphaned and kept running. It finished `save_model` normally ~20 s later and wrote `models/qwen/qwen-image-2.1-edit-mflux-q4.export.json` (78.1 s total; MLX active after load 10.289 GB; peak 11.884 GB).
- **Conditions.** AC power; the user's meeting apps (Microsoft, Brave, Slack) were open, 71% free before start; residual swap 1.98 GB before start. Most of the swap growth was the OS paging those apps out while the export held ≈ 11 GB.
- **Disposition.**
  - The output was not deleted. It was renamed `models/qwen/ABORTED-20261007T0005-qwen-image-2.1-edit-mflux-q4/` (gitignored) and is not used as the canonical export.
  - The watchdog was fixed to signal the Python child too (`pkill -P`).
  - The canonical export is a clean re-run; byte identity with the aborted copy is checked and recorded in `QWEN-EDITING-BASELINE.md`.
  - Evidence: `research/qwen/export/run1-aborted/` (console log, 1 Hz monitor CSV, `/usr/bin/time` output, stdout, the run's export.json).
- **Lesson for inference.** mflux 0.21.0's edit initializer materializes all three q4/fp32 components up front (≈ 10.3 GB active) before the text encoder can be released. That is the resident floor of every edit on this 16 GB machine.

## 2026-10-07 00:19 — harness edited while a chain was executing it (S2)
- **What happened.** `research/qwen/run_edit.sh` gained the `worker0/1` mode while the `S2-plain-512` instance (smoke chain 1) was inside its watchdog loop. zsh then continued reading at the old byte offset of the modified file. After S2's own `EDIT_RUN_END S2-plain-512 rc=0` line, it executed fragments of the loop body: a stray `uid=…` line and `break: not in while… loop` in `research/qwen/smoke-chain1.log`.
- **Impact.** None on the measurement. The mflux process had already exited (rc 0, `/usr/bin/time` 90.82 s, peak footprint 12.648 GB; `runs/S2-plain-512/console.log`). Its output is pixel-identical (RGB and RGBA) to S1 and S3. No orphaned monitor or edit process remained (checked with `pgrep`). S3 started afterwards and read the new file in full.
- **Fix.** The harness body is now a single function, parsed completely before it executes. Rule: never edit a script a running chain uses.
- **Follow-up (00:51).** After `main "$@"` returned, the B0r2 instance read past the end of the grown file and printed `run_edit.sh:63: parse error near ')'`. Nothing executed: the run had already finished, rc 0, and its result was recorded. The harness now ends with `main "$@"; exit $?`.
