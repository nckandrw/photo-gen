"""Build the G2 blind-review item list (protocol.md §5) from the run records, for `g2_blind.py prepare`.

Items = every distinct G2 output: all primary and second-seed runs. A repeat is added as an extra item only if its
RGB pixels differ from its original (then criterion D has already failed, protocol.md §5). Sources are the staged
inputs the model actually received (sidecar input_image.staged_path), so the rater sees what the model saw.

Usage: mflux/.venv/bin/python3.12 research/editing/real-world/make_items.py <items.json>   (writes items.json)"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE.parents[1] / "qwen" / "runs"


def main(out: str) -> None:
    rows, items = {}, []
    for d in sorted(RUNS.glob("G2-*")):
        res = json.loads((d / "result.json").read_text() or "{}")
        if res.get("status") != "completed":
            print(f"{d.name}: no completed output ({res.get('status')}); not an item (criterion O records it)")
            continue
        meta = json.loads(Path(res["metadata_path"]).read_text())
        parts = d.name.split("-")
        rows[d.name] = {"run": d.name, "task": parts[2], "budget": int(parts[1]),
                        "kind": {"s2": "second_seed", "rep": "repeat"}.get(parts[3] if len(parts) > 3 else "", "primary"),
                        "seed": meta["seed"], "source": meta["input_image"]["staged_path"],
                        "output": res["output_path"], "pixel_sha256": res["pixel_sha256"]}
    for r in rows.values():
        if r["kind"] == "repeat":
            orig = rows[r["run"].removesuffix("-rep")]
            if r["pixel_sha256"] == orig["pixel_sha256"]:
                continue  # identical pixels: already scored as its original
        items.append({k: r[k] for k in ("run", "task", "budget", "seed", "source", "output")})
    Path(out).write_text(json.dumps(items, indent=1))
    kinds = {}
    for r in rows.values():
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    print(f"{len(rows)} runs {kinds}; {len(items)} items -> {out}")


if __name__ == "__main__":
    main(sys.argv[1])
