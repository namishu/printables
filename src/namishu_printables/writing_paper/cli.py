from __future__ import annotations

import argparse

import yaml

from .. import __version__
from .app import WritingPaperApp


def main(argv: list[str] | None = None) -> int:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--config", help="YAML overrides (relative to the current directory)", default=argparse.SUPPRESS
    )
    common.add_argument(
        "-o",
        "--output",
        help="Output PDF (default: writing-paper-<kind>.pdf in the current directory)",
        default=argparse.SUPPRESS,
    )
    # Support common options both before and after the paper type.
    parser = argparse.ArgumentParser(
        prog="namishu-printables writing-paper",
        description="Generate one page of writing paper as PDF.",
        parents=[common],
    )
    subparsers = parser.add_subparsers(dest="kind", required=True)
    lined = subparsers.add_parser("lined", parents=[common], help="Lined paper (default: 20 rows, 1 column)")
    lined.add_argument("--rows", type=int, help="Writing spaces; default range 1–26")
    lined.add_argument("--columns", type=int, help="书写栏数；默认允许范围 1～3")
    grid = subparsers.add_parser("grid", parents=[common], help="Square grid (default: 10 mm cells)")
    grid.add_argument("--cell-size", type=float, help="Square side in mm; default range 5–20")
    english = subparsers.add_parser("english", parents=[common], help="Four-line English handwriting paper")
    english.add_argument("--columns", type=int, help="书写栏数；默认允许范围 1～3")
    parser.add_argument("--version", action="version", version=f"namishu-printables {__version__}")
    args = parser.parse_args(argv)
    try:
        app = WritingPaperApp(getattr(args, "config", None))
        plan = app.plan(
            args.kind,
            rows=getattr(args, "rows", None),
            columns=getattr(args, "columns", None),
            cell_size=getattr(args, "cell_size", None),
        )
        output = app.render(plan, getattr(args, "output", None))
    except (ValueError, OSError, yaml.YAMLError) as exc:
        parser.error(str(exc))
    details = f"{plan.rows} rows × {plan.columns} columns"
    if plan.cell_size_mm is not None:
        details += f", {plan.cell_size_mm:g} mm squares, {plan.rows * plan.columns} cells"
    print(f"Generated 1 page: {output} ({details})")
    return 0
