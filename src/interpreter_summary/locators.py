from __future__ import annotations

import re
from dataclasses import dataclass, field

from interpreter_summary.pdf_utils import PdfCorpus

# Optional **bold** around a bracketed label, as in bullet leads:
# **[Short label]** (link to "opening words"; page N)
LOCATOR_RE = re.compile(
    r"(?P<bracket>(?:\*\*)?\[(?P<label>[^\]]+)\](?:\*\*)?\s*)?"
    r'\(link to\s+[“"”](?P<phrase>[^“"”]+)[“"”];\s*page\s+(?P<page>\d+)\)',
    re.IGNORECASE,
)


@dataclass(frozen=True)
class LocatorEdit:
    phrase: str
    original_page: int
    final_page: int | None
    action: str  # kept | corrected | dropped
    # Journal pages where the full phrase occurs. Empty when it occurs nowhere.
    hit_pages: tuple[int, ...] = ()


@dataclass
class LocatorReport:
    markdown: str
    kept: int = 0
    corrected: int = 0
    dropped: int = 0
    printed_start: int | None = None
    printed_end: int | None = None
    used_printed_pages: bool = False
    edits: list[LocatorEdit] = field(default_factory=list)

    @property
    def locator_count(self) -> int:
        return self.kept + self.corrected

    def summary_line(self) -> str:
        page_bit = ""
        if self.printed_start is not None and self.printed_end is not None:
            page_bit = f"printed {self.printed_start}–{self.printed_end} · "
        return (
            f"{page_bit}{self.locator_count} locators "
            f"({self.corrected} corrected, {self.dropped} dropped)"
        )


def locator_count(markdown: str) -> int:
    return len(list(LOCATOR_RE.finditer(markdown)))


def choose_journal_page(claimed: int, hits: list[int]) -> int | None:
    """Keep a verifiable page; correct only when the phrase is unambiguous."""
    if not hits:
        return None
    if claimed in hits:
        return claimed
    if len(set(hits)) == 1:
        return hits[0]
    return None


def format_locator(label: str | None, phrase: str, page: int, *, bold: bool = False) -> str:
    body = f'(link to "{phrase}"; page {page})'
    if not label:
        return body
    token = f"[{label}]"
    if bold:
        token = f"**{token}**"
    return f"{token} {body}"


def verify_locators(markdown: str, corpus: PdfCorpus) -> LocatorReport:
    """Keep, correct, or drop locators by searching the PDF text."""
    report = LocatorReport(
        markdown=markdown,
        printed_start=corpus.journal_start,
        printed_end=corpus.journal_end,
        used_printed_pages=corpus.used_printed_pages,
    )
    pieces: list[str] = []
    last = 0
    for match in LOCATOR_RE.finditer(markdown):
        phrase = match.group("phrase")
        claimed = int(match.group("page"))
        label = match.group("label")
        bracket = match.group("bracket") or ""
        label_is_bold = "**" in bracket
        hits = corpus.pages_containing(phrase)
        exact_hits = tuple(corpus.phrase_pages(phrase))
        chosen = choose_journal_page(claimed, hits)
        start = match.start()
        if chosen is None:
            replacement = label or ""
            if not label and start > last and markdown[start - 1].isspace():
                start -= 1
            action = "dropped"
            report.dropped += 1
        elif chosen == claimed:
            replacement = match.group(0)
            action = "kept"
            report.kept += 1
        else:
            replacement = format_locator(label, phrase, chosen, bold=label_is_bold)
            action = "corrected"
            report.corrected += 1
        end = match.end()
        if action == "dropped":
            # A removed locator can leave "word  ." or "word . Next". Eat only
            # the spaces that touch this locator. "from . Robb" elsewhere is a
            # dropped initial and has to stay visible to the surface check.
            skipped = re.match(r"[ \t]+(?=[.,;:])", markdown[end:])
            if skipped:
                end += skipped.end()
        chunk = markdown[last:start]
        if action == "dropped" and not replacement and markdown[end : end + 1] in ".,;:":
            chunk = chunk.rstrip(" \t")
        pieces.append(chunk)
        pieces.append(replacement)
        last = end
        report.edits.append(
            LocatorEdit(
                phrase=phrase,
                original_page=claimed,
                final_page=chosen,
                action=action,
                hit_pages=exact_hits,
            )
        )
    pieces.append(markdown[last:])
    report.markdown = _tidy_dropped_spacing("".join(pieces))
    return report


def _tidy_dropped_spacing(text: str) -> str:
    # Collapse leftover "word ." / "word ," from a removed locator. Do not
    # rewrite "from . Robb Smith": space, period, then a name is a dropped
    # initial, and the surface check flags it instead of silently joining it.
    text = re.sub(r"[ \t]+\.(?![ \t]+[A-Z])", ".", text)
    text = re.sub(r"[ \t]+,", ",", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text
