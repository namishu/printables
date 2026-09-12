from __future__ import annotations

import re
from importlib.resources import files
from pathlib import Path

import yaml

from ..core.configuration import merge, resolve_fonts
from .catalog import CATEGORIES


def validate(cfg: dict) -> None:
    if cfg["card"]["shape"] not in {"square", "rectangle"}:
        raise ValueError("card.shape must be square or rectangle")
    columns = cfg["grid"]["columns"]
    if type(columns) is not int or columns <= 0:
        raise ValueError("grid.columns must be a positive integer")
    for section, values in cfg.items():
        for name, value in values.items():
            if isinstance(value, bool):
                continue
            if isinstance(value, (int, float)):
                zero = name.startswith("margin_") or name in {"column_gap_mm", "row_gap_mm"}
                if value < 0 if zero else value <= 0:
                    raise ValueError(f"{section}.{name} must be {'non-negative' if zero else 'positive'}")
            if name.endswith("color") and not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
                raise ValueError(f"{section}.{name} must be #RRGGBB")
    layout = cfg["layout"]
    if layout["margin_left_mm"] + layout["margin_right_mm"] >= layout["width_mm"]:
        raise ValueError("Horizontal margins leave no usable width")
    if layout["margin_top_mm"] + layout["margin_bottom_mm"] >= layout["height_mm"]:
        raise ValueError("Vertical margins leave no usable height")
    if any(not raw.strip() for raw in cfg["fonts"].values()):
        raise ValueError("Font paths must be bundled or a font path")


def load_configs(path: Path | None) -> dict[str, dict]:
    base = yaml.safe_load(
        files("namishu_printables.pinyin_card").joinpath("config/defualt.yaml").read_text(encoding="utf-8")
    )
    defaults = base.pop("categories")
    override = {} if path is None else yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    if not isinstance(override, dict):
        raise ValueError("config must be a mapping")
    override = dict(override)
    categories = override.pop("categories", {})
    if not isinstance(categories, dict):
        raise ValueError("categories must be a mapping")
    if unknown := set(categories) - {c.id for c in CATEGORIES}:
        raise ValueError(f"Unknown categories: {sorted(unknown, key=str)}")
    result = {}
    for category in CATEGORIES:
        # Built-in page settings supply the per-page fields of the configuration schema.
        page_defaults = defaults[category.id]
        cfg = {section: {**values, **page_defaults.get(section, {})} for section, values in base.items()}
        cfg = merge(cfg, override)
        cfg = merge(cfg, categories.get(category.id, {}), f"categories.{category.id}")
        validate(cfg)
        result[category.id] = {**cfg, "fonts": resolve_fonts(cfg["fonts"], path)}
    return result
