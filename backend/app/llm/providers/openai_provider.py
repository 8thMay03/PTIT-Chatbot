from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any

from app.llm.base import BaseLLMProvider, LLMConfigurationError, LLMMessage, LLMProviderError

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """LLM provider using OpenAI API."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = "gpt-4.1-mini",
        base_url: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 2,
    ) -> None:
        super().__init__(model_name=model_name, timeout=timeout, max_retries=max_retries)
        self.api_key = api_key
        self.base_url = base_url
        self._client = None

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def _get_client(self):
        if not self.is_configured():
            raise LLMConfigurationError("OPENAI_API_KEY is not configured.")
        if self._client is None:
            from openai import OpenAI

            client_kwargs: dict[str, Any] = {
                "api_key": self.api_key.strip() if self.api_key else self.api_key,
                "timeout": self.timeout,
            }
            if self.base_url and self.base_url.strip():
                client_kwargs["base_url"] = self.base_url.strip()

            self._client = OpenAI(**client_kwargs)
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

        return self._execute_with_retry(_call, operation_name="OpenAI completion")

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
            logger.error("OpenAI streaming failed: %s", exc)
            raise LLMProviderError(f"OpenAI streaming error: {exc}") from exc
