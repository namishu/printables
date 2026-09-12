from __future__ import annotations

from typing import TYPE_CHECKING

from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm

if TYPE_CHECKING:
    from reportlab.pdfgen.canvas import Canvas

    from .app import PagePlan


def draw_page(pdf: Canvas, plan: PagePlan) -> None:
    cfg = plan.config
    heart, cut = cfg["heart"], cfg["page"]["cut"]

    def line_style(path):
        style = cfg
        for part in path.split("."):
            style = style[part]
        pdf.setLineWidth(style["width_pt"])
        pdf.setStrokeColor(HexColor(style["color"]))
        pdf.setDash([style["dash_length_mm"] * mm, style["dash_gap_mm"] * mm])

    for box in (*plan.boxes, *plan.badges):
        border = cfg[box.style]["border"]
        stroke = border["width_pt"]
        pdf.setDash([])
        pdf.setStrokeColor(HexColor(border["color"]))
        pdf.setLineWidth(stroke)
        pdf.roundRect(
            box.x * mm + stroke / 2,
            box.y * mm + stroke / 2,
            box.width * mm - stroke,
            box.height * mm - stroke,
            border["radius_mm"] * mm,
            stroke=1,
            fill=0,
        )
    for text in plan.texts:
        pdf.setFillColor(HexColor(cfg[text.style]["color"]))
        pdf.setFont(plan.font, text.size)
        pdf.drawString(text.x * mm, text.y * mm, text.value)
    for line in plan.lines:
        line_style(line.style)
        pdf.line(line.x1 * mm, line.y * mm, line.x2 * mm, line.y * mm)
    for divider in plan.dividers:
        line_style(divider.style)
        pdf.line(divider.x * mm, divider.y1 * mm, divider.x * mm, divider.y2 * mm)
    pdf.setDash([])
    # Draw vector outlines, so hearts stay crisp at any print scale and need no icon font.
    stroke = heart["width_pt"]
    pdf.setLineWidth(stroke)
    pdf.setStrokeColor(HexColor(heart["color"]))
    for item in plan.hearts:
        x, y = item.x * mm + stroke / 2, item.y * mm + stroke / 2
        size = heart["size_mm"] * mm - stroke
        path = pdf.beginPath()
        path.moveTo(x + size / 2, y)
        path.curveTo(x + size * 0.39, y + size * 0.17, x, y + size * 0.46, x, y + size * 0.72)
        path.curveTo(x, y + size * 1.0, x + size * 0.36, y + size * 1.08, x + size / 2, y + size * 0.82)
        path.curveTo(x + size * 0.64, y + size * 1.08, x + size, y + size * 1.0, x + size, y + size * 0.72)
        path.curveTo(x + size, y + size * 0.46, x + size * 0.61, y + size * 0.17, x + size / 2, y)
        path.close()
        pdf.drawPath(path, stroke=1, fill=0)
    pdf.setLineWidth(cut["width_pt"])
    pdf.setStrokeColor(HexColor(cut["color"]))
    pdf.setDash([cut["dash_length_mm"] * mm, cut["dash_gap_mm"] * mm])
    middle = cfg["page"]["height_mm"] * mm / 2
    pdf.line(0, middle, cfg["page"]["width_mm"] * mm, middle)
    pdf.setDash([])
