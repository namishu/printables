from __future__ import annotations

import math
import re
from importlib.resources import files
from pathlib import Path

import yaml

from ..core.configuration import merge


def positive(value: object, name: str, *, integer: bool = False, zero: bool = False) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or (value < 0 if zero else value <= 0)
        or (integer and not isinstance(value, int))
    ):
        requirement = "non-negative" if zero else "positive"
        raise ValueError(f"{name} must be a {requirement} {'integer' if integer else 'finite number'}")


def load_config(path: str | Path | None = None) -> dict:
    cfg = yaml.safe_load(
        files("namishu_printables.writing_paper").joinpath("config/default.yaml").read_text(encoding="utf-8")
    )
    if path is not None:
        override = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        cfg = merge(cfg, override)
    validate_config(cfg)
    return cfg


def validate_config(cfg: dict) -> None:
    layout = cfg["layout"]
    for key, value in layout.items():
        positive(value, f"layout.{key}", zero=key.startswith("margin_"))
    if layout["margin_left_mm"] + layout["margin_right_mm"] >= layout["width_mm"]:
        raise ValueError("Horizontal margins leave no usable page width")
    if layout["margin_top_mm"] + layout["margin_bottom_mm"] >= layout["height_mm"]:
        raise ValueError("Vertical margins leave no usable page height")
    for kind, parameters in cfg["parameters"].items():
        for name, rule in parameters.items():
            location = f"parameters.{kind}.{name}"
            for key, value in rule.items():
                positive(value, f"{location}.{key}", integer=name != "cell_size_mm")
            if not rule["min"] <= rule["default"] <= rule["max"]:
                raise ValueError(f"{location} must satisfy min <= default <= max")
    for kind in ("lined", "grid", "english"):
        for name, style in cfg[kind]["style"].items():
            positive(style["width_pt"], f"{kind}.style.{name}.width_pt")
            if not re.fullmatch(r"#[0-9a-fA-F]{6}", style["color"]):
                raise ValueError(f"{kind}.style.{name}.color must be #RRGGBB")
    for kind in ("lined", "english"):
        positive(cfg[kind]["layout"]["column_gap_mm"], f"{kind}.layout.column_gap_mm", zero=True)
    english = cfg["english"]["layout"]
    positive(english["groups"], "english.layout.groups", integer=True)
    positive(english["group_height_mm"], "english.layout.group_height_mm")
    for direction in ("horizontal", "vertical"):
        if cfg["grid"]["layout"][f"{direction}_alignment"] not in {"start", "center", "end"}:
            raise ValueError(f"grid.layout.{direction}_alignment must be start, center, or end")
    grid_style = cfg["grid"]["style"]
    if grid_style["horizontal"]["width_pt"] <= grid_style["vertical"]["width_pt"]:
        raise ValueError("grid horizontal width_pt must be greater than vertical width_pt")


def parameter(cfg: dict, kind: str, name: str, value: int | float | None) -> int | float:
    rule = cfg["parameters"][kind][name]
    value = rule["default"] if value is None else value
    positive(value, name, integer=name != "cell_size_mm")
    if not rule["min"] <= value <= rule["max"]:
        raise ValueError(f"{name} must be between {rule['min']} and {rule['max']} (got {value})")
    return value
