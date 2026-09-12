from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from fontTools.ttLib import TTFont
from pypdf import PdfReader
from reportlab.lib.units import mm

import namishu_printables.pinyin_chart.app as app_module
from namishu_printables.pinyin_chart import PinyinChartApp
from namishu_printables.pinyin_chart.catalog import CATEGORIES
from namishu_printables.pinyin_chart.layout import text_grid

ROOT = Path(__file__).resolve().parents[1]


def configured(tmp_path, overrides):
    path = tmp_path / "design.yaml"
    path.write_text(yaml.safe_dump(overrides), encoding="utf-8")
    return PinyinChartApp(path)


@pytest.mark.parametrize("category,count", [("shengmu", 1), ("yunmu", 1), ("yinjie", 1), ("all", 3)])
def test_pdf_pages_content_order_no_footer(tmp_path, monkeypatch, category, count):
    monkeypatch.chdir(tmp_path)
    app = PinyinChartApp()
    plan = app.plan(category)
    output = app.render(plan)
    assert output == tmp_path / f"pinyin-chart-{category}.pdf"
    assert list(tmp_path.iterdir()) == [output]
    pdf = PdfReader(output)
    assert len(pdf.pages) == count
    for page, expected in zip(pdf.pages, plan.pages, strict=True):
        assert page.extract_text().splitlines() == list(expected.category.items)
        assert float(page.mediabox.width) == pytest.approx(297 * mm, abs=0.001)
        assert float(page.mediabox.height) == pytest.approx(210 * mm, abs=0.001)
        operations = page.get_contents().operations
        assert sum(op == b"re" for _, op in operations) == (len(expected.cards))
        assert any(
            "/FontFile2" in font.get_object().get("/FontDescriptor", {})
            for font in page["/Resources"]["/Font"].values()
        )


def test_category_contents():
    assert [(c.id, len(c.items)) for c in CATEGORIES] == [("shengmu", 23), ("yunmu", 24), ("yinjie", 16)]
    assert CATEGORIES[0].items == (
        "b",
        "p",
        "m",
        "f",
        "d",
        "t",
        "n",
        "l",
        "g",
        "k",
        "h",
        "j",
        "q",
        "x",
        "zh",
        "ch",
        "sh",
        "r",
        "z",
        "c",
        "s",
        "y",
        "w",
    )
    assert CATEGORIES[1].items == (
        "a",
        "o",
        "e",
        "i",
        "u",
        "ü",
        "ai",
        "ei",
        "ui",
        "ao",
        "ou",
        "iu",
        "ie",
        "üe",
        "er",
        "an",
        "en",
        "in",
        "un",
        "ün",
        "ang",
        "eng",
        "ing",
        "ong",
    )
    assert CATEGORIES[2].items == (
        "zhi",
        "chi",
        "shi",
        "ri",
        "zi",
        "ci",
        "si",
        "yi",
        "wu",
        "yu",
        "ye",
        "yue",
        "yuan",
        "yin",
        "yun",
        "ying",
    )


def test_pinyin_font_character_coverage():
    font = TTFont(ROOT / "src/namishu_printables/assets/fonts/pinyin-regular.ttf")
    cmap = font.getBestCmap()
    required = "abcdefghijklmnopqrstuvwxyzāáǎàōóǒòēéěèīíǐìūúǔùüǖǘǚǜ"
    assert all(ord(char) in cmap for char in required)
    assert font["name"].getDebugName(6) == "pinyin"


def test_font_paths_relative_to_config(tmp_path, monkeypatch):
    design = tmp_path / "design"
    design.mkdir()
    font = ROOT / "src/namishu_printables/assets/fonts/pinyin-regular.ttf"
    (design / "content.ttf").write_bytes(font.read_bytes())
    app = configured(design, {"fonts": {"content": "content.ttf"}})
    monkeypatch.chdir(tmp_path)
    assert app.plan("yunmu").pages[0].config["fonts"]["content"] == str(design / "content.ttf")
    assert app.generate("yunmu").exists()


def test_atomic_failure_keeps_existing_file(tmp_path, monkeypatch):
    output = tmp_path / "cards.pdf"
    output.write_bytes(b"old PDF")
    plan = PinyinChartApp().plan("all")
    original = app_module.draw_page
    count = 0

    def fail(pdf, page):
        nonlocal count
        count += 1
        if count == 2:
            raise RuntimeError("drawing failed")
        original(pdf, page)

    monkeypatch.setattr(app_module, "draw_page", fail)
    with pytest.raises(RuntimeError, match="drawing failed"):
        PinyinChartApp().render(plan, output)
    assert output.read_bytes() == b"old PDF"
    assert list(tmp_path.iterdir()) == [output]


def cli(tmp_path, *args):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "namishu_printables", "pinyin-chart", *args],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
    )


def test_cli_relative_paths_and_single_pdf(tmp_path):
    (tmp_path / "design.yaml").write_text("content:\n  font_size_pt: 48\n")
    result = cli(tmp_path, "all", "--config", "design.yaml", "--output", "out/cards.pdf")
    assert result.returncode == 0, result.stderr
    assert "3 pages" in result.stdout and "23 items" in result.stdout
    assert len(PdfReader(tmp_path / "out/cards.pdf").pages) == 3
    assert len(list(tmp_path.rglob("*.pdf"))) == 1


@pytest.mark.parametrize(
    "args,message",
    [
        (["abc"], "invalid choice"),
        (["unknown"], "invalid choice"),
        (["shengmu", "--rows", "4"], "unrecognized arguments"),
        (["yunmu", "--output", "cards.png"], ".pdf extension"),
        (["yunmu", "--config", "missing.yaml"], "No such file"),
    ],
)
def test_cli_errors(tmp_path, args, message):
    result = cli(tmp_path, *args)
    assert result.returncode == 2
    assert message in result.stderr
    assert "Traceback" not in result.stderr
    assert not list(tmp_path.glob("*.pdf"))


def test_cli_help(tmp_path):
    result = cli(tmp_path, "--help")
    assert result.returncode == 0
    assert "{shengmu,yunmu,yinjie,all}" in result.stdout


@pytest.mark.parametrize("category, count", [(None, 3), ("shengmu", 1), ("yunmu", 1), ("yinjie", 1)])
def test_cli_default_and_single_category(tmp_path, category, count):
    result = cli(tmp_path, *([] if category is None else [category]))
    assert result.returncode == 0, result.stderr
    pdf = PdfReader(tmp_path / f"pinyin-chart-{category or 'all'}.pdf")
    assert len(pdf.pages) == count
    assert all(not any(title in p.extract_text() for title in ("声母", "韵母", "整体认读音节")) for p in pdf.pages)


@pytest.mark.parametrize(
    "overrides",
    [
        {},
        {
            "layout": {"margin_left_mm": 12, "margin_right_mm": 24, "margin_top_mm": 16, "margin_bottom_mm": 30},
            "content": {"font_size_pt": 44},
        },
        {"content": {"font_size_pt": 36}, "grid": {"column_gap_mm": 8, "row_gap_mm": 12}},
        {"grid": {"column_gap_mm": 0, "row_gap_mm": 0}},
    ],
)
def test_grid_geometry_and_uniform_font(tmp_path, overrides):
    app = configured(tmp_path, overrides)
    plan = app.plan()
    for category in CATEGORIES:
        assert [c.text for p in plan.pages if p.category == category for c in p.cards] == list(category.items)
    for page in plan.pages:
        layout, grid = page.config["layout"], page.config["grid"]
        boxes = [c.box_mm for c in page.cards]
        left = min(x for x, y, w, h in boxes)
        right = max(x + w for x, y, w, h in boxes)
        bottom = min(y for x, y, w, h in boxes)
        top = max(y + h for x, y, w, h in boxes)
        assert (left + right) / 2 == pytest.approx(
            (layout["margin_left_mm"] + layout["width_mm"] - layout["margin_right_mm"]) / 2
        )
        assert (bottom + top) / 2 == pytest.approx(
            (layout["margin_bottom_mm"] + layout["height_mm"] - layout["margin_top_mm"]) / 2
        )
        assert {c.font_size_pt for c in page.cards} == {page.config["content"]["font_size_pt"]}
        stroke = page.config["card"]["border_width_pt"] / mm
        for row in page.rows:
            for a, b in zip(row, row[1:], strict=False):
                assert b.box_mm[0] - a.box_mm[0] - a.box_mm[2] - stroke == pytest.approx(grid["column_gap_mm"])
        for upper, lower in zip(page.rows, page.rows[1:], strict=False):
            assert upper[0].box_mm[1] - lower[0].box_mm[1] - lower[0].box_mm[3] - stroke == pytest.approx(
                grid["row_gap_mm"]
            )
    pdf = PdfReader(app.render(plan, tmp_path / "text.pdf"))
    assert len(pdf.pages) == len(plan.pages)
    for actual, page in zip(pdf.pages, plan.pages, strict=True):
        assert actual.extract_text().splitlines() == [c.text for c in page.cards]
        origins = [args[4:6] for args, op in actual.get_contents().operations if op == b"Tm"]
        for card, (x, y) in zip(page.cards, origins, strict=True):
            assert float(x) == pytest.approx(card.x_mm * mm, abs=0.001)
            assert float(y) == pytest.approx(card.y_mm * mm, abs=0.001)


def test_default_grid_fills_page_and_matches_single_category():
    plan = PinyinChartApp().plan()
    assert [len(page.rows) for page in plan.pages] == [4, 4, 4]
    assert [{card.font_size_pt for card in page.cards} for page in plan.pages] == [{96}, {64}, {80}]
    assert [page.config["grid"]["row_gap_mm"] for page in plan.pages] == [8, 10, 10]
    for page in plan.pages:
        assert all(len(row) == page.grid.columns for row in page.rows[:-1])
        assert page.cards == PinyinChartApp().plan(page.category.id).pages[0].cards
    assert len(plan.pages[0].rows[-1]) == 5


def test_fixed_text_spacing_and_overflow():
    grid = text_grid(24, 257, 170, 37, 25.4, 6, 10, 6)
    assert (grid.rows, grid.columns) == (4, 6)
    assert grid.width_mm == 252
    assert grid.height_mm == pytest.approx(131.6)
    with pytest.raises(ValueError, match="exceed usable area"):
        text_grid(24, 257, 170, 50, 25.4, 6, 10, 6)
    with pytest.raises(ValueError, match="exceed usable area"):
        text_grid(24, 257, 170, 37, 25.4, 6, 30, 6)


@pytest.mark.parametrize(
    "override,message",
    [
        ({"content": {"font_size_pt": 0}}, "positive"),
        ({"content": {"font_size_pt": True}}, "Invalid value"),
        ({"grid": {"column_gap_mm": -1}}, "non-negative"),
        ({"grid": {"row_gap_mm": -1}}, "non-negative"),
        ({"grid": {"column_gap_mm": "wrong"}}, "Invalid value"),
        ({"grid": {"row_gap_mm": True}}, "Invalid value"),
        ({"content": {"font_size_pt": 500}}, "exceed usable area"),
        ({"layout": {"height_mm": 45}}, "exceed usable area"),
        ({"layout": {"width_mm": float("nan")}}, "Invalid value"),
        ({"layout": {"margin_left_mm": 297}}, "Horizontal margins"),
        ({"layout": {"margin_top_mm": 297}}, "Vertical margins"),
        ({"content": {"color": "red"}}, "#RRGGBB"),
        ({"fonts": {"content": "missing.ttf"}}, "Cannot load font"),
        ({"card": {"padding_mm": -1}}, "positive"),
        ({"title": {"enabled": True}}, "Unknown configuration key"),
        ({"fonts": {"title": "bundled"}}, "Unknown configuration key"),
        ({"grid": {"rows": 4}}, "Unknown configuration key"),
        ({"categories": {"unknown": {}}}, "Unknown categories"),
    ],
)
def test_invalid_config(tmp_path, override, message):
    with pytest.raises(ValueError, match=message):
        configured(tmp_path, override).generate(output_path=tmp_path / "bad.pdf")
    assert not (tmp_path / "bad.pdf").exists()


def test_category_overrides_and_config_reload(tmp_path):
    app = configured(tmp_path, {"categories": {"yinjie": {"grid": {"column_gap_mm": 4}}}})
    plan = app.plan()
    assert plan.pages[0].config["grid"]["column_gap_mm"] == 6
    assert plan.pages[2].config["grid"]["column_gap_mm"] == 4
    app.config_path.write_text("content:\n  font_size_pt: 36\n")
    assert all(c.font_size_pt == 36 for p in app.plan().pages for c in p.cards)


@pytest.mark.parametrize("columns", [0, -1, 2.5, True, "auto"])
def test_invalid_column_count(tmp_path, columns):
    with pytest.raises(ValueError):
        configured(tmp_path, {"categories": {"shengmu": {"grid": {"columns": columns}}}}).plan()


def test_independent_columns_and_automatic_rows(tmp_path):
    app = configured(tmp_path, {"categories": {"shengmu": {"grid": {"columns": 8}, "content": {"font_size_pt": 64}}}})
    pages = app.plan().pages
    assert [(p.grid.rows, p.grid.columns) for p in pages] == [(3, 8), (4, 6), (4, 4)]
    assert [c.text for c in pages[0].cards] == list(CATEGORIES[0].items)
    assert len(pages[0].rows[-1]) == 7
    assert pages[0].cards == app.plan("shengmu").pages[0].cards


def test_common_columns_and_category_precedence(tmp_path):
    pages = (
        configured(
            tmp_path,
            {
                "grid": {"columns": 5},
                "content": {"font_size_pt": 36},
                "categories": {"yinjie": {"grid": {"columns": 4}}},
            },
        )
        .plan()
        .pages
    )
    assert [p.grid.columns for p in pages] == [5, 5, 4]


@pytest.mark.parametrize("category", ["shengmu", "yunmu", "yinjie"])
def test_boxes_center_visible_letters(tmp_path, category):
    from namishu_printables.pinyin_chart.typography import text_bounds

    app = PinyinChartApp()
    plan = app.plan(category)
    page = plan.pages[0]
    bounds = text_bounds(page.content_font, tuple(c.text for c in page.cards))
    layout = page.config["layout"]
    for card, (x0, y0, x1, y1) in zip(page.cards, bounds, strict=True):
        x, y, width, height = card.box_mm
        assert (width > height) if category in {"yunmu", "yinjie"} else width == pytest.approx(height)
        scale = card.font_size_pt / mm
        assert card.x_mm + (x0 + x1) * scale / 2 == pytest.approx(x + width / 2)
        assert card.y_mm + (y0 + y1) * scale / 2 == pytest.approx(y + height / 2)
        assert (x1 - x0) * scale <= width - 6 + 1e-8
        assert (y1 - y0) * scale <= height - 6 + 1e-8
        assert x >= layout["margin_left_mm"] and x + width <= layout["width_mm"] - layout["margin_right_mm"]
        assert y >= layout["margin_bottom_mm"] and y + height <= layout["height_mm"] - layout["margin_top_mm"]
    pdf = PdfReader(app.render(plan, tmp_path / "boxes.pdf"))
    operations = pdf.pages[0].get_contents().operations
    assert sum(op == b"re" for _, op in operations) == len(page.cards)
    assert not any(op in {b"l", b"d"} for _, op in operations)


def test_hiding_border_preserves_layout(tmp_path):
    original = PinyinChartApp().plan()
    app = configured(tmp_path, {"card": {"enabled": False}})
    hidden = app.plan()
    assert [p.cards for p in hidden.pages] == [p.cards for p in original.pages]
    pdf = PdfReader(app.render(hidden, tmp_path / "hidden.pdf"))
    assert all(not any(op == b"re" for _, op in page.get_contents().operations) for page in pdf.pages)


def test_excess_columns_do_not_reserve_empty_space(tmp_path):
    app = configured(
        tmp_path,
        {
            "grid": {"columns": 100},
            "content": {"font_size_pt": 12},
            "card": {"padding_mm": 1},
            "categories": {"yinjie": {"grid": {"column_gap_mm": 1}}},
        },
    )
    page = app.plan("yinjie").pages[0]
    assert page.grid.columns == 16
    assert len(page.rows) == 1
    left = page.cards[0].box_mm[0]
    right = page.cards[-1].box_mm[0] + page.cards[-1].box_mm[2]
    assert (left + right) / 2 == pytest.approx(297 / 2)
