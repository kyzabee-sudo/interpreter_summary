from __future__ import annotations

import re
from dataclasses import dataclass

# Bands from 32 of Kyler's article/summary pairs (volumes 60–70). Summary
# words exclude the closing block quote and the "(link to …; page N)" text.
# Page count is the default. Body words can only tighten the band, because
# figures and heavy notes inflate page count (Ewell 68_12, Smith 68_15).

_SEPARATOR_CELL_RE = re.compile(r":?-{3,}:?")
_QUESTION_HEADING_RE = re.compile(r"^#{2,3}\s+(.+?)\s*$", re.MULTILINE)
_BOLD_QUESTION_RE = re.compile(r"^\*\*[^*]+\?\*\*\s*$", re.MULTILINE)
_QA_QUESTION_RE = re.compile(r"^(?:#{2,3}\s+.+|\*\*[^*]+\*\*)\s*$")
_LENGTH_COMMENT_RE = re.compile(
    r"<!--\s*length-note\s*:\s*(.*?)\s*-->",
    re.IGNORECASE | re.DOTALL,
)
_LENGTH_SECTION_RE = re.compile(
    r"(?ims)^#{1,3}[ \t]+length note[ \t]*\n.*?(?=^#{1,2}[ \t]+\S|\Z)"
)
_LENGTH_LINE_RE = re.compile(r"(?im)^[ \t]*length note\s*:\s*(.+?)\s*$")

# (max pages or max body words, low, high, soft_max, label)
_PAGE_BANDS: tuple[tuple[int, int, int, int, str], ...] = (
    (12, 200, 330, 400, "≤12 pages"),
    (24, 330, 500, 650, "13–24 pages"),
    (40, 380, 620, 800, "25–40 pages"),
    (10**9, 450, 750, 950, "41+ pages"),
)
# under 5k, 5–8k, 8–11k, 11k+. Upper bounds are exclusive except the last.
_WORD_BANDS: tuple[tuple[int, int, int, int, str], ...] = (
    (5_000, 200, 330, 400, "<5k body words"),
    (8_000, 330, 500, 650, "5–8k body words"),
    (11_000, 380, 620, 800, "8–11k body words"),
    (10**9, 450, 750, 950, "11k+ body words"),
)

TAKEAWAY_LOW, TAKEAWAY_HIGH, TAKEAWAY_SOFT = 20, 35, 45
QA_ANSWER_LOW, QA_ANSWER_HIGH, QA_ANSWER_SOFT = 35, 70, 90
QUOTE_LOW, QUOTE_HIGH, QUOTE_SOFT = 60, 125, 140


@dataclass(frozen=True)
class SummaryTarget:
    low: int
    high: int
    soft_max: int
    page_label: str
    word_label: str | None
    used_body_words: bool

    def describe(self) -> str:
        band = f"target {self.low}–{self.high}, soft max {self.soft_max}"
        if self.used_body_words and self.word_label:
            return f"{band}; {self.word_label} (tighter than {self.page_label})"
        return f"{band}; {self.page_label}"


def _page_band(article_pages: int) -> tuple[int, int, int, str]:
    pages = max(article_pages, 0)
    for limit, low, high, soft, label in _PAGE_BANDS:
        if pages <= limit:
            return low, high, soft, label
    low, high, soft, label = _PAGE_BANDS[-1][1:]
    return low, high, soft, label


def _word_band(body_words: int) -> tuple[int, int, int, str]:
    # under 5k, 5–8k (through 8000), 8–11k (through 11000), 11k+.
    if body_words < 5_000:
        return _WORD_BANDS[0][1:]
    if body_words <= 8_000:
        return _WORD_BANDS[1][1:]
    if body_words <= 11_000:
        return _WORD_BANDS[2][1:]
    return _WORD_BANDS[3][1:]


def usable_body_words(article_pages: int, body_words: int | None) -> int | None:
    """Ignore a body-word estimate that is too thin to trust."""
    if body_words is None or body_words < 400:
        return None
    pages = max(article_pages, 1)
    if pages >= 8 and body_words / pages < 40:
        return None
    return body_words


def summary_target(article_pages: int, body_words: int | None = None) -> SummaryTarget:
    """Pick the Summary band. Body words may only select a shorter band."""
    page_low, page_high, page_soft, page_label = _page_band(article_pages)
    words = usable_body_words(article_pages, body_words)
    if words is None:
        return SummaryTarget(page_low, page_high, page_soft, page_label, None, False)
    word_low, word_high, word_soft, word_label = _word_band(words)
    if (word_soft, word_high, word_low) < (page_soft, page_high, page_low):
        return SummaryTarget(word_low, word_high, word_soft, page_label, word_label, True)
    return SummaryTarget(page_low, page_high, page_soft, page_label, word_label, False)


def summary_word_target(
    article_pages: int,
    body_words: int | None = None,
) -> tuple[int, int, int]:
    """Return (low, high, soft_max) for Summary prose before the closing quote."""
    target = summary_target(article_pages, body_words)
    return target.low, target.high, target.soft_max


def summary_prose(summary: str) -> str:
    """Summary text with the closing block quote removed.

    The 'As [Surname] concludes' line stays. Kyler's counts include that
    lead-in and exclude only the indented quotation.
    """
    lines = summary.replace("\r\n", "\n").split("\n")
    start, end = _closing_quote_span(lines)
    if start is None or end is None:
        return summary.strip()
    kept = lines[:start] + lines[end:]
    return "\n".join(kept).strip()


def closing_quote_text(summary: str) -> str:
    lines = summary.replace("\r\n", "\n").split("\n")
    start, end = _closing_quote_span(lines)
    if start is None or end is None:
        return ""
    parts: list[str] = []
    for line in lines[start:end]:
        if line.startswith("> "):
            parts.append(line[2:])
        elif line.startswith(">"):
            parts.append(line[1:])
        elif line.strip():
            parts.append(line.strip())
    return " ".join(parts).strip()


def _closing_quote_span(lines: list[str]) -> tuple[int | None, int | None]:
    last_quote = None
    for index, line in enumerate(lines):
        if line.startswith(">"):
            last_quote = index
    if last_quote is None:
        return None, None
    start = last_quote
    while start > 0 and (lines[start - 1].startswith(">") or not lines[start - 1].strip()):
        start -= 1
    end = last_quote + 1
    while end < len(lines) and (lines[end].startswith(">") or not lines[end].strip()):
        if lines[end].strip() and not lines[end].startswith(">"):
            break
        end += 1
    return start, end


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


def qa_answer_word_counts(qa_markdown: str) -> list[int]:
    """Word counts for each answer, locators excluded."""
    lines = qa_markdown.replace("\r\n", "\n").split("\n")
    chunks: list[list[str]] = []
    current: list[str] | None = None
    for line in lines:
        if _QA_QUESTION_RE.match(line.strip()) and "?" in line:
            if current is not None:
                chunks.append(current)
            current = []
            continue
        if current is not None:
            current.append(line)
    if current is not None:
        chunks.append(current)
    return [count_words("\n".join(chunk)) for chunk in chunks]


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


def extract_length_note(markdown: str) -> tuple[str, str | None]:
    """Pull a length explanation out of the draft so it never enters the post.

    The model is asked for one HTML comment. A 'Length note' heading or a
    line that starts with 'Length note:' is accepted and removed too.
    """
    reasons: list[str] = []

    def take_comment(match: re.Match[str]) -> str:
        reasons.append(_clean_reason(match.group(1)))
        return ""

    text = _LENGTH_COMMENT_RE.sub(take_comment, markdown)

    def take_section(match: re.Match[str]) -> str:
        body = re.sub(r"(?i)^#{1,3}[ \t]+length note[ \t]*\n", "", match.group(0))
        reasons.append(_clean_reason(body))
        return ""

    text = _LENGTH_SECTION_RE.sub(take_section, text)

    def take_line(match: re.Match[str]) -> str:
        reasons.append(_clean_reason(match.group(1)))
        return ""

    text = _LENGTH_LINE_RE.sub(take_line, text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    cleaned = f"{text}\n" if text else ""
    joined = " ".join(part for part in reasons if part)
    return cleaned, (joined or None)


def _clean_reason(text: str) -> str:
    flattened = re.sub(r"\s+", " ", text).strip(" -–—:.")
    if len(flattened) > 240:
        flattened = flattened[:237].rstrip() + "…"
    return flattened


def _band_status(words: int, low: int, high: int, soft_max: int) -> str:
    if words > soft_max:
        return "over max"
    if words > high:
        return "long"
    if words < low:
        return "short"
    return "on target"


def length_hint(
    article_pages: int,
    *,
    printed_start: int | None = None,
    printed_end: int | None = None,
    body_words: int | None = None,
) -> str:
    target = summary_target(article_pages, body_words)
    span = ""
    if printed_start is not None and printed_end is not None:
        span = f" (printed {printed_start}–{printed_end})"
    words = usable_body_words(article_pages, body_words)
    body_bit = f" About {words} body words were extracted." if words else ""
    return (
        f"This article is {article_pages} PDF pages{span}.{body_bit} "
        f"Follow this Summary band by default: {target.describe()}, "
        "counted before the closing block quote and not counting locator text. "
        "Short summaries of long articles are the exception. "
        "Go below the band only for a close reading of a single passage, a "
        "literary-structure or wordplay study, or an article that makes few "
        "distinct points (Squire 70_04 and 69_10, Bowen 68_01 and 67_12). "
        "Go above the band only for a list of many parallel points, at about "
        "100 words per point (Ahlstrom 70_01). "
        "If you leave the band, do not explain that choice inside the post. "
        "After the video script, add one HTML comment and nothing else: "
        '<!-- length-note: below the band because this is a literary-structure study of one chapter -->. '
        f"The closing block quote itself: {QUOTE_LOW}–{QUOTE_HIGH} words, soft max {QUOTE_SOFT}. "
        f"The Takeaway: one or two sentences, {TAKEAWAY_LOW}–{TAKEAWAY_HIGH} words, soft max {TAKEAWAY_SOFT}. "
        "The Q&A: exactly three questions. Each answer is 2–4 plain sentences, "
        f"{QA_ANSWER_LOW}–{QA_ANSWER_HIGH} words, soft max {QA_ANSWER_SOFT}. "
        "At most one short quoted phrase per bullet. Explain what each point shows. "
        "End the Summary with As [Surname] concludes (link to \"opening words\"; page N): "
        "and a verbatim block quote. "
        "Mention an appendix in one sentence if it matters; do not summarize it. "
        "Video script: about 10 rows (9–12). Row 1 is a conversational hook about a person or detail. "
        "Each narration is one to three spoken sentences. "
        'The last row ends with "and I\'ll see you next time." '
        "Do not write a Reflection. Output only the post, with no preamble."
    )


def summary_length_note(
    summary_words: int,
    article_pages: int,
    *,
    body_words: int | None = None,
    justification: str | None = None,
) -> str:
    target = summary_target(article_pages, body_words)
    status = _band_status(summary_words, target.low, target.high, target.soft_max)
    reason = ""
    if status != "on target" and justification:
        status = "heads-up"
        reason = f"; model: {justification}"
    elif status != "on target":
        reason = "; no reason given"
    elif justification:
        reason = f"; model: {justification}"
    return (
        f"summary {summary_words} words before the closing quote "
        f"({status}; {target.describe()}{reason})"
    )


def closing_quote_length_note(quote_words: int) -> str:
    status = _band_status(quote_words, QUOTE_LOW, QUOTE_HIGH, QUOTE_SOFT)
    return (
        f"closing quote {quote_words} words "
        f"({status}; target {QUOTE_LOW}–{QUOTE_HIGH}, soft max {QUOTE_SOFT})"
    )


def takeaway_length_note(takeaway_words: int) -> str:
    status = _band_status(takeaway_words, TAKEAWAY_LOW, TAKEAWAY_HIGH, TAKEAWAY_SOFT)
    return (
        f"takeaway {takeaway_words} words "
        f"({status}; target {TAKEAWAY_LOW}–{TAKEAWAY_HIGH}, soft max {TAKEAWAY_SOFT}, "
        "one or two sentences)"
    )


def qa_length_note(qa_markdown: str) -> str:
    questions = question_count(qa_markdown)
    counts = qa_answer_word_counts(qa_markdown)
    count = "3 questions" if questions == 3 else f"{questions} questions (expected 3)"
    if not counts:
        return (
            f"Q&A no answers parsed ({'short' if questions != 3 else 'short'}; {count}, "
            f"each answer {QA_ANSWER_LOW}–{QA_ANSWER_HIGH}, soft max {QA_ANSWER_SOFT})"
        )
    statuses = [
        _band_status(words, QA_ANSWER_LOW, QA_ANSWER_HIGH, QA_ANSWER_SOFT) for words in counts
    ]
    if any(status == "over max" for status in statuses):
        status = "over max"
    elif any(status == "long" for status in statuses) and any(status == "short" for status in statuses):
        status = "outside the band"
    elif any(status == "long" for status in statuses):
        status = "long"
    elif any(status == "short" for status in statuses):
        status = "short"
    else:
        status = "on target"
    listed = ", ".join(str(words) for words in counts)
    return (
        f"Q&A answers {listed} words ({status}; {count}, "
        f"each {QA_ANSWER_LOW}–{QA_ANSWER_HIGH}, soft max {QA_ANSWER_SOFT})"
    )


def video_length_note(rows: int) -> str:
    if 9 <= rows <= 12:
        status = "on target"
    elif rows < 9:
        status = "short"
    else:
        status = "long"
    return f"video {rows} rows ({status}; target about 10)"
