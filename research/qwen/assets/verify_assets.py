"""Phase 5 §9 / addendum: full-content verification of the Qwen-Image-2.1 assets before any deletion.

Hashes EVERY file (full read, no inode/mtime cache) of:
  - the canonical q4 export   models/qwen/qwen-image-2.1-edit-mflux-q4          (pinned: config/backend-qwen21-edit-mflux.json)
  - the duplicate q4 export   models/qwen/ABORTED-20261007T0005-qwen-image-2.1-edit-mflux-q4 (incident 1)
  - the source checkpoint     models/research/qwen-image-2.1                    (pinned: research/qwen/upstream-file-manifest.json)
and records sha256 + git-blob-sha1 + size + inode + link count for each, symlinks, and the comparisons:
  canonical vs manifest pins, duplicate vs canonical (path list, sizes, sha256, shared inodes), source vs upstream.
Read-only: it never modifies, moves or deletes anything.

Usage: mflux/.venv/bin/python3.12 research/qwen/assets/verify_assets.py <out.json>"""
import hashlib
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CANON = ROOT / "models/qwen/qwen-image-2.1-edit-mflux-q4"
DUP = ROOT / "models/qwen/ABORTED-20261007T0005-qwen-image-2.1-edit-mflux-q4"
SRC = ROOT / "models/research/qwen-image-2.1"


def hash_file(p: Path) -> dict:
    st = p.lstat()
    sha, git = hashlib.sha256(), hashlib.sha1()
    git.update(f"blob {st.st_size}\0".encode())
    with p.open("rb") as f:
        while chunk := f.read(16 * 1024 * 1024):
            sha.update(chunk)
            git.update(chunk)
    return {"size": st.st_size, "sha256": sha.hexdigest(), "git_sha1": git.hexdigest(), "inode": st.st_ino,
            "nlink": st.st_nlink}


def scan(d: Path) -> dict:
    files, links = {}, []
    for dirpath, dirnames, filenames in os.walk(d):
        for name in sorted(filenames):
            p = Path(dirpath) / name
            rel = str(p.relative_to(d))
            if p.is_symlink():
                links.append({"path": rel, "target": os.readlink(p)})
                continue
            files[rel] = hash_file(p)
        for name in dirnames:
            if (Path(dirpath) / name).is_symlink():
                links.append({"path": str((Path(dirpath) / name).relative_to(d)), "target": os.readlink(Path(dirpath) / name)})
    return {"path": str(d.relative_to(ROOT)), "files": files, "symlinks": links,
            "total_bytes": sum(f["size"] for f in files.values()), "file_count": len(files)}


def main(out: str) -> None:
    t0 = time.time()
    res = {"generated": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "tool": "research/qwen/assets/verify_assets.py"}
    canon, dup, src = scan(CANON), scan(DUP), scan(SRC)
    res["canonical_export"], res["duplicate_export"], res["source_checkpoint"] = canon, dup, src

    man = json.loads((ROOT / "config/backend-qwen21-edit-mflux.json").read_text())
    pins = {f["path"]: f for f in man["model"]["files"]}
    res["canonical_vs_manifest"] = {
        "pinned": len(pins),
        "mismatched": [p for p, f in pins.items() if canon["files"].get(p, {}).get("sha256") != f["digest"]
                       or canon["files"].get(p, {}).get("size") != f["size"]],
        "missing": [p for p in pins if p not in canon["files"]],
        "unpinned_present": sorted(set(canon["files"]) - set(pins)),
    }
    cf, df = canon["files"], dup["files"]
    res["duplicate_vs_canonical"] = {
        "same_path_set": set(cf) == set(df),
        "only_in_canonical": sorted(set(cf) - set(df)), "only_in_duplicate": sorted(set(df) - set(cf)),
        "sha256_or_size_differs": sorted(p for p in set(cf) & set(df)
                                         if (cf[p]["sha256"], cf[p]["size"]) != (df[p]["sha256"], df[p]["size"])),
        "shared_inodes": sorted(p for p in set(cf) & set(df) if cf[p]["inode"] == df[p]["inode"]),
        "files_with_nlink_gt_1": sorted([f"canonical:{p}" for p, f in cf.items() if f["nlink"] > 1]
                                        + [f"duplicate:{p}" for p, f in df.items() if f["nlink"] > 1]),
        "symlinks": {"canonical": canon["symlinks"], "duplicate": dup["symlinks"]},
    }
    res["duplicate_vs_canonical"]["byte_identical"] = (
        res["duplicate_vs_canonical"]["same_path_set"] and not res["duplicate_vs_canonical"]["sha256_or_size_differs"])

    up = json.loads((ROOT / "research/qwen/upstream-file-manifest.json").read_text())
    repo = up["repos"]["Qwen/Qwen-Image-2.1"]
    res["source_vs_upstream"] = {"repo": "Qwen/Qwen-Image-2.1", "revision": repo["revision"], "checked": 0,
                                 "mismatched": [], "missing": []}
    for f in repo["files"]:
        got = src["files"].get(f["path"])
        res["source_vs_upstream"]["checked"] += 1
        if got is None:
            res["source_vs_upstream"]["missing"].append(f["path"])
            continue
        key = "sha256" if f["algo"] == "sha256" else "git_sha1"
        if got[key] != f["digest"] or got["size"] != f["size"]:
            res["source_vs_upstream"]["mismatched"].append(f["path"])
    res["source_vs_upstream"]["extra_local"] = sorted(p for p in src["files"]
                                                      if p not in {f["path"] for f in repo["files"]})
    res["seconds"] = round(time.time() - t0, 1)
    Path(out).write_text(json.dumps(res, indent=1))
    print(json.dumps({k: res[k] for k in ("canonical_vs_manifest", "source_vs_upstream")}, indent=1))
    print("duplicate byte_identical:", res["duplicate_vs_canonical"]["byte_identical"],
          "shared_inodes:", res["duplicate_vs_canonical"]["shared_inodes"],
          "nlink>1:", res["duplicate_vs_canonical"]["files_with_nlink_gt_1"], "seconds:", res["seconds"])
    print("VERIFY_ASSETS_DONE")


if __name__ == "__main__":
    main(sys.argv[1])
