from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from pypdf import PdfReader
from reportlab.lib.units import mm

import namishu_printables.hanzi_card.app as app_module
from namishu_printables.hanzi_card import HanziCardApp
from namishu_printables.hanzi_card.input import clean_text, is_hanzi

ROOT = Path(__file__).resolve().parents[1]


def configured(tmp_path: Path, data: dict) -> HanziCardApp:
    path = tmp_path / "design.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return HanziCardApp(path)


@pytest.mark.parametrize("text,count", [("天", 1), ("天地", 1), ("天地人", 2), ("天地玄黄人", 3), ("天" * 300, 150)])
def test_one_pdf_correct_pages_no_cover(tmp_path, text, count):
    output = HanziCardApp().generate(text, no_pinyin=True, output_path=tmp_path / "cards.pdf")
    assert list(tmp_path.iterdir()) == [output]
    pdf = PdfReader(output)
    assert len(pdf.pages) == count
    for i, page in enumerate(pdf.pages):
        assert page.extract_text().replace("\n", "") == text[i * 2 : i * 2 + 2]
        assert float(page.mediabox.width) == pytest.approx(297 * mm, abs=0.001)
        assert float(page.mediabox.height) == pytest.approx(210 * mm, abs=0.001)
        embedded = [font.get_object() for font in page["/Resources"]["/Font"].values()]
        assert any("/FontFile2" in font.get("/FontDescriptor", {}) for font in embedded)


def test_pinyin_is_resolved_before_pagination_and_override():
    app = HanziCardApp()
    plan = app.plan("去重庆")
    assert [[c.pinyin for c in page] for page in plan.pages] == [["qù", "chóng"], ["qìng"]]
    plan = app.plan("重，庆！", pinyin="zhòng qìng")
    assert [c.pinyin for c in plan.pages[0]] == ["zhòng", "qìng"]
    assert all(c.pinyin == "" for c in app.plan("重庆", no_pinyin=True).pages[0])


def test_pinyin_text_in_pdf(tmp_path):
    output = HanziCardApp().generate("女绿", output_path=tmp_path / "pinyin.pdf")
    text = PdfReader(output).pages[0].extract_text()
    assert all(token in text for token in ["女", "绿", "nǚ", "lǜ"])


def test_single_card_centered_and_same_size_on_last_page(tmp_path):
    app = HanziCardApp()
    plan = app.plan("天地人")
    single = plan.pages[-1][0]
    assert single.x_mm + plan.config["card"]["size_mm"] / 2 == pytest.approx(74.25)
    assert single.y_mm == plan.pages[0][0].y_mm
    pdf = PdfReader(app.render(plan, tmp_path / "cards.pdf"))
    for page in pdf.pages:
        operations = page.get_contents().operations
        assert any(op == b"d" for _, op in operations)
        start = next(args for args, op in operations if op == b"m")
        end = next(args for args, op in operations if op == b"l")
        assert float(start[0]) == pytest.approx(148.5 * mm, abs=0.001)
        assert float(end[0]) == pytest.approx(float(start[0]))
        assert float(start[1]) == 0
        assert float(end[1]) == pytest.approx(float(page.mediabox.height))


def test_cleaning_preserves_order_duplicates_and_traditional():
    assert clean_text(" 天A地，\n天123！🙂學〇 ", 100) == ("天地天學〇", 10)
    assert is_hanzi("𠮷")
    assert not is_hanzi("⼀")


@pytest.mark.parametrize(
    "text,message", [("", "No Chinese"), ("abc 123。🙂", "No Chinese"), ("天" * 301, "maximum is 300")]
)
def test_input_rejected_without_output(tmp_path, text, message):
    with pytest.raises(ValueError, match=message):
        HanziCardApp().generate(text, output_path=tmp_path / "cards.pdf")
    assert list(tmp_path.iterdir()) == []


def test_limit_counts_after_cleaning_and_is_configurable(tmp_path):
    app = configured(tmp_path, {"input": {"max_characters": 2}})
    assert app.plan("天，地！！！abc123").characters == "天地"
    with pytest.raises(ValueError, match="maximum is 2"):
        app.plan("天天天")
    app.config_path.write_text("input:\n  max_characters: 101\n")
    assert len(app.plan("天" * 101).pages) == 51


@pytest.mark.parametrize(
    "kwargs,message",
    [
        ({"text": "天", "file": "anything"}, "either text or file"),
        ({"text": "天地", "pinyin": "tiān"}, "Expected 2"),
        ({"text": "天", "pinyin": "tiān", "no_pinyin": True}, "cannot be used together"),
        ({"text": "天", "pinyin": "123"}, "No valid pinyin"),
        ({"text": "天", "no_pinyin": 1}, "must be a boolean"),
        ({"text": "𠮷", "no_pinyin": True}, "missing glyphs"),
    ],
)
def test_invalid_requests(kwargs, message):
    with pytest.raises(ValueError, match=message):
        HanziCardApp().plan(**kwargs)


def test_bom_file_newlines_and_filename(tmp_path, monkeypatch):
    (tmp_path / "words.txt").write_text("天地\n人\n山水", encoding="utf-8-sig")
    monkeypatch.chdir(tmp_path)
    app = HanziCardApp()
    plan = app.plan(file="words.txt")
    assert ["".join(c.character for c in p) for p in plan.pages] == ["天地", "人山", "水"]
    assert app.render(plan) == tmp_path / "hanzi-card.pdf"
    assert app.generate("天") == tmp_path / "hanzi-card.pdf"
    assert app.generate("天地") == tmp_path / "hanzi-card.pdf"
    assert app.generate("天地玄黄宇宙洪荒") == tmp_path / "hanzi-card.pdf"


@pytest.mark.parametrize(
    "config,message",
    [
        ({"cover": {"enable": True}}, "Unknown configuration key"),
        ({"layout": None}, "must be a mapping"),
        ({"input": {"max_characters": True}}, "Invalid value"),
        ({"input": {"max_characters": 1.5}}, "positive integer"),
        ({"input": {"max_characters": 0}}, "must be positive"),
        ({"layout": {"width_mm": float("nan")}}, "Invalid value"),
        ({"layout": {"width_mm": 200}}, "landscape"),
        ({"layout": {"margin_left_mm": 300}}, "Unknown configuration key"),
        ({"layout": {"margin_top_mm": 210}}, "Unknown configuration key"),
        ({"card": {"size_mm": 140}}, "between 80 and 120"),
        ({"card": {"padding_mm": 50}}, "no room"),
        ({"card": {"border_radius_mm": 80}}, "half the card"),
        ({"card": {"border_color": "blue"}}, "#RRGGBB"),
        ({"hanzi": {"font_size_pt": 300}}, "Hanzi font_size_pt"),
        ({"fonts": {"hanzi": "missing.ttf"}}, "Cannot load font"),
        ({"pinyin": {"font_size_pt": 300}}, "Pinyin font_size_pt"),
        ({"pinyin": {"gap_mm": 100}}, "page height"),
        ({"layout": {"card_gap_mm": 0.1}}, "Unknown configuration key"),
    ],
)
def test_invalid_config_or_geometry(tmp_path, config, message):
    app = configured(tmp_path, config)
    with pytest.raises(ValueError, match=message):
        app.generate("天地", output_path=tmp_path / "bad.pdf")
    assert not (tmp_path / "bad.pdf").exists()


def test_font_paths_relative_to_yaml_and_separate_pinyin_font(tmp_path, monkeypatch):
    design = tmp_path / "design"
    design.mkdir()
    shutil.copyfile(ROOT / "src/namishu_printables/assets/fonts/NotoSansSC-Light.ttf", design / "hanzi.ttf")
    app = configured(design, {"fonts": {"hanzi": "hanzi.ttf"}})
    monkeypatch.chdir(tmp_path)
    plan = app.plan("天地")
    assert plan.hanzi_font != plan.pinyin_font
    assert Path(plan.config["fonts"]["hanzi"]) == design / "hanzi.ttf"
    assert app.render(plan).exists()


def test_generation_failure_preserves_existing_file_and_cleans_temp(tmp_path, monkeypatch):
    output = tmp_path / "cards.pdf"
    output.write_bytes(b"previous content")
    app = HanziCardApp()
    plan = app.plan("天地人")
    original = app_module.draw_page
    drawn = 0

    def fail_on_second(pdf, cards, plan):
        nonlocal drawn
        drawn += 1
        if drawn == 2:
            raise RuntimeError("drawing failed")
        original(pdf, cards, plan)

    monkeypatch.setattr(app_module, "draw_page", fail_on_second)
    with pytest.raises(RuntimeError, match="drawing failed"):
        app.render(plan, output)
    assert output.read_bytes() == b"previous content"
    assert list(tmp_path.iterdir()) == [output]


def test_success_replaces_one_file(tmp_path):
    output = tmp_path / "cards.pdf"
    output.write_bytes(b"previous content")
    app = HanziCardApp()
    app.generate("天地人", output_path=output)
    assert len(PdfReader(output).pages) == 2
    assert list(tmp_path.iterdir()) == [output]


def test_examples_fit_default_limit():
    app = HanziCardApp()
    for path in (ROOT / "examples/hanzi-card").glob("*.txt"):
        plan = app.plan(file=path)
        assert len(plan.characters) <= 100


def cli(tmp_path, *args):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "namishu_printables", "hanzi-card", *args],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )


def test_cli_current_directory_and_relative_paths(tmp_path):
    (tmp_path / "words.txt").write_text("天地玄黄人")
    (tmp_path / "design.yaml").write_text("separator:\n  enabled: false\n")
    result = cli(tmp_path, "--file", "words.txt", "--config", "design.yaml", "--output", "out/cards.pdf")
    assert result.returncode == 0, result.stderr
    assert "Generated 1 PDF" in result.stdout and "3 pages" in result.stdout
    assert len(PdfReader(tmp_path / "out/cards.pdf").pages) == 3
    assert len(list(tmp_path.rglob("*.pdf"))) == 1


@pytest.mark.parametrize(
    "args,message",
    [
        (["天", "--file", "words.txt"], "not allowed"),
        (["天", "--pinyin", "tiān", "--no-pinyin"], "not allowed"),
        (["天地", "--pinyin", "tiān"], "Expected 2"),
        (["天", "--output", "out.png"], ".pdf extension"),
        (["--file", "missing.txt"], "No such file"),
        (["天", "--config", "missing.yaml"], "No such file"),
        (["abc"], "No Chinese"),
    ],
)
def test_cli_errors(tmp_path, args, message):
    result = cli(tmp_path, *args)
    assert result.returncode == 2
    assert message in result.stderr
    assert "Traceback" not in result.stderr
    assert list(tmp_path.glob("*.pdf")) == []


def test_cli_help(tmp_path):
    result = cli(tmp_path, "--help")
    assert result.returncode == 0
    assert "--file" in result.stdout and "--pinyin" in result.stdout
    assert "--cover" not in result.stdout


@pytest.mark.parametrize("size", [80, 100, 120])
@pytest.mark.parametrize("no_pinyin", [False, True])
def test_half_page_centering_and_scaled_content(tmp_path, size, no_pinyin):
    app = configured(tmp_path, {"card": {"size_mm": size}})
    plan = app.plan("天地人", no_pinyin=no_pinyin)
    assert plan.config["hanzi"]["font_size_pt"] == pytest.approx(size * 2)
    assert plan.config["pinyin"]["font_size_pt"] == pytest.approx(size * 0.48)
    pdf = PdfReader(app.render(plan, tmp_path / "scaled.pdf"))
    for cards, page in zip(plan.pages, pdf.pages, strict=True):
        for col, card in enumerate(cards):
            assert card.x_mm + size / 2 == pytest.approx(74.25 + col * 148.5)
            assert card.y_mm + size / 2 == pytest.approx(105)
        # Inspect the actual rounded-box paths, excluding the first separator path.
        paths = []
        points = []
        for args, op in page.get_contents().operations:
            if op in (b"m", b"l", b"c"):
                points.extend(zip(map(float, args[::2]), map(float, args[1::2]), strict=True))
            elif op == b"S":
                if len(points) > 2:
                    paths.append(points)
                points = []
        assert len(paths) == len(cards)
        for col, points in enumerate(paths):
            xs, ys = zip(*points, strict=True)
            assert (max(xs) + min(xs)) / 2 / mm == pytest.approx(74.25 + col * 148.5, abs=0.001)
            assert (max(ys) + min(ys)) / 2 / mm == pytest.approx(105, abs=0.001)
            assert (max(xs) - min(xs)) / mm == pytest.approx(size, abs=0.001)


@pytest.mark.parametrize("size", [79, 121])
def test_card_size_outside_range(tmp_path, size):
    with pytest.raises(ValueError, match="between 80 and 120"):
        configured(tmp_path, {"card": {"size_mm": size}}).generate("天", output_path=tmp_path / "bad.pdf")
    assert not (tmp_path / "bad.pdf").exists()


@pytest.mark.parametrize(
    "text, pinyin, expected",
    [
        ("重庆", "chong2 qing4", ["chóng", "qìng"]),
        ("女绿", "nv3 lv4", ["nǚ", "lǜ"]),
        ("女绿", "nu:3 lü4", ["nǚ", "lǜ"]),
        ("妈妈", "ma1 ma5", ["mā", "ma"]),
        ("妈妈", "mā ma0", ["mā", "ma"]),
        ("水流", "SHUI3 liu2", ["shuǐ", "liú"]),
    ],
)
def test_numbered_pinyin_in_pdf(tmp_path, text, pinyin, expected):
    app = HanziCardApp()
    plan = app.plan(text, pinyin=pinyin)
    assert [card.pinyin for card in plan.pages[0]] == expected
    pdf = PdfReader(app.render(plan, tmp_path / "tones.pdf"))
    assert all(syllable in pdf.pages[0].extract_text() for syllable in expected)


def test_inline_pinyin_occurrences_and_phrase_context(tmp_path):
    app = HanziCardApp()
    plan = app.plan("去重[zhong4]庆，重[chong2]阳！")
    assert plan.characters == "去重庆重阳"
    assert plan.ignored_characters == 2
    assert [card.pinyin for page in plan.pages for card in page] == ["qù", "zhòng", "qìng", "chóng", "yáng"]
    assert len(plan.pages) == 3
    assert app.plan("重[chóng]庆").pages[0][0].pinyin == "chóng"
    assert configured(tmp_path, {"input": {"max_characters": 2}}).plan("重[chong2]庆").characters == "重庆"
    hidden = app.plan("重[chong2]庆", no_pinyin=True)
    assert all(card.pinyin == "" for card in hidden.pages[0])


@pytest.mark.parametrize(
    "text", ["重[]庆", "重[chong2庆", "重[chong6]庆", "重[chong2 qing4]庆", "重[重庆]", "重[[chong2]]", "[chong2]重"]
)
def test_invalid_inline_pinyin_preserves_output(tmp_path, text):
    output = tmp_path / "cards.pdf"
    output.write_bytes(b"previous")
    with pytest.raises(ValueError):
        HanziCardApp().generate(text, output_path=output)
    assert output.read_bytes() == b"previous"


@pytest.mark.parametrize("pinyin", ["chong6", "chong22", "ch2ong", "chóng2", "123"])
def test_invalid_tone_numbers(pinyin):
    with pytest.raises(ValueError, match="No valid pinyin"):
        HanziCardApp().plan("重", pinyin=pinyin)


def test_cli_annotated_file_and_full_override_conflict(tmp_path):
    (tmp_path / "words.txt").write_text("重[chong2]庆\n重[zhong4]量", encoding="utf-8-sig")
    result = cli(tmp_path, "--file", "words.txt")
    assert result.returncode == 0, result.stderr
    pdf = PdfReader(tmp_path / "hanzi-card.pdf")
    assert len(pdf.pages) == 2
    assert "chóng" in pdf.pages[0].extract_text()
    assert "zhòng" in pdf.pages[1].extract_text()
    result = cli(tmp_path, "重[chong2]庆", "--pinyin", "chong2 qing4")
    assert result.returncode == 2
    assert "cannot be used together" in result.stderr
    result = cli(tmp_path, "重庆", "--pinyin", "chong2 qing4")
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("no_pinyin", [False, True])
def test_bundled_characters_without_source(tmp_path, monkeypatch, no_pinyin):
    from importlib.resources import files

    expected = "".join(files("namishu_printables.hanzi_card").joinpath("data/characters.txt").read_text().split())
    assert len(expected) == 300
    monkeypatch.chdir(tmp_path)
    app = HanziCardApp()
    plan = app.plan(no_pinyin=no_pinyin)
    assert plan.characters == expected
    assert plan.ignored_characters == 0
    assert len(plan.pages) == 150
    pdf = PdfReader(app.render(plan))
    assert len(pdf.pages) == 150
    for index, page in enumerate(pdf.pages):
        extracted = "".join(char for char in page.extract_text() if is_hanzi(char))
        assert extracted == expected[index * 2 : index * 2 + 2]


def test_cli_default_uses_bundled_characters(tmp_path):
    result = cli(tmp_path)
    assert result.returncode == 0, result.stderr
    assert "300 characters, 150 pages" in result.stdout
    assert len(PdfReader(tmp_path / "hanzi-card.pdf").pages) == 150


def test_bundled_content_independent_of_custom_input_limit(tmp_path):
    app = configured(tmp_path, {"input": {"max_characters": 2}})
    assert len(app.plan().characters) == 300
    assert app.plan("天地").characters == "天地"
    with pytest.raises(ValueError, match="maximum is 2"):
        app.plan("天地人")
