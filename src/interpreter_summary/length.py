from __future__ import annotations

import re

# Length follows Kyler's September 2026 posts after the Squire trial: the AI
# draft ran about 850 summary words and 290 Q&A words against his ~444 and
# ~145. A typical article stays near 400–550 summary words before the closing
# quote, even when the PDF is 15–25 pages. Only a genuinely list-heavy article
# should run longer, and the checker still flags that as long rather than
# treating 800 words as the target. Video scripts stay about 10 rows.

_SEPARATOR_CELL_RE = re.compile(r":?-{3,}:?")
_QUESTION_HEADING_RE = re.compile(r"^#{2,3}\s+(.+?)\s*$", re.MULTILINE)
_BOLD_QUESTION_RE = re.compile(r"^\*\*[^*]+\?\*\*\s*$", re.MULTILINE)
_ATTRIBUTION_RE = re.compile(
    r"(?i)\b(concludes?|writes?|argues?|notes?|states?|observes?|explains?|puts it)\b.*:\s*$"
)


def summary_word_target(article_pages: int) -> tuple[int, int, int]:
    """Return (low, high, hard_max) for Summary prose before the closing quote.

    Page count is accepted so callers can keep passing it, and so a very long
    PDF can name itself in the hint. It does not raise the target: a 16-page
    article and an 8-page article share the same band.
    """
    del article_pages
    return 400, 550, 700


def summary_prose(summary: str) -> str:
    """Summary text with the closing attribution and block quote removed."""
    lines = summary.replace("\r\n", "\n").split("\n")
    last_quote = None
    for index, line in enumerate(lines):
        if line.startswith(">"):
            last_quote = index
    if last_quote is None:
        return summary.strip()
    start = last_quote
    while start > 0 and (lines[start - 1].startswith(">") or not lines[start - 1].strip()):
        start -= 1
    attr = start - 1
    while attr >= 0 and not lines[attr].strip():
        attr -= 1
    end = start
    if attr >= 0 and _ATTRIBUTION_RE.search(lines[attr].strip()):
        end = attr
    return "\n".join(lines[:end]).strip()


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
        "The Takeaway: one sentence, about 15–25 words. "
        "The Q&A: exactly three questions. Each answer is 2–4 plain sentences, about 40–60 words. "
        f"The Summary, before the closing block quote: about {low}–{high} words, never more than {hard_max}. "
        "That band does not grow with page count. A genuinely list-heavy article (many distinct "
        "people or parallels) may run past the high target, but stay under 1000 and do not "
        "inventory every sub-element. "
        "At most one short quoted phrase per bullet. Explain what each point shows. "
        "End the Summary with As [Surname] concludes (link to \"opening words\"; page N): "
        "and a verbatim block quote. "
        "Mention an appendix in one sentence if it matters; do not summarize it. "
        "Video script: about 10 rows (9–12). Row 1 is a conversational hook about a person or detail. "
        "Each narration is one to three spoken sentences. "
        'The last row ends with "and I\'ll see you next time." '
        "Do not write a Reflection. Output only the post, with no preamble."
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
    return (
        f"summary {summary_words} words before the closing quote "
        f"({status}; target {low}–{high}, max {hard_max})"
    )


def takeaway_length_note(takeaway_words: int) -> str:
    if 15 <= takeaway_words <= 25:
        status = "on target"
    elif takeaway_words < 15:
        status = "short"
    else:
        status = "long"
    return f"takeaway {takeaway_words} words ({status}; target 15–25, one sentence)"


def qa_length_note(qa_words: int, questions: int) -> str:
    count = "3 questions" if questions == 3 else f"{questions} questions (expected 3)"
    # Three answers of about 40–60 words, plus the question lines. Kyler's
    # Squire Q&A is ~145 words; a 280-word Q&A is the too-dense failure.
    if qa_words < 100:
        status = "short"
    elif qa_words > 230:
        status = "long"
    else:
        status = "on target"
    return f"Q&A {qa_words} words ({status}; {count}, answers about 40–60 words)"


def video_length_note(rows: int) -> str:
    if 9 <= rows <= 12:
        status = "on target"
    elif rows < 9:
        status = "short"
    else:
        status = "long"
    return f"video {rows} rows ({status}; target about 10)"
