<h1 align="center">Namishu Printables</h1>

<p align="center">Printable cards and paper templates for learning and family activities.</p>

<p align="center">Python 3.10+ · A4 PDF · MIT code / OFL fonts</p>
<p align="center"><strong>English</strong> · <a href="README.zh-CN.md">简体中文</a></p>

<p align="center"><a href="examples/pinyin-card/pinyin-card.pdf"><img src="examples/pinyin-card/preview.png" alt="Pinyin finals in four rows and six columns with a uniform font size" width="400"></a></p>

Generate Chinese character cards, pinyin cards, reward vouchers, values checklists and handwriting paper, ready to print at home or in a classroom.
Each generation command writes one PDF, with as many pages as the selected content needs.
There are no covers, branding footers or parameter labels on the pages.

| Template | What it generates | Guide |
| --- | --- | --- |
| `hanzi-card` | 300 built-in characters, two per landscape page, with pinyin by default | [Guide](docs/hanzi-card.md) |
| `pinyin-card` | Initials, finals or whole syllables in individual bordered cards, with a uniform font size on each landscape page; one page per category | [Guide](docs/pinyin-card.md) |
| `values-card` | One page of values with checkboxes; built-in or custom items | [Guide](docs/values-card.md) |
| `reward-card` | A blank handwritten reward voucher with signatures and usage notes, one page | [Guide](docs/reward-card.md) |
| `writing-paper` | One page of lined, square-grid or four-line English handwriting paper | [Guide](docs/writing-paper.md) |

## Install

Requires Python 3.10 or later. The first release is being prepared; install from a local checkout:

```bash
uv tool install .
```

Or install into a Python environment:

```bash
python -m pip install .
```

Both provide the `namishu-printables` command. Default designs and fonts are included;
PDF generation works offline without system fonts or the original repository.
Once published on PyPI, the package name will be `namishu-printables`.

## Quick start

```bash
namishu-printables hanzi-card
namishu-printables pinyin-card
namishu-printables reward-card
namishu-printables values-card
namishu-printables values-card --file examples/values-card/family.txt
namishu-printables writing-paper lined
namishu-printables writing-paper grid
namishu-printables writing-paper english
```

The default character-card PDF contains 300 characters across 150 pages. See the [guide](docs/hanzi-card.md) for custom text.

For writing paper, choose `lined`, `grid` or `english`; the default layout is ready to print.
See the [writing paper guide](docs/writing-paper.md) for two- or three-column layouts.

Text-file examples are included in the source checkout. You can pass any local UTF-8 file after installation.
Output defaults to the directory where you run the command. Use `-o` / `--output` for a custom PDF path:

```bash
namishu-printables hanzi-card "天地" -o cards/characters.pdf
namishu-printables pinyin-card yunmu --config examples/pinyin-card/design.yaml
```

Relative input, configuration and output paths are relative to the working directory.
Relative font paths in YAML are relative to that YAML file. Missing output directories are created.
A successfully generated PDF replaces an existing file of the same name; failed generation preserves it.
The command prints the absolute output path and page count.
Print on A4 at **actual size / 100%**, especially when using a specified square size.

```bash
namishu-printables --help
namishu-printables hanzi-card --help
namishu-printables --version
python -m namishu_printables writing-paper grid
```

## Customize

CLI options select the content and quantities for this run. YAML controls layout, colors, fonts,
and configured defaults or limits. Each template has a separate configuration.
Overrides merge with bundled defaults; unknown keys and invalid layouts produce an error.
Distances use `_mm`, font sizes and line widths use `_pt`, and colors use quoted `"#RRGGBB"` strings.
Custom fonts go under `fonts`, with role names such as `hanzi`, `pinyin` or `content`.

Full configurations and PDFs are in [示例下载](docs/examples.md).
For example, `design.yaml` can contain only:

```yaml
layout:
  margin_left_mm: 20
  margin_right_mm: 20
```

```bash
namishu-printables hanzi-card "天地" --config design.yaml
```

## Python API

Each template can be used independently of the CLI:

```python
from namishu_printables.hanzi_card import HanziCardApp
from namishu_printables.pinyin_card import PinyinCardApp
from namishu_printables.writing_paper import WritingPaperApp
from namishu_printables.reward_card import RewardCardApp
from namishu_printables.values_card import ValuesCardApp

output = HanziCardApp().generate("天地玄黄")
output = PinyinCardApp().generate("all")
output = WritingPaperApp().generate("grid")
output = RewardCardApp().generate()
output = ValuesCardApp().generate()
```

`generate()` returns an absolute `Path`. `plan()` validates input and computes layout without writing a PDF;
`render(plan, output_path=...)` writes the complete document. See each guide for template-specific arguments.

## Development

```bash
uv sync --group dev
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv build
```

Tests inspect actual PDF pages, text, geometry, fonts and failure behavior.
CI is configured for Python 3.10 and 3.14 on Linux, macOS and Windows, including wheel-install smoke tests.
See [architecture](docs/architecture.md), [migration](docs/migration.md), and [release instructions](docs/releasing.md).

## Scope and roadmap

This collection focuses on recognition cards, family activities and writing templates.
[Calendar](https://github.com/namishu/calendar), [Sudoku](https://github.com/namishu/sudoku),
and [Arithmetic](https://github.com/namishu/arithmetic) remain separate projects.

Planned templates: `feedback-card` for parent–child feedback and `reflection-card` for self-reflection.
These are not available commands yet. `reward-card` is a redeemable voucher, not a progress tracker.
China map cards are excluded from the project: the old Amap-derived data is not included in this repository or package.
See the [map-data review](docs/map-data-review.md).

## License

Original code, documentation and template designs are licensed under [MIT](LICENSE).
Bundled fonts retain [SIL OFL 1.1](src/namishu_printables/assets/fonts/OFL.txt).
Pinyin cards use the regular font from the pinyin-font project; see [font sources and licenses](src/namishu_printables/assets/fonts/README.md).
Generated character cards, pinyin cards, reward vouchers, values checklists and writing paper may be printed, shared, modified and sold;
embedded fonts retain their license. See [third-party notices](THIRD_PARTY_NOTICES.md).
