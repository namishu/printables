from __future__ import annotations

from typing import TYPE_CHECKING

from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen.canvas import Canvas

if TYPE_CHECKING:
    from .app import PagePlan


def draw_page(pdf: Canvas, plan: PagePlan) -> None:
    box = plan.config["checkbox"]
    size, stroke = plan.checkbox_size_pt, box["line_width_pt"]
    prefix = size + box["gap_mm"] * mm
    ascent, descent = pdfmetrics.getAscentDescent(plan.font, plan.font_size_pt)
    pdf.setFont(plan.font, plan.font_size_pt)
    pdf.setFillColor(HexColor(plan.config["text"]["color"]))
    pdf.setStrokeColor(HexColor(box["color"]))
    pdf.setLineWidth(stroke)
    for item in plan.items:
        # Keep the full checkbox stroke inside its allocated square.
        pdf.rect(
            item.x_pt + stroke / 2,
            item.center_y_pt - size / 2 + stroke / 2,
            size - stroke,
            size - stroke,
            stroke=1,
            fill=0,
        )
        pdf.drawString(item.x_pt + prefix, item.center_y_pt - (ascent + descent) / 2, item.value)

    separator = plan.config["separator"]
    pdf.setStrokeColor(HexColor(separator["color"]))
    pdf.setLineWidth(separator["line_width_pt"])
    left = plan.items[0].x_pt
    for y in plan.separator_ys_pt:
        pdf.line(left, y, left + plan.block_width_pt, y)
