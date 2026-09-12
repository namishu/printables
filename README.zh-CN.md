<h1 align="center">Namishu Printables</h1>

<p align="center">面向亲子与教育的可打印卡片和书写模板。</p>

<p align="center">Python 3.10+ · A4 PDF · MIT 代码 / OFL 字体</p>
<p align="center"><a href="README.md">English</a> · <strong>简体中文</strong></p>

<p align="center"><a href="examples/pinyin-card/pinyin-card.pdf"><img src="examples/pinyin-card/preview.png" alt="统一字号、横向四行六列排列的韵母页" width="400"></a></p>

生成汉字卡、拼音卡、权益卡、价值观探索卡和书写纸，供家庭或课堂打印使用。每次生成调用只输出一个 PDF，
内容较多时在同一文件中分页。没有封面、品牌页脚或参数标识。

| 工具 | 内容 | 详细说明 |
| --- | --- | --- |
| `hanzi-card` | 内置 300 字的横向汉字卡，每页两个字，默认带拼音 | [使用说明](docs/hanzi-card.md) |
| `pinyin-card` | 声母、韵母、整体认读音节，每页字号一致、横向排列，每类一页 | [使用说明](docs/pinyin-card.md) |
| `values-card` | 价值观探索卡，默认 72 项或自定义文本，单页勾选列表 | [使用说明](docs/values-card.md) |
| `reward-card` | 可签字发放的空白手写权益卡，每次一页 | [使用说明](docs/reward-card.md) |
| `writing-paper` | 横条纸、正方格纸、英文四线三格纸，每次一页 | [使用说明](docs/writing-paper.md) |

## 安装

需要 Python 3.10+。首版尚在发布准备阶段，请在新项目目录中安装：

```bash
uv tool install .
```

或者安装到当前 Python 环境：

```bash
python -m pip install .
```

两种方式均提供 `namishu-printables` 命令。内置配置和字体随包提供，生成 PDF 无需联网、
系统字体或旧项目。正式发布后的 PyPI 包名为 `namishu-printables`。

## 快速开始

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

汉字卡默认生成 300 字、共 150 页；自定义少量汉字的用法见[汉字卡说明](docs/hanzi-card.md)。

书写纸只需选择 `lined`（横条）、`grid`（方格）或 `english`（英文），即可生成默认版式。
需要两三栏书写纸时，见[书写纸进阶用法](docs/writing-paper.md)。

示例文本文件位于源码目录；安装后也可以传入任意本地 UTF-8 文件。
默认输出到运行命令时的当前目录。通过 `-o` / `--output` 指定 PDF 路径：

```bash
namishu-printables hanzi-card "天地" -o cards/characters.pdf
namishu-printables pinyin-card yunmu --config examples/pinyin-card/design.yaml
```

输入、输出和配置的相对路径以当前目录为准；YAML 内的相对字体路径以 YAML 所在目录为准。
输出目录不存在时自动创建。完整生成成功后才覆盖同名文件，失败会保留原文件。
命令会显示绝对输出路径和页数。打印时选择 A4、**实际大小 / 100%**，以保持方格的毫米尺寸。

```bash
namishu-printables --help
namishu-printables hanzi-card --help
namishu-printables --version
python -m namishu_printables writing-paper grid
```

## 配置

命令行选择本次内容和数量，YAML 配置设计、布局、默认值和允许范围。
每个工具单独使用配置文件，只填写需要覆盖的字段；未知字段、非法数值或放不下的布局会报错。
尺寸使用 `_mm`，字号和线宽使用 `_pt`，颜色使用加引号的 `"#RRGGBB"`。
字体统一放在 `fonts` 下，按 `hanzi`、`pinyin`、`content` 等用途分别配置。

完整配置和 PDF 见 [示例下载](docs/examples.md)。例如 `design.yaml` 只需写：

```yaml
layout:
  margin_left_mm: 20
  margin_right_mm: 20
```

```bash
namishu-printables hanzi-card "天地" --config design.yaml
```

## Python 调用

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

模块不依赖 CLI，可独立调用。`generate()` 返回绝对路径；`plan()` 校验输入和计算布局，
不写 PDF；`render(plan, output_path=...)` 将计划一次写入一个 PDF。

## 开发

```bash
uv sync --group dev
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv build
```

测试检查真实 PDF 的页数、文字、几何尺寸、字体和失败保护。
CI 配置覆盖 Linux、macOS、Windows 的 Python 3.10 和 3.14，并验证安装后的 wheel。
更多内容见[架构](docs/architecture.md)、[迁移记录](docs/migration.md)、[发布流程](docs/releasing.md)。

## 范围与后续计划

本项目聚焦识认卡片、亲子活动和基础书写模板。
[Calendar](https://github.com/namishu/calendar)、[Sudoku](https://github.com/namishu/sudoku)、
[Arithmetic](https://github.com/namishu/arithmetic) 继续独立维护。

权益卡 `reward-card` 已实现，用于发放和兑换奖励，不是奖励进度记录表。
后续逐个设计双向评价卡 `feedback-card` 和自评卡 `reflection-card`，尚不提供这两个命令。
地图卡已从项目计划中移除：旧高德数据及其生成的地图 PDF 不随本项目发布，
原因见[地图数据授权核查](docs/map-data-review.md)。

## 许可证

代码、原创文档和模板设计采用 [MIT](LICENSE)。
字体保留 [SIL OFL 1.1](src/namishu_printables/assets/fonts/OFL.txt)。
拼音卡使用宝宝字帖拼音常规体，来源及许可见[字体说明](src/namishu_printables/assets/fonts/README.md)。
生成的汉字卡、拼音卡、权益卡、价值观探索卡和书写纸可打印、分享、修改及销售；嵌入字体保留自己的许可证。
详见[第三方资源说明](THIRD_PARTY_NOTICES.md)。
