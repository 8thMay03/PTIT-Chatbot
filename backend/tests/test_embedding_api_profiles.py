"""Profile embedding qua API trong kho mô hình và kiểm tra kết nối (task embedding-api-providers).

- AC-01: tạo/sửa profile Voyage/Cohere/Gemini/Jina (khoá bắt buộc) và tương thích OpenAI
  (Base URL qua allowlist, khoá tuỳ chọn); khoá mã hoá, không trả về client.
- AC-04: chọn dùng được profile ít chiều hơn VECTOR_DIM; nhiều hơn thì 422.
- AC-06: áp profile đặt đủ provider/model/khoá/Base URL/số chiều; sửa số chiều cần khởi động lại.
- AC-07: POST /model-profiles/test-embedding.

Không gọi mạng thật: ``httpx.post`` của ``app.embeddings.api_clients`` được thay bằng hàm giả.
"""

from __future__ import annotations

import httpx
import pytest
from cryptography.fernet import Fernet

from app.core import model_profiles
from app.core.config import settings
from app.db.models import AppConfigOverride, ModelProfile
from app.embeddings import EmbeddingModel, api_clients, embedding_runtime
from app.ingestion.pipeline import ingestion_pipeline
from app.retrieval.retriever import retriever

TEST_API_KEY = "pa-unit-test-voyage-key-0123456789"
LOCAL_URL = "http://localhost:11434/v1"


@pytest.fixture(autouse=True)
def _restore_settings(monkeypatch):
    snapshot = settings.model_dump()
    monkeypatch.setattr(retriever, "embedding_model", retriever.embedding_model)
    monkeypatch.setattr(ingestion_pipeline, "embedding_model", ingestion_pipeline.embedding_model)
    monkeypatch.setattr(settings, "config_encryption_key", Fernet.generate_key().decode())
    monkeypatch.setattr(settings, "llm_base_url_allowlist", "http://localhost:11434")
    yield
    for field, value in snapshot.items():
        setattr(settings, field, value)


@pytest.fixture
def fake_http(monkeypatch):
    """Dịch vụ embedding giả: trả vector ``dim`` chiều hoặc HTTP ``status``; ghi request."""

    class _Fake:
        dim = 1024
        status = 200
        def __init__(self) -> None:
            self.calls: list[dict] = []

        def __call__(self, url, *, json, headers, timeout):
            self.calls.append({"url": url, "json": json, "headers": headers})
            if self.status != 200:
                return httpx.Response(self.status)
            if "texts" in json:  # Cohere
                return httpx.Response(200, json={"embeddings": {"float": [[0.5] * self.dim for _ in json["texts"]]}})
            data = [{"index": i, "embedding": [0.5] * self.dim} for i in range(len(json["input"]))]
            return httpx.Response(200, json={"data": data})

    fake = _Fake()
    monkeypatch.setattr(api_clients.httpx, "post", fake)
    return fake


def _post(client, **body):
    return client.post("/api/model-profiles", json={"kind": "embedding", **body})


def _create(client, **body) -> dict:
    response = _post(client, **body)
    assert response.status_code == 201, response.text
    return next(p for p in response.json()["profiles"] if p["name"] == body["name"])


def _voyage(client, **extra) -> dict:
    body = {"name": "Voyage", "provider": "voyage", "model": "voyage-3.5", "dimension": 1024, "api_key": TEST_API_KEY}
    return _create(client, **{**body, **extra})


def _activate(client, profile_id):
    return client.post("/api/model-profiles/activate", json={"kind": "embedding", "profile_id": profile_id})


def _rows(session_factory, model):
    with session_factory() as session:
        return list(session.query(model))


# ==========================================
# Lưu profile (AC-01)
# ==========================================
@pytest.mark.parametrize("provider", ["voyage", "cohere", "gemini", "jina"])
def test_vendor_profile_requires_key_and_hides_it(admin_client, config_store_db, provider) -> None:
    body = {"name": provider, "provider": provider, "model": "m", "dimension": 1024}
    response = _post(admin_client, **body)
    assert response.status_code == 422
    assert "API key" in response.json()["detail"]

    response = _post(admin_client, **body, api_key=TEST_API_KEY)
    assert response.status_code == 201, response.text
    assert TEST_API_KEY not in response.text
    profile = next(p for p in response.json()["profiles"] if p["name"] == provider)
    assert profile["has_api_key"] is True
    [row] = _rows(config_store_db, ModelProfile)
    assert row.encrypted_api_key and TEST_API_KEY not in row.encrypted_api_key


def test_openai_compatible_profile(admin_client, config_store_db) -> None:
    base = {"name": "Ollama", "provider": "openai_compatible", "model": "nomic-embed-text", "dimension": 768}
    assert _post(admin_client, **base).status_code == 422  # thiếu Base URL
    response = _post(admin_client, **base, base_url="http://10.0.0.5:11434/v1")
    assert response.status_code == 422
    assert "LLM_BASE_URL_ALLOWLIST" in response.json()["detail"]

    profile = _create(admin_client, **base, base_url=LOCAL_URL)
    assert profile["base_url"] == LOCAL_URL
    assert profile["has_api_key"] is False


def test_update_keeps_key_and_provider_change_clears_it(admin_client, config_store_db) -> None:
    profile = _voyage(admin_client)
    url = f"/api/model-profiles/{profile['id']}"

    response = admin_client.put(url, json={"name": "Voyage", "provider": "voyage", "model": "voyage-3-large", "dimension": 1024})
    assert response.status_code == 200, response.text
    assert _rows(config_store_db, ModelProfile)[0].encrypted_api_key

    # Khoá Voyage không được mang sang Cohere: đổi hãng mà không nhập khoá mới thì bị từ chối.
    response = admin_client.put(url, json={"name": "Voyage", "provider": "cohere", "model": "embed-v4.0", "dimension": 1536})
    assert response.status_code == 422
    assert _rows(config_store_db, ModelProfile)[0].provider == "voyage"

    response = admin_client.put(
        url, json={"name": "Voyage", "provider": "sentence-transformers", "model": "BAAI/bge-m3", "dimension": 1024}
    )
    assert response.status_code == 200, response.text
    assert _rows(config_store_db, ModelProfile)[0].encrypted_api_key is None


# ==========================================
# Chọn dùng và áp profile (AC-04, AC-06)
# ==========================================
def test_smaller_dimension_can_be_selected_larger_cannot(admin_client, config_store_db) -> None:
    small = _voyage(admin_client)
    large = _voyage(admin_client, name="Voyage 2048", dimension=settings.vector_dim + 512)

    response = _activate(admin_client, large["id"])
    assert response.status_code == 422
    assert "VECTOR_DIM" in response.json()["detail"]

    response = _activate(admin_client, small["id"])
    assert response.status_code == 200, response.text
    assert settings.embedding_profile_id == small["id"]


def test_load_selected_embedding_applies_all_fields(admin_client, config_store_db, monkeypatch) -> None:
    profile = _create(
        admin_client,
        name="Ollama",
        provider="openai_compatible",
        model="nomic-embed-text",
        dimension=768,
        base_url=LOCAL_URL,
        api_key="local-key",
    )
    assert _activate(admin_client, profile["id"]).status_code == 200
    seen = {}

    class _Fake(EmbeddingModel):
        def embed(self, texts):
            return [[0.0] * settings.vector_dim for _ in texts]

    def factory():
        seen.update(
            provider=settings.embedding_provider,
            model=settings.embedding_model,
            key=settings.embedding_api_key,
            base_url=settings.embedding_base_url,
            dimension=settings.embedding_dimension,
        )
        return _Fake()

    monkeypatch.setattr("app.embeddings.create_embedding_model", factory)
    embedding_runtime.reset()
    model_profiles.load_selected_embedding_at_startup()

    assert seen == {
        "provider": "openai_compatible",
        "model": "nomic-embed-text",
        "key": "local-key",
        "base_url": LOCAL_URL,
        "dimension": 768,
    }
    registry = admin_client.get("/api/model-profiles").json()
    assert registry["embedding_runtime"]["profile_id"] == profile["id"]
    assert registry["embedding_runtime"]["restart_required"] is False

    # Đổi số chiều của profile đang chạy → tạo lại embedder ngay (D-01 reembed-documents).
    response = admin_client.put(
        f"/api/model-profiles/{profile['id']}",
        json={"name": "Ollama", "provider": "openai_compatible", "model": "nomic-embed-text", "dimension": 512,
              "base_url": LOCAL_URL},
    )
    assert response.status_code == 200, response.text
    assert seen["dimension"] == 512
    assert admin_client.get("/api/model-profiles").json()["embedding_runtime"]["restart_required"] is False


def test_load_failure_restores_previous_settings(admin_client, config_store_db, monkeypatch) -> None:
    from app.embeddings import EmbeddingUnavailableError

    profile = _voyage(admin_client)
    _activate(admin_client, profile["id"])
    before = tuple(getattr(settings, field) for field in model_profiles._EMBEDDING_SETTINGS_FIELDS)

    def broken():
        raise EmbeddingUnavailableError("Không dùng được.")

    monkeypatch.setattr("app.embeddings.create_embedding_model", broken)
    model_profiles.load_selected_embedding_at_startup()
    assert tuple(getattr(settings, field) for field in model_profiles._EMBEDDING_SETTINGS_FIELDS) == before


# ==========================================
# Kiểm tra kết nối (AC-07)
# ==========================================
def test_test_embedding_requires_admin(client) -> None:
    assert client.post("/api/model-profiles/test-embedding", json={"provider": "voyage"}).status_code == 401


def test_test_embedding_uses_stored_key_and_saves_nothing(admin_client, config_store_db, fake_http) -> None:
    profile = _voyage(admin_client)
    before_profiles = [(r.id, r.encrypted_api_key) for r in _rows(config_store_db, ModelProfile)]
    before_overrides = [(r.key, r.value) for r in _rows(config_store_db, AppConfigOverride)]
    body = {"provider": "voyage", "model": "voyage-3.5", "dimension": 1024, "profile_id": profile["id"]}

    response = admin_client.post("/api/model-profiles/test-embedding", json=body)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["success"] is True, data
    assert "1024 chiều" in data["sample_output"] and "đệm 0" in data["sample_output"]
    assert TEST_API_KEY not in response.text
    call = fake_http.calls[-1]
    assert call["url"] == "https://api.voyageai.com/v1/embeddings"
    assert call["headers"]["Authorization"] == f"Bearer {TEST_API_KEY}"
    assert call["json"]["input_type"] == "query"

    admin_client.post("/api/model-profiles/test-embedding", json={**body, "api_key": "pa-typed"})
    assert fake_http.calls[-1]["headers"]["Authorization"] == "Bearer pa-typed"

    assert [(r.id, r.encrypted_api_key) for r in _rows(config_store_db, ModelProfile)] == before_profiles
    assert [(r.key, r.value) for r in _rows(config_store_db, AppConfigOverride)] == before_overrides


def test_test_embedding_does_not_send_key_of_other_provider(admin_client, config_store_db, fake_http) -> None:
    profile = _voyage(admin_client)
    response = admin_client.post(
        "/api/model-profiles/test-embedding",
        json={"provider": "jina", "model": "jina-embeddings-v3", "dimension": 1024, "profile_id": profile["id"]},
    )
    assert response.status_code == 422
    assert fake_http.calls == []


def test_test_embedding_reports_dimension_mismatch_and_http_errors(admin_client, config_store_db, fake_http) -> None:
    body = {"provider": "cohere", "model": "embed-v4.0", "dimension": 1536, "api_key": TEST_API_KEY}
    fake_http.dim = 1024
    data = admin_client.post("/api/model-profiles/test-embedding", json=body).json()
    assert data["success"] is False
    assert "1024" in data["message"] and "1536" in data["message"]

    fake_http.status = 401
    data = admin_client.post("/api/model-profiles/test-embedding", json=body).json()
    assert data["success"] is False
    assert "HTTP 401" in data["message"] and "API key" in data["message"]
    assert TEST_API_KEY not in data["message"]


@pytest.mark.parametrize(
    "body",
    [
        {"provider": "sentence-transformers", "model": "BAAI/bge-m3"},
        {"provider": "voyage", "api_key": TEST_API_KEY},
        {"provider": "openai_compatible", "model": "m"},
        {"provider": "openai_compatible", "model": "m", "base_url": "https://evil.example.com/v1"},
    ],
)
def test_test_embedding_rejects_invalid_request(admin_client, config_store_db, fake_http, body) -> None:
    response = admin_client.post("/api/model-profiles/test-embedding", json=body)
    assert response.status_code == 422
    assert fake_http.calls == []


def test_test_embedding_openai_compatible_without_key(admin_client, config_store_db, fake_http) -> None:
    fake_http.dim = 768
    response = admin_client.post(
        "/api/model-profiles/test-embedding",
        json={"provider": "openai_compatible", "model": "nomic-embed-text", "base_url": LOCAL_URL, "dimension": 768},
    )
    data = response.json()
    assert data["success"] is True, data
    assert "Authorization" not in fake_http.calls[-1]["headers"]
