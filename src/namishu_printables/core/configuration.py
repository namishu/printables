"""Strict configuration merging shared by all templates."""

from __future__ import annotations

import math
from pathlib import Path


def merge(base: dict, override: dict, path: str = "config", *, auto_counts: bool = False) -> dict:
    if not isinstance(override, dict):
        raise ValueError(f"{path} must be a mapping")
    result = dict(base)
    for key, value in override.items():
        name = f"{path}.{key}"
        if key not in base:
            raise ValueError(f"Unknown configuration key: {name}")
        expected = base[key]
        if isinstance(expected, dict):
            result[key] = merge(expected, value, name, auto_counts=auto_counts)
            continue
        if auto_counts and key in {"rows", "columns"}:
            valid = value == "auto" or (type(value) is int and value > 0)
        elif isinstance(expected, bool):
            valid = isinstance(value, bool)
        elif isinstance(expected, (int, float)):
            valid = isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
        else:
            valid = isinstance(value, type(expected))
        if not valid:
            raise ValueError(f"Invalid value for {name}: {value!r}")
        result[key] = value
    return result


def resolve_fonts(fonts: dict[str, str], config_path: Path | None) -> dict[str, str]:
    resolved = {}
    for role, raw in fonts.items():
        if not raw.strip():
            raise ValueError(f"fonts.{role} must be bundled or a font file path")
        if raw == "bundled":
            resolved[role] = raw
        else:
            path = Path(raw)
            if not path.is_absolute():
                if config_path is None:
                    raise ValueError("Relative font paths require a YAML configuration file")
                path = config_path.parent / path
            resolved[role] = str(path.resolve())
    return resolved
