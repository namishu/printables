from __future__ import annotations

import math
import re
from importlib.resources import files
from pathlib import Path

import yaml

from ..core.configuration import merge, resolve_fonts
from .images import BUILTIN_ICONS, read_icon


def load_config(path: Path | None = None) -> dict:
    cfg = yaml.safe_load(files(__package__).joinpath("config/main.yaml").read_text(encoding="utf-8"))
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
                    name.startswith(("margin_", "padding_"))
                    or name.endswith("gap_mm")
                    or name in {"border_radius_mm", "icon_inset_mm"}
                )
                if not math.isfinite(value) or (value < 0 if zero else value <= 0):
                    raise ValueError(f"{key} must be {'non-negative' if zero else 'positive'}")
            elif not value.strip() or any(ord(c) < 32 or ord(c) == 127 or c in "\u2028\u2029" for c in value):
                raise ValueError(f"{key} must be non-empty single-line text")

    validate(cfg, "config")
    if type(cfg["lower"]["lines"]) is not int:
        raise ValueError("lower.lines must be a positive integer")
    for item in cfg["upper"]["fields"].values():
        raw = item["icon"]
        if raw in BUILTIN_ICONS or raw == "none":
            continue
        image_path = Path(raw)
        if not image_path.is_absolute():
            if path is None:
                raise ValueError("Relative icon paths require a YAML configuration file")
            image_path = path.parent / image_path
        read_icon(str(image_path))
        item["icon"] = str(image_path.resolve())
    cfg["fonts"] = resolve_fonts(cfg["fonts"], path)
    return cfg
