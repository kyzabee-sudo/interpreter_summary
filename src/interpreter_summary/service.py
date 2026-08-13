from __future__ import annotations

from dataclasses import dataclass

from interpreter_summary.config import Settings
from interpreter_summary.export import locator_count, parse_sections
from interpreter_summary.grok import GrokClient
from interpreter_summary.pdf_utils import pdf_page_count, validate_pdf
from interpreter_summary.prompts import build_user_prompt, default_system_prompt
from interpreter_summary.style import load_style_bytes, load_style_text


@dataclass
class SummaryResult:
    markdown: str
    title: str
    intro: str
    takeaway: str
    summary: str
    reflection: str
    page_count: int
    locator_count: int
    model: str


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
    page_count = pdf_page_count(pdf_bytes)
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
            user_prompt=build_user_prompt(style_text, extra_instructions),
        )
    finally:
        if file_id:
            await grok.delete_file(file_id)
        if owns_client:
            await grok.aclose()

    sections = parse_sections(markdown)
    return SummaryResult(
        markdown=markdown,
        title=sections["title"],
        intro=sections["intro"],
        takeaway=sections["takeaway"],
        summary=sections["summary"],
        reflection=sections["reflection"],
        page_count=page_count,
        locator_count=locator_count(markdown),
        model=settings.xai_model,
    )
