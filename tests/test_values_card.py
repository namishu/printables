from __future__ import annotations

import pytest
import yaml
from pypdf import PdfReader
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics

from namishu_printables.values_card import ValuesCardApp
from namishu_printables.values_card import app as app_module


def config(tmp_path, override):
    path = tmp_path / "design.yaml"
    path.write_text(yaml.safe_dump(override), encoding="utf-8")
    return path


def test_default_pdf_and_geometry(tmp_path):
    app = ValuesCardApp()
    plan = app.plan()
    assert (plan.columns, plan.rows, len(plan.items)) == (4, 20, 80)
    assert [i.value for i in plan.items[:4]] == ["健康", "诚实", "成长", "内心平静"]
    assert [i.value for i in plan.items[-4:]] == ["忠诚", "和平", "幽默感", "留下作品"]
    assert 12 <= plan.font_size_pt <= 18
    assert len({i.value for i in plan.items}) == 80
    assert all(len(i.value) <= 5 for i in plan.items)
    assert all(
        len(row.value) <= len(next_item.value)
        for index, row in enumerate(plan.items[:-1])
        if index % 4 < 3
        for next_item in [plan.items[index + 1]]
    )
    output = app.render(plan, output_path=tmp_path / "card.pdf")
    pdf = PdfReader(output)
    assert len(pdf.pages) == 1
    page = pdf.pages[0]
    assert float(page.mediabox.width) == pytest.approx(210 * mm, abs=0.001)
    assert float(page.mediabox.height) == pytest.approx(297 * mm, abs=0.001)
    assert page.extract_text().splitlines() == [i.value for i in plan.items]
    assert len([op for _, op in page.get_contents().operations if op == b"re"]) == 80
    assert not page["/Resources"].get("/XObject")
    ascent, descent = pdfmetrics.getAscentDescent(plan.font, plan.font_size_pt)
    for index, item in enumerate(plan.items):
        right = (
            item.x_pt
            + plan.checkbox_size_pt
            + 2.5 * mm
            + pdfmetrics.stringWidth(item.value, plan.font, plan.font_size_pt)
        )
        assert item.x_pt >= 20 * mm
        assert right <= 190 * mm + 1e-6
        assert item.center_y_pt - (ascent - descent) / 2 >= 20 * mm
        assert item.center_y_pt + (ascent - descent) / 2 <= 277 * mm
        if index % 4 < 3:
            assert right + 6 * mm <= plan.items[index + 1].x_pt + 1e-6


def test_file_order_blank_lines_duplicates_and_naming(tmp_path, monkeypatch):
    source = tmp_path / "家庭.txt"
    source.write_bytes("\ufeff 健康 \r\n\r\n内心的平静\n健康\nMeaningful work\n".encode())
    app = ValuesCardApp()
    assert [i.value for i in app.plan(file_path=source).items] == ["健康", "内心的平静", "健康", "Meaningful work"]
    monkeypatch.chdir(tmp_path)
    output = app.generate(file_path=source)
    assert output == tmp_path / "values-card-家庭.pdf"
    assert len(PdfReader(output).pages) == 1


@pytest.mark.parametrize(
    "content,error",
    [
        (b" \n", "at least one"),
        (b"\xff", "UTF-8"),
        (("健康\n" * 101).encode(), "max_items"),
        (("健" * 81).encode(), "max_item_length"),
        (b"x" * 65537, "max_file_bytes"),
        (b"a\x00b", "control"),
        (b"a\x0bb", "control"),
        ("a\u2028b".encode(), "control"),
        ("\U0001f9d0".encode(), "missing glyphs"),
        ("a\u200bb".encode(), "control"),
        ("\U0010ffff".encode(), "control"),
    ],
)
def test_invalid_inputs_preserve_output(tmp_path, content, error):
    source = tmp_path / "input.txt"
    source.write_bytes(content)
    output = tmp_path / "card.pdf"
    output.write_bytes(b"existing")
    with pytest.raises(ValueError, match=error):
        ValuesCardApp().generate(file_path=source, output_path=output)
    assert output.read_bytes() == b"existing"


@pytest.mark.parametrize(
    "override",
    [
        {"grid": {"columns": 0}},
        {"grid": {"columns": 1.5}},
        {"grid": {"columns": True}},
        {"grid": {"row_gap_mm": -1}},
        {"grid": {"columns": 100}},
        {"text": {"font_size_pt": float("nan")}},
        {"text": {"min_font_size_pt": 20}},
        {"text": {"color": "red"}},
        {"checkbox": {"line_width_pt": 20}},
        {"layout": {"margin_left_mm": 210}},
        {"layout": {"height_mm": 10}},
        {"limits": {"max_items": 1.5}},
        {"unknown": 1},
        {"fonts": {"content": "missing.ttf"}},
    ],
)
def test_invalid_config_or_layout(tmp_path, override):
    with pytest.raises(ValueError):
        ValuesCardApp(config(tmp_path, override)).plan()


def test_too_long_to_fit_and_item_limits_override(tmp_path):
    source = tmp_path / "input.txt"
    source.write_text("有意义的工作" * 10, encoding="utf-8")
    with pytest.raises(ValueError, match="one page"):
        ValuesCardApp().plan(file_path=source)
    source.write_text("健康\n" * 101, encoding="utf-8")
    plan = ValuesCardApp(config(tmp_path, {"limits": {"max_items": 101}, "grid": {"row_gap_mm": 2}})).plan(
        file_path=source
    )
    assert len(plan.items) == 101


def test_small_list_and_configurable_columns(tmp_path):
    source = tmp_path / "input.txt"
    source.write_text("成长\n健康\n家庭", encoding="utf-8")
    assert ValuesCardApp().plan(file_path=source).columns == 3
    plan = ValuesCardApp(config(tmp_path, {"grid": {"columns": 2}})).plan(file_path=source)
    assert (plan.columns, plan.rows) == (2, 2)
    assert plan.items[0].x_pt == plan.items[2].x_pt
    assert plan.items[0].center_y_pt > plan.items[2].center_y_pt


def test_font_shrinks_within_readability_limit(tmp_path):
    source = tmp_path / "input.txt"
    source.write_text("健康\n" * 100, encoding="utf-8")
    plan = ValuesCardApp(config(tmp_path, {"grid": {"row_gap_mm": 5}})).plan(file_path=source)
    assert 12 <= plan.font_size_pt < 18


def test_plan_is_rendered_without_rereading_file_or_config(tmp_path):
    path = config(tmp_path, {"grid": {"columns": 3}})
    source = tmp_path / "input.txt"
    source.write_text("成长\n健康", encoding="utf-8")
    app = ValuesCardApp(path)
    plan = app.plan(file_path=source)
    path.unlink()
    source.unlink()
    output = app.render(plan, output_path=tmp_path / "card.pdf")
    assert PdfReader(output).pages[0].extract_text().splitlines() == ["成长", "健康"]


def test_drawing_failure_preserves_destination(tmp_path, monkeypatch):
    output = tmp_path / "card.pdf"
    output.write_bytes(b"existing")

    def fail(*args):
        raise RuntimeError("draw failed")

    monkeypatch.setattr(app_module, "draw_page", fail)
    with pytest.raises(RuntimeError, match="draw failed"):
        ValuesCardApp().generate(output_path=output)
    assert output.read_bytes() == b"existing"
    assert list(tmp_path.iterdir()) == [output]


def test_adaptive_column_gaps_centering_and_separators(tmp_path):
    overrides = {
        "layout": {"margin_left_mm": 25, "margin_right_mm": 15, "margin_top_mm": 30, "margin_bottom_mm": 10},
        "grid": {"columns": 3, "row_gap_mm": 3},
    }
    app = ValuesCardApp(config(tmp_path, overrides))
    plan = app.plan()
    ascent, descent = pdfmetrics.getAscentDescent(plan.font, plan.font_size_pt)
    assert plan.checkbox_size_pt == pytest.approx(ascent - descent)
    assert plan.items[0].center_y_pt - plan.items[3].center_y_pt == pytest.approx(plan.checkbox_size_pt + 3 * mm)
    gaps = []
    for column in range(2):
        width = max(pdfmetrics.stringWidth(i.value, plan.font, plan.font_size_pt) for i in plan.items[column::3])
        gaps.append(plan.items[column + 1].x_pt - plan.items[column].x_pt - plan.checkbox_size_pt - 2.5 * mm - width)
    assert gaps[0] == pytest.approx(gaps[1])
    assert gaps[0] > 0
    assert plan.items[0].x_pt == pytest.approx(25 * mm)
    assert plan.block_width_pt == pytest.approx(170 * mm)
    assert plan.items[0].x_pt + plan.block_width_pt / 2 == pytest.approx(110 * mm)
    top, bottom = plan.separator_ys_pt
    assert top - 0.3 - (plan.items[0].center_y_pt + plan.checkbox_size_pt / 2) == pytest.approx(3 * mm)
    assert plan.items[-1].center_y_pt - plan.checkbox_size_pt / 2 - bottom - 0.3 == pytest.approx(3 * mm)
    assert (top + bottom) / 2 == pytest.approx(138.5 * mm)
    assert top + 0.3 <= 267 * mm
    assert bottom - 0.3 >= 10 * mm
    page = PdfReader(app.render(plan, output_path=tmp_path / "layout.pdf")).pages[0]
    assert len([op for _, op in page.get_contents().operations if op == b"l"]) == 2


def test_single_column_centered(tmp_path):
    source = tmp_path / "one.txt"
    source.write_text("陪伴\n信任", encoding="utf-8")
    plan = ValuesCardApp(config(tmp_path, {"grid": {"columns": 1}})).plan(file_path=source)
    assert plan.items[0].x_pt + plan.block_width_pt / 2 == pytest.approx(105 * mm)
    assert plan.items[0].x_pt == plan.items[1].x_pt
