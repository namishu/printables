from __future__ import annotations

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from reportlab.pdfbase import pdfmetrics


def text_bounds(font_name: str, texts: tuple[str, ...]) -> list[tuple[float, float, float, float]]:
    """Visible outline bounds at one point, including glyph advance offsets."""
    with TTFont(pdfmetrics.getFont(font_name).face.filename) as font:
        glyphs = font.getGlyphSet()
        cmap = font.getBestCmap()
        units = font["head"].unitsPerEm
        result = []
        for text in texts:
            pen = BoundsPen(glyphs)
            advance = 0
            for char in text:
                glyph = glyphs[cmap[ord(char)]]
                glyph.draw(TransformPen(pen, (1, 0, 0, 1, advance, 0)))
                advance += glyph.width
            if pen.bounds is None:
                raise ValueError(f"No visible outline for {text!r}")
            result.append(tuple(value / units for value in pen.bounds))
        return result
