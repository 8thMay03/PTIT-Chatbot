"""Cấu hình admin đổi trên UI được lưu vào DB và còn sau khi restart (persist-runtime-config).

- PUT /config ghi phần khác `.env` vào bảng app_config_overrides; về đúng `.env` thì xoá dòng.
- API key chỉ lưu dạng bản mã Fernet; thiếu CONFIG_ENCRYPTION_KEY thì từ chối, không ghi bản rõ.
- Lỗi lưu (thiếu khoá, DB lỗi) để settings đang chạy y như trước request.
- Khởi động (lifespan) áp lại override; dòng không dùng được bị bỏ qua, không làm sập app.

Bảng cấu hình chạy trên SQLite tạm (fixture ``config_store_db`` trong conftest).
"""

from __future__ import annotations

import re

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app.core import config_store
from app.core.config import _INITIAL_SETTINGS, Settings, settings
from app.core.config_crypto import encrypt_secret
from app.db.models import AppConfigOverride
from app.main import app

TEST_API_KEY = "sk-unit-test-plaintext-key-0123456789"


@pytest.fixture(autouse=True)
def _restore_settings():
    """PUT /config đổi settings toàn cục: trả lại nguyên trạng sau mỗi test."""
    snapshot = settings.model_dump()
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


def _rows(session_factory) -> dict[str, AppConfigOverride]:
    with session_factory() as session:
        return {row.key: row for row in session.scalars(select(AppConfigOverride))}


def _different(field: str, *candidates):
    """Giá trị khác `.env` hiện tại, để test không phụ thuộc .env máy chạy."""
    return next(value for value in candidates if value != _INITIAL_SETTINGS[field])


def _simulate_restart() -> list[str]:
    """Đưa settings về `.env` rồi chạy bước nạp lúc khởi động."""
    for field in config_store.PERSISTED_FIELDS:
        setattr(settings, field, _INITIAL_SETTINGS[field])
    with config_store.SessionLocal() as session:
        return config_store.load_overrides(session)


# ==========================================
# Lưu trường thường
# ==========================================
def test_put_config_persists_changes_and_survives_restart(admin_client, config_store_db, no_encryption_key) -> None:
    top_k = _different("retrieval_default_top_k", 7, 8)
    temperature = _different("llm_temperature", 1.25, 1.5)

    response = admin_client.put(
        "/api/config",
        json={"retrieval": {"top_k": top_k}, "llm": {"temperature": temperature}},
    )
    assert response.status_code == 200, response.text

    rows = _rows(config_store_db)
    assert rows["retrieval_default_top_k"].value == top_k
    assert rows["llm_temperature"].value == temperature
    assert rows["llm_temperature"].encrypted_value is None
    # Chỉ trường đã đổi so với .env được ghi.
    assert set(rows) == {"retrieval_default_top_k", "llm_temperature"}

    applied = _simulate_restart()
    assert set(applied) == {"retrieval_default_top_k", "llm_temperature"}
    assert settings.retrieval_default_top_k == top_k
    assert settings.llm_temperature == temperature


def test_value_back_to_env_removes_row(admin_client, config_store_db) -> None:
    top_k = _different("retrieval_default_top_k", 7, 8)
    admin_client.put("/api/config", json={"retrieval": {"top_k": top_k}})
    assert "retrieval_default_top_k" in _rows(config_store_db)

    response = admin_client.put(
        "/api/config", json={"retrieval": {"top_k": _INITIAL_SETTINGS["retrieval_default_top_k"]}}
    )
    assert response.status_code == 200
    assert "retrieval_default_top_k" not in _rows(config_store_db)


def test_reset_clears_saved_config(admin_client, config_store_db) -> None:
    admin_client.put("/api/config", json={"retrieval": {"top_k": _different("retrieval_default_top_k", 7, 8)}})
    assert _rows(config_store_db)

    response = admin_client.post("/api/config/reset")
    assert response.status_code == 200
    assert _rows(config_store_db) == {}
    assert _simulate_restart() == []


# ==========================================
# Secret: luôn mã hoá
# ==========================================
def test_api_key_is_stored_encrypted_only(admin_client, config_store_db, encryption_key) -> None:
    response = admin_client.put("/api/config", json={"llm": {"openai_api_key": TEST_API_KEY}})
    assert response.status_code == 200, response.text
    # Response không bao giờ trả key.
    assert TEST_API_KEY not in response.text

    row = _rows(config_store_db)["openai_api_key"]
    assert row.value is None
    assert row.encrypted_value
    assert TEST_API_KEY not in row.encrypted_value
    # Bản rõ không xuất hiện ở bất kỳ đâu trong file DB.
    with config_store_db() as session:
        db_path = session.get_bind().url.database
    with open(db_path, "rb") as db_file:
        assert TEST_API_KEY.encode() not in db_file.read()

    settings.openai_api_key = _INITIAL_SETTINGS["openai_api_key"]
    assert "openai_api_key" in _simulate_restart()
    assert settings.openai_api_key == TEST_API_KEY


def test_generic_api_key_field_is_encrypted_for_active_provider(admin_client, config_store_db, encryption_key) -> None:
    response = admin_client.put(
        "/api/config", json={"llm": {"provider": "gemini", "api_key": TEST_API_KEY}}
    )
    assert response.status_code == 200, response.text
    row = _rows(config_store_db)["gemini_api_key"]
    assert row.value is None
    assert TEST_API_KEY not in row.encrypted_value


def test_api_key_without_encryption_key_is_rejected_and_nothing_changes(
    admin_client, config_store_db, no_encryption_key
) -> None:
    before = settings.model_dump()
    response = admin_client.put(
        "/api/config",
        json={"llm": {"openai_api_key": TEST_API_KEY, "temperature": _different("llm_temperature", 1.25, 1.5)}},
    )

    assert response.status_code == 422
    assert "CONFIG_ENCRYPTION_KEY" in response.json()["detail"]
    assert settings.model_dump() == before
    assert _rows(config_store_db) == {}


def test_invalid_encryption_key_is_rejected(admin_client, config_store_db, monkeypatch) -> None:
    monkeypatch.setattr(settings, "config_encryption_key", "khong-phai-khoa-fernet")
    response = admin_client.put("/api/config", json={"llm": {"openai_api_key": TEST_API_KEY}})
    assert response.status_code == 422
    assert "không hợp lệ" in response.json()["detail"]
    # Không lộ giá trị khoá trong thông báo lỗi.
    assert "khong-phai-khoa-fernet" not in response.text
    assert _rows(config_store_db) == {}


def test_non_secret_changes_save_without_encryption_key(admin_client, config_store_db, no_encryption_key) -> None:
    response = admin_client.put("/api/config", json={"reranker": {"enabled": not _INITIAL_SETTINGS["reranker_enabled"]}})
    assert response.status_code == 200
    assert "reranker_enabled" in _rows(config_store_db)


def test_get_config_reports_encryption_status(admin_client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "config_encryption_key", None)
    assert admin_client.get("/api/config").json()["persistence"] == {"secret_encryption_enabled": False}

    monkeypatch.setattr(settings, "config_encryption_key", Fernet.generate_key().decode())
    assert admin_client.get("/api/config").json()["persistence"] == {"secret_encryption_enabled": True}


def test_key_rotation_decrypts_old_and_reencrypts_with_new(admin_client, config_store_db, monkeypatch) -> None:
    old_key = Fernet.generate_key().decode()
    new_key = Fernet.generate_key().decode()
    monkeypatch.setattr(settings, "config_encryption_key", old_key)
    admin_client.put("/api/config", json={"llm": {"openai_api_key": TEST_API_KEY}})

    monkeypatch.setattr(settings, "config_encryption_key", f"{new_key},{old_key}")
    assert "openai_api_key" in _simulate_restart()
    assert settings.openai_api_key == TEST_API_KEY

    # Lần lưu kế tiếp mã hoá lại bằng khoá mới; bỏ khoá cũ vẫn đọc được.
    admin_client.put("/api/config", json={"retrieval": {"top_k": _different("retrieval_default_top_k", 7, 8)}})
    monkeypatch.setattr(settings, "config_encryption_key", new_key)
    assert "openai_api_key" in _simulate_restart()
    assert settings.openai_api_key == TEST_API_KEY


# ==========================================
# Lỗi DB: không "lưu nửa vời"
# ==========================================
def test_db_failure_returns_503_and_keeps_running_config(admin_client, config_store_db, monkeypatch) -> None:
    def broken_save(session):
        raise OperationalError("UPDATE app_config_overrides", {}, Exception("db down"))

    monkeypatch.setattr(config_store, "save_overrides", broken_save)
    before = settings.model_dump()

    response = admin_client.put(
        "/api/config", json={"retrieval": {"top_k": _different("retrieval_default_top_k", 7, 8)}}
    )
    assert response.status_code == 503
    assert settings.model_dump() == before


# ==========================================
# Nạp lúc khởi động
# ==========================================
def test_load_skips_unusable_rows_and_applies_the_rest(config_store_db, monkeypatch) -> None:
    monkeypatch.setattr(settings, "config_encryption_key", Fernet.generate_key().decode())
    undecryptable = encrypt_secret(TEST_API_KEY)
    monkeypatch.setattr(settings, "config_encryption_key", Fernet.generate_key().decode())
    monkeypatch.setattr(settings, "llm_base_url_allowlist", "https://api.openai.com")
    top_k = _different("retrieval_default_top_k", 7, 8)

    with config_store_db() as session:
        session.add_all(
            [
                AppConfigOverride(key="openai_api_key", encrypted_value=undecryptable),
                AppConfigOverride(key="openai_base_url", value="https://evil.example.com/v1"),
                AppConfigOverride(key="admin_password", value="mat-khau-tu-db"),
                AppConfigOverride(key="retrieval_default_top_k", value=top_k),
            ]
        )
        session.commit()

    applied = _simulate_restart()

    assert applied == ["retrieval_default_top_k"]
    assert settings.retrieval_default_top_k == top_k
    assert settings.openai_api_key == _INITIAL_SETTINGS["openai_api_key"]
    assert settings.openai_base_url == _INITIAL_SETTINGS["openai_base_url"]
    assert settings.admin_password != "mat-khau-tu-db"


def test_lifespan_applies_saved_config(config_store_db) -> None:
    top_k = _different("retrieval_default_top_k", 7, 8)
    with config_store_db() as session:
        session.add(AppConfigOverride(key="retrieval_default_top_k", value=top_k))
        session.commit()

    with TestClient(app):
        assert settings.retrieval_default_top_k == top_k


def test_startup_survives_unavailable_db(monkeypatch) -> None:
    def broken_factory():
        raise OperationalError("SELECT", {}, Exception("db down"))

    monkeypatch.setattr(config_store, "SessionLocal", broken_factory)
    before = settings.model_dump()
    config_store.load_persisted_config()
    assert settings.model_dump() == before


# ==========================================
# Whitelist
# ==========================================
def test_secret_looking_fields_are_always_encrypted() -> None:
    secret_like = {f for f in config_store.PERSISTED_FIELDS if re.search(r"key|secret|password|token", f)}
    assert secret_like <= config_store.SECRET_FIELDS


def test_security_settings_are_never_persisted() -> None:
    forbidden = {
        "admin_password",
        "admin_session_secret",
        "user_session_secret",
        "config_encryption_key",
        "llm_base_url_allowlist",
        "trusted_proxy_ips",
        "database_url",
        "cookie_secure",
    }
    assert not (forbidden & config_store.PERSISTED_FIELDS)
    assert config_store.PERSISTED_FIELDS <= set(Settings.model_fields)
