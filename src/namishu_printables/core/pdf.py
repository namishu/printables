"""Atomic PDF output: preserve the destination until the whole document succeeds."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile

from reportlab.pdfgen.canvas import Canvas


def output_path(path: str | Path) -> Path:
    output = Path(path).resolve()
    if output.suffix.lower() != ".pdf":
        raise ValueError("output_path must have a .pdf extension")
    return output


@contextmanager
def pdf_document(output: Path, *, title: str) -> Iterator[Canvas]:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with NamedTemporaryFile(prefix=f".{output.stem}-", suffix=".tmp", dir=output.parent, delete=False) as handle:
            temporary = Path(handle.name)
        pdf = Canvas(str(temporary), pageCompression=1)
        pdf.setTitle(title)
        yield pdf
        pdf.save()
        os.replace(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
