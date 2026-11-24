"""Lấy danh sách mô hình từ nhà cung cấp (task list-provider-models).

- AC-01: request/response của từng nhà cung cấp, lọc theo loại mô hình, lỗi HTTP/định dạng.
- AC-02: POST /model-profiles/list-models — Base URL qua allowlist trước khi lấy khoá; hãng URL
  cố định bỏ Base URL client gửi; khoá profile chỉ dùng khi cùng loại và cùng nhà cung cấp.

Không gọi mạng thật: ``httpx.get`` của ``provider_models`` được thay bằng hàm giả.
"""

from __future__ import annotations

import httpx
import pytest
from cryptography.fernet import Fernet

from app.core import model_profiles, provider_models
from app.core.config import settings

TEST_API_KEY = "sk-unit-test-list-models-0123456789"
LOCAL_URL = "http://ollama.local:11434/v1"


@pytest.fixture(autouse=True)
def _restore_settings(monkeypatch):
    snapshot = settings.model_dump()
    monkeypatch.setattr(settings, "config_encryption_key", Fernet.generate_key().decode())
    monkeypatch.setattr(settings, "llm_base_url_allowlist", "http://ollama.local:11434,http://tei.local:8080")
    yield
    for field, value in snapshot.items():
        setattr(settings, field, value)


class _FakeGet:
    """Ghi lại các request; trả response theo thứ tự (dict/list → JSON 200, int → mã lỗi)."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls: list[tuple[str, dict]] = []

    def __call__(self, url, headers=None, timeout=None, **kwargs):
        assert "follow_redirects" not in kwargs
        self.calls.append((url, dict(headers or {})))
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        request = httpx.Request("GET", url)
        if isinstance(item, int):
            return httpx.Response(item, json={"error": "secret detail"}, request=request)
        if isinstance(item, str):
            return httpx.Response(200, text=item, request=request)
        return httpx.Response(200, json=item, request=request)


def _fake(monkeypatch, *responses) -> _FakeGet:
    fake = _FakeGet(*responses)
    monkeypatch.setattr(provider_models.httpx, "get", fake)
    return fake


# ==========================================
# Từng nhà cung cấp (AC-01)
# ==========================================
OPENAI_MODELS = {
    "data": [
        {"id": "gpt-4.1-mini"},
        {"id": "gpt-4o"},
        {"id": "text-embedding-3-small"},
        {"id": "text-embedding-3-large"},
        {"id": "whisper-1"},
        {"id": "tts-1"},
        {"id": "dall-e-3"},
        {"id": "omni-moderation-latest"},
        {"id": "gpt-4o-realtime-preview"},
        {"id": "o3-mini"},
    ]
}


def test_openai_llm_lists_chat_models_only(monkeypatch) -> None:
    fake = _fake(monkeypatch, OPENAI_MODELS)
    models = provider_models.list_models("llm", "openai", api_key=TEST_API_KEY, base_url=None)
    assert models == ["gpt-4.1-mini", "gpt-4o", "o3-mini"]
    url, headers = fake.calls[0]
    assert url == "https://api.openai.com/v1/models"
    assert headers["Authorization"] == f"Bearer {TEST_API_KEY}"


def test_openai_embedding_lists_embedding_models_only(monkeypatch) -> None:
    _fake(monkeypatch, OPENAI_MODELS)
    models = provider_models.list_models("embedding", "openai", api_key=TEST_API_KEY, base_url=None)
    assert models == ["text-embedding-3-large", "text-embedding-3-small"]


def test_compatible_uses_base_url_and_optional_key(monkeypatch) -> None:
    fake = _fake(monkeypatch, {"object": "list", "data": [{"id": "qwen2.5:7b"}, {"id": "nomic-embed-text"}]})
    assert provider_models.list_models("llm", "openai_compatible", api_key=None, base_url=LOCAL_URL + "/") == [
        "qwen2.5:7b"
    ]
    url, headers = fake.calls[0]
    assert url == f"{LOCAL_URL}/models"
    assert "Authorization" not in headers

    # Embedding qua máy chủ tương thích: không đoán loại theo tên, trả đủ.
    _fake(monkeypatch, {"data": [{"id": "bge-m3"}, {"id": "qwen2.5:7b"}]})
    assert provider_models.list_models("embedding", "openai_compatible", api_key=None, base_url=LOCAL_URL) == [
        "bge-m3",
        "qwen2.5:7b",
    ]


def test_gemini_filters_by_generation_method_and_follows_pages(monkeypatch) -> None:
    page1 = {
        "models": [
            {"name": "models/gemini-2.0-flash", "supportedGenerationMethods": ["generateContent", "countTokens"]},
            {"name": "models/gemini-embedding-001", "supportedGenerationMethods": ["embedContent"]},
        ],
        "nextPageToken": "next",
    }
    page2 = {"models": [{"name": "models/gemini-2.5-pro", "supportedGenerationMethods": ["generateContent"]}]}
    fake = _fake(monkeypatch, page1, page2)
    models = provider_models.list_models("llm", "gemini", api_key=TEST_API_KEY, base_url="http://ignored.example")
    assert models == ["gemini-2.0-flash", "gemini-2.5-pro"]
    assert fake.calls[0][0].startswith("https://generativelanguage.googleapis.com/v1beta/models?")
    assert "pageToken=next" in fake.calls[1][0]
    assert fake.calls[0][1]["x-goog-api-key"] == TEST_API_KEY
    assert all(TEST_API_KEY not in url for url, _ in fake.calls)

    _fake(monkeypatch, page1 | {"nextPageToken": None})
    assert provider_models.list_models("embedding", "gemini", api_key=TEST_API_KEY, base_url=None) == [
        "gemini-embedding-001"
    ]


def test_cohere_filters_by_endpoint_and_skips_deprecated(monkeypatch) -> None:
    fake = _fake(
        monkeypatch,
        {"models": [{"name": "rerank-v3.5", "endpoints": ["rerank"]}, {"name": "rerank-old", "is_deprecated": True}]},
    )
    assert provider_models.list_models("reranker", "cohere", api_key=TEST_API_KEY, base_url=None) == ["rerank-v3.5"]
    url, headers = fake.calls[0]
    assert url.startswith("https://api.cohere.com/v1/models?") and "endpoint=rerank" in url
    assert headers["Authorization"] == f"Bearer {TEST_API_KEY}"

    fake = _fake(monkeypatch, {"models": [{"name": "embed-v4.0"}]})
    provider_models.list_models("embedding", "cohere", api_key=TEST_API_KEY, base_url=None)
    assert "endpoint=embed" in fake.calls[0][0]


def test_pinecone_lists_rerank_models(monkeypatch) -> None:
    fake = _fake(
        monkeypatch,
        {"models": [{"model": "bge-reranker-v2-m3", "type": "rerank"}, {"model": "multilingual-e5-large", "type": "embed"}]},
    )
    assert provider_models.list_models("reranker", "pinecone", api_key=TEST_API_KEY, base_url=None) == [
        "bge-reranker-v2-m3"
    ]
    url, headers = fake.calls[0]
    assert url == "https://api.pinecone.io/models?type=rerank"
    assert headers["Api-Key"] == TEST_API_KEY and headers["X-Pinecone-Api-Version"]


def test_tei_reads_model_id_from_info(monkeypatch) -> None:
    fake = _fake(monkeypatch, {"model_id": "BAAI/bge-reranker-v2-m3", "model_type": {"reranker": {}}})
    assert provider_models.list_models("reranker", "tei", api_key=None, base_url="http://tei.local:8080") == [
        "BAAI/bge-reranker-v2-m3"
    ]
    assert fake.calls[0][0] == "http://tei.local:8080/info"


def test_cleans_duplicates_blank_and_overlong_ids(monkeypatch) -> None:
    _fake(monkeypatch, {"data": [{"id": "b"}, {"id": "A"}, {"id": "b"}, {"id": " "}, {"id": "x" * 300}, {}, "junk"]})
    assert provider_models.list_models("reranker", "rerank_api", api_key=None, base_url=LOCAL_URL) == ["A", "b"]


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (401, "HTTP 401. Kiểm tra API key."),
        (404, "HTTP 404. Máy chủ không có API liệt kê mô hình"),
        ("<html>", "Response không phải JSON."),
        ({"data": "nope"}, "Response sai định dạng."),
        (httpx.ConnectTimeout("t"), "Hết thời gian chờ."),
        (httpx.ConnectError("refused"), "Không kết nối được (ConnectError)."),
    ],
)
def test_errors_are_safe_messages(monkeypatch, response, expected) -> None:
    _fake(monkeypatch, response)
    with pytest.raises(provider_models.ModelListError) as info:
        provider_models.list_models("llm", "openai_compatible", api_key=TEST_API_KEY, base_url=LOCAL_URL)
    message = provider_models.error_message(info.value)
    assert message.startswith(expected)
    assert TEST_API_KEY not in message and "secret detail" not in message


def test_rejects_unsupported_missing_key_and_disallowed_url(monkeypatch) -> None:
    fake = _fake(monkeypatch)
    cases = [
        ("llm", "azure", TEST_API_KEY, None),
        ("embedding", "voyage", TEST_API_KEY, None),
        ("reranker", "cross-encoder", None, None),
        ("reranker", "cohere", None, None),
        ("llm", "openai_compatible", None, None),
        ("llm", "openai_compatible", TEST_API_KEY, "http://169.254.169.254/latest"),
        ("llm", "openai", TEST_API_KEY, "https://evil.example.com/v1"),
    ]
    for kind, provider, key, base_url in cases:
        with pytest.raises(provider_models.ModelListError):
            provider_models.list_models(kind, provider, api_key=key, base_url=base_url)
    assert fake.calls == []


# ==========================================
# Endpoint (AC-02)
# ==========================================
ENDPOINT = "/api/model-profiles/list-models"


def _create(client, **body) -> dict:
    response = client.post("/api/model-profiles", json=body)
    assert response.status_code == 201, response.text
    return next(p for p in response.json()["profiles"] if p["name"] == body["name"])


def test_endpoint_requires_admin(client) -> None:
    response = client.post(ENDPOINT, json={"kind": "llm", "provider": "openai"})
    assert response.status_code in (401, 403)


def test_endpoint_lists_with_typed_key(admin_client, config_store_db, monkeypatch) -> None:
    fake = _fake(monkeypatch, {"data": [{"id": "qwen2.5:7b"}]})
    response = admin_client.post(
        ENDPOINT,
        json={"kind": "llm", "provider": "openai_compatible", "base_url": LOCAL_URL, "api_key": TEST_API_KEY},
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"success": True, "message": None, "models": ["qwen2.5:7b"]}
    assert fake.calls[0][1]["Authorization"] == f"Bearer {TEST_API_KEY}"


def test_endpoint_checks_url_before_using_stored_key(admin_client, config_store_db, monkeypatch) -> None:
    profile = _create(
        admin_client,
        kind="llm",
        name="Local",
        provider="openai_compatible",
        base_url=LOCAL_URL,
        model="qwen2.5:7b",
        api_key=TEST_API_KEY,
    )
    fake = _fake(monkeypatch)
    for base_url in ("http://169.254.169.254/latest", None):
        response = admin_client.post(
            ENDPOINT,
            json={"kind": "llm", "provider": "openai_compatible", "base_url": base_url, "profile_id": profile["id"]},
        )
        assert response.status_code == 422
    assert fake.calls == []

    fake = _fake(monkeypatch, {"data": [{"id": "qwen2.5:7b"}]})
    response = admin_client.post(
        ENDPOINT,
        json={"kind": "llm", "provider": "openai_compatible", "base_url": LOCAL_URL, "profile_id": profile["id"]},
    )
    assert response.status_code == 200 and response.json()["models"] == ["qwen2.5:7b"]
    assert fake.calls[0][1]["Authorization"] == f"Bearer {TEST_API_KEY}"
    assert TEST_API_KEY not in response.text


def test_endpoint_fixed_url_provider_ignores_client_base_url(admin_client, config_store_db, monkeypatch) -> None:
    fake = _fake(monkeypatch, {"models": [{"name": "rerank-v3.5"}]})
    response = admin_client.post(
        ENDPOINT,
        json={"kind": "reranker", "provider": "cohere", "base_url": "https://evil.example.com", "api_key": "co-key"},
    )
    assert response.status_code == 200, response.text
    assert fake.calls[0][0].startswith("https://api.cohere.com/")


def test_endpoint_never_uses_key_of_other_provider_or_kind(admin_client, config_store_db, monkeypatch) -> None:
    cohere = _create(
        admin_client, kind="reranker", name="C", provider="cohere", model="rerank-v3.5", api_key=TEST_API_KEY
    )
    fake = _fake(monkeypatch, {"models": []})
    # Khoá Cohere không gửi sang Pinecone: thiếu khoá → báo lỗi, không gọi mạng.
    response = admin_client.post(ENDPOINT, json={"kind": "reranker", "provider": "pinecone", "profile_id": cohere["id"]})
    assert response.status_code == 200
    assert response.json()["success"] is False and "API key" in response.json()["message"]
    assert fake.calls == []
    # Profile khác loại bị từ chối.
    response = admin_client.post(ENDPOINT, json={"kind": "embedding", "provider": "cohere", "profile_id": cohere["id"]})
    assert response.status_code == 422
    assert fake.calls == []


def test_endpoint_env_key_fallback_only_for_env_providers(admin_client, config_store_db, monkeypatch) -> None:
    monkeypatch.setitem(model_profiles._INITIAL_SETTINGS, "openai_api_key", "sk-env-key")
    monkeypatch.setitem(model_profiles._INITIAL_SETTINGS, "openai_compatible_api_key", "sk-env-compatible")
    fake = _fake(monkeypatch, OPENAI_MODELS, {"data": []})
    response = admin_client.post(ENDPOINT, json={"kind": "llm", "provider": "openai"})
    assert response.status_code == 200 and "gpt-4o" in response.json()["models"]
    assert fake.calls[0][1]["Authorization"] == "Bearer sk-env-key"

    # Máy chủ tương thích không dùng khoá `.env`.
    response = admin_client.post(ENDPOINT, json={"kind": "llm", "provider": "openai_compatible", "base_url": LOCAL_URL})
    assert response.json() == {"success": True, "message": "Máy chủ không trả về mô hình phù hợp nào.", "models": []}
    assert "Authorization" not in fake.calls[1][1]


def test_endpoint_rejects_unsupported_provider(admin_client, config_store_db) -> None:
    response = admin_client.post(ENDPOINT, json={"kind": "llm", "provider": "azure"})
    assert response.status_code == 422


def test_endpoint_reports_upstream_error(admin_client, config_store_db, monkeypatch) -> None:
    _fake(monkeypatch, 401)
    response = admin_client.post(ENDPOINT, json={"kind": "llm", "provider": "gemini", "api_key": "bad"})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False and data["models"] == []
    assert data["message"] == "HTTP 401. Kiểm tra API key."
