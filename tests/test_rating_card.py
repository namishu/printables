from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pypdf import PdfReader
from reportlab.lib.units import mm

from namishu_printables.rating_card import RatingCardApp
from namishu_printables.rating_card import app as app_module


def configured(tmp_path, override):
    path = tmp_path / "design.yaml"
    path.write_text(yaml.safe_dump(override, allow_unicode=True), encoding="utf-8")
    return RatingCardApp(path)


def test_default_pdf_geometry_and_content(tmp_path):
    app = RatingCardApp()
    plan = app.plan()
    assert (len(plan.boxes), len(plan.badges), len(plan.hearts)) == (2, 6, 30)
    assert (len(plan.dividers), len(plan.lines)) == (10, 8)
    assert plan.boxes[0].y - plan.boxes[1].y == pytest.approx(148.5)
    stroke = plan.config["table"]["border"]["width_pt"] / mm
    for half, box in enumerate(plan.boxes):
        assert box.x + box.width / 2 == pytest.approx(105)
        title, reviewer, date = plan.badges[half * 3 : half * 3 + 3]
        assert title.x + title.width / 2 == pytest.approx(105)
        assert title.y - box.y - box.height == pytest.approx(11)
        assert reviewer.x == box.x
        assert date.x + date.width == pytest.approx(box.x + box.width)
        assert reviewer.width == date.width == 55
        assert reviewer.y == date.y
        assert reviewer.y + reviewer.height + 7 == pytest.approx(box.y)
        assert (title.y + title.height + reviewer.y) / 2 == pytest.approx(222.75 if half == 0 else 74.25)
        assert (
            plan.config[title.style]["border"]["radius_mm"] == plan.config[reviewer.style]["border"]["radius_mm"] == 3
        )
        splits = plan.dividers[half * 5 + 1 : half * 5 + 3]
        assert box.x < splits[0].x < splits[1].x < box.x + box.width
        assert box.x + box.width - stroke - splits[1].x == pytest.approx(60)
        rows = plan.lines[half * 4 : half * 4 + 4]
        assert all(line.x2 == pytest.approx(box.x + box.width - stroke) for line in rows)
        edges = [box.y + box.height - stroke, *(line.y for line in rows), box.y + stroke]
        heights = [edges[i] - edges[i + 1] for i in range(5)]
        assert heights == pytest.approx([heights[0]] * 5)
        first_heart = 0
        for row in range(5):
            item = plan.hearts[half * 15 + first_heart]
            assert item.y + 3.5 == pytest.approx((edges[row] + edges[row + 1]) / 2)
            first_heart += 5 - row
        for item in plan.hearts[half * 15 : half * 15 + 15]:
            assert box.x < item.x < item.x + 7 < splits[0].x
            assert box.y < item.y < item.y + 7 < box.y + box.height
    output = app.render(plan, output_path=tmp_path / "score.pdf")
    pdf = PdfReader(output)
    assert len(pdf.pages) == 1
    page = pdf.pages[0]
    assert float(page.mediabox.width) == pytest.approx(210 * mm, abs=0.001)
    assert float(page.mediabox.height) == pytest.approx(297 * mm, abs=0.001)
    extracted = page.extract_text()
    for value in ("评分卡", "评价人", "日期", "非常满意", "值得表扬", "没有问题", "差点意思", "无话可说"):
        assert extracted.count(value) == 2
    for value in ("选一行", "这次评价", "我想说", "得分人", "的评分", " 分"):
        assert value not in extracted
    assert not page["/Resources"].get("/XObject")
    moves = [tuple(map(float, args)) for args, op in page.get_contents().operations if op == b"m"]
    assert any(x == 0 and abs(y - 148.5 * mm) < 0.001 for x, y in moves)


def test_independent_styles_padding_and_snapshot(tmp_path):
    app = configured(
        tmp_path,
        {
            "page": {"margin_left_mm": 20, "margin_right_mm": 10, "margin_top_mm": 14, "margin_bottom_mm": 10},
            "layout": {"title_gap_mm": 8, "footer_gap_mm": 5},
            "title": {
                "font_size_pt": 20,
                "color": "#112233",
                "border": {"width_pt": 1.5, "color": "#224466"},
                "separator": {"width_pt": 0.9, "dash_length_mm": 3, "dash_gap_mm": 2},
            },
            "table": {
                "padding": {"left_mm": 4, "right_mm": 6, "top_mm": 2, "bottom_mm": 4},
                "labels": {"five": "特别棒"},
                "color": "#334455",
                "vertical": {"width_pt": 1.2, "color": "#778899", "dash_length_mm": 4},
                "horizontal": {"width_pt": 0.4, "color": "#998877"},
            },
            "footer": {"font_size_pt": 12, "color": "#556677", "border": {"width_pt": 1.2}},
        },
    )
    plan = app.plan()
    box = plan.boxes[0]
    assert box.x + box.width / 2 == pytest.approx(110)
    title, footer, _ = plan.badges[:3]
    assert (title.y + title.height + footer.y) / 2 == pytest.approx(220.75)
    assert title.y - box.y - box.height == pytest.approx(8)
    assert box.y - footer.y - footer.height == pytest.approx(5)
    split = plan.dividers[1]
    # Padding is measured from the visible divider edge.
    assert plan.texts[1].x - split.x - 1.2 / mm / 2 == pytest.approx(4)
    row_top = box.y + box.height - plan.config["table"]["border"]["width_pt"] / mm
    assert row_top - 0.4 / mm / 2 - (plan.hearts[0].y + 7) == pytest.approx(2)
    assert plan.config["title"]["border"]["width_pt"] != plan.config["table"]["border"]["width_pt"]
    app.config_path.unlink()
    page = PdfReader(app.render(plan, output_path=tmp_path / "custom.pdf")).pages[0]
    assert "特别棒" in page.extract_text()
    operations = page.get_contents().operations
    widths = [float(args[0]) for args, op in operations if op == b"w"]
    for expected in (1.5, 0.9, 1.2, 0.4):
        assert expected in widths
    colors = [tuple(map(float, args)) for args, op in operations if op == b"rg"]
    assert any(color == pytest.approx((17 / 255, 34 / 255, 51 / 255), abs=1e-6) for color in colors)


@pytest.mark.parametrize(
    "override",
    [
        {"unknown": 1},
        {"table": {"row_gap_mm": 5}},
        {"layout": {"title_gap_mm": 60}},
        {"table": {"padding": {"top_mm": -1}}},
        {"table": {"labels": {"five": "长" * 40}}},
        {"table": {"labels": {"one": "\n"}}},
        {"table": {"border": {"color": "red"}}},
        {"table": {"border": {"radius_mm": 100}}},
        {"heart": {"size_mm": True}},
        {"heart": {"size_mm": 0}},
        {"heart": {"width_pt": 30}},
        {"title": {"font_size_pt": float("nan")}},
        {"footer": {"reviewer": "很长" * 20}},
        {"footer": {"width_mm": 150}},
        {"writing": {"width_mm": 100}},
        {"writing": {"width_mm": 0}},
        {"footer": {"padding": {"top_mm": 40}}},
        {"title": {"text": "长" * 40}},
        {"page": {"cut": {"width_pt": 100}}},
        {"table": {"horizontal": {"width_pt": 100}}},
        {"title": {"separator": {"width_pt": 100}}},
        {"fonts": {"content": "missing.ttf"}},
    ],
)
def test_invalid_config_preserves_output(tmp_path, override):
    output = tmp_path / "existing.pdf"
    output.write_bytes(b"keep")
    with pytest.raises(ValueError):
        configured(tmp_path, override).generate(output_path=output)
    assert output.read_bytes() == b"keep"


def test_render_failure_preserves_output(tmp_path, monkeypatch):
    output = tmp_path / "existing.pdf"
    output.write_bytes(b"keep")

    def fail(*args):
        raise RuntimeError("draw failed")

    monkeypatch.setattr(app_module, "draw_page", fail)
    with pytest.raises(RuntimeError):
        RatingCardApp().generate(output_path=output)
    assert output.read_bytes() == b"keep"
    assert list(tmp_path.iterdir()) == [output]


def test_example_config_matches_defaults():
    example = Path(__file__).resolve().parents[1] / "examples/rating-card/design.yaml"
    assert RatingCardApp(example).plan().config == RatingCardApp().plan().config
    assert RatingCardApp(example).plan() == RatingCardApp().plan()


def test_frame_width_adapts_to_content(tmp_path):
    normal = RatingCardApp().plan()
    smaller = configured(
        tmp_path,
        {
            "table": {
                "labels": {
                    "five": "很棒",
                    "four": "不错",
                    "three": "还行",
                    "two": "加油",
                    "one": "努力",
                }
            }
        },
    ).plan()
    assert smaller.boxes[0].width < normal.boxes[0].width
    assert smaller.boxes[0].height == normal.boxes[0].height
    vertical = smaller.config["table"]["vertical"]["width_pt"] / mm
    assert smaller.texts[1].x - smaller.dividers[1].x - vertical / 2 == pytest.approx(5)
    assert smaller.dividers[1].x - smaller.hearts[4].x - 7 - vertical / 2 == pytest.approx(5)
