from __future__ import annotations

import unicodedata
from importlib.resources import files
from pathlib import Path


def export_default(output_path: str | Path) -> Path:
    text = files(__package__).joinpath("data/values.txt").read_text(encoding="utf-8")
    output = Path(output_path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)
    return output


def read_items(file_path: str | Path | None, limits: dict) -> tuple[str, ...]:
    if file_path is None:
        text = files(__package__).joinpath("data/values.txt").read_text(encoding="utf-8")
    else:
        with Path(file_path).open("rb") as stream:
            raw = stream.read(limits["max_file_bytes"] + 1)
        if len(raw) > limits["max_file_bytes"]:
            raise ValueError(f"Input file exceeds limits.max_file_bytes ({limits['max_file_bytes']})")
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError("Input file must be UTF-8 text") from exc
    items = []
    for line in text.replace("\r\n", "\n").split("\n"):
        value = line.strip()
        if not value:
            continue
        if len(value) > limits["max_item_length"]:
            raise ValueError(f"Item exceeds limits.max_item_length ({limits['max_item_length']}): {value[:20]}")
        if any((unicodedata.category(char).startswith("C") or char in "\u2028\u2029") for char in value):
            raise ValueError("Items must not contain control or invisible formatting characters")
        items.append(value)
    if not items:
        raise ValueError("Input must contain at least one non-empty item")
    if len(items) > limits["max_items"]:
        raise ValueError(f"Input has {len(items)} items; limits.max_items is {limits['max_items']}")
    return tuple(items)
