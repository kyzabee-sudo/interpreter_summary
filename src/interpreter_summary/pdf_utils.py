from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader

PDF_MAGIC = b"%PDF"
MAX_PAGES_HINT = 400


class PdfError(ValueError):
    """Raised when an upload is not a usable PDF."""


def validate_pdf(data: bytes, filename: str, max_bytes: int) -> None:
    if not filename.lower().endswith(".pdf"):
        raise PdfError("Please upload a PDF file.")
    if not data:
        raise PdfError("The PDF file is empty.")
    if len(data) > max_bytes:
        mb = max_bytes // (1024 * 1024)
        raise PdfError(f"PDF is larger than the {mb} MB upload limit.")
    if not data.lstrip().startswith(PDF_MAGIC):
        raise PdfError("File does not look like a PDF.")


def pdf_page_count(data: bytes) -> int:
    reader = PdfReader(BytesIO(data))
    return len(reader.pages)


def extract_pdf_text(data: bytes, max_chars: int = 500_000) -> str:
    """Local text extract used only as a fallback if file-search is unavailable."""
    reader = PdfReader(BytesIO(data))
    chunks: list[str] = []
    total = 0
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        block = f"[Page {index}]\n{text.strip()}\n"
        chunks.append(block)
        total += len(block)
        if total >= max_chars:
            chunks.append("\n[Truncated for length]\n")
            break
    return "\n".join(chunks)
