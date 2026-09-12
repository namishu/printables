from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pypdf import PdfReader
from pypdf.generic import ContentStream
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics

import namishu_printables.reward_card.app as app_module
from namishu_printables.reward_card import RewardCardApp

ROOT = Path(__file__).resolve().parents[1]


def configured(tmp_path, data):
    path = tmp_path / "design.yaml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return RewardCardApp(path)


def test_single_page_blank_card_with_embedded_font(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    output = RewardCardApp().generate()
    reader = PdfReader(output)
    assert len(reader.pages) == 1
    page = reader.pages[0]
    assert float(page.mediabox.width) == pytest.approx(210 * mm, abs=0.01)
    assert float(page.mediabox.height) == pytest.approx(297 * mm, abs=0.01)
    assert page.extract_text().split() == ["权益名称", "截止日期", "孩子签名", "权", "益", "说", "明", "家长签名"]
    assert len(page["/Resources"]["/XObject"]) == 4
    fonts = [font.get_object() for font in page["/Resources"]["/Font"].values()]
    assert any("/FontFile2" in font.get("/FontDescriptor", {}) for font in fonts)
    operations = ContentStream(page.get_contents(), reader).operations
    assert sum(op == b"c" for _, op in operations) == 24  # Two cards and four framed labels.
    # Every straight rule is horizontal; no vertical divider or extra middle rules.
    paths = []
    for i, (args, op) in enumerate(operations):
        if op == b"l" and operations[i + 1][1] == b"S":
            start, previous = operations[i - 1]
            assert previous == b"m"
            assert start[1] == args[1]
            paths.append(float(args[1]) / mm)
    assert len(paths) == 7
    middle_index = next(
        i for i, (args, op) in enumerate(operations) if op == b"l" and abs(float(args[1]) / mm - 148.5) < 0.01
    )
    assert float(operations[middle_index - 1][0][0]) == 0
    assert float(operations[middle_index][0][0]) == pytest.approx(210 * mm, abs=0.01)
    assert sum(abs(y - 148.5) < 0.01 for y in paths) == 1
    assert len(list(tmp_path.iterdir())) == 1


def test_geometry_and_handwriting_space():
    plan = RewardCardApp().plan()
    assert len(plan.cards) == 2
    assert len(plan.labels) == 4
    for box, cy in zip(plan.cards, (222.75, 74.25), strict=True):
        assert box.x_mm + box.width_mm / 2 == 105
        assert box.y_mm + box.height_mm / 2 == cy
        assert (box.width_mm, box.height_mm) == (160, 88)
    assert len(plan.lines) == 6
    assert [line.dashed for line in plan.lines] == [False, False, False, True, True, True]
    for text in plan.texts:
        ascent, descent = (n / mm for n in pdfmetrics.getAscentDescent(plan.font, text.size_pt))
        width = pdfmetrics.stringWidth(text.value, plan.font, text.size_pt) / mm
        assert any(
            box.x_mm <= text.x_mm
            and text.x_mm + width <= box.x_mm + box.width_mm
            and box.y_mm <= text.y_mm + descent
            and text.y_mm + ascent <= box.y_mm + box.height_mm
            for box in plan.labels
        )
    for line in plan.lines:
        assert line.x2_mm - line.x1_mm >= 20
        assert any(
            box.x_mm + 10 <= line.x1_mm < line.x2_mm <= box.x_mm + box.width_mm - 10
            and box.y_mm + 10 <= line.y_mm <= box.y_mm + box.height_mm - 10
            for box in plan.cards
        )
    assert plan.labels[-1].x_mm == plan.labels[0].x_mm
    for upper, lower in zip(plan.lines[:3], plan.lines[3:], strict=True):
        assert upper.x1_mm > lower.x1_mm
        label = plan.labels[-1]
        assert lower.x1_mm - label.x_mm - label.width_mm == pytest.approx(plan.config["lower"]["padding_left_mm"])


@pytest.mark.parametrize(
    "data,match",
    [
        ({"unknown": 1}, "Unknown configuration"),
        ({"lower": {"lines": True}}, "Invalid value"),
        ({"lower": {"lines": 2.5}}, "positive integer"),
        ({"lower": {"lines": 0}}, "positive"),
        ({"lower": {"lines": 1000000}}, "does not fit"),
        ({"upper": {"title_gap_mm": 140}}, "20 mm"),
        ({"title": {"font_size_pt": 100}}, "does not fit"),
        ({"title": {"border_radius_mm": 100}}, "Title border radius"),
        ({"cut": {"watermark_font_size_pt": 400}}, "Watermark"),
        ({"upper": {"line_width_pt": 100}}, "too large"),
        ({"upper": {"title_gap_mm": float("nan")}}, "Invalid value"),
        ({"card": {"width_mm": 190}}, "half-page margins"),
        ({"card": {"height_mm": 50}}, "does not fit card height"),
        ({"card": {"border_radius_mm": 100}}, "radius"),
        ({"upper": {"padding_left_mm": 0.1}}, "border width"),
        ({"lower": {"padding_right_mm": 160}}, "Padding"),
        ({"card": {"border_color": "blue"}}, "#RRGGBB"),
        ({"lower": {"title": "说明" * 30}}, "Description label"),
        ({"cut": {"text": "\n签名"}}, "single-line"),
        ({"lower": {"title": " "}}, "single-line"),
        ({"lower": {"title": "\U0010ffff"}}, "missing glyphs"),
        ({"fonts": {"content": "missing.ttf"}}, "Cannot load font"),
        ({"upper": {"fields": {"reward": {"icon": "missing.png"}}}}, "Cannot load icon"),
        ({"cut": {"icon_size_mm": 200}}, "Watermark"),
    ],
)
def test_invalid_design_preserves_existing_pdf(tmp_path, data, match):
    output = tmp_path / "reward.pdf"
    output.write_bytes(b"existing PDF")
    app = configured(tmp_path, data)
    with pytest.raises(ValueError, match=match):
        app.generate(output_path=output)
    assert output.read_bytes() == b"existing PDF"
    assert not list(tmp_path.glob("*.tmp"))


def test_labels_lines_and_config_snapshot(tmp_path):
    app = configured(
        tmp_path,
        {"upper": {"fields": {"reward": {"title": "奖励名称"}, "child": {"title": "领取人"}}}, "lower": {"lines": 2}},
    )
    plan = app.plan()
    assert len(plan.lines) == 5
    app.config_path.write_text("upper:\n  fields:\n    reward:\n      title: 新的标题\n", encoding="utf-8")
    original = app.render(plan, tmp_path / "snapshot.pdf")
    assert "奖励名称" in PdfReader(original).pages[0].extract_text()
    assert "领取人" in PdfReader(original).pages[0].extract_text()
    assert app.plan().texts[0].value == "新的标题"


def test_font_relative_to_yaml_and_full_example(tmp_path, monkeypatch):
    design = tmp_path / "design"
    design.mkdir()
    (design / "font.ttf").write_bytes((ROOT / "src/namishu_printables/assets/fonts/NotoSansSC-Light.ttf").read_bytes())
    app = configured(design, {"fonts": {"content": "font.ttf"}})
    monkeypatch.chdir(tmp_path)
    assert app.plan().config["fonts"]["content"] == str(design / "font.ttf")
    example = RewardCardApp(ROOT / "examples/reward-card/design.yaml").plan()
    assert example.texts == RewardCardApp().plan().texts


def test_drawing_failure_is_atomic(tmp_path, monkeypatch):
    output = tmp_path / "reward.pdf"
    output.write_bytes(b"existing PDF")

    def fail(pdf, plan):
        pdf.drawString(10, 10, "partial")
        raise RuntimeError("drawing failed")

    monkeypatch.setattr(app_module, "draw_page", fail)
    with pytest.raises(RuntimeError, match="drawing failed"):
        RewardCardApp().generate(output_path=output)
    assert output.read_bytes() == b"existing PDF"
    assert list(tmp_path.iterdir()) == [output]


def test_custom_half_page_margins(tmp_path):
    plan = configured(
        tmp_path,
        {
            "layout": {
                "margin_left_mm": 10,
                "margin_right_mm": 30,
                "margin_top_mm": 15,
                "margin_bottom_mm": 25,
            }
        },
    ).plan()
    for box, cy in zip(plan.cards, (227.75, 79.25), strict=True):
        assert box.x_mm + box.width_mm / 2 == 95
        assert box.y_mm + box.height_mm / 2 == cy
    assert (
        plan.watermark.x_mm + pdfmetrics.stringWidth(plan.watermark.value, plan.font, plan.watermark.size_pt) / mm / 2
        == 105
    )


def test_migrated_icons_match_reference():
    reference = ROOT.parent / "printables-latex/07-reward-card/gfx"
    if not reference.exists():
        pytest.skip("Reference project is not available")
    for name in ("star", "event", "face", "cut"):
        assert (ROOT / f"src/namishu_printables/reward_card/gfx/{name}.png").read_bytes() == (
            reference / f"{name}.png"
        ).read_bytes()


def test_independent_padding_styles_and_frame_alignment(tmp_path):
    app = configured(
        tmp_path,
        {
            "title": {"font_size_pt": 20, "padding_mm": 3, "border_width_pt": 1.5, "color": "#123456"},
            "upper": {
                "padding_top_mm": 6,
                "padding_bottom_mm": 14,
                "padding_left_mm": 12,
                "padding_right_mm": 8,
                "line_color": "#ff0000",
                "line_width_pt": 1.2,
            },
            "lower": {
                "padding_top_mm": 14,
                "padding_bottom_mm": 6,
                "padding_left_mm": 8,
                "padding_right_mm": 12,
                "line_color": "#0000ff",
                "line_width_pt": 0.4,
            },
            "cut": {"text": "签字发卡", "dash_length_mm": 3, "dash_gap_mm": 2},
        },
    )
    plan = app.plan()
    for label, line in zip(plan.labels[:3], plan.lines[:3], strict=True):
        assert line.y_mm - line.width_pt / mm / 2 == pytest.approx(label.y_mm)
        assert (line.color, line.width_pt) == ("#ff0000", 1.2)
    for icon, label in zip(plan.icons, plan.labels[:3], strict=True):
        assert icon.size_mm == label.height_mm
        assert icon.y_mm == label.y_mm
    assert plan.labels[0].x_mm == plan.cards[0].x_mm + 12
    assert plan.labels[-1].x_mm == plan.cards[1].x_mm + 8
    assert plan.labels[-1].y_mm + plan.labels[-1].height_mm / 2 == plan.cards[1].y_mm + 40
    for line in plan.lines[3:]:
        assert (line.color, line.width_pt) == ("#0000ff", 0.4)
        assert line.x2_mm == plan.cards[1].x_mm + 160 - 12
        assert line.x1_mm == pytest.approx(plan.labels[-1].x_mm + plan.labels[-1].width_mm + 8)
    assert plan.lines[0].y_mm - plan.lines[1].y_mm == pytest.approx(68 / 3)
    reader = PdfReader(app.generate(output_path=tmp_path / "styled.pdf"))
    assert "签字发卡" in reader.pages[0].extract_text()
    operations = ContentStream(reader.pages[0].get_contents(), reader).operations
    assert any(op == b"d" and list(map(float, args[0])) == pytest.approx([3 * mm, 2 * mm]) for args, op in operations)


def test_custom_icons_and_disabled_icon(tmp_path, monkeypatch):
    image = tmp_path / "custom.png"
    image.write_bytes((ROOT / "src/namishu_printables/reward_card/gfx/star.png").read_bytes())
    app = configured(
        tmp_path,
        {
            "upper": {
                "fields": {"reward": {"icon": "custom.png"}, "expiry": {"icon": "none"}, "child": {"icon": "event"}}
            }
        },
    )
    monkeypatch.chdir(ROOT)
    plan = app.plan()
    assert len(plan.icons) == 2
    assert plan.icons[0].name == str(image)
    assert plan.lines[1].x2_mm - plan.lines[0].x2_mm == pytest.approx(plan.labels[0].height_mm + 6)
    assert app.generate(output_path=tmp_path / "custom.pdf").exists()


def test_wide_icon_keeps_label_height(tmp_path):
    from PIL import Image

    Image.new("RGB", (200, 100), "white").save(tmp_path / "wide.png")
    app = configured(tmp_path, {"upper": {"fields": {"reward": {"icon": "wide.png"}}}})
    plan = app.plan()
    icon = plan.icons[0]
    assert icon.size_mm == plan.labels[0].height_mm
    assert icon.width_mm == 2 * icon.size_mm
    assert icon.x_mm - plan.lines[0].x2_mm == pytest.approx(plan.config["upper"]["icon_gap_mm"])
    app.generate(output_path=tmp_path / "wide.pdf")


def test_title_padding_measured_from_inner_border(tmp_path):
    plan = configured(tmp_path, {"title": {"border_width_pt": 3, "padding_mm": 2}}).plan()
    stroke = 3 / mm
    for box, text in zip(plan.labels[:3], plan.texts[:3], strict=True):
        ascent, descent = (v / mm for v in pdfmetrics.getAscentDescent(plan.font, text.size_pt))
        assert text.y_mm + descent - box.y_mm - stroke == pytest.approx(2)
        assert box.y_mm + box.height_mm - stroke - text.y_mm - ascent == pytest.approx(2)


def test_oversized_cut_line_rejected(tmp_path):
    app = configured(tmp_path, {"cut": {"line_width_pt": 200}})
    with pytest.raises(ValueError, match="Cut line width"):
        app.plan()
