from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from interpreter_summary.config import Settings


class GrokError(RuntimeError):
    """Raised when the xAI API returns an error or an empty summary."""


class GrokClient:
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        if not settings.xai_api_key:
            raise GrokError(
                "Missing XAI_API_KEY. Copy .env.example to .env and add a key from https://console.x.ai"
            )
        self.settings = settings
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=settings.xai_base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {settings.xai_api_key}"},
            timeout=httpx.Timeout(settings.request_timeout_seconds),
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def upload_pdf(self, data: bytes, filename: str) -> str:
        # expires_after must appear before the file field in the multipart body.
        files = {
            "expires_after": (None, str(self.settings.file_ttl_seconds)),
            "purpose": (None, "assistants"),
            "file": (filename, data, "application/pdf"),
        }
        response = await self._client.post("/v1/files", files=files)
        payload = _json_or_error(response, "upload")
        file_id = payload.get("id")
        if not file_id:
            raise GrokError("xAI file upload did not return a file id.")
        return str(file_id)

    async def delete_file(self, file_id: str) -> None:
        try:
            await self._client.delete(f"/v1/files/{file_id}")
        except httpx.HTTPError:
            return

    async def summarize_file(
        self,
        file_id: str,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        response = await self._client.post(
            "/v1/responses",
            json=_responses_payload(
                model=self.settings.xai_model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                file_id=file_id,
                stream=False,
            ),
            headers={"Content-Type": "application/json"},
        )
        payload = _json_or_error(response, "summarize")
        text = extract_output_text(payload)
        if not text.strip():
            raise GrokError("Grok returned an empty summary.")
        return text.strip() + "\n"

    async def summarize_file_stream(
        self,
        file_id: str,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> AsyncIterator[str]:
        async with self._client.stream(
            "POST",
            "/v1/responses",
            json=_responses_payload(
                model=self.settings.xai_model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                file_id=file_id,
                stream=True,
            ),
            headers={"Content-Type": "application/json"},
        ) as response:
            if response.status_code >= 400:
                body = (await response.aread()).decode("utf-8", errors="replace")
                raise GrokError(_format_api_error(response.status_code, body, "summarize"))
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if not data or data == "[DONE]":
                    continue
                try:
                    event = json.loads(data)
                except json.JSONDecodeError:
                    continue
                delta = _stream_delta(event)
                if delta:
                    yield delta


def _responses_payload(
    *,
    model: str,
    system_prompt: str,
    user_prompt: str,
    file_id: str,
    stream: bool,
) -> dict[str, Any]:
    return {
        "model": model,
        "stream": stream,
        "store": False,
        "input": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": user_prompt},
                    {"type": "input_file", "file_id": file_id},
                ],
            },
        ],
    }


def extract_output_text(payload: dict[str, Any]) -> str:
    if isinstance(payload.get("output_text"), str) and payload["output_text"].strip():
        return payload["output_text"]
    chunks: list[str] = []
    for item in payload.get("output") or []:
        if not isinstance(item, dict):
            continue
        for content in item.get("content") or []:
            if not isinstance(content, dict):
                continue
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                chunks.append(str(content["text"]))
    if chunks:
        return "".join(chunks)
    choices = payload.get("choices") or []
    if choices:
        message = choices[0].get("message") or {}
        content = message.get("content")
        if isinstance(content, str):
            return content
    return ""


def _stream_delta(event: dict[str, Any]) -> str:
    event_type = event.get("type") or ""
    if event_type in {"response.output_text.delta", "response.output_text.delta.added"}:
        delta = event.get("delta")
        if isinstance(delta, str):
            return delta
    if event_type == "response.output_text.delta" and isinstance(event.get("text"), str):
        return event["text"]
    choices = event.get("choices") or []
    if choices:
        delta = choices[0].get("delta") or {}
        content = delta.get("content")
        if isinstance(content, str):
            return content
    return ""


def _json_or_error(response: httpx.Response, action: str) -> dict[str, Any]:
    try:
        payload = response.json()
    except json.JSONDecodeError:
        payload = {"error": response.text}
    if response.status_code >= 400:
        raise GrokError(_format_api_error(response.status_code, json.dumps(payload), action))
    if not isinstance(payload, dict):
        raise GrokError(f"Unexpected xAI {action} response.")
    return payload


def _format_api_error(status: int, body: str, action: str) -> str:
    snippet = body.strip().replace("\n", " ")
    if len(snippet) > 400:
        snippet = snippet[:400] + "…"
    return f"xAI {action} failed ({status}): {snippet}"
