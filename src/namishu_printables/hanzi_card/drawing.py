from __future__ import annotations

from typing import TYPE_CHECKING

from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen.canvas import Canvas

if TYPE_CHECKING:
    from .app import Card, DocumentPlan


def draw_page(pdf: Canvas, cards: tuple[Card, ...], plan: DocumentPlan) -> None:
    cfg = plan.config
    layout, style = cfg["layout"], cfg["card"]
    size = style["size_mm"] * mm
    separator = cfg["separator"]
    if separator["enabled"]:
        x = layout["width_mm"] / 2 * mm
        pdf.setStrokeColor(HexColor(separator["color"]))
        pdf.setLineWidth(separator["width_pt"])
        pdf.setDash([3, 2] if separator["dashed"] else [])
        pdf.line(x, 0, x, layout["height_mm"] * mm)
        pdf.setDash()
    for card in cards:
        x, y = card.x_mm * mm, card.y_mm * mm
        pdf.setStrokeColor(HexColor(style["border_color"]))
        pdf.setLineWidth(style["border_width_pt"])
        pdf.roundRect(x, y, size, size, style["border_radius_mm"] * mm)
        hanzi = cfg["hanzi"]
        font_size = hanzi["font_size_pt"]
        ascent, descent = pdfmetrics.getAscentDescent(plan.hanzi_font, font_size)
        pdf.setFont(plan.hanzi_font, font_size)
        pdf.setFillColor(HexColor(hanzi["color"]))
        pdf.drawCentredString(x + size / 2, y + size / 2 - (ascent + descent) / 2, card.character)
        if plan.pinyin_font:
            pinyin = cfg["pinyin"]
            _, descent = pdfmetrics.getAscentDescent(plan.pinyin_font, pinyin["font_size_pt"])
            pdf.setFont(plan.pinyin_font, pinyin["font_size_pt"])
            pdf.setFillColor(HexColor(pinyin["color"]))
            pdf.drawCentredString(x + size / 2, y + size + pinyin["gap_mm"] * mm - descent, card.pinyin)
