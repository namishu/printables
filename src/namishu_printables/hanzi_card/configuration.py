from __future__ import annotations

import re
from importlib.resources import files
from pathlib import Path

import yaml

from ..core.configuration import merge, resolve_fonts


def load_config(path: Path | None) -> dict:
    cfg = yaml.safe_load(
        files("namishu_printables.hanzi_card").joinpath("config/default.yaml").read_text(encoding="utf-8")
    )
    if path is not None:
        cfg = merge(cfg, yaml.safe_load(path.read_text(encoding="utf-8-sig")))
    for section, values in cfg.items():
        for name, value in values.items():
            location = f"{section}.{name}"
            if isinstance(value, bool):
                continue
            if isinstance(value, (int, float)):
                zero_allowed = name.startswith("margin_") or name in {"padding_mm", "gap_mm", "border_radius_mm"}
                if value < 0 if zero_allowed else value <= 0:
                    raise ValueError(f"{location} must be {'non-negative' if zero_allowed else 'positive'}")
            if name.endswith("color") and not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
                raise ValueError(f"{location} must be #RRGGBB")
    if not isinstance(cfg["input"]["max_characters"], int):
        raise ValueError("input.max_characters must be a positive integer")
    layout = cfg["layout"]
    if layout["width_mm"] <= layout["height_mm"]:
        raise ValueError("Page must be landscape: width_mm must exceed height_mm")
    card = cfg["card"]
    if not 80 <= card["size_mm"] <= 120:
        raise ValueError("card.size_mm must be between 80 and 120")
    scale = card["size_mm"] / 100
    card["padding_mm"] *= scale
    cfg["hanzi"]["font_size_pt"] *= scale
    cfg["pinyin"]["font_size_pt"] *= scale
    cfg["pinyin"]["gap_mm"] *= scale
    if 2 * card["padding_mm"] >= card["size_mm"]:
        raise ValueError("card.padding_mm leaves no room for the character")
    if 2 * card["border_radius_mm"] > card["size_mm"]:
        raise ValueError("card.border_radius_mm exceeds half the card size")
    cfg["fonts"] = resolve_fonts(cfg["fonts"], path)
    return cfg
