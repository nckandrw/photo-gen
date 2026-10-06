"""Verify Phase 4 downloads against the pinned HF manifest (upstream-file-manifest.json). Read-only.

Usage (from the repo root): mflux/.venv/bin/python3.12 research/qwen/verify_downloads.py
Writes research/qwen/download-verification.json and exits non-zero on any mismatch or missing file."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = json.loads((ROOT / "research/qwen/upstream-file-manifest.json").read_text())["repos"]
TARGETS = {
    "Qwen/Qwen-Image-2.1": (ROOT / "models/research/qwen-image-2.1", None),
    "Qwen/Qwen3-VL-8B-Instruct-GGUF": (ROOT / "models/text_encoders",
                                       {"Qwen3VL-8B-Instruct-Q4_K_M.gguf", "mmproj-Qwen3VL-8B-Instruct-F16.gguf"}),
}


def digest(path: Path, algo: str) -> str:
    h = hashlib.sha256() if algo == "sha256" else hashlib.sha1()
    if algo == "git-sha1":
        h.update(f"blob {path.stat().st_size}\0".encode())
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 24), b""):
            h.update(chunk)
    return h.hexdigest()


report, bad = {}, 0
for repo, (base, subset) in TARGETS.items():
    rows = []
    for f in MANIFEST[repo]["files"]:
        if subset is not None and f["path"] not in subset:
            continue
        p = base / f["path"]
        if not p.is_file():
            rows.append({**f, "ok": False, "detail": "missing"}); bad += 1; continue
        got = digest(p, f["algo"])
        ok = got == f["digest"] and (f["size"] is None or p.stat().st_size == f["size"])
        bad += not ok
        rows.append({"path": f["path"], "algo": f["algo"], "digest": f["digest"], "size": f["size"], "ok": ok,
                     **({} if ok else {"found": got, "found_size": p.stat().st_size})})
        print(("OK  " if ok else "BAD ") + f"{repo}:{f['path']}", flush=True)
    report[repo] = {"revision": MANIFEST[repo]["revision"], "local_dir": str(base.relative_to(ROOT)),
                    "files": rows, "all_ok": all(r["ok"] for r in rows)}
(ROOT / "research/qwen/download-verification.json").write_text(json.dumps(report, indent=1))
print("ALL OK" if not bad else f"{bad} PROBLEM(S)")
sys.exit(1 if bad else 0)
