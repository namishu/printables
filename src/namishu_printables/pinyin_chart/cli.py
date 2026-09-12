from __future__ import annotations

import argparse

import yaml

from .. import __version__
from .app import PinyinChartApp


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="namishu-printables pinyin-chart",
        description="生成声母、韵母和整体认读音节表，每页字号一致，文字在框内居中。",
    )
    parser.add_argument(
        "category",
        nargs="?",
        default="all",
        choices=["shengmu", "yunmu", "yinjie", "all"],
        help="默认生成全部三类；指定类别可单独生成",
    )
    parser.add_argument("--config", help="YAML design overrides")
    parser.add_argument("-o", "--output", help="PDF path (default: descriptive filename in current directory)")
    parser.add_argument("--version", action="version", version=f"namishu-printables {__version__}")
    args = parser.parse_args(argv)
    try:
        app = PinyinChartApp(args.config)
        plan = app.plan(args.category)
        output = app.render(plan, args.output)
    except (ValueError, OSError, yaml.YAMLError) as exc:
        parser.error(str(exc))
    print(f"Generated 1 PDF: {output} ({len(plan.pages)} pages)")
    for page in plan.pages:
        print(f"  {page.category.id}: {len(page.cards)} items, {len(page.rows)} rows")
    return 0
