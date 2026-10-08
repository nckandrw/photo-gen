"""Phase 6 Q-Q: assemble the q8 diagnostic export from its two per-component parts and record its identity
(research/qwen/qq/PROTOCOL.md §3). Pure Python (safetensors headers are parsed directly); no model code runs.

Usage: mflux/.venv/bin/python3.12 research/qwen/qq/merge_q8.py <part_vae_transformer> <part_text_encoder> <dst> <canonical_q4> <record.json>

1. Every file the two parts share (processor, scheduler, model_index.json, the three config.json) must be
   byte-identical between them; each is also compared with the canonical q4 export (recorded, expected equal).
2. <dst> is built by renaming (no copy): vae/ + transformer/ from the first part, text_encoder/ from the second,
   the shared files from the first. Refuses an existing <dst>.
3. Records sha256 + size of every file of <dst>, the safetensors metadata of every shard (quantization_level,
   mflux_version), and a tensor-level comparison of the VAE with the canonical q4 VAE (dtype, shape, raw bytes):
   the file bytes differ only through the shards' quantization_level metadata.
4. Leftover part files are removed only after each was shown byte-identical to the file kept in <dst>.
"""
import hashlib
import json
import os
import struct
import sys
import time
from pathlib import Path


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        while b := f.read(1 << 24):
            h.update(b)
    return h.hexdigest()


def files(root: Path) -> dict[str, Path]:
    return {str(p.relative_to(root)): p for p in sorted(root.rglob("*")) if p.is_file()}


def header(p: Path) -> tuple[dict, int]:
    with p.open("rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        return json.loads(f.read(n)), 8 + n


def tensors(comp_dir: Path) -> dict:
    out = {}
    for sh in sorted(comp_dir.glob("*.safetensors")):
        h, base = header(sh)
        for k, v in h.items():
            if k != "__metadata__":
                out[k] = (sh, base, v)
    return out


def raw(sh: Path, base: int, v: dict) -> bytes:
    a, b = v["data_offsets"]
    with sh.open("rb") as f:
        f.seek(base + a)
        return f.read(b - a)


def main(part_a: str, part_b: str, dst: str, canon: str, out: str) -> None:
    A, B, D, C = Path(part_a), Path(part_b), Path(dst), Path(canon)
    if D.exists():
        sys.exit(f"refusing: {D} exists")
    fa, fb, fc = files(A), files(B), files(C)
    weights = lambda rel: rel.endswith(".safetensors") or rel.endswith("model.safetensors.index.json")  # noqa: E731
    shared = sorted((set(fa) & set(fb)))
    shared_check = {rel: {"part_a": sha256(fa[rel]), "part_b": sha256(fb[rel])} for rel in shared}
    bad = [rel for rel, v in shared_check.items() if v["part_a"] != v["part_b"]]
    if bad or any(weights(r) for r in shared):
        sys.exit(f"refusing: shared files differ or include weights: {bad or [r for r in shared if weights(r)]}")
    for rel, v in shared_check.items():
        v["canonical_q4"] = sha256(fc[rel]) if rel in fc else None
        v["equal_to_canonical_q4"] = v["canonical_q4"] == v["part_a"]
    D.mkdir(parents=True)
    moved = []
    for comp, src in (("vae", A), ("transformer", A), ("text_encoder", B)):
        os.rename(src / comp, D / comp)
        moved.append(f"{src.name}/{comp}")
    for rel in sorted(fa):  # remaining files of part A not already provided by a moved component dir
        if (A / rel).exists() and not (D / rel).exists():
            (D / rel).parent.mkdir(parents=True, exist_ok=True)
            os.rename(A / rel, D / rel)
            moved.append(f"{A.name}/{rel}")
    leftovers = {}
    for root in (A, B):
        for rel, p in files(root).items():
            kept = D / rel
            same = kept.is_file() and sha256(kept) == sha256(p)
            leftovers[f"{root.name}/{rel}"] = same
    if not all(leftovers.values()):
        sys.exit(f"refusing to remove leftovers that differ from the kept files: {[k for k, v in leftovers.items() if not v]}")
    for root in (A, B):
        for rel, p in sorted(files(root).items(), reverse=True):
            p.unlink()
        for d in sorted((x for x in root.rglob("*") if x.is_dir()), key=lambda x: -len(x.parts)):
            d.rmdir()
        root.rmdir()
    fd = files(D)
    manifest = {rel: {"size": p.stat().st_size, "sha256": sha256(p)} for rel, p in fd.items()}
    shards = {}
    for rel, p in fd.items():
        if rel.endswith(".safetensors"):
            shards[rel] = header(p)[0].get("__metadata__")
    vq4, vq8 = tensors(C / "vae"), tensors(D / "vae")
    vae_diff = [k for k in sorted(set(vq4) | set(vq8)) if k not in vq4 or k not in vq8
                or vq4[k][2]["dtype"] != vq8[k][2]["dtype"] or vq4[k][2]["shape"] != vq8[k][2]["shape"]
                or raw(*vq4[k]) != raw(*vq8[k])]
    comp_bytes = {}
    for rel, v in manifest.items():
        comp_bytes[rel.split("/")[0] if "/" in rel else "."] = comp_bytes.get(rel.split("/")[0] if "/" in rel else ".", 0) + v["size"]
    rec = {"tool": "research/qwen/qq/merge_q8.py", "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "dst": dst,
           "parts": [part_a, part_b], "moved": moved, "shared_files": shared_check, "leftovers_identical_and_removed": leftovers,
           "files": manifest, "file_count": len(manifest), "total_bytes": sum(v["size"] for v in manifest.values()),
           "bytes_by_component": comp_bytes, "shard_metadata": shards,
           "vae_vs_canonical_q4": {"tensors_q4": len(vq4), "tensors_q8": len(vq8), "differing": vae_diff,
                                   "tensor_identical": not vae_diff}}
    Path(out).write_text(json.dumps(rec, indent=1))
    print(json.dumps({k: rec[k] for k in ("file_count", "total_bytes", "bytes_by_component", "vae_vs_canonical_q4")}, indent=1))
    print("shared files equal to canonical q4:", {k: v["equal_to_canonical_q4"] for k, v in shared_check.items()})
    print("shard metadata:", sorted({json.dumps(v, sort_keys=True) for v in shards.values()}))


if __name__ == "__main__":
    main(*sys.argv[1:6])
