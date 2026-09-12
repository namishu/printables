from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Grid:
    rows: int
    columns: int
    column_width_mm: float
    line_height_mm: float
    width_mm: float
    height_mm: float


def text_grid(
    count: int,
    width: float,
    height: float,
    text_width: float,
    line_height: float,
    column_gap: float,
    row_gap: float,
    columns: int,
) -> Grid:
    columns = min(columns, count)
    rows = math.ceil(count / columns)
    drawn_width = columns * text_width + (columns - 1) * column_gap
    drawn_height = rows * line_height + (rows - 1) * row_gap
    if drawn_width > width + 1e-9 or drawn_height > height + 1e-9:
        raise ValueError("Text and gaps exceed usable area; reduce font size, gaps or margins")
    return Grid(rows, columns, text_width, line_height, drawn_width, drawn_height)
