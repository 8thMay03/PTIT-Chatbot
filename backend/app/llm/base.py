from __future__ import annotations

import logging
import random
import re
import threading
import time
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, Callable, TypeVar

from app.llm.budget import LLMBudget

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class LLMMessage:
    role: str
    content: str


# Kind của delta stream: "content" là phần câu trả lời, "reasoning" là phần
# suy luận của model (reasoning_content của DeepSeek/GLM, thought part của
# Gemini). Provider không hỗ trợ thinking chỉ phát delta "content".
CONTENT_DELTA = "content"
REASONING_DELTA = "reasoning"


@dataclass
class StreamDelta:
    kind: str
    text: str


@dataclass
class LLMResponse:
    content: str
    model: str | None = None
    finish_reason: str | None = None
    usage: dict[str, int] = field(default_factory=dict)


class LLMProviderError(Exception):
    """Base exception for LLM provider errors.

    ``status_code`` là mã HTTP của provider (nếu có); ``retryable`` ghi đè cách
    ``_is_retryable_error`` phân loại lỗi; ``retry_after`` là giá trị header
    ``Retry-After`` (giây) khi provider gửi kèm.
    """

    def __init__(
        self,
        message: str = "",
        *,
        status_code: int | None = None,
        retryable: bool | None = None,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable
        self.retry_after = retry_after


class LLMConfigurationError(LLMProviderError):
    """Raised when an LLM provider is misconfigured or missing credentials."""
    pass


class LLMStreamError(LLMProviderError):
    """Raised when a streaming LLM call fails after at least one token was emitted."""
    pass


class LLMDeadlineExceeded(LLMProviderError):
    """Raised when the chat turn's LLM budget ran out before (another) attempt."""

    def __init__(self, message: str = "LLM deadline exceeded.") -> None:
        super().__init__(message, retryable=False)


# Một tầng retry duy nhất (BE-12): client SDK tạo với max_retries=0, mọi retry nằm ở
# `_execute_with_retry`. Lần thử cần ít nhất MIN_ATTEMPT_SECONDS; backoff bắt đầu từ
# INITIAL_BACKOFF_SECONDS, nhân đôi mỗi lần; Retry-After dài hơn MAX_RETRY_AFTER_SECONDS
# thì dừng thay vì chờ.
MIN_ATTEMPT_SECONDS = 1.0
INITIAL_BACKOFF_SECONDS = 1.0
MAX_RETRY_AFTER_SECONDS = 20.0
_RETRYABLE_STATUS = frozenset({408, 409, 429})

# Chuỗi giống API key (OpenAI `sk-...`, Google `AIza...`) và tham số `key=` trong URL.
_SECRET_PATTERNS = (
    re.compile(r"\b(sk-[A-Za-z0-9]{0,4})[A-Za-z0-9_\-*]{8,}"),
    re.compile(r"\b(AIza)[0-9A-Za-z_\-]{16,}"),
    re.compile(r"((?:api[_-]?)?key=)[^&\s\"']+", re.IGNORECASE),
)


def redact_secrets(text: str, secrets: tuple[str | None, ...] = ()) -> str:
    """Che chuỗi giống API key trước khi ghi log hoặc đưa vào thông điệp lỗi."""
    for secret in secrets:
        if secret and len(secret.strip()) >= 6:
            text = text.replace(secret.strip(), "[redacted]")
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub(lambda m: f"{m.group(1)}[redacted]", text)
    return text


def error_status_code(exc: BaseException) -> int | None:
    """Mã HTTP của lỗi provider/SDK/httpx, nếu có."""
    for attr in ("status_code", "code"):
        value = getattr(exc, attr, None)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    response = getattr(exc, "response", None)
    value = getattr(response, "status_code", None)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None


def describe_error(exc: BaseException, max_chars: int = 300) -> str:
    """Tên lớp + mã HTTP + thông điệp đã che key, cắt ngắn; dùng cho log và lỗi admin."""
    status = error_status_code(exc)
    label = type(exc).__name__ + (f" (HTTP {status})" if status is not None else "")
    message = redact_secrets(" ".join(str(exc).split()))
    if len(message) > max_chars:
        message = message[:max_chars] + "…"
    return f"{label}: {message}" if message else label


def _retry_after_seconds(exc: BaseException) -> float | None:
    value = getattr(exc, "retry_after", None)
    if value is None:
        headers = getattr(getattr(exc, "response", None), "headers", None)
        value = headers.get("retry-after") if headers is not None else None
    try:
        seconds = float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
    return seconds if seconds is not None and seconds >= 0 else None


class BaseLLMProvider(ABC):
    """Abstract base class for all LLM providers.

    Instance do ``get_llm_provider()`` trả về được dùng chung giữa các request và
    thread: không gán thuộc tính lên provider dùng chung.
    """

    def __init__(
        self,
        model_name: str = "",
        timeout: float = 30.0,
        max_retries: int = 2,
    ) -> None:
        self.model_name = model_name
        self.timeout = timeout
        self.max_retries = max_retries
        self._client_lock = threading.Lock()

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
        budget: LLMBudget | None = None,
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
        budget: LLMBudget | None = None,
        **kwargs: Any,
    ) -> Iterator[str]:
        """Generate streamed text chunks."""
        raise NotImplementedError

    def generate_stream_deltas(
        self,
        messages: list[LLMMessage | dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int | None = None,
        budget: LLMBudget | None = None,
        **kwargs: Any,
    ) -> Iterator[StreamDelta]:
        """Stream typed deltas so callers can separate reasoning from content.

        Default implementation wraps :meth:`generate_stream` and only emits
        ``content`` deltas; providers whose models expose reasoning tokens
        (DeepSeek/GLM reasoning_content, Gemini thought parts) override this.
        """
        for text in self.generate_stream(
            messages, temperature=temperature, max_tokens=max_tokens, budget=budget, **kwargs
        ):
            yield StreamDelta(kind=CONTENT_DELTA, text=text)

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

    def _secrets(self) -> tuple[str | None, ...]:
        """Giá trị cần che khi ghi log lỗi của provider này."""
        return (getattr(self, "api_key", None),)

    def _execute_with_retry(
        self,
        func: Callable[[float], T],
        operation_name: str = "LLM call",
        budget: LLMBudget | None = None,
    ) -> T:
        """Chạy ``func(timeout)`` với retry cho lỗi tạm thời, bị chặn bởi ``budget``.

        Thử tối đa ``1 + max_retries`` lần. ``timeout`` mỗi lần thử là
        ``min(self.timeout, budget.remaining())``; còn dưới ``MIN_ATTEMPT_SECONDS`` thì
        dừng. Backoff (hoặc ``Retry-After`` của 429) không vượt thời gian còn lại. Lỗi
        tạm thời thất bại tới cùng đặt ``budget.degraded`` để bước tùy chọn sau bỏ qua LLM.
        """
        budget = budget or LLMBudget.unlimited()
        max_attempts = 1 + max(0, self.max_retries)
        delay = INITIAL_BACKOFF_SECONDS
        attempts = 0
        last_exception: Exception | None = None

        while attempts < max_attempts:
            attempt_timeout = min(self.timeout, budget.remaining())
            if attempt_timeout < MIN_ATTEMPT_SECONDS:
                break
            attempts += 1
            try:
                return func(attempt_timeout)
            except Exception as exc:
                last_exception = exc
                retryable = _is_retryable_error(exc)
                # Mức warning chỉ ghi lớp lỗi + mã HTTP; chi tiết (đã che key) ở dòng error cuối.
                logger.warning(
                    "%s attempt %d/%d failed: %s (status=%s, retryable=%s)",
                    operation_name,
                    attempts,
                    max_attempts,
                    type(exc).__name__,
                    error_status_code(exc),
                    retryable,
                )
                if not retryable or attempts >= max_attempts:
                    break
                retry_after = _retry_after_seconds(exc)
                if retry_after is not None and retry_after > MAX_RETRY_AFTER_SECONDS:
                    break
                wait = retry_after if retry_after is not None else delay * (1.0 + random.uniform(0.0, 0.25))
                if wait + MIN_ATTEMPT_SECONDS > budget.remaining():
                    break
                time.sleep(wait)
                delay *= 2.0

        if last_exception is None:
            budget.degraded = True
            logger.warning("%s skipped: LLM deadline exceeded.", operation_name)
            raise LLMDeadlineExceeded(f"{operation_name} skipped: LLM deadline exceeded.")

        status_code = error_status_code(last_exception)
        retryable = _is_retryable_error(last_exception)
        if retryable:
            budget.degraded = True
        detail = redact_secrets(describe_error(last_exception), self._secrets())
        logger.error("%s failed after %d attempt(s): %s", operation_name, attempts, detail)
        raise LLMProviderError(
            f"{operation_name} failed: {detail}",
            status_code=status_code,
            retryable=retryable,
        ) from last_exception

    def _stream_with_retry(
        self,
        open_stream: Callable[[float], Iterator[T]],
        operation_name: str = "LLM stream",
        budget: LLMBudget | None = None,
    ) -> Iterator[T]:
        """Mở stream và chờ phần tử đầu tiên với retry; sau đó không retry nữa.

        ``open_stream(timeout)`` trả iterator thô của SDK/HTTP. Lỗi trước phần tử đầu
        tiên được retry như ``_execute_with_retry``; lỗi giữa chừng ném
        ``LLMProviderError`` (generation chuyển thành ``LLMStreamError``).
        """

        def _first(timeout: float) -> tuple[Any, Iterator[T], Any]:
            # Giữ object gốc (Stream của SDK, generator SSE) để đóng kết nối HTTP.
            source = open_stream(timeout)
            iterator = iter(source)
            try:
                return source, iterator, next(iterator)
            except StopIteration:
                return source, iterator, _EMPTY_STREAM
            except BaseException:
                _close_iterator(source)
                raise

        source, iterator, first = self._execute_with_retry(_first, operation_name, budget)
        try:
            if first is _EMPTY_STREAM:
                return
            yield first
            try:
                yield from iterator
            except Exception as exc:
                detail = redact_secrets(describe_error(exc), self._secrets())
                logger.error("%s failed mid-stream: %s", operation_name, detail)
                raise LLMProviderError(
                    f"{operation_name} failed mid-stream: {detail}",
                    status_code=error_status_code(exc),
                    retryable=False,
                ) from exc
        finally:
            _close_iterator(source)


_EMPTY_STREAM = object()


def _close_iterator(iterator: Any) -> None:
    close = getattr(iterator, "close", None)
    if close is None:
        return
    try:
        close()
    except Exception:
        logger.debug("Closing LLM stream failed.", exc_info=True)


def _is_retryable_error(exc: Exception) -> bool:
    """Lỗi tạm thời (mạng, timeout, 408/409/429/5xx) thì retry; 4xx khác và lỗi cấu hình thì không."""
    if isinstance(exc, LLMConfigurationError):
        return False
    if isinstance(exc, LLMProviderError) and exc.retryable is not None:
        return exc.retryable

    status_code = error_status_code(exc)
    if status_code is not None:
        return status_code in _RETRYABLE_STATUS or status_code >= 500

    exc_name = exc.__class__.__name__
    if any(
        name in exc_name
        for name in (
            "AuthenticationError",
            "PermissionDeniedError",
            "NotFoundError",
            "BadRequestError",
            "UnprocessableEntityError",
        )
    ):
        return False

    err_str = str(exc).lower()
    if "invalid_api_key" in err_str or "incorrect api key" in err_str:
        return False

    return True
