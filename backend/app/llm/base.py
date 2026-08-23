from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class LLMMessage:
    role: str
    content: str


@dataclass
class LLMResponse:
    content: str
    model: str | None = None
    finish_reason: str | None = None
    usage: dict[str, int] = field(default_factory=dict)


class LLMProviderError(Exception):
    """Base exception for LLM provider errors."""
    pass


class LLMConfigurationError(LLMProviderError):
    """Raised when an LLM provider is misconfigured or missing credentials."""
    pass


class BaseLLMProvider(ABC):
    """Abstract base class for all LLM providers."""

    def __init__(
        self,
        model_name: str = "",
        timeout: float = 30.0,
        max_retries: int = 2,
    ) -> None:
        self.model_name = model_name
        self.timeout = timeout
        self.max_retries = max_retries

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if the provider has all necessary credentials/settings."""
        raise NotImplementedError

    @abstractmethod
    def generate(
        self,
        messages: list[LLMMessage | dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> str:
        """Generate a complete text response (non-streaming)."""
        raise NotImplementedError

    @abstractmethod
    def generate_stream(
        self,
        messages: list[LLMMessage | dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> Iterator[str]:
        """Generate streamed text chunks."""
        raise NotImplementedError

    def _normalize_messages(
        self,
        messages: list[LLMMessage | dict[str, str]],
    ) -> list[dict[str, str]]:
        """Normalize messages into list of {'role': str, 'content': str}."""
        normalized: list[dict[str, str]] = []
        for msg in messages:
            if isinstance(msg, LLMMessage):
                normalized.append({"role": msg.role, "content": msg.content})
            elif isinstance(msg, dict):
                normalized.append({
                    "role": str(msg.get("role", "user")),
                    "content": str(msg.get("content", "")),
                })
            else:
                normalized.append({"role": "user", "content": str(msg)})
        return normalized

    def _execute_with_retry(
        self,
        func: Callable[[], T],
        operation_name: str = "LLM call",
    ) -> T:
        """Execute a callable with retry and exponential backoff for transient errors."""
        retries = 0
        delay = 1.0
        last_exception: Exception | None = None

        while retries <= self.max_retries:
            try:
                return func()
            except Exception as exc:
                last_exception = exc
                if not _is_retryable_error(exc) or retries >= self.max_retries:
                    break
                retries += 1
                logger.warning(
                    "%s failed (attempt %d/%d): %s. Retrying in %.1fs...",
                    operation_name,
                    retries,
                    self.max_retries,
                    exc,
                    delay,
                )
                time.sleep(delay)
                delay *= 2.0

        logger.error("%s failed: %s", operation_name, last_exception)
        raise LLMProviderError(f"{operation_name} failed: {last_exception}") from last_exception


def _is_retryable_error(exc: Exception) -> bool:
    """Determine whether an exception is transient (network/rate limit/server error) or non-retryable."""
    status_code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    if status_code in {400, 401, 403, 404}:
        return False

    exc_name = exc.__class__.__name__
    if any(name in exc_name for name in ("AuthenticationError", "PermissionDeniedError", "NotFoundError", "BadRequestError")):
        return False

    err_str = str(exc).lower()
    if "invalid_api_key" in err_str or "incorrect api key" in err_str:
        return False

    return True

