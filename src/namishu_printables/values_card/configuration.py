from __future__ import annotations

import re
from importlib.resources import files
from pathlib import Path

import yaml

from ..core.configuration import merge, resolve_fonts


def load_config(path: Path | None = None) -> dict:
    cfg = yaml.safe_load(files(__package__).joinpath("config/default.yaml").read_text(encoding="utf-8"))
    if path is not None:
        cfg = merge(cfg, yaml.safe_load(path.read_text(encoding="utf-8-sig")))
    for section in ("layout", "grid", "text", "checkbox", "separator", "limits"):
        for name, value in cfg[section].items():
            key = f"{section}.{name}"
            if name == "color":
                if not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
                    raise ValueError(f"{key} must be #RRGGBB")
                continue
            zero = name.startswith("margin_") or name.endswith("gap_mm")
            if value < 0 or (value == 0 and not zero):
                raise ValueError(f"{key} must be {'non-negative' if zero else 'positive'}")
            if (section == "limits" or name == "columns") and type(value) is not int:
                raise ValueError(f"{key} must be an integer")
    if cfg["text"]["min_font_size_pt"] > cfg["text"]["font_size_pt"]:
        raise ValueError("text.min_font_size_pt must not exceed text.font_size_pt")
    cfg["fonts"] = resolve_fonts(cfg["fonts"], path)
    return cfg
