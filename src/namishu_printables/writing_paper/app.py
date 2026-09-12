from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from reportlab.lib.units import mm

from ..core.pdf import output_path as resolve_output_path
from ..core.pdf import pdf_document
from .configuration import load_config, parameter
from .drawing import draw_page


@dataclass(frozen=True)
class PagePlan:
    """Resolved page geometry in millimeters; rows count spaces or English groups."""

    kind: str
    rows: int
    columns: int
    page_width_mm: float
    page_height_mm: float
    x_mm: float
    y_mm: float
    width_mm: float
    height_mm: float
    cell_size_mm: float | None = None
    config: dict = field(default_factory=dict, repr=False, compare=False)

    @property
    def filename(self) -> str:
        return f"writing-paper-{self.kind}.pdf"


class WritingPaperApp:
    def __init__(self, config_path: str | Path | None = None):
        self.config_path = Path(config_path).resolve() if config_path is not None else None

    def plan(
        self,
        kind: str,
        *,
        rows: int | None = None,
        columns: int | None = None,
        cell_size: float | None = None,
    ) -> PagePlan:
        if kind not in {"lined", "grid", "english"}:
            raise ValueError("kind must be lined, grid, or english")
        if kind != "lined" and rows is not None:
            raise ValueError("rows is only supported for lined paper")
        if kind == "grid" and columns is not None:
            raise ValueError("grid columns are calculated from cell_size")
        if kind != "grid" and cell_size is not None:
            raise ValueError("cell_size is only supported for grid paper")
        cfg = load_config(self.config_path)
        layout = cfg["layout"]
        page_width, page_height = layout["width_mm"], layout["height_mm"]
        # Decimal arithmetic avoids dropping a full cell at exact decimal boundaries.
        width = (
            Decimal(str(page_width)) - Decimal(str(layout["margin_left_mm"])) - Decimal(str(layout["margin_right_mm"]))
        )
        height = (
            Decimal(str(page_height)) - Decimal(str(layout["margin_top_mm"])) - Decimal(str(layout["margin_bottom_mm"]))
        )
        x, y = layout["margin_left_mm"], layout["margin_bottom_mm"]
        if kind == "grid":
            cell_size = parameter(cfg, kind, "cell_size_mm", cell_size)
            side = Decimal(str(cell_size))
            columns, rows = int(width // side), int(height // side)
            if rows < 1 or columns < 1:
                raise ValueError("cell_size does not fit a complete square inside the page margins")
            grid_width, grid_height = columns * side, rows * side
            alignment = cfg["grid"]["layout"]
            x += float(width - grid_width) * {"start": 0, "center": 0.5, "end": 1}[alignment["horizontal_alignment"]]
            y += float(height - grid_height) * {"start": 1, "center": 0.5, "end": 0}[alignment["vertical_alignment"]]
            width, height = grid_width, grid_height
        else:
            columns = parameter(cfg, kind, "columns", columns)
            gap = cfg[kind]["layout"]["column_gap_mm"]
            if columns > 1 and float(width) / columns <= (gap if columns > 2 else gap / 2):
                raise ValueError("column_gap_mm leaves no writing width; reduce the gap or columns")
            if kind == "lined":
                rows = parameter(cfg, kind, "rows", rows)
            else:
                rows = cfg["english"]["layout"]["groups"]
                group_height = cfg["english"]["layout"]["group_height_mm"]
                if Decimal(str(group_height)) * rows > height:
                    raise ValueError("English groups do not fit; reduce groups or group_height_mm")
        return PagePlan(kind, rows, columns, page_width, page_height, x, y, float(width), float(height), cell_size, cfg)

    def generate(
        self,
        kind: str,
        *,
        rows: int | None = None,
        columns: int | None = None,
        cell_size: float | None = None,
        output_path: str | Path | None = None,
    ) -> Path:
        return self.render(self.plan(kind, rows=rows, columns=columns, cell_size=cell_size), output_path)

    def render(self, plan: PagePlan, output_path: str | Path | None = None) -> Path:
        """Render a previously resolved plan, returning its absolute output path."""
        output = resolve_output_path(output_path if output_path is not None else plan.filename)
        with pdf_document(output, title="Writing paper") as pdf:
            pdf.setPageSize((plan.page_width_mm * mm, plan.page_height_mm * mm))
            draw_page(pdf, plan)
            pdf.showPage()
        return output
