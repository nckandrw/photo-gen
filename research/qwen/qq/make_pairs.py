"""Build the Q-Q review pairs (research/qwen/qq/PROTOCOL.md §6) from the run records, for `qq_blind.py prepare`.
One pair per (task, budget, seed) that has a completed q4 run and a completed q8 run; q8 repeats are never pairs.
The source is the staged input the model received (G2 sidecar input_image.staged_path).

Usage: mflux/.venv/bin/python3.12 research/qwen/qq/make_pairs.py <pairs.json>"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / "research/qwen/runs"


def done(rid: str) -> dict | None:
    ident = RUNS / rid / "worker" / "identity.json"
    if not ident.exists():
        return None
    x = json.loads(ident.read_text())
    return x if x.get("rc") == 0 and x.get("pixel_sha256") else None


def main(out: str) -> None:
    pairs, skipped = [], []
    for budget in (512, 1024):
        for task, kind in (("R02", ""), ("R12", ""), ("R15", ""), ("R12", "-s2")):
            q4, q8 = f"QQ-{budget}-{task}{kind}-q4", f"QQ-{budget}-{task}{kind}-q8"
            if not (RUNS / q4).exists() and not (RUNS / q8).exists():
                continue
            if not (done(q4) and done(q8)):
                skipped.append([q4, q8])
                continue
            sc = json.loads((RUNS / f"G2-{budget}-{task}{kind}" / "sidecar.json").read_text())
            pairs.append({"pair": f"{task}{kind}-{budget}", "task": task, "budget": budget, "seed": sc["seed"],
                          "kind": "second_seed" if kind else "primary", "source": sc["input_image"]["staged_path"],
                          "q4": str(RUNS / q4 / "worker" / "out.png"), "q8": str(RUNS / q8 / "worker" / "out.png"),
                          "q4_run": q4, "q8_run": q8})
    Path(out).write_text(json.dumps(pairs, indent=1))
    print(f"{len(pairs)} pairs -> {out}; not paired (a run missing or failed): {skipped}")


if __name__ == "__main__":
    main(sys.argv[1])
