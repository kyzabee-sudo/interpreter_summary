from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO

from pypdf import PdfReader

PDF_MAGIC = b"%PDF"
MAX_PAGES_HINT = 400

PAGE_MARKER_RE = re.compile(r"\[Page\s+(\d+)\]", re.IGNORECASE)
INTERPRETER_LEADING_RE = re.compile(
    r"^(\d{1,4})\s*[•·.\u00b7\u2022]\s*Interpreter\b",
    re.IGNORECASE,
)
INTERPRETER_TRAILING_RE = re.compile(
    r"[•·.\u00b7\u2022]\s*(\d{1,4})\s*$",
)

_CHAR_MAP = str.maketrans(
    {
        "\u00ad": "",
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2002": " ",
        "\u2003": " ",
        "\u2009": " ",
        "\u00a0": " ",
    }
)
_SOFT_HYPHEN_RE = re.compile(r"\u00ad\s*")
# Line-break hyphenation from PDF extractors: "writ -\nten" and "writ-\nten".
# A compound with no line break ("thirty-seventh") is left alone.
_LINE_HYPHEN_RE = re.compile(r"([A-Za-z])\s*-\s*\n\s*([A-Za-z])")
# After dashes are mapped to "-", drop spaces so "hand — the" matches "hand-the".
_DASH_SPACE_RE = re.compile(r"(?<=[A-Za-z])\s*-\s*(?=[A-Za-z])")


class PdfError(ValueError):
    """Raised when an upload is not a usable PDF."""


@dataclass(frozen=True)
class PdfPage:
    viewer_page: int
    journal_page: int
    text: str
    normalized: str


@dataclass(frozen=True)
class PdfCorpus:
    pages: list[PdfPage]
    used_printed_pages: bool
    # Body words at the main text size, when the PDF exposes font sizes.
    # Notes and running furniture are left out. None if the extract failed.
    body_words: int | None = None

    @property
    def page_count(self) -> int:
        return len(self.pages)

    @property
    def journal_start(self) -> int | None:
        return self.pages[0].journal_page if self.pages else None

    @property
    def journal_end(self) -> int | None:
        return self.pages[-1].journal_page if self.pages else None

    def pages_containing(self, phrase: str) -> list[int]:
        needle = normalize_for_match(phrase)
        if not needle:
            return []
        hits = [page.journal_page for page in self.pages if needle in page.normalized]
        if hits:
            return hits
        words = phrase.split()
        for count in (4, 3):
            if len(words) <= count:
                continue
            shorter = " ".join(words[:count])
            short_needle = normalize_for_match(shorter)
            if len(short_needle) < 12:
                continue
            hits = [page.journal_page for page in self.pages if short_needle in page.normalized]
            if hits:
                return hits
        return []

    def pagination_hint(self) -> str:
        n = self.page_count
        if not self.pages:
            return "The attached PDF appears to have no extractable pages."
        start = self.journal_start
        end = self.journal_end
        if not self.used_printed_pages:
            return (
                f"No printed journal pagination was detected. There are {n} viewer pages. "
                "Omit locators rather than guessing page numbers."
            )
        if start == 1 and end == n:
            return (
                f"Printed pages are {start}–{end}, matching the page labels in the PDF "
                "(including any [Page N] markers)."
            )
        offset = start - 1
        return (
            f"Printed journal pages are {start}–{end}. "
            f"PDF viewer page 1 is printed page {start} "
            f"(viewer page k = printed page {offset} + k). "
            "Use printed pages in locators, never the viewer index. "
            f'Running headers look like "{start + 1} • Interpreter …" or '
            f'"Author, "Short Title" • {start + 2}". '
            f"The first leaf may omit the header; it is still printed page {start}."
        )

    def joined_body_readable(self) -> str:
        """Page bodies joined so quotes can span printed pages and hyphen breaks."""
        chunks = [_page_body(page.text) for page in self.pages]
        return readable_text("\n".join(chunks))


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


def readable_text(text: str) -> str:
    """Join hyphenation and collapse whitespace while keeping original casing."""
    return _prepare_text(text, casefold=False)


def normalize_for_match(text: str) -> str:
    """Collapse hyphenation, quotes, and whitespace for locator checks."""
    return _prepare_text(text, casefold=True)


def _prepare_text(text: str, *, casefold: bool) -> str:
    if not text:
        return ""
    text = _SOFT_HYPHEN_RE.sub("", text)
    text = _LINE_HYPHEN_RE.sub(r"\1\2", text)
    text = text.translate(_CHAR_MAP)
    text = re.sub(r"\s+", " ", text).strip()
    text = _DASH_SPACE_RE.sub("-", text)
    return text.casefold() if casefold else text


def _page_body(text: str) -> str:
    """Drop running headers and [Page N] markers before quote search."""
    text = PAGE_MARKER_RE.sub(" ", text)
    lines = text.splitlines()
    if not lines:
        return ""
    first = lines[0].strip()
    if INTERPRETER_LEADING_RE.match(first) or INTERPRETER_TRAILING_RE.search(first):
        lines = lines[1:]
    return "\n".join(lines)


def parse_printed_page(text: str) -> int | None:
    """Return a printed page number from Interpreter headers or [Page N] markers."""
    if not text or not text.strip():
        return None
    marker = PAGE_MARKER_RE.search(text)
    if marker:
        return int(marker.group(1))
    first_line = text.strip().splitlines()[0].strip()
    leading = INTERPRETER_LEADING_RE.match(first_line)
    if leading:
        return int(leading.group(1))
    trailing = INTERPRETER_TRAILING_RE.search(first_line)
    if trailing:
        value = int(trailing.group(1))
        if 1 <= value <= 1999:
            return value
    return None


def infer_journal_pages(raw_pages: list[int | None]) -> tuple[list[int], bool]:
    """Fill missing printed pages from a constant viewer→journal offset."""
    n = len(raw_pages)
    known = [(index, page) for index, page in enumerate(raw_pages) if page is not None]
    if not known:
        return list(range(1, n + 1)), False
    offsets = sorted(page - (index + 1) for index, page in known)
    offset = offsets[len(offsets) // 2]
    inferred: list[int] = []
    for index, page in enumerate(raw_pages):
        if page is not None:
            inferred.append(page)
            continue
        value = (index + 1) + offset
        inferred.append(value if value >= 1 else index + 1)
    return inferred, True


def extract_pdf_corpus(data: bytes) -> PdfCorpus:
    reader = PdfReader(BytesIO(data))
    texts = [(index, page.extract_text() or "") for index, page in enumerate(reader.pages, start=1)]
    raw = [parse_printed_page(text) for _index, text in texts]
    journal_pages, used_printed = infer_journal_pages(raw)
    pages = [
        PdfPage(
            viewer_page=viewer,
            journal_page=journal,
            text=text,
            normalized=normalize_for_match(text),
        )
        for (viewer, text), journal in zip(texts, journal_pages, strict=True)
    ]
    return PdfCorpus(
        pages=pages,
        used_printed_pages=used_printed,
        body_words=estimate_body_words(data),
    )


def estimate_body_words(data: bytes) -> int | None:
    """Count words set in the article's main text size.

    Interpreter PDFs usually store a font size of 1 and the real size in the
    text matrix. The size that carries the most words is treated as the body.
    Smaller text (notes, captions, running heads) is left out. Titles and
    other larger text are kept. Returns None when the file yields no words.
    """
    reader = PdfReader(BytesIO(data))
    buckets: dict[float, int] = {}

    def visitor(text, cm, tm, font_dict, font_size):
        words = len(re.findall(r"[A-Za-z0-9']+", text or ""))
        if not words:
            return
        scale = 1.0
        if tm is not None and len(tm) >= 4:
            scale *= abs(float(tm[3])) or 1.0
        if cm is not None and len(cm) >= 4:
            scale *= abs(float(cm[3])) or 1.0
        rendered = round(float(font_size) * scale, 1)
        buckets[rendered] = buckets.get(rendered, 0) + words

    for page in reader.pages:
        page.extract_text(visitor_text=visitor)
    if not buckets:
        return None
    usable = {size: count for size, count in buckets.items() if size >= 6}
    if not usable:
        # Sizes never left the unit square. Count every word rather than guess.
        total = sum(buckets.values())
        return total or None
    modal = max(usable, key=usable.get)
    body = sum(count for size, count in usable.items() if size + 0.05 >= modal)
    return body or None


def extract_pdf_text(data: bytes, max_chars: int = 500_000) -> str:
    """Local text extract used for locator checks and as a fallback dump."""
    corpus = extract_pdf_corpus(data)
    chunks: list[str] = []
    total = 0
    for page in corpus.pages:
        block = f"[Page {page.journal_page}]\n{page.text.strip()}\n"
        chunks.append(block)
        total += len(block)
        if total >= max_chars:
            chunks.append("\n[Truncated for length]\n")
            break
    return "\n".join(chunks)
