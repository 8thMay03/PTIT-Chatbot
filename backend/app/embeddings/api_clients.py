"""Embedding qua API: Voyage, Cohere, Gemini, Jina và dịch vụ chuẩn OpenAI ``/embeddings``.

Gọi bằng ``httpx``, không thêm SDK của từng hãng.

- Voyage, Cohere, Gemini, Jina dùng URL cố định trong code (D-03) và bắt buộc API key (D-04).
- ``openai_compatible`` (Mistral, Ollama, vLLM, HF TEI…) dùng Base URL admin nhập; URL được
  kiểm lại qua allowlist mỗi lần gọi vì allowlist có thể đã bị thu hẹp. Khoá tuỳ chọn.
- Câu hỏi và đoạn tài liệu được nhúng khác nhau (``input_type``) khi dịch vụ hỗ trợ.
- Chia lô theo giới hạn từng dịch vụ, trả vector đúng thứ tự đầu vào.
- Nạp tài liệu thử lại khi 429/5xx/timeout/lỗi mạng (backoff, tôn trọng ``Retry-After``);
  câu hỏi gọi một lần với timeout ngắn (D-05).

Log và ``EmbeddingAPIError.reason`` không chứa khoá, nội dung gửi đi hay response thô.
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass
from typing import Any, Literal
from urllib.parse import quote, urlsplit

import httpx

from app.core.config import ConfigValidationError, validate_llm_url
from app.embeddings.errors import (
    EmbeddingAPIError,
    EmbeddingNotConfiguredError,
    EmbeddingUnavailableError,
)
from app.embeddings.models import EmbeddingModel

logger = logging.getLogger(__name__)

InputType = Literal["query", "document"]

API_PROVIDERS = ("voyage", "cohere", "gemini", "jina", "openai_compatible")
KEY_REQUIRED_PROVIDERS = frozenset({"voyage", "cohere", "gemini", "jina"})
PROVIDER_LABELS = {
    "voyage": "Voyage AI",
    "cohere": "Cohere",
    "gemini": "Google Gemini",
    "jina": "Jina AI",
    "openai_compatible": "Tương thích OpenAI",
}
FIXED_BASE_URLS = {
    "voyage": "https://api.voyageai.com/v1",
    "cohere": "https://api.cohere.com/v2",
    "gemini": "https://generativelanguage.googleapis.com/v1beta",
    "jina": "https://api.jina.ai/v1",
}
# Số đoạn tối đa mỗi request. Cohere giới hạn 96, Gemini batchEmbedContents 100; Voyage và
# Jina giới hạn theo tổng token nên lấy lô nhỏ để đoạn dài không vượt hạn mức.
BATCH_SIZES = {"voyage": 64, "cohere": 96, "gemini": 100, "jina": 64, "openai_compatible": 64}

QUERY_TIMEOUT_SECONDS = 15.0
DOCUMENT_TIMEOUT_SECONDS = 60.0
# Nạp tài liệu: 1 lần gọi + 3 lần thử lại; câu hỏi: không thử lại.
DOCUMENT_MAX_ATTEMPTS = 4
RETRY_AFTER_MAX_SECONDS = 30.0

# Mô hình số chiều cố định: không gửi tham số số chiều (dịch vụ từ chối tham số này).
_FIXED_DIMENSION_MODELS = {
    "voyage": frozenset(
        {
            "voyage-3",
            "voyage-3-lite",
            "voyage-multilingual-2",
            "voyage-large-2",
            "voyage-large-2-instruct",
            "voyage-2",
            "voyage-law-2",
            "voyage-finance-2",
            "voyage-code-2",
        }
    ),
    "cohere": frozenset(
        {
            "embed-multilingual-v3.0",
            "embed-english-v3.0",
            "embed-multilingual-light-v3.0",
            "embed-english-light-v3.0",
            "embed-multilingual-v2.0",
            "embed-english-v2.0",
        }
    ),
    "gemini": frozenset({"embedding-001"}),
}
# Jina: chỉ thế hệ v3 trở đi nhận `task` và `dimensions`.
_JINA_TASK_PREFIXES = ("jina-embeddings-v3", "jina-embeddings-v4", "jina-clip-v2")

# Có thể ghi đè trong test để không phải chờ thật.
_sleep = time.sleep


@dataclass(frozen=True)
class EmbeddingAPIConfig:
    provider: str
    model: str
    api_key: str | None = None
    base_url: str | None = None
    # Số chiều yêu cầu dịch vụ trả về; None = mặc định của mô hình.
    dimension: int | None = None


def _label(config: EmbeddingAPIConfig) -> str:
    return f"{PROVIDER_LABELS.get(config.provider, config.provider)} ({config.model})"


def check_config(config: EmbeddingAPIConfig) -> None:
    """Kiểm cấu hình trước khi gọi; thiếu khoá/Base URL hay URL ngoài allowlist thì ném lỗi."""
    if config.provider not in API_PROVIDERS:
        raise EmbeddingUnavailableError(f"Provider embedding '{config.provider}' chưa được hỗ trợ.")
    if not config.model:
        raise EmbeddingNotConfiguredError(f"Chưa có tên mô hình cho embedding {PROVIDER_LABELS[config.provider]}.")
    if config.provider in KEY_REQUIRED_PROVIDERS and not config.api_key:
        raise EmbeddingNotConfiguredError(f"Chưa có API key cho embedding {_label(config)}.")
    if config.provider == "openai_compatible":
        if not config.base_url:
            raise EmbeddingNotConfiguredError(f"Chưa có Base URL cho embedding {_label(config)}.")
        try:
            validate_llm_url(config.base_url)
        except ConfigValidationError:
            raise EmbeddingUnavailableError(
                f"Base URL của embedding {_label(config)} không nằm trong LLM_BASE_URL_ALLOWLIST."
            ) from None


def _base_url(config: EmbeddingAPIConfig) -> str:
    base = FIXED_BASE_URLS.get(config.provider) or config.base_url or ""
    return base.rstrip("/")


def _accepts_dimension(config: EmbeddingAPIConfig) -> bool:
    if config.dimension is None:
        return False
    if config.provider == "jina":
        return config.model.startswith(_JINA_TASK_PREFIXES)
    if config.provider == "openai_compatible":
        # Máy chủ tương thích thường từ chối `dimensions` với mô hình không hỗ trợ.
        return False
    return config.model.removeprefix("models/") not in _FIXED_DIMENSION_MODELS.get(config.provider, ())


def build_request(config: EmbeddingAPIConfig, texts: list[str], input_type: InputType) -> tuple[str, dict, dict]:
    """(url, headers, body) của một lô theo định dạng của từng dịch vụ."""
    provider = config.provider
    is_query = input_type == "query"
    base = _base_url(config)
    headers = {"Content-Type": "application/json"}
    if provider == "gemini":
        headers["x-goog-api-key"] = config.api_key or ""
    elif config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"
    send_dimension = _accepts_dimension(config)

    if provider == "voyage":
        body: dict[str, Any] = {
            "model": config.model,
            "input": texts,
            "input_type": "query" if is_query else "document",
        }
        if send_dimension:
            body["output_dimension"] = config.dimension
        return f"{base}/embeddings", headers, body

    if provider == "cohere":
        body = {
            "model": config.model,
            "texts": texts,
            "input_type": "search_query" if is_query else "search_document",
            "embedding_types": ["float"],
        }
        if send_dimension:
            body["output_dimension"] = config.dimension
        return f"{base}/embed", headers, body

    if provider == "gemini":
        model = config.model.removeprefix("models/")
        request: dict[str, Any] = {
            "model": f"models/{model}",
            "taskType": "RETRIEVAL_QUERY" if is_query else "RETRIEVAL_DOCUMENT",
        }
        if send_dimension:
            request["outputDimensionality"] = config.dimension
        body = {"requests": [{**request, "content": {"parts": [{"text": text}]}} for text in texts]}
        return f"{base}/models/{quote(model, safe='')}:batchEmbedContents", headers, body

    body = {"model": config.model, "input": texts}
    if provider == "jina" and config.model.startswith(_JINA_TASK_PREFIXES):
        body["task"] = "retrieval.query" if is_query else "retrieval.passage"
        if send_dimension:
            body["dimensions"] = config.dimension
    return f"{base}/embeddings", headers, body


def _as_vector(value: Any) -> list[float] | None:
    if not isinstance(value, list) or not value:
        return None
    vector: list[float] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)) or not math.isfinite(item):
            return None
        vector.append(float(item))
    return vector


def parse_response(provider: str, payload: Any, count: int) -> list[list[float]] | None:
    """Vector theo thứ tự đầu vào; None nếu response sai định dạng hoặc sai số lượng."""
    if not isinstance(payload, dict):
        return None
    if provider == "cohere":
        embeddings = payload.get("embeddings")
        raw = embeddings.get("float") if isinstance(embeddings, dict) else None
    elif provider == "gemini":
        items = payload.get("embeddings")
        if not isinstance(items, list):
            return None
        raw = [item.get("values") if isinstance(item, dict) else None for item in items]
    else:
        items = payload.get("data")
        if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
            return None
        indexes = [item.get("index") for item in items]
        if all(isinstance(index, int) and not isinstance(index, bool) for index in indexes):
            if sorted(indexes) != list(range(len(items))):
                return None
            items = sorted(items, key=lambda item: item["index"])
        raw = [item.get("embedding") for item in items]
    if not isinstance(raw, list) or len(raw) != count:
        return None
    vectors = [_as_vector(value) for value in raw]
    if any(vector is None for vector in vectors):
        return None
    return vectors


def _retry_delay(response: httpx.Response | None, attempt: int) -> float:
    if response is not None:
        raw = response.headers.get("retry-after", "").strip()
        try:
            seconds = float(raw)
        except ValueError:
            seconds = None
        if seconds is not None and math.isfinite(seconds) and seconds >= 0:
            return min(seconds, RETRY_AFTER_MAX_SECONDS)
    return float(2**attempt)


def _is_retryable_status(status_code: int) -> bool:
    return status_code in (408, 429) or status_code >= 500


def _host(url: str) -> str | None:
    try:
        return urlsplit(url).hostname
    except ValueError:
        return None


def _post(config: EmbeddingAPIConfig, url: str, headers: dict, body: dict, *, timeout: float, max_attempts: int) -> Any:
    for attempt in range(1, max_attempts + 1):
        response: httpx.Response | None = None
        status_code: int | None = None
        try:
            # Không theo redirect: đích chuyển hướng không qua allowlist.
            response = httpx.post(url, json=body, headers=headers, timeout=timeout)
        except httpx.TimeoutException:
            detail, retryable = "timeout", True
        except httpx.HTTPError as exc:
            detail, retryable = type(exc).__name__, True
        else:
            if response.is_success:
                try:
                    return response.json()
                except ValueError:
                    detail, retryable = "response không phải JSON", False
            else:
                status_code = response.status_code
                detail, retryable = f"HTTP {status_code}", _is_retryable_status(status_code)
        if not retryable or attempt == max_attempts:
            break
        _sleep(_retry_delay(response, attempt))

    logger.warning(
        "Gọi embedding thất bại: provider=%s model=%s host=%s lỗi=%s sau %d lần.",
        config.provider,
        config.model,
        _host(url),
        detail,
        attempt,
    )
    raise EmbeddingAPIError(f"Lỗi khi gọi embedding {_label(config)}: {detail}.", status_code=status_code)


def embed_texts(
    config: EmbeddingAPIConfig,
    texts: list[str],
    *,
    input_type: InputType,
    timeout: float | None = None,
    max_attempts: int | None = None,
) -> list[list[float]]:
    """Nhúng ``texts`` qua API, chia lô; lỗi bất kỳ ném ``EmbeddingAPIError`` (hoặc lỗi cấu hình)."""
    if not texts:
        return []
    check_config(config)
    is_query = input_type == "query"
    if timeout is None:
        timeout = QUERY_TIMEOUT_SECONDS if is_query else DOCUMENT_TIMEOUT_SECONDS
    if max_attempts is None:
        max_attempts = 1 if is_query else DOCUMENT_MAX_ATTEMPTS

    size = BATCH_SIZES[config.provider]
    vectors: list[list[float]] = []
    for start in range(0, len(texts), size):
        batch = texts[start : start + size]
        url, headers, body = build_request(config, batch, input_type)
        payload = _post(config, url, headers, body, timeout=timeout, max_attempts=max_attempts)
        parsed = parse_response(config.provider, payload, len(batch))
        if parsed is None:
            logger.warning(
                "Response embedding sai định dạng: provider=%s model=%s host=%s.",
                config.provider,
                config.model,
                _host(url),
            )
            raise EmbeddingAPIError(f"Lỗi khi gọi embedding {_label(config)}: response sai định dạng.")
        vectors.extend(parsed)
    return vectors


class ApiEmbeddingModel(EmbeddingModel):
    """Mô hình nhúng gọi qua API; ``embed`` cho đoạn tài liệu, ``embed_query`` cho câu hỏi."""

    def __init__(
        self,
        provider: str,
        model_name: str,
        api_key: str | None,
        base_url: str | None = None,
        dimensions: int | None = None,
    ) -> None:
        self.config = EmbeddingAPIConfig(
            provider=provider,
            model=(model_name or "").strip(),
            api_key=api_key or None,
            base_url=base_url or None,
            dimension=dimensions,
        )
        check_config(self.config)
        self.model_name = self.config.model
        self.dimensions = dimensions
        # Dịch vụ tương thích OpenAI không phân biệt câu hỏi/tài liệu.
        self.distinguishes_queries = provider != "openai_compatible"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return embed_texts(self.config, texts, input_type="document")

    def embed_query(self, texts: list[str]) -> list[list[float]]:
        return embed_texts(self.config, texts, input_type="query")
