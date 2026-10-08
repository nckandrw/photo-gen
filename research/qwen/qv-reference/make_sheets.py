"""Phase 8 Q-VR: build the review sheets list for qvr_blind.py prepare (PROTOCOL.md section 10) from the run records.
Item sheets (6): D0 (Phase 7 input.png), A1, A2, TF (if run) and, on R15-512, ID (if run). Composite sheet (1): the G2
R02-1024 output and the hard and feathered composites (if made). Every panel path is checked against its record.

Run: mflux/.venv/bin/python3.12 research/qwen/qv-reference/make_sheets.py <out.json>"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
P7 = ROOT / "research/qwen/runs"
RUNS = HERE / "runs"


def main(out: str) -> None:
    items = {i["task"]: i["staged"] for i in json.loads((ROOT / "research/qwen/qv/items.json").read_text())}
    sheets = []
    for b in (512, 1024):
        for t in ("R02", "R12", "R15"):
            panels = {"D0": str(P7 / f"QV-{b}-{t}-a/worker/input.png"),
                      "A1": str(RUNS / f"A1-{b}-{t}/data/roundtrip.png"),
                      "A2": str(RUNS / f"A2-{b}-{t}/data/roundtrip.png")}
            tf = RUNS / f"TF-{b}-{t}/data/roundtrip-tf.png"
            if tf.exists():
                panels["TF"] = str(tf)
            if (b, t) == (512, "R15"):
                r = P7 / "QVR-ID-512-R15/result.json"
                if r.exists() and json.loads(r.read_text()).get("status") == "completed":
                    panels["ID"] = json.loads(r.read_text())["output_path"]
            for p in panels.values():
                assert Path(p).is_file(), p
            sheets.append({"kind": "item", "task": t, "budget": b, "staged": items[t], "panels": panels})
    c = RUNS / "CMP-1024-R02/data/record.json"
    if c.exists():
        rec = json.loads(c.read_text())
        panels = {"G2": rec["edit"]}
        for k, arm in (("composite_hard", "HARD"), ("composite_feather", "FEATHER")):
            if k in rec:
                panels[arm] = str(ROOT / rec[k]["path"])
        sheets.append({"kind": "composite", "task": "R02", "budget": 1024, "staged": items["R02"],
                       "instruction": rec["instruction"], "panels": panels})
    Path(out).write_text(json.dumps(sheets, indent=1) + "\n")
    print(json.dumps([{"kind": s["kind"], "item": f"{s['task']}-{s['budget']}", "arms": list(s["panels"])} for s in sheets]))


if __name__ == "__main__":
    main(sys.argv[1])
