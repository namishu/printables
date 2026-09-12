from __future__ import annotations

import argparse

import yaml

from .. import __version__
from .app import RatingCardApp


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="namishu-printables rating-card", description="生成一页两张的亲子评分卡。")
    parser.add_argument("--config", help="YAML 布局和评分文字配置")
    parser.add_argument("-o", "--output", help="PDF 输出路径，默认在当前目录生成 rating-card.pdf")
    parser.add_argument("--version", action="version", version=f"namishu-printables {__version__}")
    args = parser.parse_args(argv)
    try:
        output = RatingCardApp(args.config).generate(output_path=args.output)
    except (ValueError, OSError, yaml.YAMLError) as exc:
        parser.error(str(exc))
    print(f"已生成 PDF：{output}（1 页，2 张评分卡）")
    return 0
