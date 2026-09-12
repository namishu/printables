from __future__ import annotations

import re
import unicodedata
from importlib.resources import files
from pathlib import Path

import yaml

from ..core.configuration import merge, resolve_fonts


def load_config(path: Path | None = None) -> dict:
    cfg = yaml.safe_load(files(__package__).joinpath("config/default.yaml").read_text(encoding="utf-8"))
    if path is not None:
        cfg = merge(cfg, yaml.safe_load(path.read_text(encoding="utf-8-sig")))

    def validate(section, location):
        for name, value in section.items():
            key = f"{location}.{name}"
            if isinstance(value, dict):
                validate(value, key)
            elif name.endswith("color"):
                if not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
                    raise ValueError(f"{key} must be #RRGGBB")
            elif isinstance(value, (int, float)):
                zero = (
                    name.startswith("margin_")
                    or name.endswith(("gap_mm", "radius_mm"))
                    or location.endswith(".padding")
                )
                if value < 0 or (value == 0 and not zero):
                    raise ValueError(f"{key} must be {'non-negative' if zero else 'positive'}")
            elif not value.strip() or any(
                unicodedata.category(c).startswith("C") or c in "\u2028\u2029" for c in value
            ):
                raise ValueError(f"{key} must be non-empty single-line text")

    validate(cfg, "config")
    cfg["fonts"] = resolve_fonts(cfg["fonts"], path)
    return cfg
