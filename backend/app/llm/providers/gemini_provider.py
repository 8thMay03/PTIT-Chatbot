from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from typing import Any

import httpx

from app.core.config import settings
from app.llm.base import (
    CONTENT_DELTA,
    REASONING_DELTA,
    BaseLLMProvider,
    LLMConfigurationError,
    LLMMessage,
    LLMProviderError,
    StreamDelta,
    redact_secrets,
)
from app.llm.budget import LLMBudget

logger = logging.getLogger(__name__)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiProvider(BaseLLMProvider):
    """LLM provider for Google Gemini API."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = "gemini-1.5-flash",
        timeout: float = 30.0,
        max_retries: int = 2,
        http_client: httpx.Client | None = None,
    ) -> None:
        super().__init__(model_name=model_name, timeout=timeout, max_retries=max_retries)
        self.api_key = api_key
        # httpx.Client tùy chọn (test tiêm MockTransport); None -> tạo lúc gọi đầu tiên.
        self._http_client = http_client

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def _convert_messages(
        self,
        messages: list[LLMMessage | dict[str, str]],
    ) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
        """Convert standard messages into Gemini system_instruction and contents format."""
        normalized = self._normalize_messages(messages)
        system_parts: list[str] = []
        contents: list[dict[str, Any]] = []

        for msg in normalized:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                system_parts.append(content)
            elif role == "assistant":
                contents.append({
                    "role": "model",
                    "parts": [{"text": content}],
                })
            else:
                contents.append({
                    "role": "user",
                    "parts": [{"text": content}],
                })

        system_instruction = (
            {"parts": [{"text": "\n\n".join(system_parts)}]}
            if system_parts
            else None
        )
        return system_instruction, contents

    def _build_payload(
        self,
        messages: list[LLMMessage | dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        system_instruction, contents = self._convert_messages(messages)
        generation_config: dict[str, Any] = {
            "temperature": temperature,
        }
        if max_tokens is not None:
            generation_config["maxOutputTokens"] = max_tokens
        generation_config.update(kwargs)

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": generation_config,
        }
        if system_instruction:
            payload["systemInstruction"] = system_instruction
        return payload

    def _get_http_client(self) -> httpx.Client:
        if not self.is_configured():
            raise LLMConfigurationError("GEMINI_API_KEY is not configured.")
        with self._client_lock:
            if self._http_client is None:
                # Một client giữ kết nối (keep-alive) cho mọi lời gọi của provider.
                self._http_client = httpx.Client(timeout=self.timeout)
        return self._http_client

    def _headers(self) -> dict[str, str]:
        # Key gửi qua header, không nằm trong URL (URL có thể xuất hiện trong log/exception).
        return {"Content-Type": "application/json", "x-goog-api-key": (self.api_key or "").strip()}

    def _http_error(self, response: httpx.Response) -> LLMProviderError:
        """Lỗi HTTP của Gemini, giữ status code để `_is_retryable_error` không retry 4xx."""
        status = response.status_code
        message = ""
        try:
            message = str(response.json().get("error", {}).get("message", ""))
        except (ValueError, AttributeError):
            message = response.text
        message = redact_secrets(" ".join(message.split())[:200], self._secrets())
        retry_after = response.headers.get("retry-after")
        try:
            retry_after_seconds = float(retry_after) if retry_after is not None else None
        except ValueError:
            retry_after_seconds = None
        return LLMProviderError(
            f"Gemini API error {status}" + (f": {message}" if message else ""),
            status_code=status,
            retry_after=retry_after_seconds,
        )

    def generate(
        self,
        messages: list[LLMMessage | dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int | None = None,
        budget: LLMBudget | None = None,
        **kwargs: Any,
    ) -> str:
        client = self._get_http_client()
        url = f"{GEMINI_API_BASE}/{self.model_name}:generateContent"
        payload = self._build_payload(messages, temperature=temperature, max_tokens=max_tokens, **kwargs)

        def _call(timeout: float) -> str:
            response = client.post(url, json=payload, headers=self._headers(), timeout=timeout)
            if response.is_error:
                raise self._http_error(response)
            candidates = response.json().get("candidates", [])
            if not candidates:
                return ""
            parts = candidates[0].get("content", {}).get("parts", [])
            return "".join(part.get("text", "") for part in parts)

        return self._execute_with_retry(_call, operation_name="Gemini completion", budget=budget)

    def _stream_sse_chunks(
        self,
        messages: list[LLMMessage | dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int | None = None,
        budget: LLMBudget | None = None,
        **kwargs: Any,
    ) -> Iterator[dict[str, Any]]:
        """POST streamGenerateContent and yield parsed SSE JSON chunks."""
        client = self._get_http_client()
        url = f"{GEMINI_API_BASE}/{self.model_name}:streamGenerateContent"
        payload = self._build_payload(messages, temperature=temperature, max_tokens=max_tokens, **kwargs)

        def _open(timeout: float) -> Iterator[dict[str, Any]]:
            request = client.build_request(
                "POST", url, params={"alt": "sse"}, json=payload, headers=self._headers(), timeout=timeout
            )
            response = client.send(request, stream=True)
            if response.is_error:
                try:
                    response.read()
                    raise self._http_error(response)
                finally:
                    response.close()
            return _iter_sse(response)

        return self._stream_with_retry(_open, operation_name="Gemini streaming", budget=budget)

    def generate_stream(
        self,
        messages: list[LLMMessage | dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int | None = None,
        budget: LLMBudget | None = None,
        **kwargs: Any,
    ) -> Iterator[str]:
        for chunk in self._stream_sse_chunks(
            messages, temperature=temperature, max_tokens=max_tokens, budget=budget, **kwargs
        ):
            candidates = chunk.get("candidates", [])
            if not candidates:
                continue
            parts = candidates[0].get("content", {}).get("parts", [])
            for part in parts:
                # Thought summaries chỉ xuất hiện khi includeThoughts được bật
                # ở generate_stream_deltas; ở đây luôn bỏ qua để giữ text thuần.
                text = part.get("text", "")
                if text and not part.get("thought"):
                    yield text

    def generate_stream_deltas(
        self,
        messages: list[LLMMessage | dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int | None = None,
        budget: LLMBudget | None = None,
        **kwargs: Any,
    ) -> Iterator[StreamDelta]:
        """Stream content plus thought summaries on thinking models (2.5+).

        Thought parts (``{"text": ..., "thought": true}``) become reasoning
        deltas; the rest are content deltas. ``includeThoughts`` chỉ gửi khi
        cờ bật vì model cũ (1.5) có thể từ chối field này.
        """
        if settings.llm_reasoning_stream_enabled:
            kwargs.setdefault("includeThoughts", True)
        for chunk in self._stream_sse_chunks(
            messages, temperature=temperature, max_tokens=max_tokens, budget=budget, **kwargs
        ):
            candidates = chunk.get("candidates", [])
            if not candidates:
                continue
            parts = candidates[0].get("content", {}).get("parts", [])
            for part in parts:
                text = part.get("text", "")
                if not text:
                    continue
                if part.get("thought"):
                    yield StreamDelta(kind=REASONING_DELTA, text=text)
                else:
                    yield StreamDelta(kind=CONTENT_DELTA, text=text)


def _iter_sse(response: httpx.Response) -> Iterator[dict[str, Any]]:
    """Đọc từng dòng SSE `data: {...}` của Gemini; luôn đóng response khi dừng."""
    try:
        for raw_line in response.iter_lines():
            line = raw_line.strip()
            if not line or not line.startswith("data:"):
                continue
            data_str = line[len("data:"):].strip()
            if not data_str or data_str == "[DONE]":
                continue
            try:
                yield json.loads(data_str)
            except json.JSONDecodeError:
                continue
    finally:
        response.close()
