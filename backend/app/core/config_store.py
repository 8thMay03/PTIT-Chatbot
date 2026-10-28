"""Lưu cấu hình runtime admin đổi trên UI vào Postgres để còn sau khi restart.

Bảng ``app_config_overrides`` chỉ chứa phần KHÁC giá trị `.env` lúc khởi động
(`_INITIAL_SETTINGS`): đổi một trường về đúng giá trị `.env` thì dòng bị xoá và
trường đó lại theo `.env`. Thứ tự ưu tiên khi khởi động: DB > `.env` > mặc định.

- Chỉ trường trong ``PERSISTED_FIELDS`` được ghi/đọc. Cấu hình xác thực, allowlist
  URL, DATABASE_URL, embedding... không bao giờ lấy từ DB.
- Secret (``SECRET_FIELDS``) chỉ lưu dưới dạng bản mã (app.core.config_crypto).
  Thiếu ``CONFIG_ENCRYPTION_KEY`` thì từ chối lưu, không bao giờ ghi bản rõ.
- Ghi DB lỗi thì phục hồi settings trong bộ nhớ: UI không thấy "đã lưu" cho thứ
  sẽ mất khi restart.
"""

from __future__ import annotations

import logging
from collections.abc import Generator

from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import (
    _INITIAL_SETTINGS,
    ConfigValidationError,
    get_runtime_config_dict,
    reset_runtime_config,
    settings,
    update_runtime_config,
    validate_llm_url,
)
from app.core.config_crypto import SecretDecryptionError, SecretEncryptionUnavailable, decrypt_secret, encrypt_secret
from app.db.models import AppConfigOverride
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

SECRET_FIELDS = frozenset(
    {
        "openai_api_key",
        "gemini_api_key",
        "azure_openai_api_key",
        "openai_compatible_api_key",
    }
)

# Các trường PUT /config đổi được (update_runtime_config), trừ embedding: model nhúng
# nạp một lần lúc khởi động và quyết định số chiều vector nên chỉ đổi qua `.env`.
PERSISTED_FIELDS = SECRET_FIELDS | frozenset(
    {
        "llm_provider",
        "llm_temperature",
        "llm_timeout",
        "llm_max_retries",
        "openai_model",
        "openai_base_url",
        "gemini_model",
        "azure_openai_endpoint",
        "azure_openai_deployment_name",
        "azure_openai_api_version",
        "openai_compatible_base_url",
        "openai_compatible_model",
        "multi_query_enabled",
        "multi_query_use_llm",
        "multi_query_count",
        "query_rewrite_use_llm",
        "retrieval_default_top_k",
        "hybrid_vector_weight",
        "reranker_enabled",
        "reranker_provider",
        "reranker_model",
        "reranker_candidate_multiplier",
        "guardrail_scope_enabled",
        "retrieval_min_vector_score",
        "retrieval_min_bm25_score",
    }
)

# URL LLM đọc từ DB vẫn phải qua allowlist hiện hành: allowlist trong `.env` có thể
# đã bị thu hẹp sau lần lưu.
_URL_FIELDS = frozenset({"openai_base_url", "openai_compatible_base_url", "azure_openai_endpoint"})


def get_config_store_session() -> Generator[Session, None, None]:
    """Session cho bảng cấu hình, lấy từ `SessionLocal` của module này.

    Route và lúc khởi động cùng đi qua tên này nên test chỉ cần thay
    `config_store.SessionLocal` là không chạm DB dev (tests/conftest.py).
    """
    with SessionLocal() as session:
        yield session


def save_overrides(session: Session) -> None:
    """Đồng bộ bảng với settings hiện tại: ghi trường khác `.env`, xoá trường đã về `.env`.

    Raise ``SecretEncryptionUnavailable`` (trước khi ghi gì) nếu cần lưu secret mà
    không có khoá; lỗi DB raise ``SQLAlchemyError``. Caller lo rollback.
    """
    desired: dict[str, tuple[object | None, str | None]] = {}
    for field in sorted(PERSISTED_FIELDS):
        current = getattr(settings, field)
        if current == _INITIAL_SETTINGS.get(field):
            continue
        if field in SECRET_FIELDS:
            # Mã hoá lại mỗi lần lưu: sau khi xoay khoá, mọi secret chuyển sang khoá mới.
            desired[field] = (None, encrypt_secret(current) if current is not None else None)
        else:
            desired[field] = (current, None)

    rows = {row.key: row for row in session.scalars(select(AppConfigOverride))}
    for key, row in rows.items():
        if key not in desired:
            session.delete(row)
    for key, (value, encrypted_value) in desired.items():
        row = rows.get(key)
        if row is None:
            session.add(AppConfigOverride(key=key, value=value, encrypted_value=encrypted_value))
        elif row.value != value or row.encrypted_value != encrypted_value:
            row.value = value
            row.encrypted_value = encrypted_value
    session.commit()


def apply_config_update(session: Session, payload: dict) -> dict:
    """Áp payload PUT /config vào settings rồi lưu DB; lỗi thì settings giữ nguyên như trước."""
    previous = settings.model_dump()
    try:
        update_runtime_config(payload)
        save_overrides(session)
    except BaseException:
        session.rollback()
        for field, value in previous.items():
            setattr(settings, field, value)
        raise
    return get_runtime_config_dict()


def reset_config(session: Session) -> dict:
    """Xoá mọi override trong DB rồi đưa settings về `.env`. DB lỗi thì không reset gì."""
    try:
        session.execute(delete(AppConfigOverride))
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        raise
    return reset_runtime_config()


def load_overrides(session: Session) -> list[str]:
    """Áp các override trong DB lên settings; trả về danh sách trường đã áp.

    Dòng không dùng được (trường ngoài whitelist, secret không giải mã được, URL
    ngoài allowlist) bị bỏ qua kèm cảnh báo; trường đó giữ giá trị `.env`.
    """
    applied: list[str] = []
    for row in session.scalars(select(AppConfigOverride)):
        key = row.key
        if key not in PERSISTED_FIELDS:
            logger.warning("Bỏ qua cấu hình '%s' trong DB: trường không được phép lưu.", key)
            continue
        if key in SECRET_FIELDS:
            if row.encrypted_value is None:
                value = None
            else:
                try:
                    value = decrypt_secret(row.encrypted_value)
                except (SecretDecryptionError, SecretEncryptionUnavailable) as exc:
                    logger.warning("Bỏ qua secret '%s' trong DB: %s Dùng giá trị trong .env.", key, exc)
                    continue
        else:
            value = row.value
        if key in _URL_FIELDS:
            try:
                validate_llm_url(value)
            except ConfigValidationError as exc:
                logger.warning("Bỏ qua cấu hình '%s' trong DB: %s", key, exc)
                continue
        setattr(settings, key, value)
        applied.append(key)
    return applied


def load_persisted_config() -> None:
    """Gọi lúc khởi động. DB chưa sẵn sàng thì chạy tiếp bằng cấu hình `.env`."""
    try:
        with SessionLocal() as session:
            applied = load_overrides(session)
    except SQLAlchemyError as exc:
        logger.warning("Không đọc được cấu hình đã lưu trong DB, dùng .env: %s", exc)
        return
    if applied:
        # Chỉ ghi tên trường, không ghi giá trị (có thể là API key).
        logger.info("Đã áp %d cấu hình đã lưu từ DB: %s", len(applied), ", ".join(sorted(applied)))
