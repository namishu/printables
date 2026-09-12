from __future__ import annotations

from typing import TYPE_CHECKING

from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas

if TYPE_CHECKING:
    from .app import PagePlan


def _style(pdf: Canvas, style: dict) -> None:
    pdf.setStrokeColor(HexColor(style["color"]))
    pdf.setLineWidth(style["width_pt"])
    pdf.setDash([2, 2] if style.get("dashed", False) else [])


def draw_page(pdf: Canvas, plan: PagePlan) -> None:
    x, y = plan.x_mm * mm, plan.y_mm * mm
    width, height = plan.width_mm * mm, plan.height_mm * mm
    column_width = width / plan.columns
    style = plan.config[plan.kind]["style"]
    _style(pdf, style["vertical"])
    # Vertical lines always precede horizontal lines, including the outer edges.
    indices = range(plan.columns + 1) if plan.kind == "grid" else range(1, plan.columns)
    for index in indices:
        cx = x + index * column_width
        pdf.line(cx, y, cx, y + height)

    gap = plan.config[plan.kind]["layout"].get("column_gap_mm", 0) * mm

    def horizontal(at: float, line_style: dict) -> None:
        _style(pdf, line_style)
        if plan.kind == "grid" or plan.columns == 1:
            pdf.line(x, at, x + width, at)
            return
        for col in range(plan.columns):
            left = x + col * column_width + (gap / 2 if col else 0)
            right = x + (col + 1) * column_width - (gap / 2 if col < plan.columns - 1 else 0)
            pdf.line(left, at, right, at)

    if plan.kind == "english":
        group_height = plan.config["english"]["layout"]["group_height_mm"] * mm
        step = (height - group_height) / (plan.rows - 1) if plan.rows > 1 else 0
        top = y + height if plan.rows > 1 else y + (height + group_height) / 2
        for row in range(plan.rows):
            for line in (0, 1, 3, 2):
                horizontal(
                    top - row * step - line * group_height / 3, style["baseline"] if line == 2 else style["horizontal"]
                )
    else:
        for row in range(plan.rows + 1):
            line_style = style["boundary"] if row in (0, plan.rows) else style["horizontal"]
            horizontal(y + row * height / plan.rows, line_style)
