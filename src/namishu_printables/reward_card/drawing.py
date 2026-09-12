from __future__ import annotations

from typing import TYPE_CHECKING

from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen.canvas import Canvas

from .images import read_icon

if TYPE_CHECKING:
    from .app import PagePlan


def draw_page(pdf: Canvas, plan: PagePlan) -> None:
    card, title, cut, page = (plan.config[k] for k in ("card", "title", "cut", "layout"))
    for boxes, style in ((plan.cards, card), (plan.labels, title)):
        stroke = style["border_width_pt"]
        pdf.setStrokeColor(HexColor(style["border_color"]))
        pdf.setLineWidth(stroke)
        for box in boxes:
            pdf.roundRect(
                box.x_mm * mm + stroke / 2,
                box.y_mm * mm + stroke / 2,
                box.width_mm * mm - stroke,
                box.height_mm * mm - stroke,
                style["border_radius_mm"] * mm,
                stroke=1,
                fill=0,
            )
    pdf.setFillColor(HexColor(title["color"]))
    for text in plan.texts:
        pdf.setFont(plan.font, text.size_pt)
        pdf.drawString(text.x_mm * mm, text.y_mm * mm, text.value)
    for line in plan.lines:
        pdf.setStrokeColor(HexColor(line.color))
        pdf.setLineWidth(line.width_pt)
        pdf.setDash([2 * mm, 1.5 * mm] if line.dashed else [])
        pdf.line(line.x1_mm * mm, line.y_mm * mm, line.x2_mm * mm, line.y_mm * mm)

    def icon(name, x, y, width, height):
        pdf.drawImage(read_icon(name), x * mm, y * mm, width * mm, height * mm, mask="auto")

    for item in plan.icons:
        icon(item.name, item.x_mm, item.y_mm, item.width_mm, item.size_mm)
    middle = page["height_mm"] / 2
    pdf.setStrokeColor(HexColor(cut["color"]))
    pdf.setLineWidth(cut["line_width_pt"])
    pdf.setDash([cut["dash_length_mm"] * mm, cut["dash_gap_mm"] * mm])
    pdf.line(0, middle * mm, page["width_mm"] * mm, middle * mm)
    pdf.setDash([])
    # White backing keeps the large, pale signature prompt legible on the cut line.
    text = plan.watermark
    width = pdfmetrics.stringWidth(text.value, plan.font, text.size_pt)
    asc, desc = pdfmetrics.getAscentDescent(plan.font, text.size_pt)
    pdf.setFillColorRGB(1, 1, 1)
    pdf.rect(text.x_mm * mm - 2 * mm, text.y_mm * mm + desc - mm, width + 4 * mm, asc - desc + 2 * mm, fill=1, stroke=0)
    pdf.setFillColor(HexColor(cut["watermark_color"]))
    pdf.setFont(plan.font, text.size_pt)
    pdf.drawString(text.x_mm * mm, text.y_mm * mm, text.value)
    icon("cut", cut["icon_inset_mm"], middle - cut["icon_size_mm"] / 2, cut["icon_size_mm"], cut["icon_size_mm"])
