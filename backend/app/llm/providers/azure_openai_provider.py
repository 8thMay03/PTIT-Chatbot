from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any

from app.llm.base import BaseLLMProvider, LLMConfigurationError, LLMMessage
from app.llm.budget import LLMBudget

logger = logging.getLogger(__name__)


class AzureOpenAIProvider(BaseLLMProvider):
    """LLM provider using Azure OpenAI Service."""

    def __init__(
        self,
        api_key: str | None = None,
        endpoint: str | None = None,
        deployment_name: str | None = None,
        api_version: str = "2024-02-15-preview",
        timeout: float = 30.0,
        max_retries: int = 2,
        http_client: Any | None = None,
    ) -> None:
        super().__init__(model_name=deployment_name or "", timeout=timeout, max_retries=max_retries)
        self.api_key = api_key
        self.endpoint = endpoint
        self.deployment_name = deployment_name
        self.api_version = api_version
        # httpx.Client tùy chọn (test tiêm MockTransport); None -> SDK tự tạo.
        self.http_client = http_client
        self._client = None

    def is_configured(self) -> bool:
        return bool(
            self.api_key
            and self.api_key.strip()
            and self.endpoint
            and self.endpoint.strip()
            and self.deployment_name
            and self.deployment_name.strip()
        )

    def _get_client(self):
        if not self.is_configured():
            raise LLMConfigurationError(
                "AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, and AZURE_OPENAI_DEPLOYMENT_NAME are required."
            )
        with self._client_lock:
            if self._client is None:
                from openai import AzureOpenAI

                client_kwargs: dict[str, Any] = {
                    "api_key": self.api_key,
                    "azure_endpoint": self.endpoint,
                    "api_version": self.api_version,
                    "timeout": self.timeout,
                    # Một tầng retry duy nhất: retry nằm ở _execute_with_retry (BE-12).
                    "max_retries": 0,
                }
                if self.http_client is not None:
                    client_kwargs["http_client"] = self.http_client
                self._client = AzureOpenAI(**client_kwargs)
        return self._client

    def _params(
        self,
        messages: list[LLMMessage | dict[str, str]],
        temperature: float,
        max_tokens: int | None,
        kwargs: dict[str, Any],
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "model": self.deployment_name,
            "messages": self._normalize_messages(messages),
            "temperature": temperature,
        }
        if max_tokens is not None:
            params["max_tokens"] = max_tokens
        params.update(kwargs)
        return params

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

        return self._execute_with_retry(_call, operation_name="Azure OpenAI completion", budget=budget)

    def generate_stream(
        self,
        messages: list[LLMMessage | dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int | None = None,
        budget: LLMBudget | None = None,
        **kwargs: Any,
    ) -> Iterator[str]:
        client = self._get_client()
        params = self._params(messages, temperature, max_tokens, kwargs)
        params["stream"] = True

        def _open(timeout: float):
            return client.chat.completions.create(**params, timeout=timeout)

        for chunk in self._stream_with_retry(_open, operation_name="Azure OpenAI streaming", budget=budget):
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
