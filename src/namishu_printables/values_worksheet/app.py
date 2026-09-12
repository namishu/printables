from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics

from ..core.fonts import load_font, require_glyphs
from ..core.pdf import output_path as resolve_output
from ..core.pdf import pdf_document
from .configuration import load_config
from .drawing import draw_page
from .input import read_items


@dataclass(frozen=True)
class Item:
    value: str
    x_pt: float
    center_y_pt: float


@dataclass(frozen=True)
class PagePlan:
    items: tuple[Item, ...]
    columns: int
    rows: int
    font: str
    font_size_pt: float
    checkbox_size_pt: float
    separator_ys_pt: tuple[float, float]
    block_width_pt: float
    config: dict
    filename: str


class ValuesWorksheetApp:
    def __init__(self, config_path: str | Path | None = None):
        self.config_path = Path(config_path) if config_path is not None else None

    def plan(self, *, file_path: str | Path | None = None) -> PagePlan:
        cfg = load_config(self.config_path)
        values = read_items(file_path, cfg["limits"])
        font = load_font(cfg["fonts"]["content"])
        require_glyphs(font, "".join(values))
        layout, grid, box, text = (cfg[name] for name in ("layout", "grid", "checkbox", "text"))
        width = (layout["width_mm"] - layout["margin_left_mm"] - layout["margin_right_mm"]) * mm
        height = (layout["height_mm"] - layout["margin_top_mm"] - layout["margin_bottom_mm"]) * mm
        columns = min(grid["columns"], len(values))
        rows = (len(values) + columns - 1) // columns
        row_gap = grid["row_gap_mm"] * mm
        # Column widths follow the longest label in each column; preserve row-major order.
        widths = [max(pdfmetrics.stringWidth(v, font, 1) for v in values[c::columns]) for c in range(columns)]
        ascent, descent = pdfmetrics.getAscentDescent(font, 1)
        metric_height = ascent - descent
        separator_stroke = cfg["separator"]["line_width_pt"]
        text_room = width - columns * box["gap_mm"] * mm
        separator_gap = row_gap
        row_room = (height - (rows - 1) * row_gap - 2 * separator_gap - 2 * separator_stroke) / rows
        size = min(
            text["font_size_pt"],
            text_room / (sum(widths) + columns * metric_height + (columns - 1) * 0.5),
            row_room / metric_height,
        )
        if size < text["min_font_size_pt"] - 1e-9:
            raise ValueError(
                "Items do not fit on one page at text.min_font_size_pt; shorten labels, reduce items, "
                "or adjust grid.columns, gaps or page margins in YAML"
            )
        box_size = size * metric_height
        if box["line_width_pt"] >= box_size:
            raise ValueError("checkbox.line_width_pt must be smaller than the checkbox")
        row_height = box_size
        prefix = box_size + box["gap_mm"] * mm
        column_widths = [prefix + w * size for w in widths]
        # Reserve half an em between columns when shrinking; distribute all remaining space equally.
        gap = max(0, (width - sum(column_widths)) / (columns - 1)) if columns > 1 else 0
        block_width = width if columns > 1 else column_widths[0]
        xs = [layout["margin_left_mm"] * mm + (width - block_width) / 2]
        for w in column_widths[:-1]:
            xs.append(xs[-1] + w + gap)
        block_height = rows * row_height + (rows - 1) * row_gap
        top = (layout["height_mm"] - layout["margin_top_mm"]) * mm - (height - block_height) / 2
        items = tuple(
            Item(v, xs[i % columns], top - row_height / 2 - (i // columns) * (row_height + row_gap))
            for i, v in enumerate(values)
        )
        filename = "values-worksheet.pdf" if file_path is None else f"values-worksheet-{Path(file_path).stem}.pdf"
        separator_offset = separator_gap + separator_stroke / 2
        separator_ys = (top + separator_offset, top - block_height - separator_offset)
        return PagePlan(items, columns, rows, font, size, box_size, separator_ys, block_width, cfg, filename)

    def generate(self, *, file_path: str | Path | None = None, output_path: str | Path | None = None) -> Path:
        return self.render(self.plan(file_path=file_path), output_path=output_path)

    def render(self, plan: PagePlan, *, output_path: str | Path | None = None) -> Path:
        output = resolve_output(plan.filename if output_path is None else output_path)
        layout = plan.config["layout"]
        with pdf_document(output, title="") as pdf:
            pdf.setPageSize((layout["width_mm"] * mm, layout["height_mm"] * mm))
            draw_page(pdf, plan)
            pdf.showPage()
        return output
