from pathlib import Path

import pytest

from interpreter_summary.pdf_utils import PdfError, pdf_page_count, validate_pdf
from interpreter_summary.samples import generate_samples, write_sample_pdf
from interpreter_summary.style import load_style_text


def test_validate_pdf_rejects_non_pdf():
    with pytest.raises(PdfError, match="PDF"):
        validate_pdf(b"not a pdf", "notes.txt", 1024)


def test_validate_pdf_rejects_empty():
    with pytest.raises(PdfError, match="empty"):
        validate_pdf(b"", "article.pdf", 1024)


def test_validate_pdf_rejects_oversize():
    with pytest.raises(PdfError, match="larger"):
        validate_pdf(b"%PDF-1.4 oversized", "article.pdf", 8)


def test_sample_pdf_and_style_docx(tmp_path: Path):
    pdf_path, docx_path = generate_samples(tmp_path)
    data = pdf_path.read_bytes()
    validate_pdf(data, pdf_path.name, 5 * 1024 * 1024)
    assert pdf_page_count(data) == 3

    style = load_style_text(docx_path)
    assert "The Takeaway" in style
    assert "link to" in style
    assert "Video Script" not in style
    assert "Check the links in the description" not in style


def test_write_sample_pdf_has_printed_page_markers(tmp_path: Path):
    from interpreter_summary.pdf_utils import extract_pdf_text

    path = write_sample_pdf(tmp_path / "article.pdf")
    text = extract_pdf_text(path.read_bytes())
    assert "[Page 1]" in text
    assert "bright copper" in text
