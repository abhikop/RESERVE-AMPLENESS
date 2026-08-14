"""Resolve logical dataset names to concrete snapshot paths."""
from __future__ import annotations

import json
import pathlib

RAW = pathlib.Path(__file__).resolve().parents[3] / "DATA" / "RAW"
REGISTRY = RAW / "registry.json"


def resolve(key: str, registry: pathlib.Path = REGISTRY) -> pathlib.Path:
    """Return the absolute path of the snapshot registered under `key`."""
    entries = json.loads(registry.read_text())
    if key not in entries:
        raise KeyError(f"{key!r} not in {registry}; available: {sorted(entries)}")
    path = registry.parent / entries[key]
    if not path.exists():
        raise FileNotFoundError(f"registry entry {key!r} points at missing file: {path}")
    return path