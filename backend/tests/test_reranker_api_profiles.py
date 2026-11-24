"""Profile reranker của từng hãng (Cohere, Jina, Voyage, Pinecone) và HF TEI (task reranker-api-providers).

- AC-01: hãng có URL cố định bắt buộc khoá, không lưu Base URL; TEI bắt buộc Base URL qua allowlist,
  khoá tuỳ chọn; khoá mã hoá, không trả về client; đổi hãng không mang khoá cũ.
- AC-03: POST /model-profiles/test-reranker cho mọi provider API; khoá profile chỉ dùng khi cùng hãng.

Không gọi mạng thật: ``call_rerank_api`` của routes được thay bằng hàm giả.
"""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet

from app.api import routes
from app.core.config import settings
from app.db.models import ModelProfile

TEST_API_KEY = "co-unit-test-rerank-key-0123456789"
TEI_URL = "http://tei.local:8080"
VENDORS = ["cohere", "jina", "voyage", "pinecone"]


@pytest.fixture(autouse=True)
def _restore_settings(monkeypatch):
    snapshot = settings.model_dump()
    monkeypatch.setattr(settings, "config_encryption_key", Fernet.generate_key().decode())
    # Không có host của hãng: URL cố định không phụ thuộc allowlist.
    monkeypatch.setattr(settings, "llm_base_url_allowlist", TEI_URL)
    yield
    for field, value in snapshot.items():
        setattr(settings, field, value)


def _post(client, **body):
    return client.post("/api/model-profiles", json={"kind": "reranker", **body})


def _create(client, **body) -> dict:
    response = _post(client, **body)
    assert response.status_code == 201, response.text
    return next(p for p in response.json()["profiles"] if p["name"] == body["name"])


def _activate(client, profile_id):
    return client.post("/api/model-profiles/activate", json={"kind": "reranker", "profile_id": profile_id})


def _rows(session_factory):
    with session_factory() as session:
        return list(session.query(ModelProfile))


def _fake_rerank_api(monkeypatch) -> dict:
    captured: dict = {}

    def fake(**kwargs):
        captured.update(kwargs)
        return [(0, 0.98), (1, 0.02)]

    monkeypatch.setattr(routes, "call_rerank_api", fake)
    return captured


# ==========================================
# Lưu và chọn profile (AC-01)
# ==========================================
@pytest.mark.parametrize("provider", VENDORS)
def test_vendor_profile_requires_key_drops_base_url_and_hides_key(admin_client, config_store_db, provider) -> None:
    body = {"name": provider, "provider": provider, "model": "rerank-m", "base_url": "https://evil.example.com/v1"}
    response = _post(admin_client, **body)
    assert response.status_code == 422
    assert "API key" in response.json()["detail"]

    response = _post(admin_client, **body, api_key=TEST_API_KEY)
    assert response.status_code == 201, response.text
    assert TEST_API_KEY not in response.text
    profile = next(p for p in response.json()["profiles"] if p["name"] == provider)
    assert profile["has_api_key"] is True
    assert profile["base_url"] is None
    [row] = _rows(config_store_db)
    assert row.encrypted_api_key and TEST_API_KEY not in row.encrypted_api_key

    assert _activate(admin_client, profile["id"]).status_code == 200
    assert (settings.reranker_provider, settings.reranker_model) == (provider, "rerank-m")
    assert settings.reranker_base_url is None
    assert settings.reranker_api_key == TEST_API_KEY


def test_vendor_profile_requires_model(admin_client, config_store_db) -> None:
    response = _post(admin_client, name="x", provider="cohere", api_key=TEST_API_KEY)
    assert response.status_code == 422


def test_tei_profile_needs_allowed_base_url_and_optional_key(admin_client, config_store_db) -> None:
    base = {"name": "TEI", "provider": "tei", "model": "BAAI/bge-reranker-v2-m3"}
    assert _post(admin_client, **base).status_code == 422  # thiếu Base URL
    response = _post(admin_client, **base, base_url="http://10.0.0.5:8080")
    assert response.status_code == 422
    assert "LLM_BASE_URL_ALLOWLIST" in response.json()["detail"]

    profile = _create(admin_client, **base, base_url=TEI_URL)
    assert profile["base_url"] == TEI_URL and profile["has_api_key"] is False
    assert _activate(admin_client, profile["id"]).status_code == 200
    assert settings.reranker_provider == "tei"
    assert settings.reranker_base_url == TEI_URL
    assert settings.reranker_api_key is None


def test_switching_vendor_does_not_carry_key(admin_client, config_store_db) -> None:
    profile = _create(admin_client, name="R", provider="cohere", model="rerank-v3.5", api_key=TEST_API_KEY)
    url = f"/api/model-profiles/{profile['id']}"

    # Giữ khoá khi không đổi hãng.
    response = admin_client.put(url, json={"name": "R", "provider": "cohere", "model": "rerank-v5.0-pro"})
    assert response.status_code == 200, response.text
    assert _rows(config_store_db)[0].encrypted_api_key

    # Khoá Cohere không được mang sang Voyage.
    response = admin_client.put(url, json={"name": "R", "provider": "voyage", "model": "rerank-2.5"})
    assert response.status_code == 422
    assert _rows(config_store_db)[0].provider == "cohere"

    # Sang TEI (khoá tuỳ chọn): khoá cũ bị xoá.
    response = admin_client.put(url, json={"name": "R", "provider": "tei", "model": "bge", "base_url": TEI_URL})
    assert response.status_code == 200, response.text
    assert _rows(config_store_db)[0].encrypted_api_key is None


# ==========================================
# Kiểm tra kết nối (AC-03)
# ==========================================
@pytest.mark.parametrize("provider", VENDORS)
def test_test_vendor_ignores_base_url_and_uses_stored_key(admin_client, config_store_db, monkeypatch, provider) -> None:
    profile = _create(admin_client, name="R", provider=provider, model="rerank-m", api_key=TEST_API_KEY)
    captured = _fake_rerank_api(monkeypatch)
    body = {
        "provider": provider,
        "model": "rerank-m",
        "base_url": "https://evil.example.com/v1",
        "profile_id": profile["id"],
    }

    response = admin_client.post("/api/model-profiles/test-reranker", json=body)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["success"] is True
    assert TEST_API_KEY not in response.text
    assert captured["provider"] == provider
    assert captured["base_url"] is None
    assert captured["api_key"] == TEST_API_KEY


def test_test_vendor_never_uses_key_of_other_provider(admin_client, config_store_db, monkeypatch) -> None:
    cohere = _create(admin_client, name="C", provider="cohere", model="rerank-v3.5", api_key=TEST_API_KEY)
    captured = _fake_rerank_api(monkeypatch)
    response = admin_client.post(
        "/api/model-profiles/test-reranker",
        json={"provider": "voyage", "model": "rerank-2.5", "profile_id": cohere["id"]},
    )
    assert response.status_code == 422
    assert "API key" in response.json()["detail"]
    assert captured == {}

    response = admin_client.post(
        "/api/model-profiles/test-reranker",
        json={"provider": "voyage", "model": "rerank-2.5", "profile_id": cohere["id"], "api_key": "pa-typed"},
    )
    assert response.status_code == 200
    assert captured["api_key"] == "pa-typed"


def test_test_tei_without_key(admin_client, config_store_db, monkeypatch) -> None:
    captured = _fake_rerank_api(monkeypatch)
    response = admin_client.post(
        "/api/model-profiles/test-reranker",
        json={"provider": "tei", "model": "bge", "base_url": TEI_URL},
    )
    assert response.status_code == 200, response.text
    assert "HF TEI" in response.json()["message"]
    assert captured["base_url"] == TEI_URL and captured["api_key"] is None

    for body in (
        {"provider": "tei", "model": "bge"},
        {"provider": "tei", "model": "bge", "base_url": "http://169.254.169.254/latest"},
    ):
        assert admin_client.post("/api/model-profiles/test-reranker", json=body).status_code == 422
