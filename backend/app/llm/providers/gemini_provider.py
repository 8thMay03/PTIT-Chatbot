from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from typing import Any
import urllib.error
import urllib.request

from app.llm.base import BaseLLMProvider, LLMConfigurationError, LLMMessage, LLMProviderError

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
    ) -> None:
        super().__init__(model_name=model_name, timeout=timeout, max_retries=max_retries)
        self.api_key = api_key

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

    def generate(
        self,
        messages: list[LLMMessage | dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> str:
        if not self.is_configured():
            raise LLMConfigurationError("GEMINI_API_KEY is not configured.")

        url = f"{GEMINI_API_BASE}/{self.model_name}:generateContent?key={self.api_key}"
        payload = self._build_payload(messages, temperature=temperature, max_tokens=max_tokens, **kwargs)
        data = json.dumps(payload).encode("utf-8")

        def _call() -> str:
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    candidates = resp_data.get("candidates", [])
                    if not candidates:
                        return ""
                    parts = candidates[0].get("content", {}).get("parts", [])
                    return "".join(part.get("text", "") for part in parts)
            except urllib.error.HTTPError as exc:
                err_body = exc.read().decode("utf-8", errors="replace")
                raise LLMProviderError(f"Gemini API error {exc.code}: {err_body}") from exc

        return self._execute_with_retry(_call, operation_name="Gemini completion")

    def generate_stream(
        self,
        messages: list[LLMMessage | dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> Iterator[str]:
        if not self.is_configured():
            raise LLMConfigurationError("GEMINI_API_KEY is not configured.")

        url = f"{GEMINI_API_BASE}/{self.model_name}:streamGenerateContent?alt=sse&key={self.api_key}"
        payload = self._build_payload(messages, temperature=temperature, max_tokens=max_tokens, **kwargs)
        data = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                for raw_line in resp:
                    line = raw_line.decode("utf-8").strip()
                    if not line or not line.startswith("data:"):
                        continue
                    data_str = line[len("data:"):].strip()
                    if not data_str or data_str == "[DONE]":
                        continue
                    try:
                        chunk = json.loads(data_str)
                        candidates = chunk.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            for part in parts:
                                text = part.get("text", "")
                                if text:
                                    yield text
                    except json.JSONDecodeError:
                        continue
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="replace")
            logger.error("Gemini streaming error: %s", err_body)
            raise LLMProviderError(f"Gemini streaming error {exc.code}: {err_body}") from exc
        except Exception as exc:
            logger.error("Gemini streaming failed: %s", exc)
            raise LLMProviderError(f"Gemini streaming error: {exc}") from exc
