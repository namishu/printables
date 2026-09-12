<h1 align="center">Namishu Printables</h1>

<p align="center">面向亲子与教育的可打印卡片和书写模板。</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&amp;logo=python&amp;logoColor=white" alt="Python 3.10+">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-22A06B?style=flat" alt="代码许可证：MIT"></a>
  <img src="https://img.shields.io/badge/PDF-A4-E05D44?style=flat" alt="PDF：A4">
</p>

<p align="center">
  <a href="https://github.com/namishu/printables/releases/latest">下载链接</a> · <a href="CHANGELOG.md">更新记录</a>
</p>

## 书写纸

提供横条、方格和英文四线三格三种版式，适合抄写、计算和字母练习。家里临时需要练习纸，或课堂上需要统一发放时，选择所需样式即可打印。

<p align="center">
  <a href="examples/writing-paper/writing-paper-lined.pdf"><img src="examples/writing-paper/preview.png" alt="横条书写纸" width="180"></a>
  <a href="examples/writing-paper/writing-paper-grid.pdf"><img src="examples/writing-paper/grid.png" alt="正方格纸" width="180"></a>
  <a href="examples/writing-paper/writing-paper-english.pdf"><img src="examples/writing-paper/english.png" alt="英文四线三格纸" width="180"></a>
</p>

<p align="center">
  <a href="docs/writing-paper.md">使用说明</a> · 样例 PDF：<a href="examples/writing-paper/writing-paper-lined.pdf">横条</a> · <a href="examples/writing-paper/writing-paper-grid.pdf">方格</a> · <a href="examples/writing-paper/writing-paper-english.pdf">英文</a>
</p>

## 评分卡

孩子与父母可以用同一张卡，针对一次具体表现给出反馈。选择分数、涂上爱心，再写一句感受或希望，让评分成为交流的起点。

<p align="center">
  <a href="examples/rating-card/rating-card.pdf"><img src="examples/rating-card/preview.png" alt="评分卡：上下两张卡片，五档评分及可涂色的爱心" width="320"></a>
</p>

<p align="center">
  <a href="docs/rating-card.md">使用说明</a> · <a href="examples/rating-card/rating-card.pdf">样例 PDF</a>
</p>

## 权益卡

把家长答应孩子的事写下来，减少遗忘和误会。签名后剪开，上卡交给孩子，下卡由家长留底并记录兑现条件，兑现时一起核对。

<p align="center">
  <a href="examples/reward-card/reward-card.pdf"><img src="examples/reward-card/preview.png" alt="权益卡：上半页填写约定，下半页记录权益说明，中间为签名裁剪线" width="320"></a>
</p>

<p align="center">
  <a href="docs/reward-card.md">使用说明</a> · <a href="examples/reward-card/reward-card.pdf">样例 PDF</a>
</p>

## 拼音表

把声母、韵母和整体认读音节分别排成一页，方便孩子认读、指读和复习。每页字号统一，也可以只打印当前练习的一类。

<p align="center">
  <a href="examples/pinyin-chart/pinyin-chart.pdf"><img src="examples/pinyin-chart/preview.png" alt="拼音表：韵母分别置于矩形框内，整齐排列" width="440"></a>
</p>

<p align="center">
  <a href="docs/pinyin-chart.md">使用说明</a> · <a href="examples/pinyin-chart/pinyin-chart.pdf">样例 PDF</a>
</p>

## 汉字卡

用于识字、认读和亲子练习，内置 300 个常用汉字。每页两个字，配有拼音，也可以指定孩子正在学习的几个字单独打印。

<p align="center">
  <a href="examples/hanzi-card/hanzi-card.pdf"><img src="examples/hanzi-card/preview.png" alt="汉字卡：天地两个字及其拼音，每字占半页" width="440"></a>
</p>

<p align="center">
  <a href="docs/hanzi-card.md">使用说明</a> · <a href="examples/hanzi-card/hanzi-card.pdf">样例 PDF</a>
</p>

## 价值观探索表

适合家庭聚会、朋友交流或独自思考。从 80 个选项中逐步选出自己最在意的事情，分享选择的理由，再看看日常行动是否与这些追求一致。

<p align="center">
  <a href="examples/values-worksheet/values-worksheet.pdf"><img src="examples/values-worksheet/preview.png" alt="价值观探索表：80 个选项分为四列，每项旁有勾选框" width="320"></a>
</p>

<p align="center">
  <a href="docs/values-worksheet.md">使用说明</a> · <a href="examples/values-worksheet/values-worksheet.pdf">样例 PDF</a>
</p>

## 安装

需要 Python 3.10+。在项目目录中安装：

```bash
uv tool install .
```

或者安装到当前 Python 环境：

```bash
python -m pip install .
```

两种方式均提供 `namishu-printables` 命令。内置配置和字体随包提供，可离线生成 PDF。

## 快速开始

以下命令生成的 PDF 默认保存在当前目录。

```bash
namishu-printables writing-paper lined
```

生成一页横条书写纸 `writing-paper-lined.pdf`。方格纸、英文四线三格纸和分栏用法见[书写纸说明](docs/writing-paper.md)。

```bash
namishu-printables rating-card
```

生成一页 `rating-card.pdf`，包含两张可填写、涂色的评分卡。使用步骤和评分文字设置见[评分卡说明](docs/rating-card.md)。

```bash
namishu-printables reward-card
```

生成一页 `reward-card.pdf`，包含交给孩子的权益卡和家长保留的存根。填写与使用方法见[权益卡说明](docs/reward-card.md)。

```bash
namishu-printables pinyin-chart
```

生成三页 `pinyin-chart-all.pdf`，声母、韵母和整体认读音节各一页。单独打印某一类的用法见[拼音表说明](docs/pinyin-chart.md)。

```bash
namishu-printables hanzi-card
```

生成内置 300 个汉字的 `hanzi-card.pdf`，每页两个字，共 150 页。打印少量汉字或指定拼音的用法见[汉字卡说明](docs/hanzi-card.md)。

```bash
namishu-printables values-worksheet
```

生成一页 `values-worksheet.pdf`，包含 80 个可勾选的价值选项。活动步骤、导出词表和自定义选项的用法见[价值观探索表说明](docs/values-worksheet.md)。

## 许可证

代码、原创文档和模板设计采用 [MIT](LICENSE)。内置字体的版权归原作者所有，并保留原始许可证。
