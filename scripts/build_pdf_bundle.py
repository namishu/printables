"""使用已安装的命令生成并检查发布用 PDF；输出目录必须尚不存在。"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

from pypdf import PdfReader

PDFS = (
    ("writing-paper-lined.pdf", ("writing-paper", "lined"), 1),
    ("writing-paper-grid.pdf", ("writing-paper", "grid"), 1),
    ("writing-paper-english.pdf", ("writing-paper", "english"), 1),
    ("rating-card.pdf", ("rating-card",), 1),
    ("reward-card.pdf", ("reward-card",), 1),
    ("pinyin-chart.pdf", ("pinyin-chart",), 3),
    ("hanzi-card.pdf", ("hanzi-card",), 150),
    ("values-worksheet.pdf", ("values-worksheet",), 1),
)


def build_bundle(output: Path) -> Path:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"输出目录已存在：{output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".pdf-bundle-", dir=output.parent) as temporary:
        staging = Path(temporary) / "pdfs"
        staging.mkdir()
        for filename, command, pages in PDFS:
            subprocess.run(
                [sys.executable, "-m", "namishu_printables", *command, "-o", str(staging / filename)],
                cwd=temporary,
                check=True,
            )
            with (staging / filename).open("rb") as stream:
                reader = PdfReader(stream, strict=True)
                if reader.is_encrypted or len(reader.pages) != pages:
                    raise ValueError(f"PDF 页数或格式不符合预期：{filename}")
                for page in reader.pages:
                    contents = page.get_contents()
                    if contents is None or not contents.get_data().strip():
                        raise ValueError(f"PDF 出现空白页面：{filename}")
                    # 书写纸仅包含线条，没有文字。
                    if command[0] != "writing-paper" and not page.extract_text().strip():
                        raise ValueError(f"PDF 页面缺少文字：{filename}")
        archive = staging / "namishu-printables-pdf.zip"
        with ZipFile(archive, "w", compression=ZIP_DEFLATED) as bundle:
            for filename, _, _ in PDFS:
                bundle.write(staging / filename, arcname=filename)
        with ZipFile(archive) as bundle:
            if bundle.testzip() is not None:
                raise ValueError("ZIP 校验失败")
        staging.rename(output)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("dist/pdf"), help="输出目录，默认 dist/pdf")
    args = parser.parse_args()
    build_bundle(args.output)
