from __future__ import annotations

import re

# Summary length still scales with the article, then caps. The September 2026
# posts run longer than the old Takeaway/Summary/Reflection drafts when the
# article is a list: Squire (~14 pages, narrative plus three element-pairs)
# ~520 summary words; Clark (~23 pages, one bullet per apostle) ~810; Ahlstrom
# (~22 pages, nine parallels) ~1,300. Takeaway and Q&A stay roughly fixed.
# Video scripts are about 10 rows regardless of page count.

_SEPARATOR_CELL_RE = re.compile(r":?-{3,}:?")
_QUESTION_HEADING_RE = re.compile(r"^#{2,3}\s+(.+?)\s*$", re.MULTILINE)
_BOLD_QUESTION_RE = re.compile(r"^\*\*[^*]+\?\*\*\s*$", re.MULTILINE)


def summary_word_target(article_pages: int) -> tuple[int, int, int]:
    """Return (low, high, hard_max) word counts for The Summary section."""
    pages = max(1, article_pages)
    if pages <= 12:
        return 300, 500, 650
    if pages <= 24:
        return 450, 900, 1400
    if pages <= 40:
        return 650, 1200, 1600
    return 800, 1400, 1800


def count_words(text: str) -> int:
    cleaned = re.sub(r"\(link to [^)]+\)", "", text)
    cleaned = re.sub(r"\[[^\]]+\]\s*", "", cleaned)
    return len(re.findall(r"[A-Za-z0-9']+", cleaned))


def question_count(qa_markdown: str) -> int:
    headings = [line.strip() for line in _QUESTION_HEADING_RE.findall(qa_markdown)]
    questions = [line for line in headings if line.endswith("?")]
    if questions:
        return len(questions)
    return len(_BOLD_QUESTION_RE.findall(qa_markdown))


def video_row_count(video_markdown: str) -> int:
    """Count data rows in a Markdown video-script table (header excluded)."""
    rows = 0
    seen_header = False
    for raw in video_markdown.replace("\r\n", "\n").split("\n"):
        line = raw.strip()
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if cells and all(_SEPARATOR_CELL_RE.fullmatch(cell.replace(" ", "")) for cell in cells):
            continue
        if not seen_header:
            seen_header = True
            continue
        if any(cells):
            rows += 1
    return rows


def length_hint(
    article_pages: int,
    *,
    printed_start: int | None = None,
    printed_end: int | None = None,
) -> str:
    low, high, hard_max = summary_word_target(article_pages)
    span = ""
    if printed_start is not None and printed_end is not None:
        span = f" (printed {printed_start}–{printed_end})"
    return (
        f"This article is {article_pages} PDF pages{span}. "
        "The Takeaway: one or two sentences (about 20–55 words). "
        "The Q&A: exactly three questions; each answer a few sentences (about 40–90 words). "
        f"The Summary: about {low}–{high} words, never more than {hard_max}. "
        "Cover the argument in order. One bullet per person, parallel, or element when the "
        "article is a list; that case may use the upper part of the range, up to the hard max. "
        "Do not pad a short narrative just to hit the high target. "
        "Mention an appendix in one sentence if it matters; do not summarize it. "
        "Video script: about 10 rows (9–12). Each narration is one to three spoken sentences. "
        'The last row ends with "and I\'ll see you next week." '
        "Do not write a Reflection."
    )


def summary_length_note(summary_words: int, article_pages: int) -> str:
    low, high, hard_max = summary_word_target(article_pages)
    status = "on target"
    if summary_words > hard_max:
        status = "over max"
    elif summary_words > high:
        status = "long"
    elif summary_words < low:
        status = "short"
    return f"summary {summary_words} words ({status}; target {low}–{high}, max {hard_max})"


def qa_length_note(qa_words: int, questions: int) -> str:
    count = "3 questions" if questions == 3 else f"{questions} questions (expected 3)"
    if qa_words < 120:
        status = "short"
    elif qa_words > 360:
        status = "long"
    else:
        status = "on target"
    return f"Q&A {qa_words} words ({status}; {count})"


def video_length_note(rows: int) -> str:
    if 9 <= rows <= 12:
        status = "on target"
    elif rows < 9:
        status = "short"
    else:
        status = "long"
    return f"video {rows} rows ({status}; target about 10)"
