"""Dispatch commands without importing unrelated rendering dependencies."""

from __future__ import annotations

import argparse
import sys
from importlib import import_module

from . import __version__

COMMANDS = {
    "rating-card": "亲子评分卡，每页两张，可涂色爱心",
    "values-worksheet": "价值观探索表，内置或自定义词表",
    "reward-card": "Blank reward voucher with signatures and usage notes",
    "hanzi-card": "Chinese character cards, up to two characters per page",
    "pinyin-chart": "拼音表，包含声母、韵母和整体认读音节",
    "writing-paper": "Lined, square-grid and English handwriting paper",
}


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        prog="namishu-printables",
        description="Printable cards and paper templates for learning and family activities.",
        epilog="\n".join(f"  {name:<18} {description}" for name, description in COMMANDS.items()),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"namishu-printables {__version__}")
    parser.add_argument("tool", choices=COMMANDS, help="Template to generate; use TOOL --help for options")
    parser.add_argument("arguments", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    module = import_module(f".{args.tool.replace('-', '_')}.cli", package="namishu_printables")
    return module.main(args.arguments)
