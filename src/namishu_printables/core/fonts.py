from __future__ import annotations

import hashlib
from functools import lru_cache
from importlib.resources import as_file, files
from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


def load_font(raw_path: str, *, content: bool = False) -> str:
    if raw_path == "bundled":
        name = "pinyin-regular.ttf" if content else "NotoSansSC-Light.ttf"
        with as_file(files("namishu_printables").joinpath(f"assets/fonts/{name}")) as path:
            return _load_path(path)
    return _load_path(Path(raw_path))


def _load_path(path: Path) -> str:
    try:
        stat = path.stat()
        return _register(str(path.resolve()), stat.st_mtime_ns, stat.st_size)
    except Exception as exc:
        raise ValueError(f"Cannot load font {path}: {exc}") from exc


@lru_cache(maxsize=16)
def _register(path: str, modified: int, size: int) -> str:
    identity = hashlib.sha256(f"{path}:{modified}:{size}".encode()).hexdigest()[:20]
    name = f"Namishu-{identity}"
    pdfmetrics.registerFont(TTFont(name, path))
    return name


def require_glyphs(font: str, text: str) -> None:
    face = pdfmetrics.getFont(font).face
    missing = sorted({char for char in text if ord(char) not in face.charToGlyph})
    if missing:
        labels = ", ".join(f"{char} (U+{ord(char):04X})" for char in missing)
        raise ValueError(f"Font is missing glyphs: {labels}; configure a font that supports them")
