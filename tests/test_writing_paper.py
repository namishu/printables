from __future__ import annotations

import math
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from pypdf import PdfReader
from reportlab.lib.units import mm

from namishu_printables.writing_paper import WritingPaperApp
from namishu_printables.writing_paper.configuration import load_config


def configured(tmp_path: Path, override: dict) -> WritingPaperApp:
    path = tmp_path / "design.yaml"
    path.write_text(yaml.safe_dump(override), encoding="utf-8")
    return WritingPaperApp(path)


def lines(path: Path) -> list[tuple]:
    page = PdfReader(path).pages[0]
    result = []
    width, color, start = None, None, None
    for operands, operator in page.get_contents().operations:
        if operator == b"w":
            width = float(operands[0])
        elif operator == b"RG":
            color = tuple(float(v) for v in operands)
        elif operator == b"m":
            start = tuple(float(v) / mm for v in operands)
        elif operator == b"l":
            end = tuple(float(v) / mm for v in operands)
            result.append((start, end, width, color))
    return result


@pytest.mark.parametrize(
    "kind, rows, columns, filename",
    [
        ("lined", 20, 1, "writing-paper-lined.pdf"),
        ("grid", 25, 17, "writing-paper-grid.pdf"),
        ("english", 16, 1, "writing-paper-english.pdf"),
    ],
)
def test_defaults_one_page_no_footer(tmp_path, monkeypatch, kind, rows, columns, filename):
    monkeypatch.chdir(tmp_path)
    app = WritingPaperApp()
    plan = app.plan(kind)
    assert (plan.rows, plan.columns, plan.filename) == (rows, columns, filename)
    output = app.generate(kind)
    assert output == tmp_path / filename
    pdf = PdfReader(output)
    assert len(pdf.pages) == 1
    assert pdf.pages[0].extract_text() == ""
    assert float(pdf.pages[0].mediabox.width) == pytest.approx(210 * mm, abs=0.001)
    assert float(pdf.pages[0].mediabox.height) == pytest.approx(297 * mm, abs=0.001)


@pytest.mark.parametrize("rows, columns", [(1, 1), (26, 3), (1, 3), (26, 1)])
def test_lined_limits_and_geometry(tmp_path, rows, columns):
    output = WritingPaperApp().generate("lined", rows=rows, columns=columns, output_path=tmp_path / "lined.pdf")
    strokes = lines(output)
    assert len(strokes) == columns - 1 + (rows + 1) * columns
    vertical = strokes[: columns - 1]
    horizontal = strokes[columns - 1 :]
    assert all(a[0] == b[0] for a, b, _, _ in vertical)
    assert all(a[1] == b[1] and b[0] > a[0] for a, b, _, _ in horizontal)
    assert len({round(a[1], 3) for a, _, _, _ in horizontal}) == rows + 1
    assert all(20 - 0.001 <= a[0] < b[0] <= 190 + 0.001 for a, b, _, _ in horizontal)


@pytest.mark.parametrize("size", [5, 8, 10.0, 12.5, 20])
def test_grid_squares_order_weight_and_bounds(tmp_path, size):
    app = WritingPaperApp()
    plan = app.plan("grid", cell_size=size)
    output = app.render(plan, tmp_path / "grid.pdf")
    strokes = lines(output)
    assert len(strokes) == plan.columns + plan.rows + 2
    vertical, horizontal = strokes[: plan.columns + 1], strokes[plan.columns + 1 :]
    assert all(a[0] == b[0] for a, b, _, _ in vertical)
    assert all(a[1] == b[1] for a, b, _, _ in horizontal)
    assert all(w == 0.3 for _, _, w, _ in vertical)
    assert horizontal[0][2] == horizontal[-1][2] == 1.5
    assert all(w == 0.6 for _, _, w, _ in horizontal[1:-1])
    assert sum(vertical[0][3]) > sum(horizontal[0][3])
    xs = [a[0] for a, _, _, _ in vertical]
    ys = [a[1] for a, _, _, _ in horizontal]
    for values in (xs, ys):
        assert all(b - a == pytest.approx(size, abs=0.001) for a, b in zip(values, values[1:], strict=False))
    assert (xs[0] + xs[-1]) / 2 == pytest.approx(105, abs=0.001)
    assert (ys[0] + ys[-1]) / 2 == pytest.approx(148.5, abs=0.001)
    assert xs[0] >= 20 - 0.001 and xs[-1] <= 190 + 0.001
    assert ys[0] >= 20 - 0.001 and ys[-1] <= 277 + 0.001


@pytest.mark.parametrize("columns", [1, 3])
def test_english_groups_and_baselines(tmp_path, columns):
    output = WritingPaperApp().generate("english", columns=columns, output_path=tmp_path / "english.pdf")
    horizontal = lines(output)[columns - 1 :]
    assert len(horizontal) == 16 * 4 * columns
    baseline = [a[1] for a, _, width, _ in horizontal if width == 0.8]
    assert len(baseline) == 16 * columns
    first = sorted({a[1] for a, _, _, _ in horizontal}, reverse=True)[:4]
    assert [first[i] - first[i + 1] for i in range(3)] == pytest.approx([3, 3, 3], abs=0.001)
    assert baseline[0] == pytest.approx(first[2])


@pytest.mark.parametrize(
    "kind, kwargs, message",
    [
        ("lined", {"rows": 0}, "positive integer"),
        ("lined", {"rows": 27}, "between 1 and 26"),
        ("lined", {"columns": 4}, "between 1 and 3"),
        ("lined", {"columns": 0}, "positive integer"),
        ("lined", {"rows": 2.5}, "positive integer"),
        ("lined", {"rows": True}, "positive integer"),
        ("english", {"columns": 4}, "between 1 and 3"),
        ("english", {"columns": 0}, "positive integer"),
        ("grid", {"cell_size": 4}, "between 5 and 20"),
        ("grid", {"cell_size": math.nan}, "finite number"),
        ("grid", {"cell_size": math.inf}, "finite number"),
        ("grid", {"rows": 10}, "only supported for lined"),
        ("grid", {"columns": 10}, "calculated from cell_size"),
        ("english", {"rows": 10}, "only supported for lined"),
        ("lined", {"cell_size": 10}, "only supported for grid"),
        ("unknown", {}, "kind must be"),
    ],
)
def test_invalid_parameters(tmp_path, kind, kwargs, message):
    output = tmp_path / "invalid.pdf"
    with pytest.raises(ValueError, match=message):
        WritingPaperApp().generate(kind, output_path=output, **kwargs)
    assert not output.exists()


def test_config_overrides_defaults_and_limits(tmp_path):
    app = configured(
        tmp_path,
        {
            "parameters": {
                "lined": {
                    "rows": {"default": 28, "max": 30},
                    "columns": {"default": 2, "min": 2},
                }
            }
        },
    )
    plan = app.plan("lined")
    assert (plan.rows, plan.columns) == (28, 2)
    assert app.plan("lined", rows=30).rows == 30
    with pytest.raises(ValueError, match="between 2 and 3"):
        app.plan("lined", columns=1)
    assert app.plan("lined", rows=26).rows == 26


@pytest.mark.parametrize(
    "override, message",
    [
        ({"presets": {}}, "Unknown configuration key"),
        ({"layout": None}, "must be a mapping"),
        ({"layout": {"width_mm": True}}, "Invalid value"),
        ({"layout": {"width_mm": float("nan")}}, "Invalid value"),
        ({"layout": {"width_mm": 40}}, "Horizontal margins"),
        ({"layout": {"height_mm": 40}}, "Vertical margins"),
        ({"lined": {"layout": {"column_gap_mm": -1}}}, "non-negative"),
        ({"lined": {"style": {"horizontal": {"color": "red"}}}}, "#RRGGBB"),
        ({"parameters": {"lined": {"rows": {"max": 19}}}}, "min <= default <= max"),
        ({"parameters": {"lined": {"rows": {"max": 26.5}}}}, "positive integer"),
        ({"grid": {"style": {"vertical": {"width_pt": 0.6}}}}, "greater than"),
        ({"grid": {"layout": {"horizontal_alignment": "left"}}}, "start, center, or end"),
        ({"english": {"layout": {"groups": 0}}}, "positive integer"),
    ],
)
def test_invalid_config(tmp_path, override, message):
    with pytest.raises(ValueError, match=message):
        configured(tmp_path, override).plan("lined")


@pytest.mark.parametrize(
    "kind, override, kwargs, message",
    [
        ("lined", {"lined": {"layout": {"column_gap_mm": 100}}}, {"columns": 3}, "no writing width"),
        ("english", {"english": {"layout": {"groups": 29}}}, {}, "do not fit"),
        ("grid", {"layout": {"width_mm": 45}}, {}, "complete square"),
    ],
)
def test_impossible_layout(tmp_path, kind, override, kwargs, message):
    with pytest.raises(ValueError, match=message):
        configured(tmp_path, override).plan(kind, **kwargs)


def test_decimal_fit_filename_and_zero_margins(tmp_path):
    app = configured(
        tmp_path,
        {
            "layout": {
                "width_mm": 24.6,
                "height_mm": 24.6,
                "margin_left_mm": 0,
                "margin_right_mm": 0,
                "margin_top_mm": 0,
                "margin_bottom_mm": 0,
            },
        },
    )
    plan = app.plan("grid", cell_size=8.2)
    assert (plan.rows, plan.columns) == (3, 3)
    assert plan.filename == "writing-paper-grid.pdf"
    assert WritingPaperApp().plan("grid", cell_size=10.0).filename == "writing-paper-grid.pdf"


def test_single_english_group_centered(tmp_path):
    app = configured(tmp_path, {"english": {"layout": {"groups": 1}}})
    strokes = lines(app.generate("english", output_path=tmp_path / "single.pdf"))
    ys = [a[1] for a, _, _, _ in strokes]
    assert len(ys) == 4
    assert (max(ys) + min(ys)) / 2 == pytest.approx(148.5, abs=0.001)


def test_config_reloaded_for_reused_app(tmp_path):
    app = configured(tmp_path, {"parameters": {"lined": {"rows": {"default": 12}}}})
    assert app.plan("lined").rows == 12
    app.config_path.write_text("parameters:\n  lined:\n    rows:\n      default: 13\n")
    assert app.plan("lined").rows == 13


def cli(tmp_path, *args):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    return subprocess.run(
        [sys.executable, "-m", "namishu_printables", "writing-paper", *args],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
    )


def test_cli_relative_paths_and_options(tmp_path):
    (tmp_path / "design.yaml").write_text("parameters:\n  lined:\n    rows:\n      default: 12\n")
    result = cli(tmp_path, "--config", "design.yaml", "lined", "--output", "nested/paper.pdf")
    assert result.returncode == 0, result.stderr
    assert "12 rows" in result.stdout and "Generated 1 page" in result.stdout
    assert len(PdfReader(tmp_path / "nested/paper.pdf").pages) == 1
    result = cli(tmp_path, "lined", "--config", "design.yaml")
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "writing-paper-lined.pdf").exists()


@pytest.mark.parametrize(
    "args, message",
    [
        ([], "required"),
        (["--help"], "lined"),
        (["grid", "--rows", "20"], "unrecognized arguments"),
        (["lined", "--rows", "27"], "between 1 and 26"),
        (["grid", "--cell-size", "nan"], "finite number"),
        (["english", "--config", "missing.yaml"], "No such file"),
        (["lined", "--output", "paper.png"], ".pdf extension"),
    ],
)
def test_cli_errors_and_help(tmp_path, args, message):
    result = cli(tmp_path, *args)
    assert result.returncode == (0 if args == ["--help"] else 2)
    assert message in result.stdout + result.stderr
    assert "Traceback" not in result.stderr
    assert list(tmp_path.glob("*.pdf")) == []


def test_bundled_config():
    assert load_config()["parameters"]["lined"]["rows"] == {"default": 20, "min": 1, "max": 26}


@pytest.mark.parametrize("kind", ["lined", "english"])
def test_cli_column_limit_override(tmp_path, kind):
    result = cli(tmp_path, kind, "--columns", "4")
    assert result.returncode == 2
    assert "between 1 and 3" in result.stderr
    assert not list(tmp_path.glob("*.pdf"))
    config = tmp_path / "design.yaml"
    config.write_text(yaml.safe_dump({"parameters": {kind: {"columns": {"max": 4}}}}))
    result = cli(tmp_path, kind, "--config", str(config), "--columns", "4")
    assert result.returncode == 0, result.stderr
    output = tmp_path / f"writing-paper-{kind}.pdf"
    assert len(PdfReader(output).pages) == 1
    strokes = lines(output)
    assert sum(a[0] == b[0] for a, b, _, _ in strokes) == 3
