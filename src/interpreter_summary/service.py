from __future__ import annotations

from dataclasses import dataclass

from interpreter_summary.config import Settings
from interpreter_summary.export import parse_sections, strip_reflection_section
from interpreter_summary.grok import GrokClient
from interpreter_summary.length import (
    count_words,
    length_hint,
    qa_length_note,
    question_count,
    summary_length_note,
    video_length_note,
    video_row_count,
)
from interpreter_summary.locators import LocatorReport, verify_locators
from interpreter_summary.pdf_utils import extract_pdf_corpus, validate_pdf
from interpreter_summary.prompts import build_user_prompt, default_system_prompt
from interpreter_summary.quotes import QuoteReport, verify_quotes
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
    qa_word_count: int
    qa_length_note: str
    video_row_count: int
    video_length_note: str

    def verify_summary_line(self) -> str:
        parts = [self.locator_report.summary_line()]
        if self.quote_report.examined:
            parts.append(self.quote_report.summary_line())
        parts.extend([self.summary_length_note, self.qa_length_note, self.video_length_note])
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
                ),
            ),
        )
    finally:
        if file_id:
            await grok.delete_file(file_id)
        if owns_client:
            await grok.aclose()

    drafted = strip_reflection_section(markdown)
    locator_report = verify_locators(drafted, corpus)
    quote_report = verify_quotes(locator_report.markdown, corpus)
    cleaned = quote_report.markdown
    sections = parse_sections(cleaned)
    summary_words = count_words(sections["summary"])
    qa_words = count_words(sections["qa"])
    questions = question_count(sections["qa"])
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
        summary_length_note=summary_length_note(summary_words, corpus.page_count),
        qa_word_count=qa_words,
        qa_length_note=qa_length_note(qa_words, questions),
        video_row_count=rows,
        video_length_note=video_length_note(rows),
    )
