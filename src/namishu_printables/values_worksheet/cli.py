from __future__ import annotations

import argparse

import yaml

from .. import __version__
from .app import ValuesWorksheetApp
from .input import export_default


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="namishu-printables values-worksheet", description="使用内置或自定义词表生成价值观探索表。"
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--file", help="UTF-8 词表文件，每行一项；默认使用内置的 80 项")
    source.add_argument("--export-default", metavar="FILE", help="导出默认词表到文本文件，不生成 PDF")
    parser.add_argument("--config", help="YAML 布局、样式及输入限制配置")
    parser.add_argument("-o", "--output", help="PDF 输出路径，默认输出到当前目录")
    parser.add_argument("--version", action="version", version=f"namishu-printables {__version__}")
    args = parser.parse_args(argv)
    if args.export_default is not None and (args.config is not None or args.output is not None):
        parser.error("--export-default 不能与 --config 或 --output 一起使用")
    try:
        if args.export_default is not None:
            output = export_default(args.export_default)
            print(f"已导出默认词表：{output}")
            return 0
        output = ValuesWorksheetApp(args.config).generate(file_path=args.file, output_path=args.output)
    except (ValueError, OSError, yaml.YAMLError) as exc:
        parser.error(str(exc))
    print(f"Generated 1 PDF: {output} (1 page)")
    return 0
