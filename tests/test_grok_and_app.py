import httpx
import pytest
from fastapi.testclient import TestClient

from interpreter_summary.config import Settings
from interpreter_summary.export import markdown_to_docx
from interpreter_summary.grok import GrokClient, extract_output_text
from interpreter_summary.samples import write_sample_pdf
from interpreter_summary.service import summarize_pdf
from interpreter_summary.web.app import app


WRONG_PAGE_MARKDOWN = """# Interpreting Interpreter: Tokens, Not Tonnage

This post is a summary of the article "Copper, Covenants, and the Case of the Missing Ingots" by A. Sample Scholar in Volume 99 of Interpreter: A Journal of Latter-day Saint Faith and Scholarship.

## The Takeaway

Scholar argues that the copper is a covenant token.

## The Summary

The fragment lists ingots (link to "The warehouse fragment"; page 99).

## The Reflection

I like the caution.
"""


SAMPLE_MARKDOWN = """# Interpreting Interpreter: Tokens, Not Tonnage

This post is a summary of the article "Copper, Covenants, and the Case of the Missing Ingots" by A. Sample Scholar in Volume 99 of Interpreter: A Journal of Latter-day Saint Faith and Scholarship.

## The Takeaway

Scholar argues that the copper is a covenant token.

## The Summary

The fragment lists ingots (link to "The warehouse fragment"; page 1).

## The Reflection

I like the caution.
"""


def _mock_handler(request: httpx.Request) -> httpx.Response:
    if request.method == "POST" and request.url.path == "/v1/files":
        return httpx.Response(200, json={"id": "file-123", "filename": "article.pdf"})
    if request.method == "POST" and request.url.path == "/v1/responses":
        return httpx.Response(
            200,
            json={
                "output": [
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": SAMPLE_MARKDOWN}],
                    }
                ]
            },
        )
    if request.method == "DELETE" and request.url.path.startswith("/v1/files/"):
        return httpx.Response(200, json={"deleted": True})
    return httpx.Response(404, json={"error": "unhandled"})


@pytest.mark.asyncio
async def test_summarize_pdf_with_mocked_grok(tmp_path):
    pdf_path = write_sample_pdf(tmp_path / "article.pdf")
    settings = Settings(xai_api_key="test-key", xai_model="grok-4.6")
    transport = httpx.MockTransport(_mock_handler)
    async with httpx.AsyncClient(transport=transport, base_url="https://api.x.ai") as raw:
        client = GrokClient(settings, client=raw)
        result = await summarize_pdf(
            pdf_path.read_bytes(),
            "article.pdf",
            settings,
            client=client,
        )
    assert result.title == "Interpreting Interpreter: Tokens, Not Tonnage"
    assert result.locator_count == 1
    assert result.locators_corrected == 0
    assert result.locators_dropped == 0
    assert result.quotes_kept == 0
    assert result.quotes_corrected == 0
    assert result.quotes_dropped == 0
    assert result.page_count == 3
    assert result.journal_page_start == 1
    assert result.summary_word_count > 0
    assert "target" in result.summary_length_note
    assert "covenant token" in result.takeaway


def _mock_handler_wrong_page(request: httpx.Request) -> httpx.Response:
    if request.method == "POST" and request.url.path == "/v1/files":
        return httpx.Response(200, json={"id": "file-123", "filename": "article.pdf"})
    if request.method == "POST" and request.url.path == "/v1/responses":
        return httpx.Response(
            200,
            json={"output_text": WRONG_PAGE_MARKDOWN},
        )
    if request.method == "DELETE" and request.url.path.startswith("/v1/files/"):
        return httpx.Response(200, json={"deleted": True})
    return httpx.Response(404, json={"error": "unhandled"})


@pytest.mark.asyncio
async def test_summarize_pdf_corrects_wrong_locator_pages(tmp_path):
    pdf_path = write_sample_pdf(tmp_path / "article.pdf")
    settings = Settings(xai_api_key="test-key", xai_model="grok-4.6")
    transport = httpx.MockTransport(_mock_handler_wrong_page)
    async with httpx.AsyncClient(transport=transport, base_url="https://api.x.ai") as raw:
        client = GrokClient(settings, client=raw)
        result = await summarize_pdf(
            pdf_path.read_bytes(),
            "article.pdf",
            settings,
            client=client,
        )
    assert result.locator_count == 1
    assert result.locators_corrected == 1
    assert result.locators_dropped == 0
    assert '(link to "The warehouse fragment"; page 1)' in result.markdown
    assert "page 99" not in result.markdown


PARAPHRASE_QUOTE_MARKDOWN = """# Interpreting Interpreter: Tokens, Not Tonnage

This post is a summary of the article "Copper, Covenants, and the Case of the Missing Ingots" by A. Sample Scholar in Volume 99 of Interpreter: A Journal of Latter-day Saint Faith and Scholarship.

## The Takeaway

Scholar argues that the copper is a covenant token.

## The Summary

The fragment lists ingots (link to "The warehouse fragment"; page 1).

As Scholar concludes (link to "although copper can be cargo"; page 3):

> although copper can be cargo, in this fragment it obviously memorializes a promise.

## The Reflection

I like the caution.
"""


def _mock_handler_paraphrased_quote(request: httpx.Request) -> httpx.Response:
    if request.method == "POST" and request.url.path == "/v1/files":
        return httpx.Response(200, json={"id": "file-123", "filename": "article.pdf"})
    if request.method == "POST" and request.url.path == "/v1/responses":
        return httpx.Response(200, json={"output_text": PARAPHRASE_QUOTE_MARKDOWN})
    if request.method == "DELETE" and request.url.path.startswith("/v1/files/"):
        return httpx.Response(200, json={"deleted": True})
    return httpx.Response(404, json={"error": "unhandled"})


@pytest.mark.asyncio
async def test_summarize_pdf_repairs_paraphrased_block_quote(tmp_path):
    pdf_path = write_sample_pdf(tmp_path / "article.pdf")
    settings = Settings(xai_api_key="test-key", xai_model="grok-4.6")
    transport = httpx.MockTransport(_mock_handler_paraphrased_quote)
    async with httpx.AsyncClient(transport=transport, base_url="https://api.x.ai") as raw:
        client = GrokClient(settings, client=raw)
        result = await summarize_pdf(
            pdf_path.read_bytes(),
            "article.pdf",
            settings,
            client=client,
        )
    assert result.quotes_corrected == 1
    assert result.quotes_dropped == 0
    assert "obviously" not in result.markdown
    assert "more plausibly memorializes a promise" in result.markdown


def test_extract_output_text_from_choices():
    payload = {"choices": [{"message": {"content": "hello from chat completions"}}]}
    assert extract_output_text(payload) == "hello from chat completions"


def test_health_and_index():
    client = TestClient(app)
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    home = client.get("/")
    assert home.status_code == 200
    assert "Interpreting" in home.text


def test_summarize_endpoint_rejects_non_pdf():
    client = TestClient(app)
    response = client.post(
        "/api/summarize",
        files={"pdf": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400


def test_export_docx_roundtrip():
    client = TestClient(app)
    response = client.post("/api/export/docx", json={"markdown": SAMPLE_MARKDOWN})
    assert response.status_code == 200
    assert response.content[:2] == b"PK"
    assert markdown_to_docx(SAMPLE_MARKDOWN)[:2] == b"PK"


def test_extract_handles_output_text_field():
    assert extract_output_text({"output_text": "plain"}) == "plain"
