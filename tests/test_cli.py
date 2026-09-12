from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from pypdf import PdfReader

from namishu_printables import __version__
from namishu_printables.cli import COMMANDS

ROOT = Path(__file__).resolve().parents[1]


def run(tmp_path, *args):
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    return subprocess.run(
        [sys.executable, "-m", "namishu_printables", *args],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
    )


def test_help_and_version_do_not_import_renderers(tmp_path):
    script = """
import sys
from namishu_printables.cli import main
for args in [["--help"], ["--version"]]:
    try:
        main(args)
    except SystemExit as exc:
        assert exc.code == 0
assert not {"reportlab", "pypinyin", "pyproj", "shapely", "yaml"}.intersection(sys.modules)
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert __version__ in result.stdout
    for name in COMMANDS:
        assert name in result.stdout


@pytest.mark.parametrize("command", COMMANDS)
def test_tool_help_and_version(tmp_path, command):
    help_result = run(tmp_path, command, "--help")
    assert help_result.returncode == 0, help_result.stderr
    assert f"namishu-printables {command}" in help_result.stdout
    assert "--config" in help_result.stdout
    assert "-o" in help_result.stdout
    version = run(tmp_path, command, "--version")
    assert version.returncode == 0, version.stderr
    assert version.stdout.strip() == f"namishu-printables {__version__}"


@pytest.mark.parametrize("args", [[], ["all"], ["ruled-paper"], ["reflection-card"]])
def test_invalid_top_level_does_not_generate(tmp_path, args):
    result = run(tmp_path, *args)
    assert result.returncode == 2
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "args,pages",
    [
        (["hanzi-card", "天地玄黄"], 2),
        (["pinyin-chart", "all"], 3),
        (["reward-card"], 1),
        (["rating-card"], 1),
        (["values-worksheet"], 1),
        (["writing-paper", "grid", "--cell-size", "8"], 1),
    ],
)
def test_short_output_option_from_arbitrary_directory(tmp_path, args, pages):
    result = run(tmp_path, *args, "-o", "打印/paper.pdf")
    assert result.returncode == 0, result.stderr
    output = tmp_path / "打印/paper.pdf"
    assert len(PdfReader(output).pages) == pages
    assert str(output) in result.stdout
    assert list(tmp_path.rglob("*.pdf")) == [output]


def test_values_file_cli_and_overflow(tmp_path):
    source = tmp_path / "家庭.txt"
    source.write_text("陪伴\n信任\n尊重\n", encoding="utf-8")
    result = run(tmp_path, "values-worksheet", "--file", str(source))
    assert result.returncode == 0, result.stderr
    output = tmp_path / "values-worksheet-家庭.pdf"
    assert PdfReader(output).pages[0].extract_text().splitlines() == ["陪伴", "信任", "尊重"]
    original = output.read_bytes()
    source.write_text("健康\n" * 101, encoding="utf-8")
    result = run(tmp_path, "values-worksheet", "--file", str(source))
    assert result.returncode == 2
    assert "max_items" in result.stderr
    assert "Traceback" not in result.stderr
    assert output.read_bytes() == original


def test_values_export_edit_and_generate(tmp_path):
    result = run(tmp_path, "values-worksheet", "--export-default", "词表/my-values.txt")
    assert result.returncode == 0, result.stderr
    source = tmp_path / "词表/my-values.txt"
    bundled = ROOT / "src/namishu_printables/values_worksheet/data/values.txt"
    assert source.read_text(encoding="utf-8") == bundled.read_text(encoding="utf-8")
    assert not list(tmp_path.rglob("*.pdf"))
    source.write_text("陪伴\n信任\n", encoding="utf-8")
    result = run(tmp_path, "values-worksheet", "--export-default", str(source))
    assert result.returncode == 2
    assert source.read_text(encoding="utf-8") == "陪伴\n信任\n"
    result = run(tmp_path, "values-worksheet", "--file", str(source))
    assert result.returncode == 0, result.stderr
    page = PdfReader(tmp_path / "values-worksheet-my-values.pdf").pages[0]
    assert page.extract_text().splitlines() == ["陪伴", "信任"]


@pytest.mark.parametrize("extra", [["--file", "input.txt"], ["--config", "design.yaml"], ["-o", "x.pdf"]])
def test_values_export_rejects_generation_options(tmp_path, extra):
    result = run(tmp_path, "values-worksheet", "--export-default", "values.txt", *extra)
    assert result.returncode == 2
    assert not list(tmp_path.iterdir())
