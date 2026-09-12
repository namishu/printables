from __future__ import annotations

import argparse

import yaml

from .. import __version__
from .app import RewardCardApp


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="namishu-printables reward-card", description="生成上下两张权益卡，沿页面中央虚线裁开。"
    )
    parser.add_argument("--config", help="指定 YAML 配置")
    parser.add_argument("-o", "--output", help="输出路径（默认：当前目录的 reward-card.pdf）")
    parser.add_argument("--version", action="version", version=f"namishu-printables {__version__}")
    args = parser.parse_args(argv)
    try:
        output = RewardCardApp(args.config).generate(output_path=args.output)
    except (ValueError, OSError, yaml.YAMLError) as exc:
        parser.error(str(exc))
    print(f"Generated 1 PDF: {output} (1 page)")
    return 0
