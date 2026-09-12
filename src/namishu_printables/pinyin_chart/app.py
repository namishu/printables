from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from reportlab.lib.units import mm

from ..core.fonts import load_font, require_glyphs
from ..core.pdf import output_path as resolve_output_path
from ..core.pdf import pdf_document
from .catalog import Category, select
from .configuration import load_configs
from .drawing import draw_page
from .layout import Grid, text_grid
from .typography import text_bounds


@dataclass(frozen=True)
class Card:
    text: str
    x_mm: float
    y_mm: float
    font_size_pt: float
    box_mm: tuple[float, float, float, float] | None = None


@dataclass(frozen=True)
class PagePlan:
    category: Category
    rows: tuple[tuple[Card, ...], ...]
    grid: Grid
    cards: tuple[Card, ...]
    content_font: str
    config: dict = field(repr=False, compare=False)


@dataclass(frozen=True)
class DocumentPlan:
    category: str
    pages: tuple[PagePlan, ...]

    @property
    def filename(self) -> str:
        return f"pinyin-chart-{self.category}.pdf"


class PinyinChartApp:
    def __init__(self, config_path: str | Path | None = None):
        self.config_path = Path(config_path).resolve() if config_path is not None else None

    def plan(self, category: str = "all") -> DocumentPlan:
        categories = select(category)
        configs = load_configs(self.config_path)
        pages = []
        for item in categories:
            cfg = configs[item.id]
            layout, content = cfg["layout"], cfg["content"]
            width = layout["width_mm"] - layout["margin_left_mm"] - layout["margin_right_mm"]
            height = layout["height_mm"] - layout["margin_top_mm"] - layout["margin_bottom_mm"]
            content_font = load_font(cfg["fonts"]["content"], content=True)
            require_glyphs(content_font, "".join(item.items))
            font_size = content["font_size_pt"]
            column_gap, row_gap = cfg["grid"]["column_gap_mm"], cfg["grid"]["row_gap_mm"]
            bounds = text_bounds(content_font, item.items)
            padding = cfg["card"]["padding_mm"]
            stroke = cfg["card"]["border_width_pt"] / mm
            box_width = max(x1 - x0 for x0, y0, x1, y1 in bounds) * font_size / mm
            box_height = max(y1 - y0 for x0, y0, x1, y1 in bounds) * font_size / mm
            if cfg["card"]["shape"] == "square":
                box_width = box_height = max(box_width, box_height)
            box_width += 2 * padding + stroke
            box_height += 2 * padding + stroke
            grid = text_grid(
                len(item.items), width, height, box_width, box_height, column_gap, row_gap, cfg["grid"]["columns"]
            )
            left = layout["margin_left_mm"] + (width - grid.width_mm) / 2
            bottom = layout["margin_bottom_mm"] + (height - grid.height_mm) / 2
            placed = []
            for i, (text, (x0, y0, x1, y1)) in enumerate(zip(item.items, bounds, strict=True)):
                x = left + (i % grid.columns) * (box_width + column_gap)
                y = bottom + (grid.rows - 1 - i // grid.columns) * (box_height + row_gap)
                placed.append(
                    Card(
                        text,
                        x + box_width / 2 - (x0 + x1) * font_size / mm / 2,
                        y + box_height / 2 - (y0 + y1) * font_size / mm / 2,
                        font_size,
                        (x + stroke / 2, y + stroke / 2, box_width - stroke, box_height - stroke),
                    )
                )
            cards = tuple(placed)
            rows = tuple(cards[i : i + grid.columns] for i in range(0, len(cards), grid.columns))
            pages.append(PagePlan(item, rows, grid, cards, content_font, cfg))
        return DocumentPlan(category, tuple(pages))

    def generate(self, category: str = "all", *, output_path: str | Path | None = None) -> Path:
        return self.render(self.plan(category), output_path)

    def render(self, plan: DocumentPlan, output_path: str | Path | None = None) -> Path:
        output = resolve_output_path(output_path if output_path is not None else plan.filename)
        with pdf_document(output, title="拼音表") as pdf:
            for page in plan.pages:
                layout = page.config["layout"]
                pdf.setPageSize((layout["width_mm"] * mm, layout["height_mm"] * mm))
                draw_page(pdf, page)
                pdf.showPage()
        return output
