from __future__ import annotations

from dataclasses import dataclass

from interpreter_summary.checks import (
    Finding,
    inspect_draft,
    model_finding_resolved,
    needs_revision,
    render_check_report,
    strip_embedded_check_report,
    tidy_draft,
)
from interpreter_summary.config import Settings
from interpreter_summary.export import parse_sections, strip_preamble, strip_reflection_section
from interpreter_summary.grok import GrokClient, GrokError
from interpreter_summary.lay_academic import (
    extract_lay_script,
    lay_script_length_note,
    split_lay_academic,
)
from interpreter_summary.length import (
    closing_quote_length_note,
    closing_quote_text,
    count_words,
    extract_length_note,
    lay_academic_length_hint,
    length_hint,
    qa_length_note,
    summary_length_note,
    summary_prose,
    takeaway_length_note,
    video_length_note,
    video_row_count,
)
from interpreter_summary.locators import LocatorReport, verify_locators
from interpreter_summary.pdf_utils import PdfCorpus, extract_pdf_corpus, validate_pdf
from interpreter_summary.prompts import (
    LAY_ACADEMIC_SYSTEM_PROMPT,
    build_lay_academic_user_prompt,
    build_user_prompt,
    default_system_prompt,
)
from interpreter_summary.quotes import QuoteReport, verify_quotes
from interpreter_summary.review import (
    REVIEW_REASONING_EFFORT,
    REVIEW_SYSTEM_PROMPT,
    REVISION_SYSTEM_PROMPT,
    build_review_user_prompt,
    build_revision_user_prompt,
    looks_like_post,
    parse_model_findings,
)
from interpreter_summary.style import load_style_bytes, load_style_text


@dataclass
class SummaryResult:
    markdown: str
    title: str
    intro: str
    takeaway: str
    qa: str
    summary: str
    video_script: str
    page_count: int
    locator_count: int
    locators_corrected: int
    locators_dropped: int
    quotes_kept: int
    quotes_corrected: int
    quotes_dropped: int
    journal_page_start: int | None
    journal_page_end: int | None
    used_printed_pages: bool
    model: str
    locator_report: LocatorReport
    quote_report: QuoteReport
    summary_word_count: int
    summary_length_note: str
    closing_quote_word_count: int
    closing_quote_length_note: str
    takeaway_word_count: int
    takeaway_length_note: str
    qa_word_count: int
    qa_length_note: str
    video_row_count: int
    video_length_note: str
    check_report: str = ""
    model_review: str = ""
    revision: str = ""
    checks_fixed: int = 0
    checks_open: int = 0
    lay_markdown: str = ""
    lay_row_count: int = 0
    lay_length_note: str = ""

    def verify_summary_line(self) -> str:
        parts = [self.locator_report.summary_line()]
        if self.quote_report.examined:
            parts.append(self.quote_report.summary_line())
        parts.extend(
            [
                self.takeaway_length_note,
                self.summary_length_note,
                self.closing_quote_length_note,
                self.qa_length_note,
                self.video_length_note,
                f"check {self.checks_fixed} fixed, {self.checks_open} open",
            ]
        )
        if self.lay_length_note:
            parts.append(self.lay_length_note)
        return " · ".join(parts)


async def summarize_pdf(
    pdf_bytes: bytes,
    filename: str,
    settings: Settings,
    *,
    style_bytes: bytes | None = None,
    style_filename: str | None = None,
    extra_instructions: str | None = None,
    client: GrokClient | None = None,
    model_verify: bool = True,
) -> SummaryResult:
    validate_pdf(pdf_bytes, filename, settings.max_upload_bytes)
    corpus = extract_pdf_corpus(pdf_bytes)
    style_text = (
        load_style_bytes(style_bytes, style_filename or "style.docx")
        if style_bytes
        else load_style_text()
    )
    grok = client or GrokClient(settings)
    owns_client = client is None
    file_id = None
    try:
        file_id = await grok.upload_pdf(pdf_bytes, filename)
        # Stream so a long reasoning run is not cut off by a silent read timeout.
        # The PDF stays attached; xAI turns that into document search automatically.
        markdown = await grok.summarize_file(
            file_id,
            system_prompt=default_system_prompt(),
            user_prompt=build_user_prompt(
                style_text,
                extra_instructions,
                pagination_hint=corpus.pagination_hint(),
                length_hint_text=length_hint(
                    corpus.page_count,
                    printed_start=corpus.journal_start,
                    printed_end=corpus.journal_end,
                    body_words=corpus.body_words,
                ),
            ),
        )
        if file_id:
            await grok.delete_file(file_id)
            file_id = None
        return await _finish_draft(
            markdown,
            corpus,
            settings,
            grok,
            model_verify=model_verify,
        )
    finally:
        if file_id:
            await grok.delete_file(file_id)
        if owns_client:
            await grok.aclose()


def _prepare_draft(markdown: str, corpus: PdfCorpus):
    """Strip chatter, then repair locators and quotes and tidy the surface.

    A Lay Academic script appended to the post is removed here. It is returned
    separately so it cannot enter the main ``.AI.docx``.
    """
    markdown, length_justification = extract_length_note(markdown)
    markdown, embedded_lay = split_lay_academic(markdown)
    drafted = strip_embedded_check_report(strip_preamble(strip_reflection_section(markdown)))
    locator_report = verify_locators(drafted, corpus)
    quote_report = verify_quotes(locator_report.markdown, corpus)
    tidied, tidy_notes = tidy_draft(quote_report.markdown)
    return tidied, length_justification, locator_report, quote_report, tidy_notes, embedded_lay


async def _finish_draft(
    markdown: str,
    corpus: PdfCorpus,
    settings: Settings,
    grok: GrokClient,
    *,
    model_verify: bool,
) -> SummaryResult:
    # Pull the length explanation before preamble stripping, in case the model
    # parks the comment above the title. It must not remain in the post.
    cleaned, length_justification, locator_report, quote_report, tidy_notes, embedded_lay = _prepare_draft(
        markdown, corpus
    )
    article_text, article_truncated = corpus.marked_text()
    pagination = corpus.pagination_hint()
    audit = inspect_draft(
        cleaned,
        corpus,
        article_pages=corpus.page_count,
        body_words=corpus.body_words,
        justification=length_justification,
        locator_report=locator_report,
        quote_report=quote_report,
    )
    fixed_notes = [*tidy_notes, *audit.fixed_notes]
    open_findings = list(audit.open_findings)

    model_findings: list[Finding] = []
    if not model_verify:
        review_status = (
            "skipped (--no-verify). Deterministic checks ran offline and did not call the API."
        )
        revision_status = "skipped with the model review"
    else:
        review_status, model_findings = await _review_draft(
            grok,
            settings,
            pagination=pagination,
            article_text=article_text,
            article_truncated=article_truncated,
            draft=cleaned,
            open_findings=open_findings,
        )
        if needs_revision(open_findings, model_findings):
            prior_open = list(open_findings)
            revision_status, revised, revised_justification = await _revise_draft(
                grok,
                pagination=pagination,
                article_text=article_text,
                article_truncated=article_truncated,
                draft=cleaned,
                findings=[*open_findings, *model_findings],
            )
            if revised is not None:
                if revised_justification:
                    length_justification = revised_justification
                cleaned, _ignored, locator_report, quote_report, tidy_notes, revised_lay = _prepare_draft(
                    revised, corpus
                )
                if revised_lay:
                    embedded_lay = revised_lay
                audit = inspect_draft(
                    cleaned,
                    corpus,
                    article_pages=corpus.page_count,
                    body_words=corpus.body_words,
                    justification=length_justification,
                    locator_report=locator_report,
                    quote_report=quote_report,
                )
                fixed_notes.extend(tidy_notes)
                fixed_notes.extend(audit.fixed_notes)
                fixed_notes.append("One revision pass rewrote the draft. It was told not to invent claims.")
                for finding in model_findings:
                    if model_finding_resolved(finding, cleaned):
                        fixed_notes.append(_addressed_note(finding))
                still_model = [
                    finding
                    for finding in model_findings
                    if not model_finding_resolved(finding, cleaned)
                ]
                carried = [
                    finding
                    for finding in prior_open
                    if finding.code in {"locator-dropped", "quote-dropped", "locator-partial"}
                    and not (finding.evidence and finding.evidence in cleaned)
                ]
                open_findings = _dedupe_findings([*audit.open_findings, *still_model, *carried])
            else:
                open_findings = [*open_findings, *model_findings]
        else:
            revision_status = "not needed"
            open_findings = [*open_findings, *model_findings]

    lay_markdown, lay_note = await _draft_lay_script(
        grok,
        pagination=pagination,
        article_text=article_text,
        article_truncated=article_truncated,
        draft=cleaned,
        embedded_lay=embedded_lay,
    )
    visible = [finding for finding in open_findings if finding.severity != "info"]
    check_report = render_check_report(
        corpus=corpus,
        review_status=review_status,
        revision_status=revision_status,
        fixed_notes=_dedupe(fixed_notes),
        open_findings=open_findings,
        count_lines_text=audit.count_lines,
    )
    sections = parse_sections(cleaned)
    summary_words = count_words(summary_prose(sections["summary"]))
    quote_words = count_words(closing_quote_text(sections["summary"]))
    takeaway_words = count_words(sections["takeaway"])
    qa_words = count_words(sections["qa"])
    rows = video_row_count(sections["video_script"])
    return SummaryResult(
        markdown=cleaned,
        title=sections["title"],
        intro=sections["intro"],
        takeaway=sections["takeaway"],
        qa=sections["qa"],
        summary=sections["summary"],
        video_script=sections["video_script"],
        page_count=corpus.page_count,
        locator_count=locator_report.locator_count,
        locators_corrected=locator_report.corrected,
        locators_dropped=locator_report.dropped,
        quotes_kept=quote_report.kept,
        quotes_corrected=quote_report.corrected,
        quotes_dropped=quote_report.dropped,
        journal_page_start=corpus.journal_start,
        journal_page_end=corpus.journal_end,
        used_printed_pages=corpus.used_printed_pages,
        model=settings.xai_model,
        locator_report=locator_report,
        quote_report=quote_report,
        summary_word_count=summary_words,
        summary_length_note=summary_length_note(
            summary_words,
            corpus.page_count,
            body_words=corpus.body_words,
            justification=length_justification,
        ),
        closing_quote_word_count=quote_words,
        closing_quote_length_note=closing_quote_length_note(quote_words),
        takeaway_word_count=takeaway_words,
        takeaway_length_note=takeaway_length_note(takeaway_words),
        qa_word_count=qa_words,
        qa_length_note=qa_length_note(sections["qa"]),
        video_row_count=rows,
        video_length_note=video_length_note(rows),
        check_report=check_report,
        model_review=review_status,
        revision=revision_status,
        checks_fixed=len(_dedupe(fixed_notes)),
        checks_open=len(visible),
        lay_markdown=lay_markdown,
        lay_row_count=video_row_count(lay_markdown) if lay_markdown else 0,
        lay_length_note=lay_note,
    )


async def _draft_lay_script(
    grok: GrokClient,
    *,
    pagination: str,
    article_text: str,
    article_truncated: bool,
    draft: str,
    embedded_lay: str,
) -> tuple[str, str]:
    """One text-only call. The PDF is not attached. Failure keeps the summary."""
    try:
        raw = await grok.complete_text(
            system_prompt=LAY_ACADEMIC_SYSTEM_PROMPT,
            user_prompt=build_lay_academic_user_prompt(
                pagination=pagination,
                article_text=article_text,
                article_truncated=article_truncated,
                draft=draft,
                length_hint_text=lay_academic_length_hint(),
            ),
            reasoning_effort=REVIEW_REASONING_EFFORT,
        )
    except GrokError as exc:
        fallback = extract_lay_script(embedded_lay)
        if fallback:
            return fallback, lay_script_length_note(fallback) + "; recovered from the main draft"
        return "", f"lay script failed ({_short_error(exc)})"
    script = extract_lay_script(raw)
    if script:
        return script, lay_script_length_note(script)
    fallback = extract_lay_script(embedded_lay)
    if fallback:
        return fallback, lay_script_length_note(fallback) + "; recovered from the main draft"
    return "", "lay script omitted (the response was not a Lay Academic script)"


async def _review_draft(
    grok: GrokClient,
    settings: Settings,
    *,
    pagination: str,
    article_text: str,
    article_truncated: bool,
    draft: str,
    open_findings: list[Finding],
) -> tuple[str, list[Finding]]:
    try:
        raw = await grok.complete_text(
            system_prompt=REVIEW_SYSTEM_PROMPT,
            user_prompt=build_review_user_prompt(
                pagination=pagination,
                article_text=article_text,
                article_truncated=article_truncated,
                draft=draft,
                open_findings=open_findings,
            ),
            reasoning_effort=REVIEW_REASONING_EFFORT,
        )
    except GrokError as exc:
        return f"failed ({_short_error(exc)}). The draft was still saved.", []
    findings, error = parse_model_findings(raw)
    if error:
        return (
            f"ran on {settings.xai_model} with reasoning effort {REVIEW_REASONING_EFFORT}, "
            f"but {error[0].lower()}{error[1:]} The PDF was not attached. "
            "No model issues were applied.",
            [],
        )
    return (
        f"ran on {settings.xai_model} with reasoning effort {REVIEW_REASONING_EFFORT}. "
        "The article was sent as text. The PDF was not attached, so it was not searched again.",
        findings,
    )


async def _revise_draft(
    grok: GrokClient,
    *,
    pagination: str,
    article_text: str,
    article_truncated: bool,
    draft: str,
    findings: list[Finding],
) -> tuple[str, str | None, str | None]:
    try:
        raw = await grok.complete_text(
            system_prompt=REVISION_SYSTEM_PROMPT,
            user_prompt=build_revision_user_prompt(
                pagination=pagination,
                article_text=article_text,
                article_truncated=article_truncated,
                draft=draft,
                findings=findings,
            ),
            reasoning_effort=REVIEW_REASONING_EFFORT,
        )
    except GrokError as exc:
        return f"failed ({_short_error(exc)}). The previous draft was kept.", None, None
    if not looks_like_post(raw):
        return "rejected because the response was not a post. The previous draft was kept.", None, None
    revised, justification = extract_length_note(raw)
    return "applied once", revised, justification


def _addressed_note(finding: Finding) -> str:
    page = f" (journal page {finding.page})" if finding.page else ""
    evidence = f" Article: “{finding.evidence}”." if finding.evidence else ""
    return (
        f"Revision was asked to fix {finding.location}: {finding.problem} "
        f"The quoted draft wording is gone.{page}{evidence} "
        "This was not sent through a second model check."
    )


def _dedupe_findings(findings: list[Finding]) -> list[Finding]:
    seen: set[tuple[str, str, str]] = set()
    kept: list[Finding] = []
    for finding in findings:
        key = (finding.code, finding.location, finding.problem)
        if key in seen:
            continue
        seen.add(key)
        kept.append(finding)
    return kept


def _dedupe(notes: list[str]) -> list[str]:
    seen: set[str] = set()
    kept: list[str] = []
    for note in notes:
        if not note or note in seen:
            continue
        seen.add(note)
        kept.append(note)
    return kept


def _short_error(exc: GrokError) -> str:
    text = str(exc).replace("\n", " ").strip()
    if len(text) > 240:
        return text[:237].rstrip() + "…"
    return text
