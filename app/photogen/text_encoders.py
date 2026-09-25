"""Optional text-encoder substitution (opt-in; default 'stock' = the validated pack, unchanged).

A substitute TE is usable only if it is registered in config/text-encoders.json with pinned file digests and
`enabled: true`. It runs through a composite model directory whose transformer/vae/tokenizer are symlinks to
the validated stock pack and whose text_encoder is the substitute; both properties are verified before every job.
Nothing is downloaded or converted here (conversion: research/experiments/convert_te_q4.py)."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .config import ModelFile
from .errors import ConfigError, RuntimeUnavailableError
from .integrity import _check_file

STOCK = "stock"
SHARED_COMPONENTS = ("transformer", "vae", "tokenizer")


@dataclass(frozen=True)
class TextEncoderEntry:
    name: str
    enabled: bool
    te_path: Path
    composite_path: Path
    files: tuple[ModelFile, ...]
    info: dict  # source repo/revision, conversion, status, report — recorded in job metadata


def load_registry(path: Path, root: Path) -> dict[str, TextEncoderEntry]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text())["text_encoders"]
        reg = {}
        for name, e in raw.items():
            if name == STOCK or not name.replace("-", "").replace("_", "").isalnum():
                raise ValueError(f"invalid text encoder name {name!r}")
            reg[name] = TextEncoderEntry(
                name=name, enabled=bool(e.get("enabled", False)),
                te_path=(root / e["te_path"]).resolve(), composite_path=(root / e["composite_path"]),
                files=tuple(ModelFile(**f) for f in e["files"]),
                info={k: v for k, v in e.items() if k not in ("files", "enabled", "te_path", "composite_path")})
        return reg
    except (OSError, KeyError, TypeError, ValueError) as ex:
        raise ConfigError(f"cannot load text encoder registry {path}: {ex}") from ex


def verify_entry(entry: TextEncoderEntry, stock_model_path: Path, cache_path: Path) -> dict:
    """Verify the composite layout and the substitute's file digests. Raises RuntimeUnavailableError on any problem."""
    problems = []
    comp = entry.composite_path
    for c in SHARED_COMPONENTS:
        p = comp / c
        if not p.exists() or p.resolve() != (stock_model_path / c).resolve():
            problems.append(f"{c} in {comp} does not resolve to the validated stock pack")
    if not (comp / "text_encoder").exists() or (comp / "text_encoder").resolve() != entry.te_path:
        problems.append(f"text_encoder in {comp} does not resolve to {entry.te_path}")
    try:
        cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    except (OSError, ValueError):
        cache = {}
    new_cache: dict = {}
    checks = [_check_file(entry.te_path, f, cache, new_cache, False) for f in entry.files]
    problems += [f"{c.path}: {c.detail}" for c in checks if not c.ok]
    if not entry.files:
        problems.append("no pinned files")
    try:
        cache.update(new_cache)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(cache, indent=1))
    except OSError:
        pass
    if problems:
        raise RuntimeUnavailableError(f"text encoder '{entry.name}' failed verification: " + "; ".join(problems))
    return {"files": {f.path: f.digest for f in entry.files}}
