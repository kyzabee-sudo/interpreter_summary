from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from interpreter_summary.pdf_utils import PdfCorpus, readable_text

ELLIPSIS_RE = re.compile(r"\s*(?:\.{3}|…)\s*")
ATTRIBUTION_RE = re.compile(
    r"(?i)\b(concludes?|writes?|argues?|notes?|states?|observes?|explains?|puts it)\b.*:\s*$"
)
FUZZY_KEEP = 0.98
FUZZY_REPAIR = 0.88
ANCHORED_REPAIR = 0.6


@dataclass(frozen=True)
class QuoteEdit:
    original: str
    final: str | None
    action: str  # kept | corrected | dropped


@dataclass
class QuoteReport:
    markdown: str
    kept: int = 0
    corrected: int = 0
    dropped: int = 0
    edits: list[QuoteEdit] = field(default_factory=list)

    @property
    def quote_count(self) -> int:
        return self.kept + self.corrected

    @property
    def examined(self) -> bool:
        return bool(self.kept or self.corrected or self.dropped)

    def summary_line(self) -> str:
        return (
            f"{self.quote_count} quotes "
            f"({self.corrected} corrected, {self.dropped} dropped)"
        )


@dataclass(frozen=True)
class _SegmentHit:
    start: int
    end: int
    ratio: float
    excerpt: str


def verify_quotes(markdown: str, corpus: PdfCorpus) -> QuoteReport:
    """Keep, repair, or drop Markdown block quotes against the PDF wording."""
    report = QuoteReport(markdown=markdown)
    lines = markdown.split("\n")
    blocks = _quote_block_ranges(lines)
    if not blocks:
        return report
    haystack = corpus.joined_body_readable()
    for start, end in reversed(blocks):
        original = _block_text(lines[start:end])
        resolved = _resolve_quote(original, haystack)
        report.edits.append(
            QuoteEdit(original=original, final=resolved.text, action=resolved.action)
        )
        if resolved.action == "kept":
            report.kept += 1
            continue
        if resolved.action == "corrected":
            lines[start:end] = [f"> {resolved.text}"]
            report.corrected += 1
            continue
        attr_index = _attribution_index(lines, start)
        del lines[start:end]
        if attr_index is not None:
            del lines[attr_index]
            if attr_index < len(lines) and not lines[attr_index].strip():
                if attr_index == 0 or not lines[attr_index - 1].strip():
                    del lines[attr_index]
        report.dropped += 1
    report.markdown = re.sub(r"\n{3,}", "\n\n", "\n".join(lines))
    return report


@dataclass(frozen=True)
class _ResolvedQuote:
    action: str
    text: str | None = None


def _resolve_quote(quote: str, haystack: str) -> _ResolvedQuote:
    segments = [part.strip() for part in ELLIPSIS_RE.split(quote) if part.strip()]
    if not segments:
        return _ResolvedQuote("dropped")
    cursor = 0
    excerpts: list[str] = []
    ratios: list[float] = []
    for segment in segments:
        hit = _find_segment(haystack, segment, cursor)
        if hit is None:
            return _ResolvedQuote("dropped")
        excerpts.append(hit.excerpt)
        ratios.append(hit.ratio)
        cursor = hit.end
    if min(ratios) >= FUZZY_KEEP:
        return _ResolvedQuote("kept", quote)
    repaired = " ... ".join(excerpts) if len(excerpts) > 1 else excerpts[0]
    return _ResolvedQuote("corrected", repaired)


def _find_segment(haystack: str, segment: str, start_at: int) -> _SegmentHit | None:
    needle = readable_text(segment)
    if len(needle) < 12:
        return None
    hay_cf = haystack.casefold()
    needle_cf = needle.casefold()
    exact = hay_cf.find(needle_cf, start_at)
    if exact >= 0:
        excerpt = haystack[exact : exact + len(needle)].strip()
        return _SegmentHit(exact, exact + len(needle), 1.0, excerpt)

    words = needle.split()
    if len(words) < 5:
        return None
    head_n = min(8, max(5, len(words) // 3 + 3))
    head = " ".join(words[:head_n])
    head_pos = hay_cf.find(head.casefold(), start_at)
    if head_pos < 0 and head_n > 5:
        head = " ".join(words[:5])
        head_pos = hay_cf.find(head.casefold(), start_at)
    if head_pos < 0:
        return None

    if len(words) >= 8:
        for tail_n in (8, 5, 4, 3):
            if len(words) < tail_n + 3:
                continue
            tail = " ".join(words[-tail_n:])
            if len(readable_text(tail)) < 16:
                continue
            tail_pos = hay_cf.find(tail.casefold(), head_pos + len(head))
            if tail_pos < 0:
                continue
            end = tail_pos + len(tail)
            excerpt = haystack[head_pos:end].strip()
            ratio = SequenceMatcher(None, needle_cf, excerpt.casefold()).ratio()
            if ratio >= ANCHORED_REPAIR:
                return _SegmentHit(head_pos, end, ratio, excerpt)

    window_end = min(len(haystack), head_pos + int(len(needle) * 1.25) + 40)
    window = haystack[head_pos:window_end]
    ratio = SequenceMatcher(None, needle_cf, window.casefold()).ratio()
    if ratio >= FUZZY_REPAIR:
        return _SegmentHit(head_pos, head_pos + len(window.strip()), ratio, window.strip())
    return None


def _quote_block_ranges(lines: list[str]) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    index = 0
    while index < len(lines):
        if _quote_body(lines[index]) is None:
            index += 1
            continue
        start = index
        while index < len(lines) and _quote_body(lines[index]) is not None:
            index += 1
        ranges.append((start, index))
    return ranges


def _quote_body(line: str) -> str | None:
    if line.startswith("> "):
        return line[2:]
    if line.startswith(">"):
        return line[1:]
    return None


def _block_text(lines: list[str]) -> str:
    parts = [_quote_body(line) or "" for line in lines]
    return readable_text(" ".join(parts))


def _attribution_index(lines: list[str], quote_start: int) -> int | None:
    index = quote_start - 1
    while index >= 0 and not lines[index].strip():
        index -= 1
    if index >= 0 and ATTRIBUTION_RE.search(lines[index].strip()):
        return index
    return None
