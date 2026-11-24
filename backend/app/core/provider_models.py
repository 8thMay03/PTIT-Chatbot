"""Lấy danh sách mô hình khả dụng từ nhà cung cấp cho hộp thoại "Thêm mô hình".

Chỉ đọc, không lưu gì. Gọi bằng ``httpx``, không thêm SDK của từng hãng.

- OpenAI, tương thích OpenAI, Rerank API: ``GET {base_url}/models`` (chuẩn OpenAI, ``data[].id``).
- Gemini: ``GET /v1beta/models``, lọc theo ``supportedGenerationMethods``.
- Cohere: ``GET /v1/models?endpoint=embed|rerank``.
- Pinecone: ``GET /models?type=rerank``.
- HF TEI: ``GET {base_url}/info`` (một mô hình, ``model_id``).
- Azure, Voyage, Jina và mô hình chạy cục bộ không có API liệt kê dùng được → không hỗ trợ.

Hãng có URL cố định bỏ qua Base URL client gửi, để khoá không đi tới host khác. Base URL do
admin nhập phải qua allowlist; caller kiểm trước khi lấy khoá. Không theo redirect: đích
chuyển hướng không qua allowlist. ``ModelListError.reason`` không chứa khoá hay response thô.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import ConfigValidationError, validate_llm_url
from app.retrieval.reranker import PINECONE_API_VERSION

LIST_TIMEOUT_SECONDS = 10.0
MAX_MODELS = 1000
_MAX_MODEL_ID_LENGTH = 255
# Gemini và Cohere phân trang; dừng sau vài trang để không lặp vô hạn khi dịch vụ trả token lạ.
_MAX_PAGES = 5

OPENAI_BASE_URL = "https://api.openai.com/v1"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
COHERE_MODELS_URL = "https://api.cohere.com/v1/models"
PINECONE_MODELS_URL = "https://api.pinecone.io/models"

# (loại, nhà cung cấp) lấy được danh sách. Giá trị: Base URL "required" | "optional" | None (URL cố định).
SUPPORTED: dict[tuple[str, str], str | None] = {
    ("llm", "openai"): "optional",
    ("llm", "gemini"): None,
    ("llm", "openai_compatible"): "required",
    ("embedding", "openai"): None,
    ("embedding", "gemini"): None,
    ("embedding", "cohere"): None,
    ("embedding", "openai_compatible"): "required",
    ("reranker", "cohere"): None,
    ("reranker", "pinecone"): None,
    ("reranker", "tei"): "required",
    ("reranker", "rerank_api"): "required",
}
# Không có khoá thì dịch vụ chắc chắn từ chối: báo sớm thay vì gửi request.
KEY_REQUIRED = frozenset(
    {
        ("embedding", "gemini"),
        ("embedding", "cohere"),
        ("reranker", "cohere"),
        ("reranker", "pinecone"),
    }
)

# `GET /models` của OpenAI trả mọi loại mô hình; bỏ loại không sinh văn bản / không phải embedding.
_NON_CHAT_MARKERS = (
    "embed",
    "rerank",
    "tts",
    "whisper",
    "dall-e",
    "image",
    "moderation",
    "transcribe",
    "realtime",
    "audio",
    "davinci",
    "babbage",
    "sora",
)

_HINTS = {
    401: " Kiểm tra API key.",
    403: " Kiểm tra API key.",
    404: " Máy chủ không có API liệt kê mô hình; kiểm tra Base URL hoặc nhập tên mô hình.",
    429: " Dịch vụ đang giới hạn tần suất; thử lại sau.",
}


class ModelListError(Exception):
    """Không lấy được danh sách; ``reason`` an toàn để hiển thị cho admin."""

    def __init__(self, reason: str, status_code: int | None = None):
        super().__init__(reason)
        self.reason = reason
        self.status_code = status_code


def is_supported(kind: str, provider: str) -> bool:
    return (kind, provider) in SUPPORTED


def base_url_mode(kind: str, provider: str) -> str | None:
    return SUPPORTED.get((kind, provider))


def error_message(exc: ModelListError) -> str:
    return f"{exc.reason}.{_HINTS.get(exc.status_code, '')}"


def list_models(kind: str, provider: str, *, api_key: str | None, base_url: str | None) -> list[str]:
    """Tên mô hình dùng được cho (loại, nhà cung cấp), đã lọc, bỏ trùng và sắp xếp."""
    if not is_supported(kind, provider):
        raise ModelListError("Nhà cung cấp này không hỗ trợ lấy danh sách mô hình")
    if (kind, provider) in KEY_REQUIRED and not api_key:
        raise ModelListError("Thiếu API key")
    mode = base_url_mode(kind, provider)
    base = (base_url or "").strip().rstrip("/") if mode else ""
    if mode == "required" and not base:
        raise ModelListError("Thiếu Base URL")
    if base:
        try:
            # Kiểm lại ở đây: caller nào quên kiểm cũng không gửi khoá tới host lạ.
            validate_llm_url(base)
        except ConfigValidationError as exc:
            raise ModelListError(str(exc).rstrip(".")) from None

    if provider == "gemini":
        names = _list_gemini(kind, api_key)
    elif provider == "cohere":
        names = _list_cohere("embed" if kind == "embedding" else "rerank", api_key)
    elif provider == "pinecone":
        names = _list_pinecone(api_key)
    elif provider == "tei":
        names = _list_tei(base, api_key)
    else:
        names = _list_openai_style(base or OPENAI_BASE_URL, api_key)
        names = _filter_openai(kind, provider, names)
    return _clean(names)


# ==========================================
# Gọi HTTP
# ==========================================
def _get_json(url: str, headers: dict[str, str]) -> Any:
    try:
        response = httpx.get(url, headers=headers, timeout=LIST_TIMEOUT_SECONDS)
    except httpx.TimeoutException:
        raise ModelListError("Hết thời gian chờ") from None
    except httpx.HTTPError as exc:
        raise ModelListError(f"Không kết nối được ({type(exc).__name__})") from None
    if not response.is_success:
        raise ModelListError(f"HTTP {response.status_code}", status_code=response.status_code)
    try:
        return response.json()
    except ValueError:
        raise ModelListError("Response không phải JSON") from None


def _bearer(api_key: str | None) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}"} if api_key else {}


def _invalid() -> ModelListError:
    return ModelListError("Response sai định dạng")


def _list_openai_style(base: str, api_key: str | None) -> list[str]:
    payload = _get_json(f"{base}/models", _bearer(api_key))
    # Ollama/vLLM/LiteLLM trả `{"data": [...]}`; vài máy chủ trả thẳng mảng.
    items = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        raise _invalid()
    return [item.get("id") for item in items if isinstance(item, dict)]


def _filter_openai(kind: str, provider: str, names: list[Any]) -> list[Any]:
    ids = [name for name in names if isinstance(name, str)]
    if provider == "rerank_api":
        return ids
    if kind == "embedding":
        # Máy chủ tương thích (Ollama…) không ghi loại mô hình và tên embedding không theo quy ước.
        return [name for name in ids if "embed" in name.lower()] if provider == "openai" else ids
    return [name for name in ids if not any(marker in name.lower() for marker in _NON_CHAT_MARKERS)]


def _list_gemini(kind: str, api_key: str | None) -> list[str]:
    method = "embedContent" if kind == "embedding" else "generateContent"
    headers = {"x-goog-api-key": api_key or ""}
    names: list[str] = []
    token = None
    for _ in range(_MAX_PAGES):
        query = {"pageSize": 1000, **({"pageToken": token} if token else {})}
        payload = _get_json(f"{GEMINI_BASE_URL}/models?{urlencode(query)}", headers)
        if not isinstance(payload, dict) or not isinstance(payload.get("models", []), list):
            raise _invalid()
        for item in payload.get("models", []):
            if not isinstance(item, dict) or method not in (item.get("supportedGenerationMethods") or []):
                continue
            name = item.get("name")
            if isinstance(name, str):
                names.append(name.removeprefix("models/"))
        token = payload.get("nextPageToken")
        if not token:
            break
    return names


def _list_cohere(endpoint: str, api_key: str | None) -> list[str]:
    names: list[str] = []
    token = None
    for _ in range(_MAX_PAGES):
        query = {"endpoint": endpoint, "page_size": 1000, **({"page_token": token} if token else {})}
        payload = _get_json(f"{COHERE_MODELS_URL}?{urlencode(query)}", _bearer(api_key))
        if not isinstance(payload, dict) or not isinstance(payload.get("models", []), list):
            raise _invalid()
        for item in payload.get("models", []):
            if isinstance(item, dict) and not item.get("is_deprecated"):
                names.append(item.get("name"))
        token = payload.get("next_page_token")
        if not token:
            break
    return names


def _list_pinecone(api_key: str | None) -> list[str]:
    headers = {"Api-Key": api_key or "", "X-Pinecone-Api-Version": PINECONE_API_VERSION}
    payload = _get_json(f"{PINECONE_MODELS_URL}?type=rerank", headers)
    items = payload.get("models") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        raise _invalid()
    return [item.get("model") for item in items if isinstance(item, dict) and item.get("type", "rerank") == "rerank"]


def _list_tei(base: str, api_key: str | None) -> list[str]:
    payload = _get_json(f"{base}/info", _bearer(api_key))
    if not isinstance(payload, dict) or not isinstance(payload.get("model_id"), str):
        raise _invalid()
    return [payload["model_id"]]


def _clean(names: list[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for name in names:
        if not isinstance(name, str):
            continue
        name = name.strip()
        if not name or len(name) > _MAX_MODEL_ID_LENGTH or name in seen:
            continue
        seen.add(name)
        result.append(name)
    return sorted(result, key=str.lower)[:MAX_MODELS]
