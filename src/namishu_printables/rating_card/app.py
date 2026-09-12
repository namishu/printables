from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics

from ..core.fonts import load_font, require_glyphs
from ..core.pdf import output_path as resolve_output
from ..core.pdf import pdf_document
from .configuration import load_config
from .drawing import draw_page


@dataclass(frozen=True)
class Text:
    value: str
    x: float
    y: float
    size: float
    style: str


@dataclass(frozen=True)
class Box:
    x: float
    y: float
    width: float
    height: float
    style: str


@dataclass(frozen=True)
class Line:
    x1: float
    y: float
    x2: float
    style: str = "table.horizontal"


@dataclass(frozen=True)
class Divider:
    x: float
    y1: float
    y2: float
    style: str


@dataclass(frozen=True)
class Heart:
    x: float
    y: float


@dataclass(frozen=True)
class PagePlan:
    font: str
    texts: tuple[Text, ...]
    boxes: tuple[Box, ...]
    lines: tuple[Line, ...]
    hearts: tuple[Heart, ...]
    badges: tuple[Box, ...]
    dividers: tuple[Divider, ...]
    config: dict = field(repr=False, compare=False)
    filename: str = field(default="rating-card.pdf", init=False)


class RatingCardApp:
    def __init__(self, config_path: str | Path | None = None):
        self.config_path = Path(config_path) if config_path is not None else None

    def plan(self) -> PagePlan:
        cfg = load_config(self.config_path)
        page, layout, title, table, heart, footer = (
            cfg[key] for key in ("page", "layout", "title", "table", "heart", "footer")
        )
        font = load_font(cfg["fonts"]["content"])
        labels = [table["labels"][key] for key in ("five", "four", "three", "two", "one")]
        require_glyphs(font, "".join(labels + [title["text"], footer["reviewer"], footer["date"]]))

        def width(value, size):
            return pdfmetrics.stringWidth(value, font, size) / mm

        def metrics(size):
            asc, desc = pdfmetrics.getAscentDescent(font, size)
            return asc / mm, desc / mm

        def height(size):
            asc, desc = metrics(size)
            return asc - desc

        def check_radius(style, w, h):
            border = style["border"]
            if 2 * border["radius_mm"] > min(w, h) - border["width_pt"] / mm:
                raise ValueError("Border radius does not fit the card dimensions")

        available_width = page["width_mm"] - page["margin_left_mm"] - page["margin_right_mm"]
        available_height = page["height_mm"] / 2 - page["margin_top_mm"] - page["margin_bottom_mm"]
        stroke = table["border"]["width_pt"] / mm
        horizontal = table["horizontal"]["width_pt"] / mm
        vertical = table["vertical"]["width_pt"] / mm
        padding = table["padding"]
        rs = table["font_size_pt"]
        content_height = max(height(rs), heart["size_mm"])
        # Equal row pitches include divider thickness and padding on both sides.
        row_height = content_height + padding["top_mm"] + padding["bottom_mm"] + horizontal
        box_height = 5 * row_height + 2 * stroke
        hearts_width = 5 * heart["size_mm"] + 4 * heart["gap_mm"]
        label_width = max(width(label, rs) for label in labels)
        horizontal_padding = padding["left_mm"] + padding["right_mm"]
        heart_area = hearts_width + horizontal_padding + vertical
        label_area = label_width + horizontal_padding + vertical
        writing_width = cfg["writing"]["width_mm"]
        if writing_width <= vertical / 2:
            raise ValueError("Writing column must be wider than its divider")
        total_width = 2 * stroke + heart_area + label_area + writing_width
        check_radius(table, total_width, box_height)
        if heart["width_pt"] / mm >= heart["size_mm"]:
            raise ValueError("Heart line width must be smaller than heart size")
        # Content must stay clear of rounded corners, including configurations with tiny padding.
        if (
            min(
                padding["left_mm"] + vertical / 2,
                padding["top_mm"] + horizontal / 2,
                padding["bottom_mm"] + horizontal / 2,
            )
            + stroke
            < table["border"]["radius_mm"]
        ):
            raise ValueError("Table padding must keep content clear of rounded corners")

        def badge_height(style):
            p = style["padding"]
            return height(style["font_size_pt"]) + p["top_mm"] + p["bottom_mm"] + 2 * style["border"]["width_pt"] / mm

        title_height, footer_height = badge_height(title), badge_height(footer)
        check_radius(title, title["width_mm"], title_height)
        check_radius(footer, footer["width_mm"], footer_height)
        if title["width_mm"] > total_width:
            raise ValueError("Title width exceeds the table width")
        if 2 * footer["width_mm"] + layout["footer_min_gap_mm"] > total_width:
            raise ValueError("Footer cards do not fit with layout.footer_min_gap_mm")
        block_height = title_height + box_height + footer_height + layout["title_gap_mm"] + layout["footer_gap_mm"]
        if total_width > available_width or block_height > available_height:
            raise ValueError("Card does not fit within half-page margins; reduce sizes, padding or gaps")
        cut_half_width = page["cut"]["width_pt"] / mm / 2
        clearance = min(page["margin_top_mm"], page["margin_bottom_mm"]) + (available_height - block_height) / 2
        if cut_half_width >= clearance:
            raise ValueError("Cut line does not fit between cards")
        left = page["margin_left_mm"] + (available_width - total_width) / 2
        texts, boxes, lines, hearts, badges, dividers = [], [], [], [], [], []

        def text(value, x, center, style_name):
            style = cfg[style_name]
            size = style["font_size_pt"]
            asc, desc = metrics(size)
            texts.append(Text(value, x, center - (asc + desc) / 2, size, style_name))

        def badge(value, x, top, style_name):
            style = cfg[style_name]
            p = style["padding"]
            border = style["border"]["width_pt"] / mm
            divider = style["separator"]["width_pt"] / mm
            size = style["font_size_pt"]
            h, w = badge_height(style), style["width_mm"]
            label_width = width(value, size) + p["left_mm"] + p["right_mm"]
            split = x + border + label_width + divider / 2
            blank = w - 2 * border - label_width - divider - p["left_mm"] - p["right_mm"]
            if blank < style["blank_min_width_mm"]:
                raise ValueError(f"{style_name} label must leave blank_min_width_mm for handwriting")
            badges.append(Box(x, top - h, w, h, style_name))
            text(value, x + border + p["left_mm"], top - border - p["top_mm"] - height(size) / 2, style_name)
            dividers.append(Divider(split, top - h + border, top - border, f"{style_name}.separator"))

        for half in (1, 0):
            top = (half + 1) * page["height_mm"] / 2 - page["margin_top_mm"] - (available_height - block_height) / 2
            badge(title["text"], left + (total_width - title["width_mm"]) / 2, top, "title")
            top -= title_height + layout["title_gap_mm"]
            boxes.append(Box(left, top - box_height, total_width, box_height, "table"))
            first_divider = left + stroke + heart_area
            second_divider = first_divider + label_area
            for x in (first_divider, second_divider):
                dividers.append(Divider(x, top - box_height + stroke, top - stroke, "table.vertical"))
            hx = left + stroke + vertical / 2 + padding["left_mm"]
            label_x = first_divider + vertical / 2 + padding["left_mm"]
            for row, label in enumerate(labels):
                center = top - stroke - row * row_height - horizontal / 2 - padding["top_mm"] - content_height / 2
                text(label, label_x, center, "table")
                for column in range(5 - row):
                    hearts.append(
                        Heart(hx + column * (heart["size_mm"] + heart["gap_mm"]), center - heart["size_mm"] / 2)
                    )
            for row in range(1, 5):
                lines.append(Line(left + stroke, top - stroke - row * row_height, left + total_width - stroke))
            top -= box_height + layout["footer_gap_mm"]
            badge(footer["reviewer"], left, top, "footer")
            badge(footer["date"], left + total_width - footer["width_mm"], top, "footer")
        return PagePlan(
            font, tuple(texts), tuple(boxes), tuple(lines), tuple(hearts), tuple(badges), tuple(dividers), cfg
        )

    def generate(self, *, output_path: str | Path | None = None) -> Path:
        return self.render(self.plan(), output_path=output_path)

    def render(self, plan: PagePlan, *, output_path: str | Path | None = None) -> Path:
        output = resolve_output(plan.filename if output_path is None else output_path)
        page = plan.config["page"]
        with pdf_document(output, title="评分卡") as pdf:
            pdf.setPageSize((page["width_mm"] * mm, page["height_mm"] * mm))
            draw_page(pdf, plan)
            pdf.showPage()
        return output
