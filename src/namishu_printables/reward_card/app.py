from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics

from ..core.fonts import load_font, require_glyphs
from ..core.pdf import output_path as resolve_output_path
from ..core.pdf import pdf_document
from .configuration import load_config
from .drawing import draw_page
from .images import read_icon


@dataclass(frozen=True)
class Text:
    value: str
    x_mm: float
    y_mm: float
    size_pt: float


@dataclass(frozen=True)
class Box:
    x_mm: float
    y_mm: float
    width_mm: float
    height_mm: float


@dataclass(frozen=True)
class Line:
    x1_mm: float
    y_mm: float
    x2_mm: float
    dashed: bool
    width_pt: float
    color: str


@dataclass(frozen=True)
class Icon:
    name: str
    x_mm: float
    y_mm: float
    size_mm: float
    width_mm: float


@dataclass(frozen=True)
class PagePlan:
    font: str
    cards: tuple[Box, ...]
    labels: tuple[Box, ...]
    texts: tuple[Text, ...]
    lines: tuple[Line, ...]
    icons: tuple[Icon, ...]
    watermark: Text
    config: dict = field(repr=False, compare=False)
    filename: str = field(default="reward-card.pdf", init=False)


class RewardCardApp:
    def __init__(self, config_path: str | Path | None = None):
        self.config_path = Path(config_path).resolve() if config_path is not None else None

    def plan(self) -> PagePlan:
        cfg = load_config(self.config_path)
        page, card, title, upper, lower, cut = (
            cfg[k] for k in ("layout", "card", "title", "upper", "lower", "cut")
        )
        width = page["width_mm"] - page["margin_left_mm"] - page["margin_right_mm"]
        half = page["height_mm"] / 2
        height = half - page["margin_top_mm"] - page["margin_bottom_mm"]
        cw, ch = card["width_mm"], card["height_mm"]
        stroke = card["border_width_pt"] / mm
        if cw > width or ch > height:
            raise ValueError("Card does not fit inside half-page margins")
        if 2 * card["border_radius_mm"] > min(cw, ch) - stroke:
            raise ValueError("Card border radius exceeds half its inner size")
        font = load_font(cfg["fonts"]["content"])
        values = [upper["fields"][k]["title"] for k in ("reward", "expiry", "child")]
        require_glyphs(font, "".join(values) + lower["title"] + cut["text"])
        size = title["font_size_pt"]
        asc, desc = (v / mm for v in pdfmetrics.getAscentDescent(font, size))
        text_height = asc - desc
        lp, label_stroke = title["padding_mm"], title["border_width_pt"] / mm
        label_height = text_height + 2 * lp + 2 * label_stroke
        label_width = max(pdfmetrics.stringWidth(v, font, size) / mm for v in values) + 2 * lp + 2 * label_stroke
        x = page["margin_left_mm"] + (width - cw) / 2
        y = page["margin_bottom_mm"] + (height - ch) / 2
        cards = (Box(x, y + half, cw, ch), Box(x, y, cw, ch))
        labels, texts, lines, icons = [], [], [], []

        def centered(value, cx, cy):
            tw = pdfmetrics.stringWidth(value, font, size) / mm
            return Text(value, cx - tw / 2, cy - (asc + desc) / 2, size)

        def interior(box, section):
            pads = [section[f"padding_{side}_mm"] for side in ("left", "right", "top", "bottom")]
            if min(pads) < max(stroke, card["border_radius_mm"]):
                raise ValueError("Card padding must accommodate border width and radius")
            pl, pr, pt, pb = pads
            if pl + pr >= cw or pt + pb >= ch:
                raise ValueError("Padding does not fit card size")
            return box.x_mm + pl, box.x_mm + cw - pr, box.y_mm + ch - pt, ch - pt - pb

        left, right, top, room_height = interior(cards[0], upper)
        row_height = room_height / 3
        icon_size = label_height
        if label_height > row_height:
            raise ValueError("Field content does not fit card height")
        if upper["line_width_pt"] / mm >= row_height - text_height:
            raise ValueError("Writing line width is too large for field spacing")
        line_left = left + label_width + upper["title_gap_mm"]
        for index, key in enumerate(("reward", "expiry", "child")):
            item = upper["fields"][key]
            cy = top - row_height * (index + 0.5)
            labels.append(Box(left, cy - label_height / 2, label_width, label_height))
            text = centered(item["title"], left + label_width / 2, cy)
            texts.append(text)
            icon_width = 0.0
            if item["icon"] != "none":
                image_width, image_height = read_icon(item["icon"]).getSize()
                icon_width = icon_size * image_width / image_height
            line_right = right if item["icon"] == "none" else right - icon_width - upper["icon_gap_mm"]
            if line_right - line_left < 20:
                raise ValueError("Fields need at least 20 mm of handwriting width")
            # Align the visible bottom edge of the rule with the label frame's outer bottom.
            line_y = labels[-1].y_mm + upper["line_width_pt"] / mm / 2
            lines.append(Line(line_left, line_y, line_right, False, upper["line_width_pt"], upper["line_color"]))
            if item["icon"] != "none":
                icons.append(Icon(item["icon"], right - icon_width, cy - icon_size / 2, icon_size, icon_width))

        left, right, top, room_height = interior(cards[1], lower)
        value = lower["title"]
        char_height = text_height + lp
        vertical_height = len(value) * char_height + lp + 2 * label_stroke
        vertical_width = max(pdfmetrics.stringWidth(c, font, size) / mm for c in value) + 2 * lp + 2 * label_stroke
        if vertical_height > room_height:
            raise ValueError("Description label does not fit card")
        cx, cy = left + vertical_width / 2, top - room_height / 2
        labels.append(Box(left, cy - vertical_height / 2, vertical_width, vertical_height))
        for index, char in enumerate(value):
            texts.append(centered(char, cx, cy + (len(value) - 1) * char_height / 2 - index * char_height))
        line_left = left + vertical_width + lower["padding_left_mm"]
        if right - line_left < 20:
            raise ValueError("Description needs at least 20 mm of handwriting width")
        gap = room_height / lower["lines"]
        if gap < max(6, text_height + lower["line_width_pt"] / mm):
            raise ValueError("Description writing area does not fit card height")
        for index in range(lower["lines"]):
            baseline = top - gap * (index + 0.5) - (asc + desc) / 2
            lines.append(Line(line_left, baseline, right, True, lower["line_width_pt"], lower["line_color"]))
        if any(2 * title["border_radius_mm"] > min(box.width_mm, box.height_mm) - label_stroke for box in labels):
            raise ValueError("Title border radius exceeds half its inner size")
        ws = cut["watermark_font_size_pt"]
        wa, wd = (v / mm for v in pdfmetrics.getAscentDescent(font, ws))
        ww = pdfmetrics.stringWidth(cut["text"], font, ws) / mm
        if ww + 4 + 2 * (cut["icon_inset_mm"] + cut["icon_size_mm"]) > page["width_mm"]:
            raise ValueError("Watermark does not fit cut line")
        if max((wa - wd) / 2 + 2, cut["icon_size_mm"] / 2) > min(half - y - ch, y):
            raise ValueError("Watermark does not fit between cards")
        if cut["line_width_pt"] / mm / 2 >= min(half - y - ch, y):
            raise ValueError("Cut line width does not fit between cards")
        watermark = Text(cut["text"], (page["width_mm"] - ww) / 2, half - (wa + wd) / 2, ws)
        return PagePlan(font, cards, tuple(labels), tuple(texts), tuple(lines), tuple(icons), watermark, cfg)

    def generate(self, *, output_path: str | Path | None = None) -> Path:
        return self.render(self.plan(), output_path)

    def render(self, plan: PagePlan, output_path: str | Path | None = None) -> Path:
        output = resolve_output_path(output_path if output_path is not None else plan.filename)
        page = plan.config["layout"]
        with pdf_document(output, title="权益卡") as pdf:
            pdf.setPageSize((page["width_mm"] * mm, page["height_mm"] * mm))
            draw_page(pdf, plan)
            pdf.showPage()
        return output
