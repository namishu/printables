"""检查标签与包版本一致，并提取该版本的中文更新记录。"""

from __future__ import annotations

import sys
from pathlib import Path

from namishu_printables import __version__


def release_notes(tag: str, changelog: str) -> str:
    if tag != f"v{__version__}":
        raise ValueError(f"标签 {tag} 与包版本 {__version__} 不一致")
    heading = f"## {__version__}"
    lines = changelog.splitlines()
    for index, line in enumerate(lines):
        if line == heading or line.startswith(heading + " - "):
            body = []
            for entry in lines[index + 1 :]:
                if entry.startswith("## "):
                    break
                body.append(entry)
            notes = "\n".join(body).strip()
            if notes:
                url = f"https://github.com/namishu/printables/releases/download/{tag}/namishu-printables-pdf.zip"
                return f"[下载整套 PDF]({url})\n\n{notes}\n"
    raise ValueError(f"CHANGELOG.md 缺少 {__version__} 的更新记录")


if __name__ == "__main__":
    changelog = Path(__file__).resolve().parents[1] / "CHANGELOG.md"
    print(release_notes(sys.argv[1], changelog.read_text(encoding="utf-8")), end="")
