"""Offline checks for a draft: locators, quotations, junk, and house counts.

Nothing in this module calls the network. Journal pages come from the PDF
corpus. A phrase matches across line-break hyphenation and curly quotes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from interpreter_summary.export import parse_sections
from interpreter_summary.length import (
    TAKEAWAY_HIGH,
    TAKEAWAY_LOW,
    TAKEAWAY_SOFT,
    count_words,
    summary_length_note,
    summary_prose,
    summary_target,
    takeaway_length_note,
    video_length_note,
    closing_quote_length_note,
    closing_quote_text,
    qa_length_note,
)
from interpreter_summary.locators import LOCATOR_RE, LocatorReport
from interpreter_summary.pdf_utils import PdfCorpus, normalize_for_match, readable_text
from interpreter_summary.quotes import ELLIPSIS_RE, QuoteReport

_RANGE_RE = re.compile(r"(?<![\w/])(\d+)\s*([-–—])\s*(\d+)(?!\d)")
_DOUBLED_WORD_RE = re.compile(r"\b([A-Za-z]{2,})\b(\s+\1\b)+", re.IGNORECASE)
_JUNK_RE = re.compile(
    r"X{3,}|\[\s*\]|_{3,}|\?{3,}|\[\s*(?:\.\.\.|…)\s*\]|\b(?:TODO|TBD|FIXME)\b",
    re.IGNORECASE,
)
_DROPPED_INITIAL_RE = re.compile(r"\b[A-Za-z]{2,}\s+\.\s+[A-Z][A-Za-z]+")
_ARTICLE_POSSESSIVE_RE = re.compile(r"\b[Tt]he\s+([A-Z][A-Za-z]+['’]s)\b")
_INLINE_QUOTE_RE = re.compile(r"[“\"]([^“\"”]+)[”\"]")
_HEADING_RE = re.compile(r"(?m)^#{1,3}[ \t]+(.+)$")
_SIGNOFF_RE = re.compile(r"and I['’]ll see you next time[.!]?\s*$", re.IGNORECASE)
_TERMINAL_RE = re.compile(r"""[.!?…:)"”’\"]$|\.\.\.$""")
_SEPARATOR_CELL_RE = re.compile(r":?-{3,}:?")
_CHECK_REPORT_RE = re.compile(r"(?im)^#\s+Check report\s*$")

_ALLOWED_POSSESSIVES = {
    "lord's",
    "god's",
    "church's",
    "bible's",
    "spirit's",
    "savior's",
    "saviour's",
    "father's",
    "son's",
    "lamb's",
    "king's",
    "queen's",
}

_NEAR_QUOTE = 0.86


@dataclass(frozen=True)
class Finding:
    code: str
    location: str
    problem: str
    evidence: str = ""
    page: int | None = None
    suggested_fix: str = ""
    source: str = "deterministic"
    severity: str = "error"  # error | warning | info


@dataclass
class DraftAudit:
    fixed_notes: list[str] = field(default_factory=list)
    open_findings: list[Finding] = field(default_factory=list)
    count_lines: list[str] = field(default_factory=list)


def tidy_draft(markdown: str) -> tuple[str, list[str]]:
    """Fix spacing, numeric-range dashes, and straight apostrophes in place.

    These edits do not change claims. Hyphenated compounds (``five-part``)
    are left alone; only a hyphen or em dash between numbers becomes an en dash.
    """
    notes: list[str] = []
    text = markdown.replace("\r\n", "\n")
    text, spaces = re.subn(r"[ \t]{2,}", " ", text)
    if spaces:
        notes.append(f"Collapsed {spaces} run{'s' if spaces != 1 else ''} of extra spaces.")

    edge = 0
    lines: list[str] = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped != line:
            edge += 1
        lines.append(stripped)
    if edge:
        notes.append(
            f"Removed leading or trailing spaces on {edge} line{'s' if edge != 1 else ''}."
        )
    text = "\n".join(lines)

    def dash_repl(match: re.Match[str]) -> str:
        return f"{match.group(1)}\u2013{match.group(3)}"

    ranges = list(_RANGE_RE.finditer(text))
    changed_ranges = [
        match
        for match in ranges
        if match.group(0) != f"{match.group(1)}\u2013{match.group(3)}"
    ]
    if changed_ranges:
        text = _RANGE_RE.sub(dash_repl, text)
        notes.append(
            f"Changed {len(changed_ranges)} numeric range"
            f"{'s' if len(changed_ranges) != 1 else ''} to an en dash."
        )

    text, apostrophes = re.subn(r"(?<=[A-Za-z])'(?=[A-Za-z])", "\u2019", text)
    if apostrophes:
        notes.append(
            f"Changed {apostrophes} straight apostrophe"
            f"{'s' if apostrophes != 1 else ''} to curly."
        )
    return text, notes


def strip_embedded_check_report(markdown: str) -> str:
    """Drop a Check report if a revision pasted one onto the post."""
    match = _CHECK_REPORT_RE.search(markdown)
    if not match:
        return markdown
    text = markdown[: match.start()].strip()
    return f"{text}\n" if text else ""


def inspect_draft(
    markdown: str,
    corpus: PdfCorpus,
    *,
    article_pages: int,
    body_words: int | None = None,
    justification: str | None = None,
    locator_report: LocatorReport | None = None,
    quote_report: QuoteReport | None = None,
) -> DraftAudit:
    """Run every offline check. ``markdown`` should already be tidied."""
    fixed: list[str] = []
    findings: list[Finding] = []
    if locator_report is not None:
        locator_fixed, locator_open = notes_from_locators(locator_report)
        fixed.extend(locator_fixed)
        findings.extend(locator_open)
    if quote_report is not None:
        quote_fixed, quote_open = notes_from_quotes(quote_report)
        fixed.extend(quote_fixed)
        findings.extend(quote_open)
    findings.extend(remaining_locator_findings(markdown, corpus))
    findings.extend(quotation_findings(markdown, corpus))
    findings.extend(surface_findings(markdown))
    findings.extend(
        length_findings(
            markdown,
            article_pages=article_pages,
            body_words=body_words,
            justification=justification,
        )
    )
    findings.extend(video_findings(markdown))
    return DraftAudit(
        fixed_notes=_unique(fixed),
        open_findings=_unique_findings(findings),
        count_lines=count_lines(
            markdown,
            article_pages=article_pages,
            body_words=body_words,
            justification=justification,
        ),
    )


def needs_revision(findings: list[Finding], model_findings: list[Finding]) -> bool:
    if model_findings:
        return True
    return any(finding.severity in {"error", "warning"} for finding in findings)


def notes_from_locators(report: LocatorReport) -> tuple[list[str], list[Finding]]:
    fixed: list[str] = []
    findings: list[Finding] = []
    for edit in report.edits:
        if edit.action == "corrected" and edit.final_page is not None:
            if edit.final_page in edit.hit_pages:
                fixed.append(
                    f"Locator “{edit.phrase}” claimed journal page {edit.original_page}; "
                    f"the phrase is on journal page {edit.final_page}. Updated the page."
                )
            else:
                findings.append(
                    Finding(
                        code="locator-partial",
                        location=f"Locator “{edit.phrase}”",
                        problem=(
                            f"Locator claimed journal page {edit.original_page} and was moved to "
                            f"{edit.final_page} on a partial match. The full phrase was not found there."
                        ),
                        evidence=edit.phrase,
                        page=edit.final_page,
                        suggested_fix=(
                            "Point the locator at the opening words of the passage that supports "
                            "the claim, on the journal page where those words appear."
                        ),
                    )
                )
        elif edit.action == "dropped":
            if len(edit.hit_pages) == 1:
                where = f"journal page {edit.hit_pages[0]}"
                page: int | None = edit.hit_pages[0]
            elif edit.hit_pages:
                where = "journal pages " + _page_list(edit.hit_pages)
                page = None
            else:
                where = ""
                page = None
            if where:
                problem = (
                    f"Link phrase “{edit.phrase}” does not appear on journal page "
                    f"{edit.original_page}. It appears on {where}. "
                    "The locator was removed because the page was not a single clear hit."
                )
            else:
                problem = (
                    f"Link phrase “{edit.phrase}” does not appear in the article "
                    f"(claimed journal page {edit.original_page}). The locator was removed."
                )
            findings.append(
                Finding(
                    code="locator-dropped",
                    location=f"Locator “{edit.phrase}”",
                    problem=problem,
                    evidence=edit.phrase,
                    page=page,
                    suggested_fix=(
                        "Restore a locator only with opening words that appear on that journal page. "
                        "Do not keep a phrase that points at a different passage."
                    ),
                )
            )
    return fixed, findings


def notes_from_quotes(report: QuoteReport) -> tuple[list[str], list[Finding]]:
    fixed: list[str] = []
    findings: list[Finding] = []
    for edit in report.edits:
        if edit.action == "corrected":
            snippet = _clip((edit.final or "").strip(), 180)
            fixed.append(f"Repaired a block quote to the article wording: “{snippet}”")
        elif edit.action == "dropped":
            findings.append(
                Finding(
                    code="quote-dropped",
                    location="Block quote",
                    problem=(
                        "A block quote could not be found in the article and was removed, "
                        "along with its attribution line when one was attached."
                    ),
                    evidence=_clip((edit.original or "").strip(), 400),
                    suggested_fix=(
                        "Restore a verbatim passage from the article, or leave the sentence out. "
                        "Do not paraphrase inside the quote."
                    ),
                )
            )
    return fixed, findings


def remaining_locator_findings(markdown: str, corpus: PdfCorpus) -> list[Finding]:
    """Flag locators whose full link phrase is not on the stated journal page."""
    findings: list[Finding] = []
    for match in LOCATOR_RE.finditer(markdown):
        phrase = match.group("phrase")
        claimed = int(match.group("page"))
        hits = corpus.phrase_pages(phrase)
        if claimed in hits:
            continue
        if len(hits) == 1:
            problem = (
                f"Link phrase “{phrase}” is on journal page {hits[0]}, not {claimed}."
            )
            page: int | None = hits[0]
            fix = f"Cite journal page {hits[0]}, or change the phrase if that passage is the wrong one."
        elif hits:
            problem = (
                f"Link phrase “{phrase}” is on journal pages {_page_list(hits)}, not {claimed}."
            )
            page = None
            fix = "Cite a page where that full phrase appears, and only if it supports the claim."
        else:
            problem = (
                f"Link phrase “{phrase}” does not appear in the article "
                f"(claimed journal page {claimed})."
            )
            page = None
            fix = "Replace the phrase with opening words that are actually on the journal page you cite."
        findings.append(
            Finding(
                code="locator-page",
                location=section_at(markdown, match.start()),
                problem=problem,
                evidence=phrase,
                page=page,
                suggested_fix=fix,
            )
        )
    return findings


def quotation_findings(markdown: str, corpus: PdfCorpus) -> list[Finding]:
    """Flag direct quotations that are not verbatim in the article."""
    findings: list[Finding] = []
    lines = markdown.split("\n")
    index = 0
    while index < len(lines):
        if not lines[index].startswith(">"):
            index += 1
            continue
        start = index
        parts: list[str] = []
        while index < len(lines) and lines[index].startswith(">"):
            body = lines[index][2:] if lines[index].startswith("> ") else lines[index][1:]
            parts.append(body.strip())
            index += 1
        offset = sum(len(line) + 1 for line in lines[:start])
        _check_quoted_text(" ".join(parts), section_at(markdown, offset), corpus, findings)
    locator_spans = [(match.start(), match.end()) for match in LOCATOR_RE.finditer(markdown)]
    for match in _INLINE_QUOTE_RE.finditer(markdown):
        if _covered(match.start(), match.end(), locator_spans):
            continue
        line_start = markdown.rfind("\n", 0, match.start()) + 1
        line_end = markdown.find("\n", match.start())
        if line_end < 0:
            line_end = len(markdown)
        if markdown[line_start:line_end].lstrip().startswith(">"):
            continue
        _check_quoted_text(
            match.group(1),
            section_at(markdown, match.start()),
            corpus,
            findings,
        )
    return findings


def surface_findings(markdown: str) -> list[Finding]:
    """Placeholders, spacing that survived tidy, dashes, and light grammar."""
    findings: list[Finding] = []
    for match in _JUNK_RE.finditer(markdown):
        findings.append(
            Finding(
                code="placeholder",
                location=section_at(markdown, match.start()),
                problem=f"Placeholder or empty gap “{_clip(match.group(0), 40)}” is still in the draft.",
                suggested_fix="Delete the placeholder or replace it with article wording. Do not leave XXXXX, empty brackets, or TBD.",
            )
        )
    for match in _DOUBLED_WORD_RE.finditer(markdown):
        findings.append(
            Finding(
                code="doubled-word",
                location=section_at(markdown, match.start()),
                problem=f"Doubled word “{match.group(0)}”.",
                suggested_fix="Delete the repeated word unless the article itself repeats it in a quotation.",
                severity="warning",
            )
        )
    for match in _DROPPED_INITIAL_RE.finditer(markdown):
        findings.append(
            Finding(
                code="dropped-initial",
                location=section_at(markdown, match.start()),
                problem=f"Space before a period in “{match.group(0).strip()}” looks like a dropped initial.",
                suggested_fix="Restore the missing initial or delete the stray period.",
            )
        )
    for match in _ARTICLE_POSSESSIVE_RE.finditer(markdown):
        token = match.group(1)
        if not _bad_article_possessive(token):
            continue
        findings.append(
            Finding(
                code="article-possessive",
                location=section_at(markdown, match.start()),
                problem=f"“the {token}” puts an article in front of a possessive name.",
                suggested_fix=f"Drop the article or restore the missing noun (“{token}”, not “the {token}”).",
                severity="warning",
            )
        )
    ranges = list(_RANGE_RE.finditer(markdown))
    hyphen_ranges = [match for match in ranges if match.group(2) != "\u2013"]
    dash_kinds = {match.group(2) for match in ranges}
    if hyphen_ranges:
        shown = ", ".join(match.group(0) for match in hyphen_ranges[:4])
        mixed = ""
        if len(dash_kinds) > 1:
            mixed = " The draft mixes hyphens and en dashes in numeric ranges."
        findings.append(
            Finding(
                code="dash-range",
                location=section_at(markdown, hyphen_ranges[0].start()),
                problem=f"Numeric range uses a hyphen or em dash ({shown}).{mixed}",
                suggested_fix="Use an en dash in every numeric and verse range, with no spaces.",
                severity="warning",
            )
        )
    if _has_straight_apostrophe(markdown):
        findings.append(
            Finding(
                code="apostrophe",
                location="Draft",
                problem="A contraction or possessive still uses a straight apostrophe.",
                suggested_fix="Use a curly apostrophe in I’ll, Nephi’s, and the same kinds of words.",
                severity="warning",
            )
        )
    if _unbalanced(markdown):
        findings.append(
            Finding(
                code="unbalanced",
                location="Draft",
                problem="Quotation marks or parentheses are unbalanced.",
                suggested_fix="Close the open quote or parenthesis, or delete the stray mark.",
            )
        )
    findings.extend(_terminal_findings(markdown))
    return findings


def length_findings(
    markdown: str,
    *,
    article_pages: int,
    body_words: int | None = None,
    justification: str | None = None,
) -> list[Finding]:
    sections = parse_sections(markdown)
    findings: list[Finding] = []
    takeaway_words = count_words(sections["takeaway"])
    if takeaway_words < TAKEAWAY_LOW or takeaway_words > TAKEAWAY_HIGH:
        severity = "error" if takeaway_words > TAKEAWAY_SOFT else "warning"
        findings.append(
            Finding(
                code="takeaway-length",
                location="The Takeaway",
                problem=(
                    f"Takeaway is {takeaway_words} words; the target is "
                    f"{TAKEAWAY_LOW}–{TAKEAWAY_HIGH} (soft max {TAKEAWAY_SOFT})."
                ),
                suggested_fix="Rewrite in one or two sentences inside the band. Do not add a new claim to fill space.",
                severity=severity,
            )
        )
    summary_words = count_words(summary_prose(sections["summary"]))
    target = summary_target(article_pages, body_words)
    if summary_words < target.low or summary_words > target.high:
        if justification and summary_words <= target.soft_max:
            severity = "info"
            fix = "A length note explains the departure. Leave it unless the note is wrong."
        elif summary_words > target.soft_max:
            severity = "error"
            fix = "Cut repetition. Do not invent points to reshape the count."
        else:
            severity = "warning"
            fix = (
                "If a real point from the article is missing, restore it. "
                "Do not add claims that are not in the article in order to hit the band. "
                "If the article is a close reading, keep the short summary and add a length-note."
            )
        findings.append(
            Finding(
                code="summary-length",
                location="The Summary",
                problem=(
                    f"Summary is {summary_words} words before the closing quote, "
                    f"not counting locator parentheticals "
                    f"(target {target.low}–{target.high}, soft max {target.soft_max}; "
                    f"{target.describe()})."
                ),
                suggested_fix=fix,
                severity=severity,
            )
        )
    return findings


def video_findings(markdown: str) -> list[Finding]:
    sections = parse_sections(markdown)
    rows = _video_rows(sections["video_script"])
    if rows is None:
        return [
            Finding(
                code="script-table",
                location="Video Script",
                problem="Video script is missing a 10-row table with columns #, Text, and Image.",
                suggested_fix="Add the table. The last Text cell must end with “and I'll see you next time.”",
            )
        ]
    findings: list[Finding] = []
    if not (9 <= len(rows) <= 12):
        findings.append(
            Finding(
                code="script-rows",
                location="Video Script",
                problem=f"Video script has {len(rows)} data rows; the target is 10 (acceptable 9–12).",
                suggested_fix="Use about 10 complete rows. Do not repeat a point to fill a row.",
            )
        )
    for index, row in enumerate(rows, start=1):
        if not row["text"] or not row["image"] or not row["number"]:
            findings.append(
                Finding(
                    code="script-cells",
                    location=f"Video Script row {index}",
                    problem="A video-script row is missing a number, narration, or image cue.",
                    suggested_fix="Fill #, Text, and Image. Image cues stay short.",
                )
            )
        elif not _TERMINAL_RE.search(row["text"]):
            findings.append(
                Finding(
                    code="terminal-punct",
                    location=f"Video Script row {index}",
                    problem="A narration cell is missing terminal punctuation.",
                    suggested_fix="End the spoken sentence with a period.",
                    severity="warning",
                )
            )
    if rows and not _SIGNOFF_RE.search(rows[-1]["text"]):
        findings.append(
            Finding(
                code="script-signoff",
                location="Video Script",
                problem="The last narration does not end with “and I'll see you next time.”",
                suggested_fix="End the last Text cell with that sign-off. A curly apostrophe in I'll is fine.",
            )
        )
    return findings


def count_lines(
    markdown: str,
    *,
    article_pages: int,
    body_words: int | None = None,
    justification: str | None = None,
) -> list[str]:
    sections = parse_sections(markdown)
    summary = summary_length_note(
        count_words(summary_prose(sections["summary"])),
        article_pages,
        body_words=body_words,
        justification=justification,
    )
    summary += (
        " Counted before the closing quote, not counting locator parentheticals "
        "(link to …; page N) or the bracketed labels in front of them."
    )
    rows = _video_rows(sections["video_script"])
    video = video_length_note(len(rows) if rows is not None else 0)
    signoff = " Sign-off present." if rows and _SIGNOFF_RE.search(rows[-1]["text"]) else " Sign-off missing."
    return [
        takeaway_length_note(count_words(sections["takeaway"])),
        summary,
        closing_quote_length_note(count_words(_closing_quote(sections["summary"]))),
        qa_length_note(sections["qa"]),
        video + signoff,
    ]


def pagination_line(corpus: PdfCorpus) -> str:
    if not corpus.pages or not corpus.used_printed_pages:
        return (
            "No printed journal pagination was detected. "
            "Locator pages were not guessed from the PDF viewer index."
        )
    offset = corpus.journal_offset()
    start = corpus.journal_start
    end = corpus.journal_end
    if offset is None:
        return f"Printed journal pages {start}–{end}."
    return (
        f"Printed journal pages {start}–{end}. "
        f"Offset derived from the PDF: journal page = PDF viewer page + {offset} "
        f"(PDF page 1 = journal page {start}). Locators use journal pages."
    )


def render_check_report(
    *,
    corpus: PdfCorpus,
    review_status: str,
    revision_status: str,
    fixed_notes: list[str],
    open_findings: list[Finding],
    count_lines_text: list[str],
) -> str:
    """A short report for Kyler. This text is not part of the post."""
    lines = [
        "# Check report",
        "",
        pagination_line(corpus),
        "",
        f"Model review: {review_status}",
        f"Revision: {revision_status}",
        "",
        "## Fixed",
    ]
    if fixed_notes:
        lines.extend(f"- {note}" for note in fixed_notes)
    else:
        lines.append("- Nothing was changed by the checker.")
    lines.extend(["", "## Still needs an eye"])
    visible = [finding for finding in open_findings if finding.severity != "info"]
    if visible:
        for finding in visible:
            lines.append(f"- {_format_finding(finding)}")
    else:
        lines.append("- Nothing unresolved.")
    lines.extend(["", "## Counts"])
    lines.extend(f"- {line}" for line in count_lines_text)
    lines.append("")
    return "\n".join(lines)


def model_finding_resolved(finding: Finding, draft: str) -> bool:
    """True when every draft snippet quoted in the finding is gone.

    Findings with no quoted draft snippet stay open. The model is not called
    a second time to confirm them.
    """
    bits = re.findall(r"[“\"]([^“\"”]{6,})[”\"]", f"{finding.location}\n{finding.problem}")
    if not bits:
        return False
    hay = normalize_for_match(draft)
    return all(normalize_for_match(bit) not in hay for bit in bits)


def section_at(markdown: str, index: int) -> str:
    headings = list(_HEADING_RE.finditer(markdown[:index]))
    if not headings:
        return "Draft"
    return headings[-1].group(1).strip()


def _check_quoted_text(
    quote: str,
    location: str,
    corpus: PdfCorpus,
    findings: list[Finding],
) -> None:
    segments = [part.strip() for part in ELLIPSIS_RE.split(quote) if part.strip()]
    if not segments:
        return
    for segment in segments:
        words = normalize_for_match(segment).split()
        if len(words) < 4:
            continue
        if corpus.phrase_pages(segment):
            continue
        near = _near_excerpt(corpus, segment)
        if near is not None:
            page, excerpt, _ratio = near
            findings.append(
                Finding(
                    code="quote-altered",
                    location=location,
                    problem=f"Quoted “{_clip(segment, 160)}” does not match the article.",
                    evidence=_clip(excerpt, 320),
                    page=page,
                    suggested_fix=(
                        "Replace the quotation with the article’s words, including the verb ending, "
                        "and keep the attribution on the model or scholar the sentence is about."
                    ),
                )
            )
            continue
        findings.append(
            Finding(
                code="quote-missing",
                location=location,
                problem=f"Quoted “{_clip(segment, 160)}” does not appear verbatim in the article.",
                suggested_fix=(
                    "Copy the passage verbatim, or remove the quotation marks if these are your own words."
                ),
                severity="error" if len(words) >= 6 else "warning",
            )
        )


def _near_excerpt(corpus: PdfCorpus, quote: str) -> tuple[int, str, float] | None:
    needle = normalize_for_match(quote)
    needle_words = needle.split()
    if len(needle_words) < 4:
        return None
    best: tuple[int, str, float] | None = None
    for page in corpus.pages:
        readable = readable_text(page.text)
        sentences = [part for part in re.split(r"(?<=[.!?])\s+", readable) if part.strip()]
        for sentence in sentences:
            norm = normalize_for_match(sentence)
            if not _shares_words(norm, needle_words):
                continue
            if needle in norm:
                return page.journal_page, sentence.strip(), 1.0
            ratio = _window_ratio(norm, needle)
            sentence_ratio = SequenceMatcher(None, needle, norm).ratio()
            ratio = max(ratio, sentence_ratio)
            if best is None or ratio > best[2]:
                best = (page.journal_page, sentence.strip(), ratio)
    if best is not None and best[2] >= _NEAR_QUOTE:
        return best
    return None


_QUOTE_STOPWORDS = {
    "the",
    "and",
    "that",
    "this",
    "with",
    "from",
    "into",
    "for",
    "are",
    "was",
    "were",
    "his",
    "her",
    "its",
    "not",
}


def _window_ratio(hay: str, needle: str) -> float:
    """Best word-window match, anchored on a content word so long pages stay cheap."""
    hay_words = hay.split()
    needle_words = needle.split()
    width = len(needle_words)
    if width < 4 or len(hay_words) < 4:
        return 0.0
    anchors = [word for word in needle_words if len(word) >= 5 and word not in _QUOTE_STOPWORDS]
    if not anchors:
        anchors = needle_words
    positions = [
        index
        for index, word in enumerate(hay_words)
        if any(_word_close(word, anchor) for anchor in anchors[:3])
    ]
    if not positions:
        return 0.0
    best = 0.0
    spans = [width, width + 1]
    if width > 4:
        spans.append(width - 1)
    for index in positions:
        for span in spans:
            if span < 4:
                continue
            last_start = min(index, len(hay_words) - span)
            first_start = max(0, index - span + 1)
            for start in range(first_start, last_start + 1):
                window = " ".join(hay_words[start : start + span])
                ratio = SequenceMatcher(None, needle, window).ratio()
                if ratio > best:
                    best = ratio
                    if best >= 0.98:
                        return best
    return best


def _shares_words(hay: str, needle_words: list[str]) -> bool:
    hay_words = hay.split()
    content = [word for word in needle_words if len(word) >= 4 and word not in _QUOTE_STOPWORDS]
    if not content:
        content = needle_words
    hits = sum(1 for word in content if any(_word_close(word, other) for other in hay_words))
    return hits >= min(2, len(content))


def _word_close(left: str, right: str) -> bool:
    if left == right:
        return True
    if len(left) >= 5 and len(right) >= 5 and (left.startswith(right) or right.startswith(left)):
        return True
    return len(left) >= 5 and len(right) >= 5 and left[:5] == right[:5]


def _terminal_findings(markdown: str) -> list[Finding]:
    sections = parse_sections(markdown)
    findings: list[Finding] = []
    for name, key in (
        ("The Takeaway", "takeaway"),
        ("The Q&A", "qa"),
        ("The Summary", "summary"),
    ):
        for line in sections[key].split("\n"):
            if not _needs_terminal(line):
                continue
            findings.append(
                Finding(
                    code="terminal-punct",
                    location=name,
                    problem=f"Missing terminal punctuation: “{_clip(line.strip(), 120)}”",
                    suggested_fix="End the sentence with a period.",
                    severity="warning",
                )
            )
    return findings


def _needs_terminal(line: str) -> bool:
    stripped = line.strip()
    if not stripped or stripped.startswith(("#", "|", ">")):
        return False
    if re.fullmatch(r"(-{3,}|\*{3,})", stripped):
        return False
    if _SEPARATOR_CELL_RE.fullmatch(stripped):
        return False
    body = re.sub(r"^(\*|-)\s+", "", stripped)
    body = body.replace("**", "").strip()
    if not body:
        return False
    return _TERMINAL_RE.search(body) is None


def _video_rows(video_markdown: str) -> list[dict[str, str]] | None:
    raw_rows: list[list[str]] = []
    for raw in video_markdown.replace("\r\n", "\n").split("\n"):
        line = raw.strip()
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if cells and all(_SEPARATOR_CELL_RE.fullmatch(cell.replace(" ", "")) for cell in cells):
            continue
        raw_rows.append(cells)
    if len(raw_rows) < 2:
        return None
    header = [cell.casefold() for cell in raw_rows[0]]
    if header[:3] != ["#", "text", "image"]:
        return None
    rows: list[dict[str, str]] = []
    for cells in raw_rows[1:]:
        padded = cells + ["", "", ""]
        rows.append({"number": padded[0], "text": padded[1], "image": padded[2]})
    return rows


def _closing_quote(summary: str) -> str:
    return closing_quote_text(summary)


def _bad_article_possessive(token: str) -> bool:
    stem = token.replace("\u2019", "'").casefold()
    if stem in _ALLOWED_POSSESSIVES:
        return False
    name = stem[:-2] if stem.endswith("'s") else stem
    if name.endswith("ite") or name.endswith("ites"):
        return False
    return True


def _has_straight_apostrophe(markdown: str) -> bool:
    return re.search(r"(?<=[A-Za-z])'(?=[A-Za-z])", markdown) is not None


def _unbalanced(markdown: str) -> bool:
    straight = markdown.count('"')
    if straight % 2:
        return True
    if markdown.count("\u201c") != markdown.count("\u201d"):
        return True
    return markdown.count("(") != markdown.count(")")


def _covered(start: int, end: int, spans: list[tuple[int, int]]) -> bool:
    return any(start >= begin and end <= stop for begin, stop in spans)


def _page_list(pages: tuple[int, ...] | list[int]) -> str:
    return ", ".join(str(page) for page in pages)


def _clip(text: str, limit: int) -> str:
    flattened = re.sub(r"\s+", " ", text).strip()
    if len(flattened) <= limit:
        return flattened
    return flattened[: limit - 1].rstrip() + "…"


def _format_finding(finding: Finding) -> str:
    page = f" (journal page {finding.page})" if finding.page else ""
    source = "Model" if finding.source == "model" else "Check"
    lines = [f"**{finding.location}**{page} — {source}: {finding.problem}"]
    if finding.evidence:
        lines.append(f"Article: “{finding.evidence}”")
    if finding.suggested_fix:
        lines.append(f"Suggested fix: {finding.suggested_fix}")
    return " ".join(lines)


def _unique(notes: list[str]) -> list[str]:
    seen: set[str] = set()
    kept: list[str] = []
    for note in notes:
        if note in seen:
            continue
        seen.add(note)
        kept.append(note)
    return kept


def _unique_findings(findings: list[Finding]) -> list[Finding]:
    seen: set[tuple[str, str, str]] = set()
    kept: list[Finding] = []
    for finding in findings:
        key = (finding.code, finding.location, finding.problem)
        if key in seen:
            continue
        seen.add(key)
        kept.append(finding)
    return kept
