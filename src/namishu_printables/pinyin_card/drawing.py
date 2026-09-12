from __future__ import annotations

from typing import TYPE_CHECKING

from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas

if TYPE_CHECKING:
    from .app import PagePlan


def draw_page(pdf: Canvas, page: PagePlan) -> None:
    pdf.setFillColor(HexColor(page.config["content"]["color"]))
    pdf.setFont(page.content_font, page.config["content"]["font_size_pt"])
    for card in page.cards:
        if page.config["card"]["enabled"] and card.box_mm is not None:
            x, y, width, height = card.box_mm
            pdf.setStrokeColor(HexColor(page.config["card"]["border_color"]))
            pdf.setLineWidth(page.config["card"]["border_width_pt"])
            pdf.rect(x * mm, y * mm, width * mm, height * mm)
        pdf.drawString(card.x_mm * mm, card.y_mm * mm, card.text)
