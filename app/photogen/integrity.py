"""Model-file and runtime-version verification. Reports drift; never repairs or downloads anything."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import logging
import platform
from dataclasses import dataclass
from pathlib import Path

from .config import BackendManifest, ModelFile

log = logging.getLogger(__name__)
_CHUNK = 1 << 24


def file_digest(path: Path, algo: str) -> str:
    size = path.stat().st_size
    if algo == "sha256":
        h = hashlib.sha256()
    elif algo == "git-sha1":  # git blob id, as published by the HF API for non-LFS files
        h = hashlib.sha1()
        h.update(f"blob {size}\0".encode())
    else:
        raise ValueError(f"unknown digest algorithm {algo}")
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(_CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class FileCheck:
    path: str
    ok: bool
    detail: str
    hashed: bool  # True if a full hash was computed now (vs. trusted from a still-valid cache entry)


def verify_model_files(manifest: BackendManifest, cache_path: Path, full: bool = False) -> list[FileCheck]:
    """Check every manifest file. A cache entry is trusted only if inode, size and mtime_ns are unchanged
    and it previously matched the manifest digest; otherwise the file is fully re-hashed."""
    try:
        cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    except (OSError, ValueError):
        cache = {}
    results, new_cache = [], {}
    for mf in manifest.model_files:
        results.append(_check_file(manifest.model_path, mf, cache, new_cache, full))
    own = {f"{mf.path}|{mf.algo}|{mf.digest}" for mf in manifest.model_files}
    new_cache.update({k: v for k, v in cache.items() if k not in own})  # keep entries owned by others (e.g. TE registry)
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(new_cache, indent=1))
    except OSError as e:
        log.warning("could not write integrity cache: %s", e)
    return results


def _check_file(root: Path, mf: ModelFile, cache: dict, new_cache: dict, full: bool) -> FileCheck:
    p = root / mf.path
    if not p.is_file():
        return FileCheck(mf.path, False, "missing", False)
    st = p.stat()
    if st.st_size != mf.size:
        return FileCheck(mf.path, False, f"size {st.st_size} != expected {mf.size}", False)
    key = f"{mf.path}|{mf.algo}|{mf.digest}"
    fingerprint = [st.st_ino, st.st_size, st.st_mtime_ns]
    if not full and cache.get(key) == fingerprint:
        new_cache[key] = fingerprint
        return FileCheck(mf.path, True, "unchanged since last full verification", False)
    got = file_digest(p, mf.algo)
    if got != mf.digest:
        return FileCheck(mf.path, False, f"{mf.algo} mismatch: got {got}", True)
    new_cache[key] = fingerprint
    return FileCheck(mf.path, True, f"{mf.algo} verified", True)


def check_versions(manifest: BackendManifest) -> dict:
    """Compare installed package versions and interpreter against the manifest."""
    checks = {}
    py = platform.python_version()
    checks["python"] = {"ok": py == manifest.python_version, "expected": manifest.python_version, "found": py}
    for pkg, want in manifest.packages.items():
        try:
            got = importlib.metadata.version(pkg)
        except importlib.metadata.PackageNotFoundError:
            got = None
        checks[pkg] = {"ok": got == want, "expected": want, "found": got}
    return checks
