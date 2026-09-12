from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files


@dataclass(frozen=True)
class Category:
    id: str
    items: tuple[str, ...]


CATEGORIES = tuple(
    Category(c["id"], tuple(c["items"]))
    for c in json.loads(
        files("namishu_printables.pinyin_chart").joinpath("data/categories.json").read_text(encoding="utf-8")
    )
)


def select(name: str) -> tuple[Category, ...]:
    if name == "all":
        return CATEGORIES
    for category in CATEGORIES:
        if category.id == name:
            return (category,)
    raise ValueError("category must be shengmu, yunmu, yinjie, or all")
