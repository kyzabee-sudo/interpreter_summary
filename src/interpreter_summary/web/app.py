from __future__ import annotations

from pathlib import Path

import markdown as md
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from interpreter_summary import __version__
from interpreter_summary.config import get_settings
from interpreter_summary.export import markdown_to_docx
from interpreter_summary.grok import GrokError
from interpreter_summary.pdf_utils import PdfError
from interpreter_summary.service import summarize_pdf

WEB_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))

app = FastAPI(title="Interpreting Interpreter Summarizer", version=__version__)
app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    settings = get_settings()
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "has_api_key": bool(settings.xai_api_key),
            "model": settings.xai_model,
            "max_upload_mb": settings.max_upload_mb,
            "version": __version__,
        },
    )


@app.get("/health")
async def health() -> dict[str, str | bool]:
    settings = get_settings()
    return {
        "status": "ok",
        "model": settings.xai_model,
        "api_key_configured": bool(settings.xai_api_key),
    }


@app.post("/api/summarize")
async def api_summarize(
    pdf: UploadFile = File(...),
    style: UploadFile | None = File(None),
    notes: str = Form(default=""),
) -> dict:
    settings = get_settings()
    pdf_bytes = await pdf.read()
    style_bytes = await style.read() if style and style.filename else None
    style_filename = style.filename if style and style.filename else None
    try:
        result = await summarize_pdf(
            pdf_bytes,
            pdf.filename or "article.pdf",
            settings,
            style_bytes=style_bytes or None,
            style_filename=style_filename,
            extra_instructions=notes or None,
        )
    except PdfError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except GrokError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    html = md.markdown(result.markdown, extensions=["extra", "sane_lists", "nl2br"])
    return {
        "title": result.title,
        "markdown": result.markdown,
        "html": html,
        "intro": result.intro,
        "takeaway": result.takeaway,
        "qa": result.qa,
        "summary": result.summary,
        "video_script": result.video_script,
        "page_count": result.page_count,
        "locator_count": result.locator_count,
        "locators_corrected": result.locators_corrected,
        "locators_dropped": result.locators_dropped,
        "quotes_kept": result.quotes_kept,
        "quotes_corrected": result.quotes_corrected,
        "quotes_dropped": result.quotes_dropped,
        "journal_page_start": result.journal_page_start,
        "journal_page_end": result.journal_page_end,
        "used_printed_pages": result.used_printed_pages,
        "locator_summary": result.verify_summary_line(),
        "summary_word_count": result.summary_word_count,
        "summary_length_note": result.summary_length_note,
        "closing_quote_word_count": result.closing_quote_word_count,
        "closing_quote_length_note": result.closing_quote_length_note,
        "takeaway_word_count": result.takeaway_word_count,
        "takeaway_length_note": result.takeaway_length_note,
        "qa_word_count": result.qa_word_count,
        "qa_length_note": result.qa_length_note,
        "video_row_count": result.video_row_count,
        "video_length_note": result.video_length_note,
        "model": result.model,
    }


@app.post("/api/export/docx")
async def api_export_docx(payload: dict) -> Response:
    markdown_text = (payload or {}).get("markdown")
    if not markdown_text:
        raise HTTPException(status_code=400, detail="Missing markdown.")
    data = markdown_to_docx(markdown_text)
    filename = "interpreting-interpreter-summary.docx"
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
