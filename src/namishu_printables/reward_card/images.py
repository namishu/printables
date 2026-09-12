from __future__ import annotations

from importlib.resources import files
from io import BytesIO

from reportlab.lib.utils import ImageReader

BUILTIN_ICONS = frozenset({"star", "event", "face", "cut"})


def read_icon(name: str) -> ImageReader:
    try:
        if name in BUILTIN_ICONS:
            resource = files(__package__).joinpath(f"gfx/{name}.png")
            reader = ImageReader(BytesIO(resource.read_bytes()))
        else:
            reader = ImageReader(name)
        reader.getRGBData()  # Decode now so damaged images fail during planning.
        return reader
    except Exception as exc:
        raise ValueError(f"Cannot load icon: {name}") from exc
