from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any

from app.llm.base import BaseLLMProvider, LLMConfigurationError, LLMMessage, LLMProviderError

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
    ) -> None:
        super().__init__(model_name=model_name, timeout=timeout, max_retries=max_retries)
        self.base_url = base_url
        self.api_key = api_key or "not-needed"
        self._client = None

    def is_configured(self) -> bool:
        return bool(self.base_url and self.base_url.strip())

    def _get_client(self):
        if not self.is_configured():
            raise LLMConfigurationError("OPENAI_COMPATIBLE_BASE_URL is not configured.")
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._client

    def generate(
        self,
        messages: list[LLMMessage | dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> str:
        client = self._get_client()
        normalized_messages = self._normalize_messages(messages)

        def _call():
            params: dict[str, Any] = {
                "model": self.model_name,
                "messages": normalized_messages,
                "temperature": temperature,
            }
            if max_tokens is not None:
                params["max_tokens"] = max_tokens
            params.update(kwargs)
            response = client.chat.completions.create(**params)
            return response.choices[0].message.content or ""

        return self._execute_with_retry(_call, operation_name="OpenAI-compatible completion")

    def generate_stream(
        self,
        messages: list[LLMMessage | dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> Iterator[str]:
        client = self._get_client()
        normalized_messages = self._normalize_messages(messages)

        params: dict[str, Any] = {
            "model": self.model_name,
            "messages": normalized_messages,
            "temperature": temperature,
            "stream": True,
        }
        if max_tokens is not None:
            params["max_tokens"] = max_tokens
        params.update(kwargs)

        try:
            stream = client.chat.completions.create(**params)
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as exc:
            logger.error("OpenAI-compatible streaming failed: %s", exc)
            raise LLMProviderError(f"OpenAI-compatible streaming error: {exc}") from exc
