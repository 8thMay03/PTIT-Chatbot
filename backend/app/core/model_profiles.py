"""Kho cấu hình mô hình (LLM, embedding, reranker) và chọn mô hình đang dùng.

Admin nhập nhiều cấu hình cho mỗi loại vào bảng ``model_profiles``; hệ thống dùng
profile đang được chọn (``settings.<kind>_profile_id``):

- LLM / reranker: chọn profile là chép trường của nó vào settings rồi lưu qua
  ``config_store.settings_transaction`` → có hiệu lực ngay và còn sau restart.
  Sửa profile đang dùng thì áp lại ngay. ``None`` = cấu hình `.env` (LLM) hoặc
  heuristic (reranker).
- Embedding: chọn profile (hoặc sửa profile đang dùng) tạo embedder mới ngay rồi mới lưu
  ``embedding_profile_id`` (task reembed-documents, D-01). Vector ghi kèm chữ ký mô hình nên
  đoạn của mô hình cũ được nhận ra: chúng bị bỏ khỏi tìm kiếm vector cho tới khi admin nhúng
  lại. Đang có embedder chạy được mà không tạo được mô hình mới → 422, giữ nguyên mọi thứ;
  chưa có embedder chạy được thì vẫn lưu lựa chọn và ghi lý do lỗi (BE-13).
  ``load_selected_embedding`` áp profile đã chọn lúc khởi động. Số chiều không được lớn hơn
  ``VECTOR_DIM``; ít hơn thì vector được đệm 0.

API key chỉ lưu dạng bản mã (app.core.config_crypto) và không bao giờ trả về client.
Lỗi bất kỳ để DB và settings đang chạy như trước thao tác.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core import config_store
from app.core.config import _INITIAL_SETTINGS, ConfigValidationError, settings, validate_llm_url
from app.core.config_crypto import (
    SecretDecryptionError,
    SecretEncryptionUnavailable,
    decrypt_secret,
    encrypt_secret,
    is_secret_encryption_configured,
)
from app.db.models import ModelProfile

logger = logging.getLogger(__name__)

KINDS = ("llm", "embedding", "reranker")

# Trường của từng (loại, nhà cung cấp): tên trường → bắt buộc. Trường không có ở đây
# bị bỏ khi lưu, nên đổi nhà cung cấp không để lại tham số cũ.
_PROVIDER_FIELDS: dict[tuple[str, str], dict[str, bool]] = {
    ("llm", "openai"): {"model": True, "base_url": False},
    ("llm", "gemini"): {"model": True},
    ("llm", "azure"): {"endpoint": True, "deployment_name": True, "api_version": True},
    ("llm", "openai_compatible"): {"base_url": True, "model": True},
    ("embedding", "openai"): {"model": True, "dimension": True},
    ("embedding", "sentence-transformers"): {"model": True, "dimension": True},
    ("embedding", "voyage"): {"model": True, "dimension": True},
    ("embedding", "cohere"): {"model": True, "dimension": True},
    ("embedding", "gemini"): {"model": True, "dimension": True},
    ("embedding", "jina"): {"model": True, "dimension": True},
    ("embedding", "openai_compatible"): {"base_url": True, "model": True, "dimension": True},
    ("reranker", "cross-encoder"): {"model": True},
    ("reranker", "rerank_api"): {"base_url": True, "model": True},
    ("reranker", "cohere"): {"model": True},
    ("reranker", "jina"): {"model": True},
    ("reranker", "voyage"): {"model": True},
    ("reranker", "pinecone"): {"model": True},
    # TEI phục vụ đúng một mô hình nên không gửi tên mô hình; vẫn cần để hiển thị.
    ("reranker", "tei"): {"base_url": True, "model": True},
}
PROVIDERS: dict[str, tuple[str, ...]] = {
    kind: tuple(provider for (k, provider) in _PROVIDER_FIELDS if k == kind) for kind in KINDS
}
# Profile được phép có API key (cross-encoder và sentence-transformers chạy cục bộ).
_KEYED = (
    {("llm", p) for p in PROVIDERS["llm"]}
    | {("embedding", p) for p in PROVIDERS["embedding"] if p != "sentence-transformers"}
    | {("reranker", p) for p in PROVIDERS["reranker"] if p != "cross-encoder"}
)
# Profile bắt buộc có API key: embedding/reranker qua API của từng hãng không dự phòng khoá
# `.env` (D-04).
_KEY_REQUIRED = {("embedding", p) for p in ("voyage", "cohere", "gemini", "jina")} | {
    ("reranker", p) for p in ("cohere", "jina", "voyage", "pinecone")
}
_URL_FIELDS = ("base_url", "endpoint")
_PARAM_FIELDS = ("base_url", "endpoint", "deployment_name", "api_version", "dimension")
_FIELD_LABELS = {
    "model": "tên mô hình",
    "base_url": "Base URL",
    "endpoint": "Endpoint",
    "deployment_name": "tên deployment",
    "api_version": "API version",
    "dimension": "số chiều vector",
}
_NAME_MAX_LENGTH = 100

# Trường API key trong settings của từng nhà cung cấp LLM. Profile không có khoá thì
# dùng khoá `.env` — trừ tương thích OpenAI: không gửi khoá `.env` sang máy chủ khác.
_LLM_KEY_FIELDS = {
    "openai": "openai_api_key",
    "gemini": "gemini_api_key",
    "azure": "azure_openai_api_key",
    "openai_compatible": "openai_compatible_api_key",
}
_LLM_ENV_KEY_FALLBACK = frozenset({"openai", "gemini", "azure"})

# Embedding đang chạy trong tiến trình này: profile và dấu vân tay (provider, model, bản mã
# khoá, params) để biết lựa chọn hiện tại đã được áp chưa.
_running_embedding: dict[str, Any] = {"profile_id": None, "fingerprint": None, "error": None}


class ProfileNotFound(LookupError):
    """Không có profile với id này (404)."""


class ProfileConflict(Exception):
    """Trùng tên trong cùng loại hoặc xoá profile đang dùng (409)."""


# ==========================================
# Chuẩn hoá và kiểm tra dữ liệu nhập
# ==========================================
def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _validate_kind(kind: str) -> str:
    if kind not in KINDS:
        raise ConfigValidationError(f"Loại mô hình không hợp lệ: {kind}.")
    return kind


def _normalize(kind: str, data: dict) -> tuple[str, str, str | None, dict]:
    """Trả về (name, provider, model, params) đã kiểm tra; sai thì ConfigValidationError."""
    name = _clean(data.get("name"))
    if not name:
        raise ConfigValidationError("Nhập tên hiển thị cho mô hình.")
    if len(name) > _NAME_MAX_LENGTH:
        raise ConfigValidationError(f"Tên hiển thị tối đa {_NAME_MAX_LENGTH} ký tự.")

    provider = (_clean(data.get("provider")) or "").lower()
    fields = _PROVIDER_FIELDS.get((kind, provider))
    if fields is None:
        allowed = ", ".join(PROVIDERS[kind])
        raise ConfigValidationError(f"Nhà cung cấp '{provider}' không hỗ trợ cho {kind}; chọn một trong: {allowed}.")

    values: dict[str, Any] = {}
    for field, required in fields.items():
        if field == "dimension":
            raw = data.get("dimension")
            if raw in (None, ""):
                value = None
            else:
                try:
                    value = int(raw)
                except (TypeError, ValueError):
                    raise ConfigValidationError("Số chiều vector phải là số nguyên dương.") from None
                if value < 1:
                    raise ConfigValidationError("Số chiều vector phải là số nguyên dương.")
        else:
            value = _clean(data.get(field))
        if required and value is None:
            raise ConfigValidationError(f"Thiếu {_FIELD_LABELS[field]}.")
        if field in _URL_FIELDS:
            validate_llm_url(value)
        values[field] = value

    model = values.pop("model", None)
    params = {key: value for key, value in values.items() if value is not None}
    return name, provider, model, params


def _ensure_unique_name(session: Session, kind: str, name: str, exclude_id: str | None = None) -> None:
    query = select(ModelProfile.id).where(ModelProfile.kind == kind, ModelProfile.name == name)
    if exclude_id is not None:
        query = query.where(ModelProfile.id != exclude_id)
    if session.scalars(query).first() is not None:
        raise ProfileConflict(f"Đã có mô hình tên '{name}' trong mục này.")


def _get(session: Session, profile_id: str) -> ModelProfile:
    row = session.get(ModelProfile, profile_id)
    if row is None:
        raise ProfileNotFound("Không tìm thấy cấu hình mô hình.")
    return row


def _decrypt_key(row: ModelProfile) -> str | None:
    if not row.encrypted_api_key:
        return None
    return decrypt_secret(row.encrypted_api_key)


def _profile_key_or_422(row: ModelProfile) -> str | None:
    try:
        return _decrypt_key(row)
    except (SecretDecryptionError, SecretEncryptionUnavailable) as exc:
        raise ConfigValidationError(
            f"Không giải mã được API key của '{row.name}' ({exc}) Nhập lại API key cho mô hình này."
        ) from exc


# ==========================================
# Đọc
# ==========================================
def serialize_profile(row: ModelProfile) -> dict:
    params = row.params or {}
    return {
        "id": row.id,
        "kind": row.kind,
        "name": row.name,
        "provider": row.provider,
        "model": row.model,
        **{field: params.get(field) for field in _PARAM_FIELDS},
        "has_api_key": bool(row.encrypted_api_key),
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def _active_ids() -> dict[str, str | None]:
    return {
        "llm": settings.llm_profile_id,
        "embedding": settings.embedding_profile_id,
        "reranker": settings.reranker_profile_id,
    }


def _embedding_fingerprint(row: ModelProfile) -> tuple:
    return (row.provider, row.model, row.encrypted_api_key, tuple(sorted((row.params or {}).items())))


def registry_state(session: Session) -> dict:
    from app.embeddings import embedding_runtime

    runtime_status = embedding_runtime.status()
    rows = list(session.scalars(select(ModelProfile).order_by(ModelProfile.created_at, ModelProfile.name)))
    by_id = {row.id: row for row in rows}

    selected_embedding = settings.embedding_profile_id
    running_id = _running_embedding["profile_id"]
    if selected_embedding != running_id:
        restart_required = True
    elif selected_embedding is None:
        restart_required = False
    else:
        row = by_id.get(selected_embedding)
        restart_required = row is not None and _embedding_fingerprint(row) != _running_embedding["fingerprint"]

    return {
        "profiles": [serialize_profile(row) for row in rows],
        "active": _active_ids(),
        "embedding_runtime": {
            "provider": settings.embedding_provider,
            "model": settings.embedding_model,
            "profile_id": running_id,
            "vector_dim": settings.vector_dim,
            "restart_required": restart_required,
            "status": runtime_status["state"],
            # Lý do profile đã chọn không được áp (khởi động lại không tự hết), hoặc lý do
            # embedder đang chạy không dùng được.
            "load_error": _running_embedding["error"] or runtime_status["reason"],
        },
        "env_defaults": {
            "llm": {"provider": _INITIAL_SETTINGS["llm_provider"], "model": _env_llm_model()},
            "embedding": {
                "provider": _INITIAL_SETTINGS["embedding_provider"],
                "model": _INITIAL_SETTINGS["embedding_model"],
            },
            "reranker": {"provider": "heuristic", "model": None},
        },
        "secret_encryption_enabled": is_secret_encryption_configured(),
    }


def _env_llm_model() -> str | None:
    provider = str(_INITIAL_SETTINGS["llm_provider"]).lower()
    if provider in ("gemini", "google"):
        return _INITIAL_SETTINGS["gemini_model"]
    if provider in ("azure", "azure_openai"):
        return _INITIAL_SETTINGS["azure_openai_deployment_name"]
    if provider == "openai":
        return _INITIAL_SETTINGS["openai_model"]
    return _INITIAL_SETTINGS["openai_compatible_model"]


# ==========================================
# Áp profile vào settings (gọi trong settings_transaction)
# ==========================================
def _restore_llm_env() -> None:
    for field in config_store.LLM_PROFILE_FIELDS:
        setattr(settings, field, _INITIAL_SETTINGS[field])
    settings.llm_profile_id = None


def _apply_llm(row: ModelProfile) -> None:
    params = row.params or {}
    # Allowlist có thể đã bị thu hẹp sau khi lưu profile.
    for field in _URL_FIELDS:
        validate_llm_url(params.get(field))
    key = _profile_key_or_422(row)

    # Về `.env` trước để override không giữ trường của nhà cung cấp cũ.
    _restore_llm_env()
    provider = row.provider
    if key is None and provider in _LLM_ENV_KEY_FALLBACK:
        key = _INITIAL_SETTINGS[_LLM_KEY_FIELDS[provider]]
    setattr(settings, _LLM_KEY_FIELDS[provider], key)
    if provider == "openai":
        settings.openai_model = row.model
        settings.openai_base_url = params.get("base_url")
    elif provider == "gemini":
        settings.gemini_model = row.model
    elif provider == "azure":
        settings.azure_openai_endpoint = params.get("endpoint")
        settings.azure_openai_deployment_name = params.get("deployment_name")
        settings.azure_openai_api_version = params.get("api_version")
    else:
        settings.openai_compatible_base_url = params.get("base_url")
        settings.openai_compatible_model = row.model
    settings.llm_provider = provider
    settings.llm_profile_id = row.id


def _apply_reranker(row: ModelProfile | None) -> None:
    if row is None:
        settings.reranker_provider = "heuristic"
        settings.reranker_model = _INITIAL_SETTINGS["reranker_model"]
        settings.reranker_base_url = _INITIAL_SETTINGS["reranker_base_url"]
        settings.reranker_api_key = _INITIAL_SETTINGS["reranker_api_key"]
        settings.reranker_profile_id = None
        return
    base_url = (row.params or {}).get("base_url")
    # Allowlist có thể đã bị thu hẹp sau khi lưu profile.
    validate_llm_url(base_url)
    # Không dự phòng bằng RERANKER_API_KEY trong `.env`: không gửi khoá của máy chủ tới
    # Base URL do admin nhập (D-02). Cross-encoder không có khoá nên luôn là None.
    key = _profile_key_or_422(row)
    settings.reranker_provider = row.provider
    settings.reranker_model = row.model
    settings.reranker_base_url = base_url
    settings.reranker_api_key = key
    settings.reranker_profile_id = row.id


def _check_embedding_dimension(row: ModelProfile) -> None:
    dimension = (row.params or {}).get("dimension")
    if not isinstance(dimension, int) or dimension > settings.vector_dim:
        raise ConfigValidationError(
            f"'{row.name}' có {dimension} chiều, nhiều hơn VECTOR_DIM={settings.vector_dim} của kho vector. "
            "Chọn số chiều nhỏ hơn (nếu mô hình hỗ trợ) hoặc đổi VECTOR_DIM và tạo lại bảng vector."
        )


def _is_active(row: ModelProfile) -> bool:
    return _active_ids()[row.kind] == row.id


# ==========================================
# Ghi
# ==========================================
def _commit(session: Session) -> None:
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ProfileConflict("Đã có mô hình cùng tên trong mục này.") from exc


def create_profile(session: Session, kind: str, data: dict) -> ModelProfile:
    kind = _validate_kind(kind)
    name, provider, model, params = _normalize(kind, data)
    _ensure_unique_name(session, kind, name)
    api_key = _clean(data.get("api_key"))
    if api_key and (kind, provider) not in _KEYED:
        raise ConfigValidationError("Mô hình chạy cục bộ này không dùng API key.")
    if not api_key and (kind, provider) in _KEY_REQUIRED:
        raise ConfigValidationError("Nhập API key cho mô hình này.")
    row = ModelProfile(
        id=uuid.uuid4().hex,
        kind=kind,
        name=name,
        provider=provider,
        model=model,
        params=params,
        encrypted_api_key=encrypt_secret(api_key) if api_key else None,
    )
    session.add(row)
    _commit(session)
    return row


def update_profile(session: Session, profile_id: str, data: dict) -> ModelProfile:
    row = _get(session, profile_id)
    name, provider, model, params = _normalize(row.kind, data)
    _ensure_unique_name(session, row.kind, name, exclude_id=row.id)

    api_key = _clean(data.get("api_key"))
    keyed = (row.kind, provider) in _KEYED
    if api_key and not keyed:
        raise ConfigValidationError("Mô hình chạy cục bộ này không dùng API key.")
    # Mã hoá trước khi đổi gì: thiếu khoá mã hoá thì không chạm vào DB/settings.
    if api_key:
        encrypted = encrypt_secret(api_key)
    elif data.get("clear_api_key") or not keyed or provider != row.provider:
        # Khoá cũ thuộc nhà cung cấp cũ: không gửi nó sang nhà cung cấp mới.
        encrypted = None
    else:
        encrypted = row.encrypted_api_key
    if encrypted is None and (row.kind, provider) in _KEY_REQUIRED:
        raise ConfigValidationError("Nhập API key cho mô hình này.")

    try:
        row.name = name
        row.provider = provider
        row.model = model
        row.params = params
        row.encrypted_api_key = encrypted
        if _is_active(row) and row.kind == "llm":
            with config_store.settings_transaction(session):
                _apply_llm(row)
        elif _is_active(row) and row.kind == "reranker":
            with config_store.settings_transaction(session):
                _apply_reranker(row)
        else:
            snapshot = _embedding_snapshot()
            switched = False
            if _is_active(row):
                _check_embedding_dimension(row)
                # Tạo embedder mới trước khi lưu: không tạo được thì 422, DB không đổi.
                switched = _switch_embedding_if_changed(row)
            try:
                _commit(session)
            except BaseException:
                if switched:
                    _restore_embedding(snapshot)
                raise
    except IntegrityError as exc:
        session.rollback()
        raise ProfileConflict("Đã có mô hình cùng tên trong mục này.") from exc
    except BaseException:
        session.rollback()
        raise
    return row


def delete_profile(session: Session, profile_id: str) -> None:
    row = _get(session, profile_id)
    if _is_active(row):
        raise ProfileConflict(f"'{row.name}' đang được dùng. Chọn mô hình khác trước khi xoá.")
    session.delete(row)
    session.commit()


def activate_profile(session: Session, kind: str, profile_id: str | None) -> None:
    kind = _validate_kind(kind)
    row = _get(session, profile_id) if profile_id else None
    if row is not None and row.kind != kind:
        raise ConfigValidationError("Cấu hình này không thuộc loại mô hình được chọn.")

    if kind == "llm":
        with config_store.settings_transaction(session):
            if row is None:
                _restore_llm_env()
            else:
                _apply_llm(row)
    elif kind == "reranker":
        with config_store.settings_transaction(session):
            _apply_reranker(row)
    else:
        if row is not None:
            _check_embedding_dimension(row)
            _profile_key_or_422(row)
        snapshot = _embedding_snapshot()
        # Tạo embedder mới trước khi lưu lựa chọn (D-01): không tạo được thì 422, không đổi gì.
        switched = _switch_embedding_if_changed(row)
        try:
            with config_store.settings_transaction(session):
                settings.embedding_profile_id = row.id if row is not None else None
        except BaseException:
            if switched:
                _restore_embedding(snapshot)
            raise


def resolve_llm_test_key(session: Session, provider: str, profile_id: str | None, api_key: str | None) -> str | None:
    """Khoá dùng cho POST /model-profiles/test-llm: nhập tay > khoá profile > khoá `.env`."""
    key = _clean(api_key)
    if key:
        return key
    if profile_id:
        key = _profile_key_or_422(_get(session, profile_id))
        if key:
            return key
    if provider in _LLM_ENV_KEY_FALLBACK:
        return _INITIAL_SETTINGS[_LLM_KEY_FIELDS[provider]]
    # Giá trị OpenAICompatibleProvider tự dùng khi không có khoá; trả None thì factory
    # lấy khoá tương thích đang chạy và gửi nó sang máy chủ của profile này.
    return "not-needed"


def resolve_reranker_test_key(
    session: Session, provider: str, profile_id: str | None, api_key: str | None
) -> str | None:
    """Khoá dùng cho POST /model-profiles/test-reranker: nhập tay > khoá profile reranker > không khoá.

    Không dự phòng khoá `.env` (D-02) và chỉ lấy khoá của profile reranker cùng nhà cung cấp,
    để khoá LLM hay khoá của hãng khác không bị gửi tới dịch vụ xếp hạng lại.
    """
    key = _clean(api_key)
    if key:
        return key
    if not profile_id:
        return None
    row = _get(session, profile_id)
    if row.kind != "reranker":
        raise ConfigValidationError("Cấu hình này không phải mô hình xếp hạng lại.")
    return _profile_key_or_422(row) if row.provider == provider else None


def resolve_embedding_test_key(
    session: Session, provider: str, profile_id: str | None, api_key: str | None
) -> str | None:
    """Khoá dùng cho POST /model-profiles/test-embedding: nhập tay > khoá profile embedding
    > khoá `.env` (chỉ provider openai, giống embedder đang chạy)."""
    key = _clean(api_key)
    if key:
        return key
    if profile_id:
        row = _get(session, profile_id)
        if row.kind != "embedding":
            raise ConfigValidationError("Cấu hình này không phải mô hình nhúng.")
        # Khoá của profile chỉ gửi tới đúng nhà cung cấp của nó.
        key = _profile_key_or_422(row) if row.provider == provider else None
        if key:
            return key
    if provider == "openai":
        return _INITIAL_SETTINGS["embedding_api_key"] or _INITIAL_SETTINGS["openai_api_key"]
    return None


def resolve_list_models_key(
    session: Session, kind: str, provider: str, profile_id: str | None, api_key: str | None
) -> str | None:
    """Khoá dùng cho POST /model-profiles/list-models: nhập tay > khoá profile > khoá `.env`.

    Khoá profile chỉ lấy khi profile cùng loại và cùng nhà cung cấp. Khoá `.env` chỉ dùng cho
    nhà cung cấp mà mô hình đang chạy cũng dự phòng bằng nó (LLM OpenAI/Gemini, embedding OpenAI).
    """
    key = _clean(api_key)
    if key:
        return key
    if profile_id:
        row = _get(session, profile_id)
        if row.kind != kind:
            raise ConfigValidationError("Cấu hình này không thuộc loại mô hình được chọn.")
        key = _profile_key_or_422(row) if row.provider == provider else None
        if key:
            return key
    if kind == "llm" and provider in _LLM_ENV_KEY_FALLBACK:
        return _INITIAL_SETTINGS[_LLM_KEY_FIELDS[provider]]
    if kind == "embedding" and provider == "openai":
        return _INITIAL_SETTINGS["embedding_api_key"] or _INITIAL_SETTINGS["openai_api_key"]
    return None


# ==========================================
# Khởi động
# ==========================================
# Trường settings mà profile embedding đặt khi được áp.
_EMBEDDING_SETTINGS_FIELDS = (
    "embedding_provider",
    "embedding_model",
    "embedding_api_key",
    "embedding_base_url",
    "embedding_dimension",
)


def _set_running_embedding(profile_id: str | None, fingerprint: tuple | None, error: str | None = None) -> None:
    _running_embedding["profile_id"] = profile_id
    _running_embedding["fingerprint"] = fingerprint
    _running_embedding["error"] = error


def load_selected_embedding(session: Session) -> bool:
    """Áp profile embedding đã chọn và tạo lại embedder; trả về True nếu đã đổi.

    Không dùng được (mất profile, sai số chiều, khoá không giải mã được, không tạo được
    mô hình) thì giữ embedder `.env` (đang chạy, hoặc tạo lười ở lần dùng đầu) và ghi
    cảnh báo — không làm sập khởi động.
    """
    profile_id = settings.embedding_profile_id
    _set_running_embedding(None, None)
    if not profile_id:
        return False
    row = session.get(ModelProfile, profile_id)
    if row is None or row.kind != "embedding":
        logger.warning("Không thấy profile embedding đã chọn (%s); dùng embedding trong .env.", profile_id)
        _set_running_embedding(None, None, "Không tìm thấy cấu hình embedding đã chọn.")
        return False
    from app.embeddings import EmbeddingUnavailableError

    try:
        _load_embedding(_embedding_values(row))
    except ConfigValidationError as exc:
        logger.warning("Không dùng được embedding '%s': %s Dùng embedding trong .env.", row.name, exc)
        _set_running_embedding(None, None, str(exc))
        return False
    except EmbeddingUnavailableError as exc:
        # `reason` không chứa chuỗi lỗi thô của SDK nên an toàn để ghi log và hiện cho admin.
        logger.warning("Không tạo được embedding '%s' (%s); dùng embedding trong .env.", row.name, exc.reason)
        _set_running_embedding(None, None, exc.reason)
        return False

    _set_running_embedding(row.id, _embedding_fingerprint(row))
    logger.info("Đang dùng embedding '%s' (%s · %s).", row.name, row.provider, row.model)
    return True


def _embedding_values(row: ModelProfile | None) -> tuple:
    """Giá trị ``_EMBEDDING_SETTINGS_FIELDS`` của profile (``None`` = cấu hình `.env`).

    Profile không dùng được (sai số chiều, Base URL ngoài allowlist, khoá không giải mã được)
    → ``ConfigValidationError``.
    """
    if row is None:
        return tuple(_INITIAL_SETTINGS[field] for field in _EMBEDDING_SETTINGS_FIELDS)
    params = row.params or {}
    _check_embedding_dimension(row)
    # Allowlist có thể đã bị thu hẹp sau khi lưu profile.
    validate_llm_url(params.get("base_url"))
    key = _profile_key_or_422(row)
    return (row.provider, row.model, key, params.get("base_url"), params.get("dimension"))


def _load_embedding(values: tuple) -> None:
    """Áp ``values`` vào settings và tạo lại embedder ngay.

    Lỗi thì khôi phục settings và ném ``EmbeddingUnavailableError`` (embedder cũ giữ nguyên).
    """
    from app.embeddings import EmbeddingUnavailableError, embedding_runtime

    previous = tuple(getattr(settings, field) for field in _EMBEDDING_SETTINGS_FIELDS)
    for field, value in zip(_EMBEDDING_SETTINGS_FIELDS, values):
        setattr(settings, field, value)
    try:
        embedding_runtime.load()
    except EmbeddingUnavailableError:
        for field, value in zip(_EMBEDDING_SETTINGS_FIELDS, previous):
            setattr(settings, field, value)
        raise


def _switch_embedding_if_changed(row: ModelProfile | None) -> bool:
    """Đổi embedder sang ``row`` (``None`` = `.env`) ngay nếu nó chưa là embedder đang chạy (D-01).

    Trả về True nếu đã thử đổi. Đang có embedder chạy được mà không tạo được mô hình mới →
    ``ConfigValidationError``, giữ embedder cũ; chưa có embedder chạy được thì chỉ ghi lý do
    lỗi để admin xem (như BE-13).
    """
    from app.embeddings import EmbeddingUnavailableError, embedding_runtime

    was_ready = embedding_runtime.is_ready()
    profile_id = row.id if row is not None else None
    fingerprint = _embedding_fingerprint(row) if row is not None else None
    if (
        was_ready
        and _running_embedding["profile_id"] == profile_id
        and _running_embedding["fingerprint"] == fingerprint
        and _running_embedding["error"] is None
    ):
        return False
    try:
        _load_embedding(_embedding_values(row))
    except (ConfigValidationError, EmbeddingUnavailableError) as exc:
        # `reason` không chứa chuỗi lỗi thô của SDK nên an toàn để hiện cho admin.
        reason = exc.reason if isinstance(exc, EmbeddingUnavailableError) else str(exc)
        if was_ready:
            raise ConfigValidationError(f"Không chuyển được mô hình nhúng: {reason}") from exc
        logger.warning("Không tạo được embedding đã chọn: %s", reason)
        _set_running_embedding(None, None, reason)
        return True
    _set_running_embedding(profile_id, fingerprint)
    if row is not None:
        logger.info("Đang dùng embedding '%s' (%s · %s).", row.name, row.provider, row.model)
    else:
        logger.info("Đang dùng embedding trong .env (%s · %s).", settings.embedding_provider, settings.embedding_model)
    return True


def _embedding_snapshot() -> tuple:
    return tuple(getattr(settings, field) for field in _EMBEDDING_SETTINGS_FIELDS), dict(_running_embedding)


def _restore_embedding(snapshot: tuple) -> None:
    """Lưu lựa chọn thất bại sau khi đã đổi embedder: cố quay lại embedder trước đó."""
    from app.embeddings import EmbeddingUnavailableError

    values, running = snapshot
    try:
        _load_embedding(values)
    except EmbeddingUnavailableError as exc:
        logger.warning("Không khôi phục được embedder trước đó: %s", exc.reason)
    _running_embedding.update(running)


def load_selected_embedding_at_startup() -> None:
    try:
        with config_store.SessionLocal() as session:
            load_selected_embedding(session)
    except SQLAlchemyError as exc:
        logger.warning("Không đọc được profile embedding trong DB, dùng .env: %s", exc)
