from __future__ import annotations

from dataclasses import dataclass, field
from importlib.resources import files
from pathlib import Path

from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics

from ..core.fonts import load_font, require_glyphs
from ..core.pdf import output_path as resolve_output_path
from ..core.pdf import pdf_document
from .configuration import load_config
from .drawing import draw_page
from .input import build_pinyin, parse_text


@dataclass(frozen=True)
class Card:
    character: str
    pinyin: str
    x_mm: float
    y_mm: float


@dataclass(frozen=True)
class DocumentPlan:
    characters: str
    ignored_characters: int
    pages: tuple[tuple[Card, ...], ...]
    filename: str
    hanzi_font: str
    pinyin_font: str | None
    config: dict = field(repr=False, compare=False)


class HanziCardApp:
    def __init__(self, config_path: str | Path | None = None):
        self.config_path = Path(config_path).resolve() if config_path is not None else None

    def plan(
        self,
        text: str | None = None,
        *,
        file: str | Path | None = None,
        no_pinyin: bool = False,
        pinyin: str | None = None,
    ) -> DocumentPlan:
        if text is not None and file is not None:
            raise ValueError("Provide either text or file, exclusively")
        if not isinstance(no_pinyin, bool):
            raise ValueError("no_pinyin must be a boolean")
        builtin = text is None and file is None
        if builtin:
            text = files("namishu_printables.hanzi_card").joinpath("data/characters.txt").read_text(encoding="utf-8")
            text = "".join(text.split())
        elif file is not None:
            text = Path(file).read_text(encoding="utf-8-sig")
        cfg = load_config(self.config_path)
        maximum = 300 if builtin else cfg["input"]["max_characters"]
        chars, ignored, inline = parse_text(text, maximum)
        syllables = build_pinyin(chars, enabled=not no_pinyin, override=pinyin, inline=inline)
        hanzi_font = load_font(cfg["fonts"]["hanzi"])
        require_glyphs(hanzi_font, chars)
        pinyin_font = None
        if not no_pinyin:
            pinyin_font = load_font(cfg["fonts"]["pinyin"])
            require_glyphs(pinyin_font, "".join(syllables))
        layout, card = cfg["layout"], cfg["card"]
        half_width = layout["width_mm"] / 2
        height = layout["height_mm"]
        size = card["size_mm"]
        stroke = card["border_width_pt"] / mm
        if size + stroke > half_width:
            raise ValueError("Cards do not fit the half-page width; reduce card size")
        y = (height - size) / 2
        if y < stroke / 2:
            raise ValueError("Cards do not fit the page height")
        hanzi_size = cfg["hanzi"]["font_size_pt"]
        ascent, descent = pdfmetrics.getAscentDescent(hanzi_font, hanzi_size)
        room = (size - 2 * card["padding_mm"]) * mm
        if ascent - descent > room or any(pdfmetrics.stringWidth(c, hanzi_font, hanzi_size) > room for c in chars):
            raise ValueError("Hanzi font_size_pt does not fit inside the card padding")
        block_height = size
        if pinyin_font:
            pinyin_size = cfg["pinyin"]["font_size_pt"]
            ascent, descent = pdfmetrics.getAscentDescent(pinyin_font, pinyin_size)
            block_height += cfg["pinyin"]["gap_mm"] + (ascent - descent) / mm
            if any(pdfmetrics.stringWidth(s, pinyin_font, pinyin_size) > size * mm for s in syllables):
                raise ValueError("Pinyin font_size_pt is too large for the card width")
        if y + block_height + stroke / 2 > height:
            raise ValueError("Cards and pinyin do not fit the page height")
        pages = []
        for index in range(0, len(chars), 2):
            count = min(2, len(chars) - index)
            pages.append(
                tuple(
                    Card(
                        chars[index + col],
                        syllables[index + col],
                        (half_width - size) / 2 + col * half_width,
                        y,
                    )
                    for col in range(count)
                )
            )
        filename = "hanzi-card.pdf"
        return DocumentPlan(chars, ignored, tuple(pages), filename, hanzi_font, pinyin_font, cfg)

    def generate(
        self,
        text: str | None = None,
        *,
        file: str | Path | None = None,
        no_pinyin: bool = False,
        pinyin: str | None = None,
        output_path: str | Path | None = None,
    ) -> Path:
        plan = self.plan(text, file=file, no_pinyin=no_pinyin, pinyin=pinyin)
        if file is not None and output_path is not None and Path(file).resolve() == Path(output_path).resolve():
            raise ValueError("Output must not replace the input file")
        return self.render(plan, output_path)

    def render(self, plan: DocumentPlan, output_path: str | Path | None = None) -> Path:
        """Draw all pages into one PDF, replacing the destination only after success."""
        output = resolve_output_path(output_path if output_path is not None else plan.filename)
        with pdf_document(output, title="Hanzi cards") as pdf:
            layout = plan.config["layout"]
            pdf.setPageSize((layout["width_mm"] * mm, layout["height_mm"] * mm))
            for cards in plan.pages:
                draw_page(pdf, cards, plan)
                pdf.showPage()
        return output
