from __future__ import annotations

import pytest
from pypdf import PdfReader

import namishu_printables.core.pdf as pdf_module
import namishu_printables.writing_paper.app as paper_module
from namishu_printables.core.configuration import merge
from namishu_printables.core.pdf import output_path, pdf_document
from namishu_printables.writing_paper import WritingPaperApp


def test_writing_paper_failure_preserves_pdf(tmp_path, monkeypatch):
    output = tmp_path / "paper.pdf"
    app = WritingPaperApp()
    app.generate("lined", output_path=output)
    before = output.read_bytes()

    def fail(pdf, plan):
        pdf.line(0, 0, 10, 10)
        raise RuntimeError("drawing failed")

    monkeypatch.setattr(paper_module, "draw_page", fail)
    with pytest.raises(RuntimeError, match="drawing failed"):
        app.generate("grid", output_path=output)
    assert output.read_bytes() == before
    assert len(PdfReader(output).pages) == 1
    assert list(tmp_path.iterdir()) == [output]


@pytest.mark.parametrize("failure", ["save", "replace"])
def test_finalization_failure_preserves_destination(tmp_path, monkeypatch, failure):
    output = tmp_path / "existing.pdf"
    output.write_bytes(b"existing document")

    def fail(*args, **kwargs):
        raise OSError("finalization failed")

    if failure == "save":
        monkeypatch.setattr(pdf_module.Canvas, "save", fail)
    else:
        monkeypatch.setattr(pdf_module.os, "replace", fail)
    with pytest.raises(OSError, match="finalization failed"), pdf_document(output, title="test") as pdf:
        pdf.drawString(10, 10, "test")
        pdf.showPage()
    assert output.read_bytes() == b"existing document"
    assert list(tmp_path.iterdir()) == [output]


def test_invalid_output_does_not_create_parent(tmp_path):
    with pytest.raises(ValueError, match=".pdf"):
        output_path(tmp_path / "missing/output.txt")
    assert not list(tmp_path.iterdir())


def test_merge_does_not_change_defaults_and_rejects_unknown():
    base = {"layout": {"width_mm": 210}, "enabled": True}
    assert merge(base, {"layout": {"width_mm": 297}})["layout"]["width_mm"] == 297
    assert base["layout"]["width_mm"] == 210
    with pytest.raises(ValueError, match="Unknown configuration key"):
        merge(base, {"layout": {"widht_mm": 100}})
    with pytest.raises(ValueError, match="Invalid value"):
        merge(base, {"layout": {"width_mm": True}})
