"""Kho mô hình LLM / embedding / reranker và chọn mô hình đang dùng (model-registry).

- CRUD profile; API key chỉ lưu dạng bản mã, response chỉ có `has_api_key`.
- Chọn profile LLM/reranker có hiệu lực ngay, còn sau restart; sửa profile đang dùng
  thì áp lại; không xoá được profile đang dùng.
- Embedding: chọn chỉ lưu lựa chọn; áp lúc khởi động; số chiều không lớn hơn VECTOR_DIM.
  Embedder chưa chạy được thì áp ngay: tests/test_safe_embedding_startup.py.

Bảng chạy trên SQLite tạm (fixture ``config_store_db`` trong conftest).
"""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import select

from app.api import routes
from app.core import config_store, model_profiles
from app.core.config import _INITIAL_SETTINGS, settings
from app.db.models import AppConfigOverride, ModelProfile
from app.embeddings import (
    EmbeddingUnavailableError,
    embedding_runtime,
    runtime_embedding_model,
)
from app.embeddings.models import EmbeddingModel
from app.ingestion import ingestion_pipeline
from app.retrieval.retriever import retriever

TEST_API_KEY = "sk-unit-test-profile-key-0123456789"


@pytest.fixture(autouse=True)
def _restore_settings(monkeypatch):
    snapshot = settings.model_dump()
    monkeypatch.setattr(retriever, "embedding_model", retriever.embedding_model)
    monkeypatch.setattr(ingestion_pipeline, "embedding_model", ingestion_pipeline.embedding_model)
    yield
    for field, value in snapshot.items():
        setattr(settings, field, value)


@pytest.fixture
def encryption_key(monkeypatch) -> str:
    key = Fernet.generate_key().decode()
    monkeypatch.setattr(settings, "config_encryption_key", key)
    return key


@pytest.fixture
def no_encryption_key(monkeypatch) -> None:
    monkeypatch.setattr(settings, "config_encryption_key", None)


def _create(client, **body) -> dict:
    response = client.post("/api/model-profiles", json=body)
    assert response.status_code == 201, response.text
    data = response.json()
    return next(p for p in data["profiles"] if p["kind"] == body["kind"] and p["name"] == body["name"])


def _openai_llm(client, name="GPT mini", **extra) -> dict:
    body = {"kind": "llm", "name": name, "provider": "openai", "model": "gpt-unit-test-mini", **extra}
    return _create(client, **body)


def _activate(client, kind, profile_id):
    return client.post("/api/model-profiles/activate", json={"kind": kind, "profile_id": profile_id})


def _rows(session_factory, model):
    with session_factory() as session:
        return list(session.scalars(select(model)))


# ==========================================
# Quyền
# ==========================================
def test_model_profile_routes_require_admin(client) -> None:
    assert client.get("/api/model-profiles").status_code == 401
    assert client.post("/api/model-profiles", json={}).status_code == 401
    assert client.post("/api/model-profiles/activate", json={"kind": "llm"}).status_code == 401
    assert client.put("/api/model-profiles/x", json={}).status_code == 401
    assert client.delete("/api/model-profiles/x").status_code == 401
    assert client.post("/api/model-profiles/test-llm", json={"provider": "openai"}).status_code == 401


# ==========================================
# Tạo / sửa / xoá
# ==========================================
def test_create_profile_encrypts_key_and_never_returns_it(admin_client, config_store_db, encryption_key) -> None:
    response = admin_client.post(
        "/api/model-profiles",
        json={
            "kind": "llm",
            "name": "  GPT mini  ",
            "provider": "openai",
            "model": "gpt-unit-test-mini",
            "base_url": "https://api.openai.com/v1",
            # Trường không thuộc OpenAI bị bỏ khi lưu.
            "deployment_name": "bo-qua",
            "api_key": TEST_API_KEY,
        },
    )
    assert response.status_code == 201, response.text
    assert TEST_API_KEY not in response.text
    profile = response.json()["profiles"][0]
    assert profile["name"] == "GPT mini"
    assert profile["has_api_key"] is True
    assert profile["base_url"] == "https://api.openai.com/v1"
    assert profile["deployment_name"] is None

    [row] = _rows(config_store_db, ModelProfile)
    assert row.encrypted_api_key and TEST_API_KEY not in row.encrypted_api_key
    assert "deployment_name" not in row.params
    assert TEST_API_KEY not in admin_client.get("/api/model-profiles").text


def test_create_profile_with_key_without_encryption_key_is_rejected(
    admin_client, config_store_db, no_encryption_key
) -> None:
    response = admin_client.post(
        "/api/model-profiles",
        json={"kind": "llm", "name": "x", "provider": "openai", "model": "m", "api_key": TEST_API_KEY},
    )
    assert response.status_code == 422
    assert "CONFIG_ENCRYPTION_KEY" in response.json()["detail"]
    assert _rows(config_store_db, ModelProfile) == []

    # Không có khoá thì vẫn tạo được (dùng khoá .env khi chạy).
    assert _openai_llm(admin_client)["has_api_key"] is False


@pytest.mark.parametrize(
    ("body", "status"),
    [
        ({"kind": "llm", "name": "x", "provider": "openai"}, 422),  # thiếu model
        ({"kind": "llm", "name": " ", "provider": "openai", "model": "m"}, 422),
        ({"kind": "llm", "name": "x", "provider": "anthropic", "model": "m"}, 422),
        ({"kind": "reranker", "name": "x", "provider": "heuristic", "model": "m"}, 422),
        ({"kind": "llm", "name": "x", "provider": "azure", "endpoint": "https://a.openai.azure.com"}, 422),
        ({"kind": "embedding", "name": "x", "provider": "openai", "model": "m"}, 422),  # thiếu dimension
        ({"kind": "embedding", "name": "x", "provider": "openai", "model": "m", "dimension": 0}, 422),
        ({"kind": "reranker", "name": "x", "provider": "cross-encoder", "model": "m", "api_key": "k"}, 422),
        ({"kind": "other", "name": "x", "provider": "openai", "model": "m"}, 422),
    ],
)
def test_create_profile_validation(admin_client, config_store_db, encryption_key, body, status) -> None:
    assert admin_client.post("/api/model-profiles", json=body).status_code == status
    assert _rows(config_store_db, ModelProfile) == []


def test_create_profile_rejects_url_outside_allowlist(admin_client, config_store_db) -> None:
    response = admin_client.post(
        "/api/model-profiles",
        json={
            "kind": "llm",
            "name": "x",
            "provider": "openai_compatible",
            "model": "m",
            "base_url": "https://evil.example.com/v1",
        },
    )
    assert response.status_code == 422
    assert "LLM_BASE_URL_ALLOWLIST" in response.json()["detail"]


def test_duplicate_name_in_same_kind_conflicts(admin_client, config_store_db) -> None:
    _openai_llm(admin_client, name="Trùng")
    response = admin_client.post(
        "/api/model-profiles",
        json={"kind": "llm", "name": "Trùng", "provider": "gemini", "model": "gemini-x"},
    )
    assert response.status_code == 409
    # Khác loại thì được trùng tên.
    _create(admin_client, kind="reranker", name="Trùng", provider="cross-encoder", model="ce")


def test_update_keeps_replaces_and_clears_key(admin_client, config_store_db, encryption_key) -> None:
    profile = _openai_llm(admin_client, api_key=TEST_API_KEY)
    [before] = _rows(config_store_db, ModelProfile)

    body = {"name": "Đổi tên", "provider": "openai", "model": "gpt-unit-test-2"}
    response = admin_client.put(f"/api/model-profiles/{profile['id']}", json=body)
    assert response.status_code == 200, response.text
    [row] = _rows(config_store_db, ModelProfile)
    assert row.name == "Đổi tên" and row.model == "gpt-unit-test-2"
    assert row.encrypted_api_key == before.encrypted_api_key

    admin_client.put(f"/api/model-profiles/{profile['id']}", json={**body, "api_key": "sk-new-key-123456"})
    [row] = _rows(config_store_db, ModelProfile)
    assert row.encrypted_api_key != before.encrypted_api_key

    response = admin_client.put(f"/api/model-profiles/{profile['id']}", json={**body, "clear_api_key": True})
    assert response.json()["profiles"][0]["has_api_key"] is False


def test_changing_provider_drops_key_of_old_provider(admin_client, config_store_db, encryption_key) -> None:
    profile = _openai_llm(admin_client, api_key=TEST_API_KEY)
    response = admin_client.put(
        f"/api/model-profiles/{profile['id']}",
        json={"name": "GPT mini", "provider": "gemini", "model": "gemini-x"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["profiles"][0]["has_api_key"] is False


def test_update_and_delete_unknown_profile_404(admin_client) -> None:
    body = {"name": "x", "provider": "openai", "model": "m"}
    assert admin_client.put("/api/model-profiles/missing", json=body).status_code == 404
    assert admin_client.delete("/api/model-profiles/missing").status_code == 404
    assert _activate(admin_client, "llm", "missing").status_code == 404


# ==========================================
# Chọn LLM
# ==========================================
def _simulate_restart() -> None:
    for field in config_store.PERSISTED_FIELDS:
        setattr(settings, field, _INITIAL_SETTINGS[field])
    with config_store.SessionLocal() as session:
        config_store.load_overrides(session)


def test_activate_llm_applies_now_and_after_restart(admin_client, config_store_db, encryption_key) -> None:
    profile = _create(
        admin_client,
        kind="llm",
        name="Gemini",
        provider="gemini",
        model="gemini-unit-test",
        api_key=TEST_API_KEY,
    )
    response = _activate(admin_client, "llm", profile["id"])
    assert response.status_code == 200, response.text
    assert response.json()["active"]["llm"] == profile["id"]

    config = admin_client.get("/api/config").json()["llm"]
    assert config["provider"] == "gemini"
    assert config["model"] == "gemini-unit-test"
    assert config["gemini_has_key"] is True
    assert settings.gemini_api_key == TEST_API_KEY

    overrides = {row.key: row for row in _rows(config_store_db, AppConfigOverride)}
    assert overrides["llm_profile_id"].value == profile["id"]
    assert TEST_API_KEY not in (overrides["gemini_api_key"].encrypted_value or "")

    _simulate_restart()
    assert settings.llm_provider == "gemini"
    assert settings.gemini_model == "gemini-unit-test"
    assert settings.gemini_api_key == TEST_API_KEY
    assert settings.llm_profile_id == profile["id"]


def test_profile_without_key_uses_env_key(admin_client, config_store_db, monkeypatch) -> None:
    monkeypatch.setitem(_INITIAL_SETTINGS, "openai_api_key", "sk-from-env-file")
    settings.openai_api_key = "sk-some-other-runtime-key"
    profile = _openai_llm(admin_client)
    assert _activate(admin_client, "llm", profile["id"]).status_code == 200
    assert settings.openai_api_key == "sk-from-env-file"
    assert settings.openai_model == "gpt-unit-test-mini"


def test_compatible_profile_without_key_does_not_reuse_env_key(admin_client, config_store_db, monkeypatch) -> None:
    monkeypatch.setitem(_INITIAL_SETTINGS, "openai_compatible_api_key", "sk-env-compatible")
    profile = _create(
        admin_client,
        kind="llm",
        name="Ollama",
        provider="openai_compatible",
        model="qwen",
        base_url="https://api.openai.com/v1",
    )
    assert _activate(admin_client, "llm", profile["id"]).status_code == 200
    assert settings.llm_provider == "openai_compatible"
    assert settings.openai_compatible_api_key is None


def test_update_active_llm_reapplies_and_delete_requires_switch(admin_client, config_store_db) -> None:
    profile = _openai_llm(admin_client)
    _activate(admin_client, "llm", profile["id"])

    response = admin_client.put(
        f"/api/model-profiles/{profile['id']}",
        json={"name": "GPT mini", "provider": "openai", "model": "gpt-unit-test-updated"},
    )
    assert response.status_code == 200, response.text
    assert settings.openai_model == "gpt-unit-test-updated"

    response = admin_client.delete(f"/api/model-profiles/{profile['id']}")
    assert response.status_code == 409
    assert len(_rows(config_store_db, ModelProfile)) == 1

    response = _activate(admin_client, "llm", None)
    assert response.json()["active"]["llm"] is None
    assert settings.llm_provider == _INITIAL_SETTINGS["llm_provider"]
    assert settings.openai_model == _INITIAL_SETTINGS["openai_model"]
    assert admin_client.delete(f"/api/model-profiles/{profile['id']}").status_code == 200
    assert _rows(config_store_db, ModelProfile) == []


def test_failed_update_of_active_profile_keeps_settings(admin_client, config_store_db, no_encryption_key) -> None:
    profile = _openai_llm(admin_client)
    _activate(admin_client, "llm", profile["id"])
    response = admin_client.put(
        f"/api/model-profiles/{profile['id']}",
        json={"name": "GPT mini", "provider": "openai", "model": "changed", "api_key": TEST_API_KEY},
    )
    assert response.status_code == 422
    assert settings.openai_model == "gpt-unit-test-mini"
    [row] = _rows(config_store_db, ModelProfile)
    assert row.model == "gpt-unit-test-mini"


def test_activating_profile_of_other_kind_is_rejected(admin_client, config_store_db) -> None:
    profile = _create(admin_client, kind="reranker", name="CE", provider="cross-encoder", model="ce")
    assert _activate(admin_client, "llm", profile["id"]).status_code == 422


def test_put_config_with_provider_fields_clears_llm_profile(admin_client, config_store_db) -> None:
    profile = _openai_llm(admin_client)
    _activate(admin_client, "llm", profile["id"])

    # Đổi tham số chung (temperature) giữ lựa chọn profile.
    admin_client.put("/api/config", json={"llm": {"temperature": 0.9}})
    assert settings.llm_profile_id == profile["id"]

    admin_client.put("/api/config", json={"llm": {"openai_model": "gpt-manual"}})
    assert settings.llm_profile_id is None
    assert admin_client.get("/api/model-profiles").json()["active"]["llm"] is None


# ==========================================
# Chọn reranker
# ==========================================
def test_activate_reranker_and_back_to_heuristic(admin_client, config_store_db) -> None:
    profile = _create(admin_client, kind="reranker", name="BGE", provider="cross-encoder", model="BAAI/bge-reranker-base")
    assert _activate(admin_client, "reranker", profile["id"]).status_code == 200
    assert settings.reranker_provider == "cross-encoder"
    assert settings.reranker_model == "BAAI/bge-reranker-base"

    admin_client.put(
        f"/api/model-profiles/{profile['id']}",
        json={"name": "BGE", "provider": "cross-encoder", "model": "BAAI/bge-reranker-v2-m3"},
    )
    assert settings.reranker_model == "BAAI/bge-reranker-v2-m3"

    assert _activate(admin_client, "reranker", None).status_code == 200
    assert settings.reranker_provider == "heuristic"
    assert settings.reranker_profile_id is None


# ==========================================
# Reranker qua API (rerank_api)
# ==========================================
RERANK_URL = "https://api.cohere.com/v2"


@pytest.fixture
def rerank_allowlist(monkeypatch) -> None:
    monkeypatch.setattr(settings, "llm_base_url_allowlist", "https://api.openai.com,https://api.cohere.com")


def _rerank_api(client, name="Cohere", **extra) -> dict:
    body = {"kind": "reranker", "name": name, "provider": "rerank_api", "model": "rerank-v3.5", "base_url": RERANK_URL}
    return _create(client, **{**body, **extra})


@pytest.mark.parametrize(
    "body",
    [
        {"name": "x", "provider": "rerank_api", "model": "m"},  # thiếu Base URL
        {"name": "x", "provider": "rerank_api", "base_url": RERANK_URL},  # thiếu mô hình
        {"name": "x", "provider": "rerank_api", "model": "m", "base_url": "https://evil.example.com/v1"},
        {"name": "x", "provider": "rerank_api", "model": "m", "base_url": "http://169.254.169.254/latest"},
    ],
)
def test_rerank_api_profile_validation(admin_client, config_store_db, rerank_allowlist, body) -> None:
    response = admin_client.post("/api/model-profiles", json={"kind": "reranker", **body})
    assert response.status_code == 422
    assert _rows(config_store_db, ModelProfile) == []


def test_rerank_api_profile_encrypts_optional_key(admin_client, config_store_db, rerank_allowlist, encryption_key) -> None:
    without_key = _rerank_api(admin_client, name="Tự host")
    assert without_key["has_api_key"] is False
    assert without_key["base_url"] == RERANK_URL

    response = admin_client.post(
        "/api/model-profiles",
        json={
            "kind": "reranker",
            "name": "Cohere",
            "provider": "rerank_api",
            "model": "rerank-v3.5",
            "base_url": RERANK_URL,
            "api_key": TEST_API_KEY,
        },
    )
    assert response.status_code == 201, response.text
    assert TEST_API_KEY not in response.text
    profile = next(p for p in response.json()["profiles"] if p["name"] == "Cohere")
    assert profile["has_api_key"] is True
    row = next(r for r in _rows(config_store_db, ModelProfile) if r.name == "Cohere")
    assert row.encrypted_api_key and TEST_API_KEY not in row.encrypted_api_key
    assert TEST_API_KEY not in admin_client.get("/api/model-profiles").text

    # Đổi sang cross-encoder: bỏ Base URL và khoá đã lưu.
    response = admin_client.put(
        f"/api/model-profiles/{profile['id']}",
        json={"name": "Cohere", "provider": "cross-encoder", "model": "BAAI/bge-reranker-base", "base_url": RERANK_URL},
    )
    assert response.status_code == 200, response.text
    updated = next(p for p in response.json()["profiles"] if p["id"] == profile["id"])
    assert updated["has_api_key"] is False
    assert updated["base_url"] is None


def test_activate_rerank_api_applies_now_and_after_restart(
    admin_client, config_store_db, rerank_allowlist, encryption_key, monkeypatch
) -> None:
    # D-02: không dự phòng khoá `.env` cho profile không có khoá.
    monkeypatch.setitem(_INITIAL_SETTINGS, "reranker_api_key", None)
    settings.reranker_api_key = None
    profile = _rerank_api(admin_client, api_key=TEST_API_KEY)
    response = _activate(admin_client, "reranker", profile["id"])
    assert response.status_code == 200, response.text
    assert TEST_API_KEY not in response.text
    assert (settings.reranker_provider, settings.reranker_model) == ("rerank_api", "rerank-v3.5")
    assert settings.reranker_base_url == RERANK_URL
    assert settings.reranker_api_key == TEST_API_KEY

    overrides = {row.key: row for row in _rows(config_store_db, AppConfigOverride)}
    assert overrides["reranker_base_url"].value == RERANK_URL
    assert overrides["reranker_api_key"].value is None
    assert overrides["reranker_api_key"].encrypted_value and TEST_API_KEY not in overrides["reranker_api_key"].encrypted_value
    assert TEST_API_KEY not in admin_client.get("/api/config").text

    _simulate_restart()
    assert settings.reranker_provider == "rerank_api"
    assert settings.reranker_base_url == RERANK_URL
    assert settings.reranker_api_key == TEST_API_KEY
    assert settings.reranker_profile_id == profile["id"]

    # Sửa profile đang dùng thì áp lại; bỏ khoá thì không dùng khoá nào.
    admin_client.put(
        f"/api/model-profiles/{profile['id']}",
        json={
            "name": "Cohere",
            "provider": "rerank_api",
            "model": "rerank-v4",
            "base_url": "https://api.cohere.com/v1",
            "clear_api_key": True,
        },
    )
    assert settings.reranker_model == "rerank-v4"
    assert settings.reranker_base_url == "https://api.cohere.com/v1"
    assert settings.reranker_api_key is None

    # Về Heuristic: xoá Base URL/khoá (về giá trị khởi động) và dòng override.
    assert _activate(admin_client, "reranker", None).status_code == 200
    assert settings.reranker_provider == "heuristic"
    assert settings.reranker_base_url == _INITIAL_SETTINGS["reranker_base_url"]
    assert settings.reranker_api_key is None
    keys = {row.key for row in _rows(config_store_db, AppConfigOverride)}
    assert "reranker_api_key" not in keys


def test_rerank_api_profile_never_uses_env_key(admin_client, config_store_db, rerank_allowlist, monkeypatch) -> None:
    monkeypatch.setitem(_INITIAL_SETTINGS, "reranker_api_key", "rk-from-env-file")
    settings.reranker_api_key = "rk-from-env-file"
    profile = _rerank_api(admin_client)
    assert _activate(admin_client, "reranker", profile["id"]).status_code == 200
    assert settings.reranker_api_key is None


def test_switching_to_cross_encoder_clears_rerank_api_settings(
    admin_client, config_store_db, rerank_allowlist, encryption_key
) -> None:
    api = _rerank_api(admin_client, api_key=TEST_API_KEY)
    ce = _create(admin_client, kind="reranker", name="CE", provider="cross-encoder", model="ce")
    _activate(admin_client, "reranker", api["id"])
    assert _activate(admin_client, "reranker", ce["id"]).status_code == 200
    assert settings.reranker_provider == "cross-encoder"
    assert settings.reranker_base_url is None
    assert settings.reranker_api_key is None


def test_activate_rerank_api_rechecks_allowlist(admin_client, config_store_db, rerank_allowlist) -> None:
    profile = _rerank_api(admin_client)
    settings.llm_base_url_allowlist = "https://api.openai.com"
    response = _activate(admin_client, "reranker", profile["id"])
    assert response.status_code == 422
    assert settings.reranker_provider != "rerank_api"


def test_load_overrides_skips_rerank_url_outside_allowlist(admin_client, config_store_db, rerank_allowlist) -> None:
    profile = _rerank_api(admin_client)
    _activate(admin_client, "reranker", profile["id"])
    settings.llm_base_url_allowlist = "https://api.openai.com"
    _simulate_restart()
    assert settings.reranker_base_url is None


# ==========================================
# Kiểm tra kết nối reranker
# ==========================================
def _fake_rerank_api(monkeypatch, *, result=None, error=None) -> dict:
    captured: dict = {}

    def fake(**kwargs):
        captured.update(kwargs)
        if error is not None:
            raise error
        return result if result is not None else [(0, 0.98), (1, 0.02)]

    monkeypatch.setattr(routes, "call_rerank_api", fake)
    return captured


def test_test_reranker_requires_admin(client) -> None:
    response = client.post("/api/model-profiles/test-reranker", json={"provider": "rerank_api"})
    assert response.status_code == 401


def test_test_reranker_uses_typed_or_stored_key_and_saves_nothing(
    admin_client, config_store_db, rerank_allowlist, encryption_key, monkeypatch
) -> None:
    profile = _rerank_api(admin_client, api_key=TEST_API_KEY)
    before_profiles = [(r.id, r.encrypted_api_key) for r in _rows(config_store_db, ModelProfile)]
    before_overrides = [(r.key, r.value) for r in _rows(config_store_db, AppConfigOverride)]
    captured = _fake_rerank_api(monkeypatch)
    body = {"provider": "rerank_api", "model": "rerank-v3.5", "base_url": RERANK_URL, "profile_id": profile["id"]}

    response = admin_client.post("/api/model-profiles/test-reranker", json=body)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["success"] is True and data["latency_ms"] is not None
    assert TEST_API_KEY not in response.text
    assert captured["api_key"] == TEST_API_KEY
    assert captured["base_url"] == RERANK_URL and captured["model"] == "rerank-v3.5"
    assert len(captured["documents"]) == 2 and captured["top_n"] == 2

    admin_client.post("/api/model-profiles/test-reranker", json={**body, "api_key": "rk-typed"})
    assert captured["api_key"] == "rk-typed"

    admin_client.post("/api/model-profiles/test-reranker", json={**body, "profile_id": None})
    assert captured["api_key"] is None

    assert [(r.id, r.encrypted_api_key) for r in _rows(config_store_db, ModelProfile)] == before_profiles
    assert [(r.key, r.value) for r in _rows(config_store_db, AppConfigOverride)] == before_overrides


def test_test_reranker_reports_failure(admin_client, config_store_db, rerank_allowlist, monkeypatch) -> None:
    from app.retrieval.reranker import RerankAPIError

    _fake_rerank_api(monkeypatch, error=RerankAPIError("HTTP 401", status_code=401))
    response = admin_client.post(
        "/api/model-profiles/test-reranker",
        json={"provider": "rerank_api", "model": "rerank-v3.5", "base_url": RERANK_URL},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "HTTP 401" in data["message"] and "API key" in data["message"]


@pytest.mark.parametrize(
    "body",
    [
        {"provider": "rerank_api", "model": "m", "base_url": "https://evil.example.com/v1"},
        {"provider": "rerank_api", "model": "m"},
        {"provider": "rerank_api", "base_url": RERANK_URL},
        {"provider": "cross-encoder", "model": "m", "base_url": RERANK_URL},
    ],
)
def test_test_reranker_rejects_invalid_request(
    admin_client, config_store_db, rerank_allowlist, monkeypatch, body
) -> None:
    captured = _fake_rerank_api(monkeypatch)
    assert admin_client.post("/api/model-profiles/test-reranker", json=body).status_code == 422
    assert captured == {}


def test_test_reranker_never_uses_llm_profile_key(
    admin_client, config_store_db, rerank_allowlist, encryption_key, monkeypatch
) -> None:
    llm = _openai_llm(admin_client, api_key=TEST_API_KEY)
    captured = _fake_rerank_api(monkeypatch)
    response = admin_client.post(
        "/api/model-profiles/test-reranker",
        json={"provider": "rerank_api", "model": "m", "base_url": RERANK_URL, "profile_id": llm["id"]},
    )
    assert response.status_code == 422
    assert captured == {}
    assert admin_client.post(
        "/api/model-profiles/test-reranker",
        json={"provider": "rerank_api", "model": "m", "base_url": RERANK_URL, "profile_id": "missing"},
    ).status_code == 404


# ==========================================
# Embedding
# ==========================================
class _FakeEmbedding(EmbeddingModel):
    def embed(self, texts):
        return [[0.0] for _ in texts]


def _embedding_profile(client, dimension=None, **extra) -> dict:
    return _create(
        client,
        kind="embedding",
        name=extra.pop("name", "ST"),
        provider="sentence-transformers",
        model="unit-test/st-model",
        dimension=dimension or settings.vector_dim,
        **extra,
    )


def test_embedding_dimension_must_match_vector_dim(admin_client, config_store_db) -> None:
    profile = _embedding_profile(admin_client, dimension=settings.vector_dim + 1)
    response = _activate(admin_client, "embedding", profile["id"])
    assert response.status_code == 422
    assert "VECTOR_DIM" in response.json()["detail"]
    assert settings.embedding_profile_id is None


def test_embedding_selection_applies_at_startup(admin_client, config_store_db, monkeypatch) -> None:
    running = (settings.embedding_provider, settings.embedding_model)
    profile = _embedding_profile(admin_client)

    response = _activate(admin_client, "embedding", profile["id"])
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["active"]["embedding"] == profile["id"]
    # Embedder đang chạy chưa đổi cho tới khi khởi động lại.
    assert data["embedding_runtime"]["restart_required"] is True
    assert (settings.embedding_provider, settings.embedding_model) == running

    fake = _FakeEmbedding()
    monkeypatch.setattr("app.embeddings.create_embedding_model", lambda: fake)
    _simulate_restart()
    embedding_runtime.reset()
    model_profiles.load_selected_embedding_at_startup()

    assert embedding_runtime.get() is fake
    assert retriever.embedding_model is runtime_embedding_model
    assert ingestion_pipeline.embedding_model is runtime_embedding_model
    assert settings.embedding_model == "unit-test/st-model"
    runtime = admin_client.get("/api/model-profiles").json()["embedding_runtime"]
    assert runtime["profile_id"] == profile["id"]
    assert runtime["restart_required"] is False

    # Sửa model của profile đang chạy → cần khởi động lại; xoá profile đang chọn → 409.
    admin_client.put(
        f"/api/model-profiles/{profile['id']}",
        json={"name": "ST", "provider": "sentence-transformers", "model": "unit-test/other", "dimension": settings.vector_dim},
    )
    assert admin_client.get("/api/model-profiles").json()["embedding_runtime"]["restart_required"] is True
    assert admin_client.delete(f"/api/model-profiles/{profile['id']}").status_code == 409


def test_embedding_load_failure_keeps_env_embedder(admin_client, config_store_db, monkeypatch) -> None:
    before = embedding_runtime.get()
    running = (settings.embedding_provider, settings.embedding_model)
    profile = _embedding_profile(admin_client)
    _activate(admin_client, "embedding", profile["id"])

    def broken_factory():
        raise EmbeddingUnavailableError("Không tải được mô hình sentence-transformers 'unit-test/st-model' (OSError).")

    monkeypatch.setattr("app.embeddings.create_embedding_model", broken_factory)
    model_profiles.load_selected_embedding_at_startup()

    assert embedding_runtime.get() is before
    assert (settings.embedding_provider, settings.embedding_model) == running
    runtime = admin_client.get("/api/model-profiles").json()["embedding_runtime"]
    assert runtime["profile_id"] is None
    assert runtime["load_error"]


def test_reset_config_clears_selection_but_keeps_profiles(admin_client, config_store_db) -> None:
    llm = _openai_llm(admin_client)
    _activate(admin_client, "llm", llm["id"])
    assert admin_client.post("/api/config/reset").status_code == 200
    data = admin_client.get("/api/model-profiles").json()
    assert data["active"] == {"llm": None, "embedding": None, "reranker": None}
    assert len(data["profiles"]) == 1


# ==========================================
# Kiểm tra kết nối
# ==========================================
def test_test_llm_uses_stored_profile_key(admin_client, config_store_db, encryption_key, monkeypatch) -> None:
    captured = {}

    class _Provider:
        def is_configured(self):
            return True

        def generate(self, *_args, **_kwargs):
            return "OK PTIT"

    def fake_factory(**kwargs):
        captured.update(kwargs)
        return _Provider()

    monkeypatch.setattr(routes, "create_llm_provider_from_config", fake_factory)
    profile = _openai_llm(admin_client, api_key=TEST_API_KEY)

    response = admin_client.post(
        "/api/model-profiles/test-llm",
        json={"provider": "openai", "model": "gpt-unit-test-mini", "profile_id": profile["id"]},
    )
    assert response.status_code == 200, response.text
    assert response.json()["success"] is True
    assert captured["api_key"] == TEST_API_KEY
    assert TEST_API_KEY not in response.text

    admin_client.post(
        "/api/model-profiles/test-llm",
        json={"provider": "openai", "api_key": "sk-typed", "profile_id": profile["id"]},
    )
    assert captured["api_key"] == "sk-typed"

    response = admin_client.post(
        "/api/model-profiles/test-llm",
        json={"provider": "openai_compatible", "base_url": "https://evil.example.com/v1", "profile_id": profile["id"]},
    )
    assert response.status_code == 422
