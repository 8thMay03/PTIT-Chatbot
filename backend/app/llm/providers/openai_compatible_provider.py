from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any

from app.llm.base import (
    CONTENT_DELTA,
    REASONING_DELTA,
    BaseLLMProvider,
    LLMConfigurationError,
    LLMMessage,
    StreamDelta,
)
from app.llm.budget import LLMBudget

logger = logging.getLogger(__name__)


class OpenAICompatibleProvider(BaseLLMProvider):
    """LLM provider for OpenAI-compatible APIs (Ollama, vLLM, LocalAI, Together, Groq, etc.)."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model_name: str = "default",
        timeout: float = 60.0,
        max_retries: int = 2,
        http_client: Any | None = None,
    ) -> None:
        super().__init__(model_name=model_name, timeout=timeout, max_retries=max_retries)
        self.base_url = base_url
        self.api_key = api_key or "not-needed"
        # httpx.Client tùy chọn (test tiêm MockTransport); None -> SDK tự tạo.
        self.http_client = http_client
        self._client = None

    def is_configured(self) -> bool:
        return bool(self.base_url and self.base_url.strip())

    def _get_client(self):
        if not self.is_configured():
            raise LLMConfigurationError("OPENAI_COMPATIBLE_BASE_URL is not configured.")
        with self._client_lock:
            if self._client is None:
                from openai import OpenAI

                client_kwargs: dict[str, Any] = {
                    "api_key": self.api_key,
                    "base_url": self.base_url,
                    "timeout": self.timeout,
                    # Một tầng retry duy nhất: retry nằm ở _execute_with_retry (BE-12).
                    "max_retries": 0,
                }
                if self.http_client is not None:
                    client_kwargs["http_client"] = self.http_client
                self._client = OpenAI(**client_kwargs)
        return self._client

    def _params(
        self,
        messages: list[LLMMessage | dict[str, str]],
        temperature: float,
        max_tokens: int | None,
        kwargs: dict[str, Any],
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "model": self.model_name,
            "messages": self._normalize_messages(messages),
            "temperature": temperature,
        }
        if max_tokens is not None:
            params["max_tokens"] = max_tokens
        params.update(kwargs)
        return params

    def _open_stream(self, params: dict[str, Any], budget: LLMBudget | None) -> Iterator[Any]:
        client = self._get_client()
        params = {**params, "stream": True}

        def _open(timeout: float):
            return client.chat.completions.create(**params, timeout=timeout)

        return self._stream_with_retry(_open, operation_name="OpenAI-compatible streaming", budget=budget)

    def generate(
        self,
        messages: list[LLMMessage | dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int | None = None,
        budget: LLMBudget | None = None,
        **kwargs: Any,
    ) -> str:
        client = self._get_client()
        params = self._params(messages, temperature, max_tokens, kwargs)

        def _call(timeout: float) -> str:
            response = client.chat.completions.create(**params, timeout=timeout)
            return response.choices[0].message.content or ""

        return self._execute_with_retry(_call, operation_name="OpenAI-compatible completion", budget=budget)

    def generate_stream(
        self,
        messages: list[LLMMessage | dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int | None = None,
        budget: LLMBudget | None = None,
        **kwargs: Any,
    ) -> Iterator[str]:
        params = self._params(messages, temperature, max_tokens, kwargs)
        for chunk in self._open_stream(params, budget):
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def generate_stream_deltas(
        self,
        messages: list[LLMMessage | dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int | None = None,
        budget: LLMBudget | None = None,
        **kwargs: Any,
    ) -> Iterator[StreamDelta]:
        """Stream content plus reasoning tokens when the model exposes them.

        DeepSeek-R1/GLM/Qwen thinking models emit ``reasoning_content`` on the
        delta; OpenRouter uses ``reasoning``. Reading the attributes is safe on
        models without thinking: they simply never set them.
        """
        params = self._params(messages, temperature, max_tokens, kwargs)
        for chunk in self._open_stream(params, budget):
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            reasoning = getattr(delta, "reasoning_content", None) or getattr(delta, "reasoning", None)
            if reasoning:
                yield StreamDelta(kind=REASONING_DELTA, text=reasoning)
            if delta.content:
                yield StreamDelta(kind=CONTENT_DELTA, text=delta.content)
