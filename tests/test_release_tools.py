from __future__ import annotations

import runpy
from pathlib import Path

import pytest

from namishu_printables import __version__

ROOT = Path(__file__).resolve().parents[1]


def test_release_requires_matching_version_and_dated_notes():
    notes = runpy.run_path(str(ROOT / "scripts/release_notes.py"))["release_notes"]
    content = f"# 更新记录\n\n## 未发布\n\n后续内容\n\n## {__version__} - 2026-09-12\n\n- 首次提供 PDF。\n"
    result = notes(f"v{__version__}", content)
    assert "首次提供 PDF" in result
    assert "后续内容" not in result
    assert f"releases/download/v{__version__}/namishu-printables-pdf.zip" in result
    with pytest.raises(ValueError, match="不一致"):
        notes("v999.0.0", content)
    with pytest.raises(ValueError, match="缺少"):
        notes(f"v{__version__}", "## 未发布\n尚未确认发布")


def test_bundle_refuses_existing_destination(tmp_path):
    build = runpy.run_path(str(ROOT / "scripts/build_pdf_bundle.py"))["build_bundle"]
    destination = tmp_path / "pdfs"
    destination.mkdir()
    existing = destination / "rating-card.pdf"
    existing.write_bytes(b"keep")
    with pytest.raises(FileExistsError):
        build(destination)
    assert existing.read_bytes() == b"keep"
