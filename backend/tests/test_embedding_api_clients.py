"""Embedding qua API: Voyage, Cohere, Gemini, Jina, tương thích OpenAI (task embedding-api-providers).

- AC-02: request đúng định dạng từng dịch vụ, đọc vector đúng thứ tự, chia lô.
- AC-03: câu hỏi dùng ``embed_query`` (input_type query), nạp tài liệu dùng ``embed``.
- AC-04: mô hình ít chiều hơn VECTOR_DIM được đệm 0; nhiều hơn thì lỗi.
- AC-05: thử lại 429/5xx/timeout khi nạp tài liệu; câu hỏi không thử lại; log an toàn.

Không gọi mạng thật: ``httpx.post`` được thay bằng hàm giả ghi lại request.
"""

from __future__ import annotations

import logging
import math

import httpx
import pytest

from app.core.config import settings
from app.embeddings import (
    ApiEmbeddingModel,
    EmbeddingAPIError,
    EmbeddingModel,
    EmbeddingNotConfiguredError,
    EmbeddingUnavailableError,
    PaddedEmbeddingModel,
    api_clients,
    create_embedding_model,
)
from app.embeddings.api_clients import EmbeddingAPIConfig, build_request, embed_texts
from app.embeddings.embedder import VECTOR_COLUMN_DIM
from app.embeddings.runtime import (
    EmbeddingRuntime,
    RuntimeEmbeddingModel,
    _settings_fingerprint,
)
from app.retrieval.retriever import Retriever

SECRET_KEY = "sk-unit-test-embedding-api-key-0123456789"
SECRET_TEXT = "Nội dung đoạn tài liệu bí mật"


class _FakeHTTP:
    """Thay ``httpx.post``: ghi request, trả lần lượt các response/lỗi trong ``replies``.

    Mỗi phần tử của ``replies`` là exception, ``httpx.Response`` hoặc hàm nhận body trả response.
    Hết danh sách thì lặp lại phần tử cuối.
    """

    def __init__(self, *replies) -> None:
        self.replies = list(replies)
        self.calls: list[dict] = []

    def __call__(self, url, *, json, headers, timeout):
        self.calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        reply = self.replies[min(len(self.calls), len(self.replies)) - 1]
        if isinstance(reply, BaseException):
            raise reply
        if callable(reply):
            return reply(json)
        return reply


def _openai_like(body: dict, dim: int = 4) -> httpx.Response:
    texts = body["input"]
    # Trả ngược thứ tự kèm index để kiểm sắp xếp lại.
    data = [{"index": i, "embedding": [float(i + 1)] * dim} for i in range(len(texts))][::-1]
    return httpx.Response(200, json={"data": data})


def _cohere_like(body: dict, dim: int = 4) -> httpx.Response:
    return httpx.Response(200, json={"embeddings": {"float": [[float(i + 1)] * dim for i in range(len(body["texts"]))]}})


def _gemini_like(body: dict, dim: int = 4) -> httpx.Response:
    return httpx.Response(200, json={"embeddings": [{"values": [float(i + 1)] * dim} for i in range(len(body["requests"]))]})


@pytest.fixture
def fake_http(monkeypatch):
    def install(*replies) -> _FakeHTTP:
        fake = _FakeHTTP(*replies)
        monkeypatch.setattr(api_clients.httpx, "post", fake)
        return fake

    return install


@pytest.fixture
def sleeps(monkeypatch) -> list[float]:
    recorded: list[float] = []
    monkeypatch.setattr(api_clients, "_sleep", recorded.append)
    return recorded


@pytest.fixture(autouse=True)
def _embedding_settings(monkeypatch):
    for field, value in (
        ("embedding_provider", "voyage"),
        ("embedding_model", "voyage-3.5"),
        ("embedding_api_key", SECRET_KEY),
        ("embedding_base_url", None),
        ("embedding_dimension", 1024),
        ("vector_dim", VECTOR_COLUMN_DIM),
        ("llm_base_url_allowlist", ""),
    ):
        monkeypatch.setattr(settings, field, value)


# ==========================================
# Định dạng request (AC-02)
# ==========================================
@pytest.mark.parametrize(
    ("input_type", "expected"),
    [("query", "query"), ("document", "document")],
)
def test_voyage_request(input_type, expected) -> None:
    config = EmbeddingAPIConfig("voyage", "voyage-3.5", SECRET_KEY, dimension=1024)
    url, headers, body = build_request(config, ["a", "b"], input_type)
    assert url == "https://api.voyageai.com/v1/embeddings"
    assert headers["Authorization"] == f"Bearer {SECRET_KEY}"
    assert body == {"model": "voyage-3.5", "input": ["a", "b"], "input_type": expected, "output_dimension": 1024}


def test_voyage_fixed_dimension_model_omits_output_dimension() -> None:
    config = EmbeddingAPIConfig("voyage", "voyage-multilingual-2", SECRET_KEY, dimension=1024)
    _, _, body = build_request(config, ["a"], "document")
    assert "output_dimension" not in body


@pytest.mark.parametrize(
    ("model", "input_type", "expected_type", "sends_dimension"),
    [
        ("embed-v4.0", "query", "search_query", True),
        ("embed-multilingual-v3.0", "document", "search_document", False),
    ],
)
def test_cohere_request(model, input_type, expected_type, sends_dimension) -> None:
    config = EmbeddingAPIConfig("cohere", model, SECRET_KEY, dimension=1024)
    url, headers, body = build_request(config, ["a"], input_type)
    assert url == "https://api.cohere.com/v2/embed"
    assert headers["Authorization"] == f"Bearer {SECRET_KEY}"
    assert body["texts"] == ["a"]
    assert body["input_type"] == expected_type
    assert body["embedding_types"] == ["float"]
    assert ("output_dimension" in body) is sends_dimension


def test_gemini_request_uses_header_key_and_task_type() -> None:
    config = EmbeddingAPIConfig("gemini", "models/gemini-embedding-001", SECRET_KEY, dimension=1536)
    url, headers, body = build_request(config, ["a", "b"], "query")
    assert url == "https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:batchEmbedContents"
    assert headers["x-goog-api-key"] == SECRET_KEY
    assert "Authorization" not in headers
    assert body["requests"][1] == {
        "model": "models/gemini-embedding-001",
        "taskType": "RETRIEVAL_QUERY",
        "outputDimensionality": 1536,
        "content": {"parts": [{"text": "b"}]},
    }
    _, _, document_body = build_request(config, ["a"], "document")
    assert document_body["requests"][0]["taskType"] == "RETRIEVAL_DOCUMENT"


def test_gemini_model_name_cannot_change_path() -> None:
    config = EmbeddingAPIConfig("gemini", "../../other", SECRET_KEY)
    url, _, _ = build_request(config, ["a"], "query")
    assert url.startswith("https://generativelanguage.googleapis.com/v1beta/models/")
    assert "/../" not in url


def test_jina_v3_sends_task_and_dimensions_v2_does_not() -> None:
    v3 = EmbeddingAPIConfig("jina", "jina-embeddings-v3", SECRET_KEY, dimension=1024)
    url, _, body = build_request(v3, ["a"], "query")
    assert url == "https://api.jina.ai/v1/embeddings"
    assert body == {"model": "jina-embeddings-v3", "input": ["a"], "task": "retrieval.query", "dimensions": 1024}
    _, _, passage = build_request(v3, ["a"], "document")
    assert passage["task"] == "retrieval.passage"

    v2 = EmbeddingAPIConfig("jina", "jina-embeddings-v2-base-en", SECRET_KEY, dimension=768)
    _, _, body = build_request(v2, ["a"], "query")
    assert body == {"model": "jina-embeddings-v2-base-en", "input": ["a"]}


def test_openai_compatible_request_without_key() -> None:
    config = EmbeddingAPIConfig("openai_compatible", "nomic-embed-text", None, "http://localhost:11434/v1/", 768)
    url, headers, body = build_request(config, ["a"], "query")
    assert url == "http://localhost:11434/v1/embeddings"
    assert "Authorization" not in headers
    assert body == {"model": "nomic-embed-text", "input": ["a"]}


# ==========================================
# Đọc response, chia lô (AC-02)
# ==========================================
def test_openai_like_response_is_reordered_by_index(fake_http) -> None:
    fake_http(_openai_like)
    config = EmbeddingAPIConfig("voyage", "voyage-3.5", SECRET_KEY)
    vectors = embed_texts(config, ["a", "b", "c"], input_type="document")
    assert [vector[0] for vector in vectors] == [1.0, 2.0, 3.0]


def test_cohere_batches_keep_order(fake_http) -> None:
    fake = fake_http(_cohere_like)
    texts = [f"đoạn {i}" for i in range(200)]
    vectors = embed_texts(EmbeddingAPIConfig("cohere", "embed-v4.0", SECRET_KEY), texts, input_type="document")
    assert [len(call["json"]["texts"]) for call in fake.calls] == [96, 96, 8]
    assert len(vectors) == 200
    # Mỗi lô đánh số lại từ 1: vector đầu của lô thứ hai là phần tử 96.
    assert vectors[95][0] == 96.0 and vectors[96][0] == 1.0


def test_gemini_response(fake_http) -> None:
    fake_http(_gemini_like)
    vectors = embed_texts(EmbeddingAPIConfig("gemini", "gemini-embedding-001", SECRET_KEY), ["a", "b"], input_type="query")
    assert vectors == [[1.0] * 4, [2.0] * 4]


@pytest.mark.parametrize(
    "payload",
    [
        {"data": [{"index": 0, "embedding": [1.0]}]},  # thiếu một vector
        {"data": [{"index": 0, "embedding": [1.0]}, {"index": 0, "embedding": [2.0]}]},  # trùng index
        {"data": [{"index": 0, "embedding": [1.0]}, {"index": 1, "embedding": ["x"]}]},
        '{"data": [{"index": 0, "embedding": [1.0]}, {"index": 1, "embedding": [NaN]}]}',
        "không phải JSON",
        {"results": []},
        [],
    ],
)
def test_invalid_response_raises(fake_http, payload) -> None:
    response = httpx.Response(200, content=payload.encode()) if isinstance(payload, str) else httpx.Response(200, json=payload)
    fake_http(response)
    with pytest.raises(EmbeddingAPIError) as info:
        embed_texts(EmbeddingAPIConfig("voyage", "voyage-3.5", SECRET_KEY), ["a", "b"], input_type="document")
    assert "sai định dạng" in info.value.reason or "JSON" in info.value.reason


# ==========================================
# Lỗi và thử lại (AC-05)
# ==========================================
def test_document_retries_429_with_retry_after(fake_http, sleeps) -> None:
    fake = fake_http(httpx.Response(429, headers={"Retry-After": "3"}), _openai_like)
    vectors = embed_texts(EmbeddingAPIConfig("voyage", "voyage-3.5", SECRET_KEY), ["a"], input_type="document")
    assert len(vectors) == 1
    assert len(fake.calls) == 2
    assert sleeps == [3.0]
    assert fake.calls[0]["timeout"] == api_clients.DOCUMENT_TIMEOUT_SECONDS


def test_document_gives_up_after_max_attempts(fake_http, sleeps, caplog) -> None:
    fake = fake_http(httpx.Response(503))
    with (
        caplog.at_level(logging.WARNING, logger="app.embeddings.api_clients"),
        pytest.raises(EmbeddingAPIError) as info,
    ):
        embed_texts(EmbeddingAPIConfig("voyage", "voyage-3.5", SECRET_KEY), [SECRET_TEXT], input_type="document")
    assert len(fake.calls) == api_clients.DOCUMENT_MAX_ATTEMPTS
    assert sleeps == [2.0, 4.0, 8.0]
    assert info.value.status_code == 503
    assert "HTTP 503" in info.value.reason and "voyage-3.5" in info.value.reason
    for text in (caplog.text, info.value.reason):
        assert SECRET_KEY not in text
        assert SECRET_TEXT not in text
    assert "api.voyageai.com" in caplog.text


def test_timeout_is_retried(fake_http, sleeps) -> None:
    fake = fake_http(httpx.ReadTimeout("chậm"), _cohere_like)
    embed_texts(EmbeddingAPIConfig("cohere", "embed-v4.0", SECRET_KEY), ["a"], input_type="document")
    assert len(fake.calls) == 2 and len(sleeps) == 1


def test_client_error_is_not_retried(fake_http, sleeps) -> None:
    fake = fake_http(httpx.Response(401, json={"message": f"invalid key {SECRET_KEY}"}))
    with pytest.raises(EmbeddingAPIError) as info:
        embed_texts(EmbeddingAPIConfig("voyage", "voyage-3.5", SECRET_KEY), ["a"], input_type="document")
    assert len(fake.calls) == 1 and sleeps == []
    assert info.value.status_code == 401
    assert SECRET_KEY not in info.value.reason


def test_query_is_not_retried_and_uses_short_timeout(fake_http, sleeps) -> None:
    fake = fake_http(httpx.Response(429))
    with pytest.raises(EmbeddingAPIError):
        embed_texts(EmbeddingAPIConfig("voyage", "voyage-3.5", SECRET_KEY), ["a"], input_type="query")
    assert len(fake.calls) == 1 and sleeps == []
    assert fake.calls[0]["timeout"] == api_clients.QUERY_TIMEOUT_SECONDS


def test_api_error_is_embedding_unavailable_for_existing_503_handlers() -> None:
    assert issubclass(EmbeddingAPIError, EmbeddingUnavailableError)


# ==========================================
# Cấu hình (D-03, D-04)
# ==========================================
@pytest.mark.parametrize("provider", ["voyage", "cohere", "gemini", "jina"])
def test_vendor_provider_requires_key(monkeypatch, provider) -> None:
    monkeypatch.setattr(settings, "embedding_provider", provider)
    monkeypatch.setattr(settings, "embedding_api_key", None)
    monkeypatch.setattr(settings, "openai_api_key", "sk-env-openai-key")
    with pytest.raises(EmbeddingNotConfiguredError) as info:
        create_embedding_model()
    assert "API key" in info.value.reason


def test_openai_compatible_requires_allowed_base_url(monkeypatch, fake_http) -> None:
    fake = fake_http(_openai_like)
    monkeypatch.setattr(settings, "embedding_provider", "openai_compatible")
    monkeypatch.setattr(settings, "embedding_model", "nomic-embed-text")
    monkeypatch.setattr(settings, "embedding_api_key", None)

    with pytest.raises(EmbeddingNotConfiguredError):
        create_embedding_model()

    monkeypatch.setattr(settings, "embedding_base_url", "http://10.0.0.5:11434/v1")
    with pytest.raises(EmbeddingUnavailableError) as info:
        create_embedding_model()
    assert "LLM_BASE_URL_ALLOWLIST" in info.value.reason

    monkeypatch.setattr(settings, "llm_base_url_allowlist", "http://10.0.0.5:11434")
    model = create_embedding_model()
    model.embed(["a"])
    assert fake.calls[0]["url"] == "http://10.0.0.5:11434/v1/embeddings"

    # Allowlist bị thu hẹp sau khi đã tạo mô hình: lần gọi sau bị chặn, không gửi request.
    monkeypatch.setattr(settings, "llm_base_url_allowlist", "https://api.openai.com")
    with pytest.raises(EmbeddingUnavailableError):
        model.embed(["b"])
    assert len(fake.calls) == 1


# ==========================================
# Số chiều và câu hỏi/tài liệu (AC-03, AC-04)
# ==========================================
def test_smaller_model_is_padded_to_vector_dim(fake_http) -> None:
    fake = fake_http(lambda body: _openai_like(body, dim=1024))
    model = create_embedding_model()
    assert isinstance(model, PaddedEmbeddingModel)
    assert model.distinguishes_queries is True

    [document] = model.embed([SECRET_TEXT])
    [query] = model.embed_query(["Học phí?"])
    assert len(document) == len(query) == VECTOR_COLUMN_DIM
    assert document[:1024] == [1.0] * 1024 and document[1024:] == [0.0] * (VECTOR_COLUMN_DIM - 1024)
    assert [call["json"]["input_type"] for call in fake.calls] == ["document", "query"]
    assert all(call["json"]["output_dimension"] == 1024 for call in fake.calls)


def test_padding_keeps_cosine_similarity() -> None:
    class _Fixed(EmbeddingModel):
        def embed(self, texts):
            return [[1.0, 2.0, 3.0], [3.0, -1.0, 0.5]]

    def cosine(a, b):
        dot = sum(x * y for x, y in zip(a, b))
        return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))

    raw = _Fixed().embed([])
    padded = PaddedEmbeddingModel(_Fixed(), 3, 8).embed([])
    assert all(len(vector) == 8 for vector in padded)
    assert cosine(*padded) == pytest.approx(cosine(*raw))


def test_wrong_dimension_from_api_marks_runtime_error(fake_http) -> None:
    fake_http(lambda body: _openai_like(body, dim=768))
    runtime = EmbeddingRuntime()
    proxy = RuntimeEmbeddingModel(runtime)
    with pytest.raises(EmbeddingUnavailableError) as info:
        proxy.embed(["a"])
    assert "768" in info.value.reason
    assert runtime.status()["state"] == "error"


def test_api_error_does_not_mark_runtime_error(fake_http, sleeps) -> None:
    fake_http(httpx.Response(500))
    runtime = EmbeddingRuntime()
    proxy = RuntimeEmbeddingModel(runtime)
    with pytest.raises(EmbeddingAPIError):
        proxy.embed_query(["a"])
    assert runtime.status()["state"] == "ready"


def test_dimension_above_vector_dim_is_rejected(monkeypatch) -> None:
    monkeypatch.setattr(settings, "embedding_dimension", VECTOR_COLUMN_DIM + 512)
    with pytest.raises(EmbeddingUnavailableError) as info:
        create_embedding_model()
    assert f"VECTOR_DIM={VECTOR_COLUMN_DIM}" in info.value.reason


def test_retriever_embeds_question_as_query() -> None:
    class _Recording(EmbeddingModel):
        def __init__(self) -> None:
            self.calls: list[str] = []

        def embed(self, texts):
            self.calls.append("document")
            return [[0.0] * VECTOR_COLUMN_DIM for _ in texts]

        def embed_query(self, texts):
            self.calls.append("query")
            return [[0.0] * VECTOR_COLUMN_DIM for _ in texts]

    class _Empty:
        def search(self, *args, **kwargs):
            return []

    model = _Recording()
    Retriever(embedding_model=model, vector_store=_Empty(), keyword_search=_Empty()).retrieve("Học phí?")
    assert model.calls == ["query"]


def test_fingerprint_tracks_key_base_url_and_dimension(monkeypatch) -> None:
    first = _settings_fingerprint()
    assert SECRET_KEY not in repr(first)
    monkeypatch.setattr(settings, "embedding_api_key", "sk-another-key")
    second = _settings_fingerprint()
    monkeypatch.setattr(settings, "embedding_dimension", 512)
    third = _settings_fingerprint()
    monkeypatch.setattr(settings, "embedding_base_url", "http://localhost:8080/v1")
    fourth = _settings_fingerprint()
    assert len({first, second, third, fourth}) == 4


def test_api_model_exposes_name_for_eval_cache() -> None:
    model = ApiEmbeddingModel("jina", " jina-embeddings-v3 ", SECRET_KEY, dimensions=1024)
    assert model.model_name == "jina-embeddings-v3"
    assert ApiEmbeddingModel("openai_compatible", "m", None, "https://api.openai.com/v1").distinguishes_queries is False
