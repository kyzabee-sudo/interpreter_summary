from __future__ import annotations

import re

# Takeaway and Reflection stay almost constant. The Summary grows with article
# length, then caps. Derived from published Interpreting Interpreter posts vs
# journal page counts (Balmer 8pp → ~250 summary words; Hudson draft 26pp → ~520;
# Thompson 56pp → ~1030; Spencer 82pp with appendix → ~690).


def summary_word_target(article_pages: int) -> tuple[int, int, int]:
    """Return (low, high, hard_max) word counts for The Summary section."""
    pages = max(1, article_pages)
    if pages <= 12:
        return 250, 400, 450
    if pages <= 24:
        return 400, 550, 600
    if pages <= 40:
        return 500, 650, 700
    return 600, 800, 850


def count_words(text: str) -> int:
    cleaned = re.sub(r"\(link to [^)]+\)", "", text)
    cleaned = re.sub(r"\[[^\]]+\]\s*", "", cleaned)
    return len(re.findall(r"[A-Za-z0-9']+", cleaned))


def length_hint(article_pages: int, *, printed_start: int | None = None, printed_end: int | None = None) -> str:
    low, high, hard_max = summary_word_target(article_pages)
    span = ""
    if printed_start is not None and printed_end is not None:
        span = f" (printed {printed_start}–{printed_end})"
    return (
        f"This article is {article_pages} PDF pages{span}. "
        f"The Takeaway: 40–70 words (one or two sentences). "
        f"The Summary: about {low}–{high} words, never more than {hard_max}. "
        "Cover the argument in order; do not expand just because the article is long. "
        "Mention an appendix in one sentence if it matters; do not summarize it. "
        "The Reflection: 100–200 words (one to three short paragraphs). "
        "Do not grow the Reflection with page count."
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
