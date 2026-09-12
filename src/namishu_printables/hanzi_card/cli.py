from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from .. import __version__
from .app import HanziCardApp


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="namishu-printables hanzi-card", description="生成汉字卡 PDF，默认使用内置 300 字，每页两个字。"
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("text", nargs="?", help="汉字文本，支持局部注音，如 重[chong2]庆")
    source.add_argument("--file", help="UTF-8 文本文件，支持 字[zi4] 注音")
    pronunciation = parser.add_mutually_exclusive_group()
    pronunciation.add_argument("--no-pinyin", action="store_true", help="Hide pinyin")
    pronunciation.add_argument("--pinyin", help="逐字指定拼音，以空格分隔，支持 chóng 或 chong2")
    parser.add_argument("--config", help="YAML design overrides")
    parser.add_argument("-o", "--output", help="PDF 保存路径（默认：当前目录下的 hanzi-card.pdf）")
    parser.add_argument("--version", action="version", version=f"namishu-printables {__version__}")
    args = parser.parse_args(argv)
    try:
        app = HanziCardApp(args.config)
        plan = app.plan(args.text, file=args.file, no_pinyin=args.no_pinyin, pinyin=args.pinyin)
        if args.file and args.output and Path(args.file).resolve() == Path(args.output).resolve():
            raise ValueError("Output must not replace the input file")
        output = app.render(plan, args.output)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        parser.error(str(exc))
    print(
        f"Generated 1 PDF: {output} ({len(plan.characters)} characters, {len(plan.pages)} pages; "
        f"ignored {plan.ignored_characters} other characters)"
    )
    return 0
