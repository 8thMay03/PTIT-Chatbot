import json
import logging
import re
import secrets
import time
import unicodedata
from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import aclosing
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import anyio
from anyio.lowlevel import RunVar
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.types import Receive, Scope, Send
from sqlalchemy.orm import Session

from app.api.schemas import (
    ActivateModelProfileRequest,
    AdminLoginRequest,
    AdminSessionResponse,
    AuthSessionResponse,
    AuthUser,
    ChatRequest,
    ChatResponse,
    ChunkAllResponse,
    ChunkItem,
    ConfigPersistenceInfo,
    ConversationDetail,
    ConversationItem,
    ConversationListResponse,
    ConversationMessage,
    ConversationMessageError,
    CreateModelProfileRequest,
    DatasetCreateRequest,
    DatasetDeleteResponse,
    DatasetItem,
    DatasetListResponse,
    DatasetParseResponse,
    DatasetUpdateRequest,
    DocumentChunksResponse,
    DocumentDeleteResponse,
    DocumentDetail,
    DocumentItem,
    DocumentListResponse,
    DocumentMarkdown,
    FullConfigResponse,
    IngestResponse,
    LoginRequest,
    ModelRegistryResponse,
    MoveDocumentsRequest,
    MoveDocumentsResponse,
    ParseJobItem,
    ParseJobListResponse,
    RegisterRequest,
    RenameConversationRequest,
    RetrievalTestRequest,
    TestLLMRequest,
    TestLLMResponse,
    TestModelProfileLLMRequest,
    UpdateConfigRequest,
    UpdateMarkdownRequest,
    UpdateModelProfileRequest,
)
from app.core import auth, model_profiles, rate_limit, user_auth
from app.core.auth import require_admin
from app.core.config import (
    PROJECT_ROOT,
    ConfigValidationError,
    get_runtime_config_dict,
    settings,
    validate_llm_url,
)
from app.core.config_crypto import SecretEncryptionUnavailable, is_secret_encryption_configured
from app.core.config_store import apply_config_update, get_config_store_session, reset_config as reset_stored_config
from app.db import check_db_health, get_session, get_session_factory
from app.db.models import Message
from app.db.repositories import (
    DatasetConflict,
    DatasetNotFound,
    add_message,
    add_message_sources,
    claim_anonymous_conversations,
    create_dataset,
    create_user,
    delete_conversation,
    delete_dataset_records,
    ensure_conversation,
    get_conversation,
    get_conversation_messages,
    get_dataset_with_stats,
    get_document_chunks,
    get_document_full_text,
    get_document_preview_text,
    get_document_with_chunk_count,
    get_enabled_dataset_ids,
    get_owned_conversation,
    get_recent_conversation_history,
    get_user_by_email,
    list_conversations,
    list_datasets_with_stats,
    list_documents,
    rename_conversation,
    serialize_document,
    serialize_markdown,
    update_dataset,
    update_message_metadata,
)
from app.embeddings import EmbeddingUnavailableError, embedding_runtime
from app.generation.citations import public_citations
from app.generation.llm import (
    _normalize_answer_citations,
    stream_answer_deltas_with_llm,
)
from app.generation.rag_chain import rag_chain
from app.generation.refusal import NO_CONTEXT_ANSWER, is_refusal
from app.guardrails import OUT_OF_SCOPE_ANSWER, filter_safe_history
from app.ingestion import ingestion_pipeline
from app.ingestion.jobs import ParseJob, ParseJobConflict, parse_jobs
from app.ingestion.pipeline import DatasetConflict as PipelineDatasetConflict
from app.ingestion.pipeline import DatasetNotFound as PipelineDatasetNotFound
from app.ingestion.pipeline import DocumentStateError
from app.ingestion.uploads import (
    PREVIEW_CHAR_LIMIT,
    DocumentUploadError,
    read_preview,
    resolve_source_path,
)
from app.llm import CONTENT_DELTA, REASONING_DELTA, LLMBudget, LLMStreamError, StreamDelta, describe_error
from app.llm.factory import create_llm_provider_from_config
from app.parsers import (
    DocumentParseError,
    read_document_text,
    registry,
    resolve_parser_name,
)
from app.retrieval.bm25 import invalidate_bm25_cache

logger = logging.getLogger(__name__)
router = APIRouter()

# Route API công khai (prefix /api) theo plan FE-06. Route mới mặc định KHÔNG
# được thêm vào đây: phải gắn require_admin hoặc thêm vào danh sách này một cách
# có chủ đích; test quét app.routes (test_admin_auth) bảo đảm điều đó.
PUBLIC_API_ROUTES: frozenset[tuple[str, str]] = frozenset(
    {
        ("GET", "/api/health"),
        ("POST", "/api/chat"),
        ("POST", "/api/chat/stream"),
        ("GET", "/api/conversations"),
        ("GET", "/api/conversations/{conversation_id}"),
        ("PATCH", "/api/conversations/{conversation_id}"),
        ("DELETE", "/api/conversations/{conversation_id}"),
        ("POST", "/api/admin/login"),
        ("POST", "/api/admin/logout"),
        ("GET", "/api/admin/session"),
        ("POST", "/api/auth/register"),
        ("POST", "/api/auth/login"),
        ("POST", "/api/auth/logout"),
        ("GET", "/api/auth/me"),
    }
)


@router.get("/health")
def health() -> dict[str, Any]:
    # Luôn HTTP 200 khi DB ổn (healthcheck docker chỉ xét mã HTTP). Route công khai nên
    # chỉ trả trạng thái embedding, không trả lý do lỗi (admin xem ở /model-profiles).
    db_health = check_db_health()
    embedding_state = embedding_runtime.status()["state"]
    is_ok = db_health.get("status") == "ok" and embedding_state == "ready"
    return {
        "status": "ok" if is_ok else "degraded",
        "database": db_health.get("database", "unknown"),
        "database_type": db_health.get("dialect", "unknown"),
        "embedding": embedding_state,
    }


# Mô hình nhúng chưa cấu hình hoặc lỗi (BE-13): chat công khai chỉ báo chung chung,
# route admin kèm lý do (không chứa chuỗi lỗi thô của SDK).
CHAT_EMBEDDING_UNAVAILABLE_DETAIL = (
    "Chatbot chưa sẵn sàng: mô hình nhúng (embedding) chưa được cấu hình hoặc đang lỗi. "
    "Vui lòng liên hệ quản trị viên."
)


def _embedding_unavailable(exc: EmbeddingUnavailableError) -> HTTPException:
    return HTTPException(status_code=503, detail=f"Mô hình nhúng chưa sẵn sàng: {exc.reason}")


# ==========================================
# Phiên quản trị (FE-06)
# ==========================================
ADMIN_NOT_CONFIGURED_DETAIL = "Chưa cấu hình ADMIN_EMAIL và ADMIN_PASSWORD."
# Dùng chung với đăng nhập người dùng để không lộ email nào là tài khoản admin.
USER_LOGIN_FAILED_DETAIL = "Email hoặc mật khẩu không đúng."
USER_THROTTLED_DETAIL = "Quá nhiều lần thử. Vui lòng thử lại sau ít phút."


def _admin_sign_in(request: Request, response: Response, email: str, password: str) -> float:
    """Kiểm email + mật khẩu admin, gắn cookie ptit_admin; trả thời điểm hết hạn.

    Chặn dò theo IP (``admin_login_limiter``); email không phải admin cũng tính là sai.
    """
    if auth.is_login_throttled(request):
        raise HTTPException(status_code=429, detail=USER_THROTTLED_DETAIL)
    # Mật khẩu admin so sánh hằng thời gian (rất nhanh); băm giả để thời gian phản hồi
    # giống đăng nhập người dùng, không dò được email admin qua thời gian.
    user_auth.burn_password_check(password)
    if not (auth.is_admin_email(email) and auth.verify_admin_password(password)):
        auth.register_failed_login(request)
        raise HTTPException(status_code=401, detail=USER_LOGIN_FAILED_DETAIL)
    auth.register_successful_login(request)
    token, expires_at = auth.issue_admin_session()
    auth.issue_admin_cookie(response, token)
    return expires_at


@router.post("/admin/login", response_model=AdminSessionResponse)
def admin_login(
    payload: AdminLoginRequest,
    request: Request,
    response: Response,
) -> AdminSessionResponse:
    """Đăng nhập lại tại lớp phủ hết phiên của /admin (trang đầy đủ dùng /auth/login)."""
    if not auth.is_admin_configured():
        raise HTTPException(status_code=503, detail=ADMIN_NOT_CONFIGURED_DETAIL)
    expires_at = _admin_sign_in(request, response, payload.email, payload.password)
    return AdminSessionResponse(
        authenticated=True,
        expires_at=auth.iso_expires_at(expires_at),
        configured=True,
    )


@router.post("/admin/logout", response_model=AdminSessionResponse)
def admin_logout(response: Response) -> AdminSessionResponse:
    # Server không lưu phiên; đăng xuất chỉ xoá cookie và luôn thành công.
    auth.clear_admin_cookie(response)
    return AdminSessionResponse(authenticated=False, configured=auth.is_admin_configured())


@router.get("/admin/session", response_model=AdminSessionResponse)
def get_admin_session(request: Request) -> AdminSessionResponse:
    """Route công khai: trả trạng thái phiên, không bao giờ 401."""
    expires_at = auth.verify_admin_token(request.cookies.get(auth.ADMIN_COOKIE_NAME))
    return AdminSessionResponse(
        authenticated=expires_at is not None and auth.is_admin_configured(),
        expires_at=auth.iso_expires_at(expires_at) if expires_at is not None else None,
        configured=auth.is_admin_configured(),
    )


# ==========================================
# Tài khoản người dùng (landing-user-auth)
# ==========================================
EMAIL_TAKEN_DETAIL = "Email đã được đăng ký."


def _auth_session_payload(user=None) -> AuthSessionResponse:
    return AuthSessionResponse(
        authenticated=user is not None,
        user=(
            AuthUser(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                created_at=user.created_at,
            )
            if user is not None
            else None
        ),
        registration_enabled=settings.user_registration_enabled,
    )


def _sign_in(session: Session, http_request: Request, response: Response, user) -> None:
    """Gắn cookie người dùng và chuyển hội thoại ẩn danh của trình duyệt này sang tài khoản.

    Gọi trước commit để chuyển hội thoại nằm cùng transaction với tạo user/cập nhật login.
    """
    client = auth.get_client_session(http_request)
    claim_anonymous_conversations(session, client.anon_owner_key, user_auth.user_owner_key(user.id))
    # Giữ ptit_sid (cấp mới nếu chưa có) để đăng xuất quay về ẩn danh.
    client.apply(response)
    user_auth.issue_user_cookie(response, user)


@router.post("/auth/register", response_model=AuthSessionResponse, status_code=201)
def register_user(
    payload: RegisterRequest,
    http_request: Request,
    response: Response,
    session: Session = Depends(get_session),
) -> AuthSessionResponse:
    if not settings.user_registration_enabled:
        raise HTTPException(status_code=503, detail="Hệ thống đang tạm dừng đăng ký tài khoản mới.")
    ip_key = auth.client_ip(http_request)
    if auth.user_register_limiter.is_blocked(ip_key):
        raise HTTPException(status_code=429, detail=USER_THROTTLED_DETAIL)
    # Email của admin coi như đã có tài khoản: /auth/login luôn nhận email đó là admin.
    if auth.is_admin_email(payload.email) or get_user_by_email(session, payload.email) is not None:
        auth.user_register_limiter.record_failure(ip_key)
        raise HTTPException(status_code=409, detail=EMAIL_TAKEN_DETAIL)

    password_hash = user_auth.hash_password(payload.password)
    try:
        user = create_user(
            session, email=payload.email, full_name=payload.full_name, password_hash=password_hash
        )
        _sign_in(session, http_request, response, user)
        session.commit()
    except IntegrityError as exc:
        # Hai request đăng ký cùng email chạy song song: unique constraint chặn bản thứ hai.
        session.rollback()
        auth.user_register_limiter.record_failure(ip_key)
        raise HTTPException(status_code=409, detail=EMAIL_TAKEN_DETAIL) from exc
    session.refresh(user)
    return _auth_session_payload(user)


@router.post("/auth/login", response_model=AuthSessionResponse)
def login_user(
    payload: LoginRequest,
    http_request: Request,
    response: Response,
    session: Session = Depends(get_session),
) -> AuthSessionResponse:
    """Trang /login dùng chung: email trùng ADMIN_EMAIL cấp phiên admin, còn lại là người dùng."""
    if auth.is_admin_email(payload.email):
        # Chỉ gắn cookie admin: không cấp phiên người dùng, không chuyển hội thoại ẩn danh.
        expires_at = _admin_sign_in(http_request, response, payload.email, payload.password)
        session_payload = _auth_session_payload(None)
        session_payload.admin = True
        session_payload.admin_expires_at = auth.iso_expires_at(expires_at)
        return session_payload

    throttle_key = auth.user_login_key(http_request, payload.email)
    if auth.user_login_limiter.is_blocked(throttle_key):
        raise HTTPException(status_code=429, detail=USER_THROTTLED_DETAIL)

    user = get_user_by_email(session, payload.email)
    if user is None:
        # Vẫn băm một lần để thời gian phản hồi không lộ email nào đã đăng ký.
        user_auth.burn_password_check(payload.password)
        verified = False
    else:
        verified = user_auth.verify_password(payload.password, user.password_hash)
    if not verified:
        auth.user_login_limiter.record_failure(throttle_key)
        raise HTTPException(status_code=401, detail=USER_LOGIN_FAILED_DETAIL)

    auth.user_login_limiter.clear(throttle_key)
    user.last_login_at = datetime.now(timezone.utc)
    _sign_in(session, http_request, response, user)
    session.commit()
    return _auth_session_payload(user)


@router.post("/auth/logout", response_model=AuthSessionResponse)
def logout_user(response: Response) -> AuthSessionResponse:
    # Không lưu phiên phía server: xoá cookie và luôn thành công. Cấp ptit_sid mới để
    # trình duyệt bắt đầu phiên ẩn danh khác, không gắn với phiên trước khi đăng nhập.
    user_auth.clear_user_cookie(response)
    auth.issue_fresh_anon_session(response)
    return _auth_session_payload(None)


@router.get("/auth/me", response_model=AuthSessionResponse)
def get_current_user(
    http_request: Request,
    session: Session = Depends(get_session),
) -> AuthSessionResponse:
    """Route công khai: cookie sai/hết hạn/user đã xoá đều là chưa đăng nhập, không 401."""
    return _auth_session_payload(user_auth.resolve_user(http_request, session))


@router.get("/config", response_model=FullConfigResponse, dependencies=[Depends(require_admin)])
def get_config() -> FullConfigResponse:
    return _config_response(get_runtime_config_dict())


def _config_response(data: dict) -> FullConfigResponse:
    return FullConfigResponse(
        **data,
        persistence=ConfigPersistenceInfo(secret_encryption_enabled=is_secret_encryption_configured()),
    )


@router.put("/config", response_model=FullConfigResponse, dependencies=[Depends(require_admin)])
def update_config(
    request: UpdateConfigRequest,
    session: Session = Depends(get_config_store_session),
) -> FullConfigResponse:
    """Áp và lưu cấu hình vào DB; mọi lỗi đều để cấu hình đang chạy như trước request."""
    payload = request.model_dump(exclude_unset=True)
    try:
        updated = apply_config_update(session, payload)
    except (ConfigValidationError, SecretEncryptionUnavailable) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        logger.exception("Không lưu được cấu hình vào DB")
        raise HTTPException(
            status_code=503,
            detail="Không lưu được cấu hình vào cơ sở dữ liệu; cấu hình chưa thay đổi.",
        ) from exc
    return _config_response(updated)


@router.post("/config/reset", response_model=FullConfigResponse, dependencies=[Depends(require_admin)])
def reset_config(session: Session = Depends(get_config_store_session)) -> FullConfigResponse:
    try:
        reset_data = reset_stored_config(session)
    except SQLAlchemyError as exc:
        logger.exception("Không xoá được cấu hình đã lưu trong DB")
        raise HTTPException(
            status_code=503,
            detail="Không xoá được cấu hình đã lưu trong cơ sở dữ liệu; cấu hình chưa thay đổi.",
        ) from exc
    return _config_response(reset_data)


@router.post("/config/test-llm", response_model=TestLLMResponse, dependencies=[Depends(require_admin)])
def test_llm(request: TestLLMRequest) -> TestLLMResponse:
    _validate_test_llm_urls(request)
    return _run_llm_test(request, request.api_key)


def _validate_test_llm_urls(request: TestLLMRequest) -> None:
    # Kiểm URL trước khi tạo provider: request ngoài allowlist bị từ chối, key
    # đang lưu không bao giờ được gửi tới host lạ.
    try:
        validate_llm_url(request.base_url)
        validate_llm_url(request.endpoint)
    except ConfigValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _run_llm_test(request: TestLLMRequest, api_key: str | None) -> TestLLMResponse:
    start_time = time.perf_counter()
    try:
        provider_instance = create_llm_provider_from_config(
            provider=request.provider,
            model=request.model,
            api_key=api_key,
            base_url=request.base_url,
            endpoint=request.endpoint,
            deployment_name=request.deployment_name,
            api_version=request.api_version,
            timeout=15.0,
        )
        if not provider_instance.is_configured():
            return TestLLMResponse(
                success=False,
                message=f"Provider '{request.provider}' chưa được cấu hình API Key hoặc Endpoint.",
            )

        prompt_messages = [
            {"role": "system", "content": "You are a test assistant."},
            {"role": "user", "content": "Reply with 'OK PTIT' in 3 words or less."},
        ]
        output = provider_instance.generate(prompt_messages, max_tokens=15, temperature=0.0)
        latency_ms = round((time.perf_counter() - start_time) * 1000, 1)
        return TestLLMResponse(
            success=True,
            message=f"Kết nối thành công tới {request.provider} ({request.model or 'mặc định'}).",
            latency_ms=latency_ms,
            sample_output=output.strip(),
        )
    except Exception as exc:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 1)
        return TestLLMResponse(
            success=False,
            message=f"Lỗi khi kết nối tới {request.provider}: {str(exc)}",
            latency_ms=latency_ms,
        )



# ==========================================
# Kho mô hình (model-registry)
# ==========================================
def _registry_response(session: Session) -> ModelRegistryResponse:
    return ModelRegistryResponse(**model_profiles.registry_state(session))


def _run_registry_write(session: Session, action) -> ModelRegistryResponse:
    """Chạy thao tác ghi kho mô hình và đổi lỗi sang HTTP; lỗi thì DB/settings như trước."""
    try:
        action()
    except model_profiles.ProfileNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except model_profiles.ProfileConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (ConfigValidationError, SecretEncryptionUnavailable) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        logger.exception("Không lưu được kho mô hình vào DB")
        raise HTTPException(
            status_code=503,
            detail="Không lưu được cấu hình mô hình vào cơ sở dữ liệu; chưa có gì thay đổi.",
        ) from exc
    return _registry_response(session)


@router.get("/model-profiles", response_model=ModelRegistryResponse, dependencies=[Depends(require_admin)])
def list_model_profiles(session: Session = Depends(get_config_store_session)) -> ModelRegistryResponse:
    return _registry_response(session)


@router.post(
    "/model-profiles",
    response_model=ModelRegistryResponse,
    status_code=201,
    dependencies=[Depends(require_admin)],
)
def create_model_profile(
    request: CreateModelProfileRequest,
    session: Session = Depends(get_config_store_session),
) -> ModelRegistryResponse:
    data = request.model_dump(exclude={"kind"})
    return _run_registry_write(session, lambda: model_profiles.create_profile(session, request.kind, data))


@router.post(
    "/model-profiles/activate",
    response_model=ModelRegistryResponse,
    dependencies=[Depends(require_admin)],
)
def activate_model_profile(
    request: ActivateModelProfileRequest,
    session: Session = Depends(get_config_store_session),
) -> ModelRegistryResponse:
    return _run_registry_write(
        session, lambda: model_profiles.activate_profile(session, request.kind, request.profile_id)
    )


@router.post(
    "/model-profiles/test-llm",
    response_model=TestLLMResponse,
    dependencies=[Depends(require_admin)],
)
def test_model_profile_llm(
    request: TestModelProfileLLMRequest,
    session: Session = Depends(get_config_store_session),
) -> TestLLMResponse:
    _validate_test_llm_urls(request)
    try:
        api_key = model_profiles.resolve_llm_test_key(
            session, request.provider, request.profile_id, request.api_key
        )
    except model_profiles.ProfileNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ConfigValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _run_llm_test(request, api_key)


@router.put(
    "/model-profiles/{profile_id}",
    response_model=ModelRegistryResponse,
    dependencies=[Depends(require_admin)],
)
def update_model_profile(
    profile_id: str,
    request: UpdateModelProfileRequest,
    session: Session = Depends(get_config_store_session),
) -> ModelRegistryResponse:
    data = request.model_dump()
    return _run_registry_write(session, lambda: model_profiles.update_profile(session, profile_id, data))


@router.delete(
    "/model-profiles/{profile_id}",
    response_model=ModelRegistryResponse,
    dependencies=[Depends(require_admin)],
)
def delete_model_profile(
    profile_id: str,
    session: Session = Depends(get_config_store_session),
) -> ModelRegistryResponse:
    return _run_registry_write(session, lambda: model_profiles.delete_profile(session, profile_id))


@router.post("/retrieval/test", dependencies=[Depends(require_admin)])
def test_retrieval(request: RetrievalTestRequest) -> dict:
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query must not be empty.")
    try:
        result = rag_chain.retrieve_context(
            request.query, top_k=request.top_k, dataset_ids=request.dataset_ids
        )
    except EmbeddingUnavailableError as exc:
        raise _embedding_unavailable(exc) from exc
    return {
        "query": request.query,
        "contexts": result.get("contexts", []),
        "retrieval_debug": result.get("retrieval_debug", {}),
        "strong_context": result.get("strong_context", False),
    }


@router.post("/ingest", response_model=IngestResponse, dependencies=[Depends(require_admin)])
def ingest() -> IngestResponse:
    try:
        result = ingestion_pipeline.ingest_documents()
    except DocumentParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except EmbeddingUnavailableError as exc:
        raise _embedding_unavailable(exc) from exc
    return IngestResponse(**result)


@router.post("/ingest/chunk", response_model=ChunkAllResponse, dependencies=[Depends(require_admin)])
def chunk_all_documents() -> ChunkAllResponse:
    """Re-chunk every document from its stored Markdown, e.g. after changing chunk settings."""
    try:
        result = ingestion_pipeline.chunk_documents()
    except DocumentStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except EmbeddingUnavailableError as exc:
        raise _embedding_unavailable(exc) from exc
    return ChunkAllResponse(**result)


@router.get("/documents", response_model=DocumentListResponse, dependencies=[Depends(require_admin)])
def get_documents(
    dataset_id: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> DocumentListResponse:
    if dataset_id is not None:
        from app.db.models import Dataset as _Dataset

        if session.get(_Dataset, dataset_id) is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy dataset.")
    documents = [
        DocumentItem(**_document_payload(document, chunk_count))
        for document, chunk_count in list_documents(session, dataset_id=dataset_id)
    ]
    return DocumentListResponse(documents=documents)


@router.get("/documents/{document_id}", response_model=DocumentDetail, dependencies=[Depends(require_admin)])
def get_document(document_id: str, session: Session = Depends(get_session)) -> DocumentDetail:
    row = get_document_with_chunk_count(session, document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")

    document, chunk_count = row
    source_p = resolve_source_path(document.source_path)
    if document.parsed_text is not None:
        # The stored parse result (or manual edit) is exactly what the chunk step reads.
        full_text = document.parsed_text
        preview = full_text
        if len(preview) > PREVIEW_CHAR_LIMIT:
            preview = preview[:PREVIEW_CHAR_LIMIT].rstrip() + "…"
    else:
        # Documents indexed before parse results were stored in the database.
        full_text, preview = _legacy_document_text(session, document, source_p)

    # Tự động đồng bộ lại source_path nếu file nằm ở thư mục con khác với đường dẫn cũ trong DB
    if source_p is not None and source_p.is_file():
        try:
            rel_posix = source_p.relative_to(PROJECT_ROOT.resolve()).as_posix()
            if rel_posix != document.source_path:
                document.source_path = rel_posix
                session.commit()
        except Exception:
            pass

    return DocumentDetail(**_document_payload(document, chunk_count), preview=preview, full_text=full_text)


def _legacy_document_text(session: Session, document, source_p: Path | None) -> tuple[str | None, str | None]:
    stored_parser = (document.document_metadata or {}).get("parser")
    full_text = None
    if source_p is not None and source_p.is_file():
        try:
            parser_name = resolve_parser_name(source_p, stored_parser)
            full_text = read_document_text(source_p, convert=False, parser_name=parser_name)
        except Exception:
            full_text = None

    if not full_text:
        full_text = get_document_full_text(session, document.id)

    preview = read_preview(document.source_path, parser_name=stored_parser) or get_document_preview_text(
        session, document.id
    )
    if not full_text:
        full_text = preview
    return full_text, preview


@router.get("/documents/{document_id}/chunks", response_model=DocumentChunksResponse, dependencies=[Depends(require_admin)])
def get_document_chunks_api(
    document_id: str,
    offset: int = 0,
    limit: int = 200,
    session: Session = Depends(get_session),
) -> DocumentChunksResponse:
    row = get_document_with_chunk_count(session, document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")

    document, chunk_count = row
    chunk_models = get_document_chunks(session, document_id, offset=offset, limit=limit)
    items = [
        ChunkItem(
            id=c.id,
            document_id=c.document_id,
            chunk_index=c.chunk_index,
            text=c.text,
            token_count=c.token_count,
            chunk_metadata=c.chunk_metadata,
            created_at=c.created_at,
        )
        for c in chunk_models
    ]
    return DocumentChunksResponse(total=chunk_count, chunks=items)


@router.get("/documents/{document_id}/file", dependencies=[Depends(require_admin)])
def download_document(
    document_id: str,
    inline: bool = Query(default=False),
    session: Session = Depends(get_session),
) -> FileResponse:
    row = get_document_with_chunk_count(session, document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")

    document, _chunk_count = row
    path = resolve_source_path(document.source_path)
    if path is None or not path.is_file():
        raise HTTPException(status_code=404, detail="File nguồn không còn trên đĩa.")

    media_type = "text/plain; charset=utf-8" if path.suffix.lower() in {".md", ".txt"} else None
    # inline: trình duyệt hiển thị bản gốc (vd. trình xem PDF) thay vì tải xuống.
    # nosniff giữ đúng kiểu đã khai báo để tệp người dùng tải lên không bị đoán thành HTML.
    return FileResponse(
        path,
        filename=path.name,
        media_type=media_type,
        content_disposition_type="inline" if inline else "attachment",
        headers={"X-Content-Type-Options": "nosniff"},
    )


@router.get("/parsers", dependencies=[Depends(require_admin)])
def parsers_for_file(file_name: str = Query(min_length=1)) -> dict:
    """Parsers able to read a file that has not been uploaded yet, by its extension."""
    return {"parsers": registry.list_parsers(Path(file_name))}


@router.post("/documents", response_model=ParseJobItem, status_code=202, dependencies=[Depends(require_admin)])
def upload_document(
    file: UploadFile = File(...),
    parser_name: str | None = Form(default=None, min_length=1),
    dataset_id: str = Form(min_length=1),
    session: Session = Depends(get_session),
) -> ParseJobItem:
    """Validate and stage the upload, then parse it in a background job.

    Only the cheap validation and the staging write happen before the response;
    conversion/parse of large PDFs no longer blocks the client. The source file
    is published into DOCUMENTS_PATH by the job after parsing and committing.
    """
    from app.db.models import Dataset as _Dataset

    if session.get(_Dataset, dataset_id) is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy dataset.")
    try:
        options = {"parser_name": parser_name} if parser_name is not None else {}
        job = parse_jobs.enqueue_upload(
            file.filename or "", file.file.read(), dataset_id=dataset_id, **options
        )
    except DocumentUploadError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except ParseJobConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return _parse_job_payload(job)


@router.get("/parse-jobs", response_model=ParseJobListResponse, dependencies=[Depends(require_admin)])
def list_parse_jobs(
    document_id: str | None = Query(default=None),
    dataset_id: str | None = Query(default=None),
    active_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
) -> ParseJobListResponse:
    jobs = parse_jobs.list(
        document_id=document_id, dataset_id=dataset_id, active_only=active_only, limit=limit
    )
    return ParseJobListResponse(jobs=[_parse_job_payload(job) for job in jobs])


@router.get("/parse-jobs/{job_id}", response_model=ParseJobItem, dependencies=[Depends(require_admin)])
def get_parse_job(job_id: str) -> ParseJobItem:
    job = parse_jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy job parse.")
    return _parse_job_payload(job)


@router.get("/documents/{document_id}/parsers", dependencies=[Depends(require_admin)])
def document_parsers(document_id: str, session: Session = Depends(get_session)) -> dict:
    row = get_document_with_chunk_count(session, document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return {"parsers": registry.list_parsers(Path(row[0].source_path))}


@router.post("/documents/{document_id}/parse", response_model=ParseJobItem, status_code=202, dependencies=[Depends(require_admin)])
def parse_single_document(document_id: str, session: Session = Depends(get_session), parser_name: str | None = Query(default=None, min_length=1)) -> ParseJobItem:
    row = get_document_with_chunk_count(session, document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")
    document, _chunk_count = row
    path = resolve_source_path(document.source_path)
    if path is None or not path.is_file():
        raise HTTPException(status_code=404, detail="File nguồn không tồn tại trên đĩa.")

    try:
        options = {"parser_name": parser_name} if parser_name is not None else {}
        job = parse_jobs.enqueue_parse(
            document.id,
            path,
            file_name=Path(document.source_path).name,
            **options,
        )
    except ParseJobConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _parse_job_payload(job)


@router.post("/documents/{document_id}/chunk", response_model=DocumentItem, dependencies=[Depends(require_admin)])
def chunk_single_document(document_id: str) -> DocumentItem:
    try:
        result = ingestion_pipeline.chunk_document(document_id)
    except DocumentStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except EmbeddingUnavailableError as exc:
        raise _embedding_unavailable(exc) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")
    return DocumentItem(**result)


@router.get("/documents/{document_id}/markdown", response_model=DocumentMarkdown, dependencies=[Depends(require_admin)])
def get_document_markdown(document_id: str, session: Session = Depends(get_session)) -> DocumentMarkdown:
    row = get_document_with_chunk_count(session, document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")
    document = row[0]
    if document.parsed_text is None:
        raise HTTPException(
            status_code=409, detail="Tài liệu chưa có bản parse đã lưu; hãy parse lại trước khi sửa Markdown."
        )
    return DocumentMarkdown(**serialize_markdown(document))


@router.get("/documents/{document_id}/markdown/download", dependencies=[Depends(require_admin)])
def download_document_markdown(document_id: str, session: Session = Depends(get_session)) -> Response:
    """Tải bản Markdown đã lưu của một tài liệu dưới dạng file `.md`.

    Dùng cho nút tải Markdown trong dataset: nội dung đúng `parsed_text` mà
    bước chia đoạn đọc (kể cả bản sửa tay). Chưa có Markdown thì 409 giống
    `GET /markdown` để client báo parse lại trước.
    """
    row = get_document_with_chunk_count(session, document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")
    document = row[0]
    if document.parsed_text is None:
        raise HTTPException(
            status_code=409, detail="Tài liệu chưa có bản parse đã lưu; hãy parse lại trước khi tải Markdown."
        )
    stem = Path(document.source_path or "").stem or document.id
    safe_stem = "".join(ch for ch in stem if ch not in {'"', "\r", "\n"}).strip() or document.id
    filename_utf8 = f"{safe_stem}.md"
    # Header latin-1 của Starlette không chứa được tiếng Việt trong `filename`,
    # nên `filename` dùng bản ASCII còn tên đầy đủ nằm ở `filename*` (RFC 5987).
    ascii_stem = re.sub(
        r"[^A-Za-z0-9._-]+",
        "_",
        unicodedata.normalize("NFKD", safe_stem.replace("đ", "d").replace("Đ", "D"))
        .encode("ascii", "ignore")
        .decode("ascii"),
    ).strip("._-") or document.id
    filename_ascii = f"{ascii_stem}.md"
    return Response(
        content=document.parsed_text.encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename_ascii}"; filename*=UTF-8\'\'{quote(filename_utf8)}',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.put("/documents/{document_id}/markdown", response_model=DocumentMarkdown, dependencies=[Depends(require_admin)])
def update_document_markdown(document_id: str, request: UpdateMarkdownRequest) -> DocumentMarkdown:
    """Save a manual Markdown fix; the document then waits in "parsed" to be chunked."""
    try:
        result = ingestion_pipeline.save_markdown(document_id, request.text, base_hash=request.base_hash)
    except DocumentStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")
    return DocumentMarkdown(**result)


@router.delete("/documents/{document_id}", response_model=DocumentDeleteResponse, dependencies=[Depends(require_admin)])
def remove_document(document_id: str) -> DocumentDeleteResponse:
    result = ingestion_pipeline.delete_ingested_document(document_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")
    return DocumentDeleteResponse(**result)


@router.post("/documents/move", response_model=MoveDocumentsResponse, dependencies=[Depends(require_admin)])
def move_documents(request: MoveDocumentsRequest) -> MoveDocumentsResponse:
    try:
        result = ingestion_pipeline.move_documents(request.document_ids, request.dataset_id)
    except (PipelineDatasetNotFound, DatasetNotFound) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (PipelineDatasetConflict, DatasetConflict) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return MoveDocumentsResponse(**result)


# ==========================================
# Dataset (multi-dataset)
# ==========================================
def _dataset_error_to_http(exc: Exception) -> HTTPException:
    if isinstance(exc, DatasetNotFound):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=409, detail=str(exc))


@router.get("/datasets", response_model=DatasetListResponse, dependencies=[Depends(require_admin)])
def list_datasets_api(session: Session = Depends(get_session)) -> DatasetListResponse:
    return DatasetListResponse(
        datasets=[DatasetItem(**item) for item in list_datasets_with_stats(session)]
    )


@router.post("/datasets", response_model=DatasetItem, status_code=201, dependencies=[Depends(require_admin)])
def create_dataset_api(
    request: DatasetCreateRequest, session: Session = Depends(get_session)
) -> DatasetItem:
    try:
        dataset = create_dataset(session, request.name, request.description)
        session.commit()
    except (DatasetConflict, DatasetNotFound) as exc:
        raise _dataset_error_to_http(exc) from exc
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="Dataset đã tồn tại.") from exc
    payload = get_dataset_with_stats(session, dataset.id)
    return DatasetItem(**payload)


@router.get("/datasets/{dataset_id}", response_model=DatasetItem, dependencies=[Depends(require_admin)])
def get_dataset_api(dataset_id: str, session: Session = Depends(get_session)) -> DatasetItem:
    payload = get_dataset_with_stats(session, dataset_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy dataset.")
    return DatasetItem(**payload)


@router.patch("/datasets/{dataset_id}", response_model=DatasetItem, dependencies=[Depends(require_admin)])
def update_dataset_api(
    dataset_id: str, request: DatasetUpdateRequest, session: Session = Depends(get_session)
) -> DatasetItem:
    from app.db.models import Dataset as _Dataset

    current = session.get(_Dataset, dataset_id)
    was_enabled = current.enabled if current is not None else None
    try:
        # clear_description=True cho phép xóa mô tả về null (PATCH {description: null} bị exclude).
        dataset = update_dataset(
            session,
            dataset_id,
            name=request.name,
            description=request.description,
            enabled=request.enabled,
            _clear_description=request.clear_description,
        )
        session.commit()
    except (DatasetConflict, DatasetNotFound) as exc:
        raise _dataset_error_to_http(exc) from exc
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="Dataset đã tồn tại.") from exc
    if was_enabled is not None and was_enabled != dataset.enabled:
        # BM25 giữ snapshot chunk của các dataset đang bật.
        invalidate_bm25_cache()
    payload = get_dataset_with_stats(session, dataset.id)
    return DatasetItem(**payload)


@router.delete("/datasets/{dataset_id}", response_model=DatasetDeleteResponse, dependencies=[Depends(require_admin)])
def delete_dataset_api(dataset_id: str) -> DatasetDeleteResponse:
    try:
        result = ingestion_pipeline.delete_dataset(dataset_id)
    except (PipelineDatasetNotFound, DatasetNotFound) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (PipelineDatasetConflict, DatasetConflict) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return DatasetDeleteResponse(**result)


@router.post("/datasets/{dataset_id}/chunk", response_model=ChunkAllResponse, dependencies=[Depends(require_admin)])
def chunk_dataset_api(dataset_id: str) -> ChunkAllResponse:
    try:
        result = ingestion_pipeline.chunk_documents(dataset_id=dataset_id)
    except (PipelineDatasetNotFound, DatasetNotFound) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DocumentStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except EmbeddingUnavailableError as exc:
        raise _embedding_unavailable(exc) from exc
    return ChunkAllResponse(**result)


@router.post("/datasets/{dataset_id}/parse", response_model=DatasetParseResponse, dependencies=[Depends(require_admin)])
def parse_dataset_api(dataset_id: str) -> DatasetParseResponse:
    try:
        result = ingestion_pipeline.enqueue_dataset_parse(dataset_id)
    except (PipelineDatasetNotFound, DatasetNotFound) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return DatasetParseResponse(
        jobs=[_parse_job_payload(job) for job in result["jobs"]],
        skipped_edited=result["skipped_edited"],
        skipped_busy=result["skipped_busy"],
    )


def _parse_job_payload(job: ParseJob) -> ParseJobItem:
    return ParseJobItem(
        id=job.id,
        kind=job.kind,
        status=job.status,
        document_id=job.document_id,
        dataset_id=job.dataset_id,
        file_name=job.file_name,
        parser_name=job.parser_name,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        error=job.error,
        result=job.result,
        progress=job.progress,
        progress_message=job.progress_message,
    )


def _document_payload(document, chunk_count: int) -> dict:
    path = resolve_source_path(document.source_path)
    size_bytes = path.stat().st_size if path is not None and path.is_file() else None
    return serialize_document(document, chunk_count, size_bytes)


# ==========================================
# Chat: 3 pha session ngắn (BE-11)
# ==========================================
# (a) `_open_chat_turn`: session ngắn xác định phiên, kiểm tra/tạo hội thoại, đọc
#     history, ghi ngay câu hỏi, commit, đóng.
# (b) retrieval + LLM chạy không giữ session/connection nào của route.
# (c) `_save_chat_answer`: session ngắn mới ghi câu trả lời (hoặc phần đã sinh khi
#     client ngắt), nguồn và `retrieval_debug` của câu hỏi.
#
# Chống lạm dụng (BE-10), theo thứ tự chi phí tăng dần; request bị chặn không ghi DB
# và không gọi retrieval/LLM:
# 1. `ChatRequest` từ chối câu hỏi dài hơn `CHAT_MESSAGE_MAX_CHARS` (422).
#    (BE-13) Câu rỗng → 400; embedding không dùng được → 503 (`_require_embedding_ready`),
#    trước mọi hạn mức nên request 503 không bị trừ lượt.
# 2. Hạn mức theo IP trước pha (a), chưa cần DB (`_enforce_chat_ip_limit`).
# 3. Trong pha (a), ngay sau khi xác định owner (cần DB để đọc tài khoản) và trước khi
#    chạm hội thoại: lấy khóa "một lượt đang chạy" rồi kiểm tra hạn mức theo owner.
# Khóa được nhả sau pha (c): `chat` trong `finally`; `chat_stream` qua `on_close` của
# `_ClosingStreamingResponse` (mọi đường kết thúc, kể cả generator chưa từng chạy); pha (a)
# lỗi thì nhả ngay. Dự phòng: tự hết hạn sau `CHAT_ACTIVE_SLOT_TTL_SECONDS` nếu response
# không bao giờ được gửi.
# Admin đã đăng nhập không bị hạn mức phút/ngày nhưng vẫn chỉ một lượt mỗi lần.
CHAT_RATE_LIMIT_DETAIL = "Bạn đã gửi quá nhiều câu hỏi. Vui lòng thử lại sau {seconds} giây."
CHAT_BUSY_DETAIL = "Câu trả lời trước vẫn đang được tạo. Vui lòng đợi hoặc bấm Dừng rồi gửi lại."
CHAT_BUSY_RETRY_AFTER_SECONDS = 1

# Lỗi của lượt chat (BE-12): client chỉ nhận thông điệp chung kèm mã tham chiếu; chi tiết
# exception chỉ nằm trong log, cùng mã. Mã gửi trong event `error` (`request_id`) và header
# `X-Request-ID` của cả hai route chat.
CHAT_REQUEST_ID_HEADER = "X-Request-ID"
CHAT_INTERNAL_ERROR_DETAIL = "Hệ thống đang bận, vui lòng thử lại sau. (Mã: {request_id})"
CHAT_LLM_STREAM_ERROR_DETAIL = "Mô hình bị gián đoạn khi đang trả lời. Vui lòng thử lại. (Mã: {request_id})"

# Luồng sinh event của /chat/stream chạy trong worker thread và bị chặn suốt lúc
# chờ LLM. Dùng limiter riêng để các stream dài không chiếm hết limiter mặc định
# của anyio (40) mà route đồng bộ khác (health, admin) cần dùng.
CHAT_STREAM_THREAD_LIMIT = 100
# Mỗi event loop một limiter (giống limiter mặc định của anyio).
_chat_stream_limiter: RunVar[anyio.CapacityLimiter] = RunVar("chat_stream_limiter")


def _get_chat_stream_limiter() -> anyio.CapacityLimiter:
    try:
        return _chat_stream_limiter.get()
    except LookupError:
        limiter = anyio.CapacityLimiter(CHAT_STREAM_THREAD_LIMIT)
        _chat_stream_limiter.set(limiter)
        return limiter


class _ClosingStreamingResponse(StreamingResponse):
    """StreamingResponse luôn `aclose()` body iterator khi kết thúc hoặc bị hủy.

    Starlette không đóng body iterator: nếu client ngắt đúng lúc đang `await send`,
    async generator dừng ở `yield` và `finally` (đóng LLM, lưu phần đã sinh) chỉ chạy
    khi GC thu hồi generator.

    ``on_close`` chạy khi response kết thúc theo mọi đường (xong, lỗi, client ngắt), kể
    cả khi body iterator chưa từng chạy: `aclose()` một async generator chưa bắt đầu
    không chạy `finally` của nó.
    """

    def __init__(self, *args: Any, on_close: Callable[[], None] | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._on_close = on_close

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        try:
            await super().__call__(scope, receive, send)
        finally:
            if self._on_close is not None:
                self._on_close()

    async def stream_response(self, send: Send) -> None:
        async with aclosing(self.body_iterator):
            await super().stream_response(send)


@dataclass(frozen=True)
class _ChatTurn:
    """Kết quả pha (a): chỉ giá trị thuần, không mang ORM object ra ngoài session."""

    conversation_id: str
    user_message_id: str
    history: list[dict[str, str]]
    client: auth.ClientSession
    # Khóa "một lượt đang chạy" của owner; None khi tắt hạn mức hoặc ngoài ngữ cảnh HTTP.
    slot: rate_limit.ChatSlot | None = None
    # Mã tham chiếu của lượt: có trong thông điệp lỗi, header X-Request-ID và log.
    request_id: str = field(default_factory=lambda: secrets.token_hex(6))

    def release_slot(self) -> None:
        if self.slot is not None:
            self.slot.release()


def _too_many_requests(detail: str, retry_after: int) -> HTTPException:
    return HTTPException(status_code=429, detail=detail, headers={"Retry-After": str(retry_after)})


def _chat_limits_apply(http_request: Request | None) -> bool:
    # Gọi hàm route trực tiếp (unit test, không có Request) thì không có phiên để giới hạn.
    return settings.chat_rate_limit_enabled and http_request is not None


def _is_admin_request(http_request: Request) -> bool:
    """Cookie admin hợp lệ (chỉ kiểm chữ ký, không truy vấn DB)."""
    return auth.is_admin_configured() and (
        auth.verify_admin_token(http_request.cookies.get(auth.ADMIN_COOKIE_NAME)) is not None
    )


def _require_embedding_ready() -> None:
    try:
        embedding_runtime.get()
    except EmbeddingUnavailableError as exc:
        raise HTTPException(status_code=503, detail=CHAT_EMBEDDING_UNAVAILABLE_DETAIL) from exc


def _enforce_chat_ip_limit(http_request: Request | None) -> None:
    if not _chat_limits_apply(http_request) or _is_admin_request(http_request):
        return
    decision = rate_limit.chat_ip_limiter.check_and_consume(auth.client_ip(http_request))
    if not decision.allowed:
        raise _too_many_requests(
            CHAT_RATE_LIMIT_DETAIL.format(seconds=decision.retry_after), decision.retry_after
        )


def _acquire_chat_slot(
    http_request: Request | None, client: auth.ClientSession
) -> rate_limit.ChatSlot | None:
    """Khóa một lượt đang chạy rồi trừ hạn mức theo owner; 429 khi không được phép."""
    if not _chat_limits_apply(http_request):
        return None
    slot = rate_limit.chat_active_slots.acquire(client.owner_key)
    if slot is None:
        # Lượt bị từ chối vì đang bận không trừ hạn mức owner.
        raise _too_many_requests(CHAT_BUSY_DETAIL, CHAT_BUSY_RETRY_AFTER_SECONDS)
    if not _is_admin_request(http_request):
        decision = rate_limit.chat_owner_limiter.check_and_consume(client.owner_key)
        if not decision.allowed:
            slot.release()
            raise _too_many_requests(
                CHAT_RATE_LIMIT_DETAIL.format(seconds=decision.retry_after), decision.retry_after
            )
    return slot


def _open_chat_turn(
    session_factory: Callable[[], Session],
    request: ChatRequest,
    http_request: Request | None,
) -> _ChatTurn:
    slot: rate_limit.ChatSlot | None = None
    try:
        with session_factory() as session:
            # Phiên (tài khoản hoặc ẩn danh) quyết định owner; user_id client gửi bị bỏ qua.
            client = auth.get_client_session(http_request, session)
            slot = _acquire_chat_slot(http_request, client)
            conversation = ensure_conversation(
                session,
                request.conversation_id,
                user_id=client.owner_key,
                title=request.message.strip()[:80],
            )
            if conversation is None:
                raise HTTPException(status_code=404, detail="Không tìm thấy hội thoại.")
            # Đọc history trước khi ghi câu hỏi để câu hỏi hiện tại không lọt vào history.
            history = (
                get_recent_conversation_history(
                    session,
                    conversation.id,
                    max_messages=settings.conversation_memory_max_messages,
                    max_chars=settings.conversation_memory_max_chars,
                )
                if settings.conversation_memory_enabled
                else []
            )
            user_message = add_message(session, conversation.id, "user", request.message, metadata={})
            # Lấy id trước commit: sau commit object hết hạn, đọc lại sẽ query DB.
            conversation_id, user_message_id = conversation.id, user_message.id
            session.commit()
        return _ChatTurn(
            conversation_id=conversation_id,
            user_message_id=user_message_id,
            history=filter_safe_history(history),
            client=client,
            slot=slot,
        )
    except BaseException:
        # Pha (a) thất bại (404, lỗi DB...): lượt chat không chạy, nhả khóa ngay.
        if slot is not None:
            slot.release()
        raise


def _save_chat_answer(
    session_factory: Callable[[], Session],
    turn: _ChatTurn,
    *,
    answer: str,
    assistant_metadata: dict[str, Any],
    contexts: list[dict],
    retrieval_debug: dict[str, Any] | None = None,
) -> None:
    with session_factory() as session:
        if retrieval_debug is not None:
            update_message_metadata(session, turn.user_message_id, {"retrieval_debug": retrieval_debug})
        assistant_message = add_message(
            session,
            turn.conversation_id,
            "assistant",
            answer,
            metadata=assistant_metadata,
        )
        add_message_sources(session, assistant_message.id, contexts)
        session.commit()


def _save_chat_answer_logged(session_factory: Callable[[], Session], turn: _ChatTurn, **kwargs: Any) -> bool:
    """Như `_save_chat_answer` nhưng log lỗi DB thay vì ném (response đã gửi một phần)."""
    try:
        _save_chat_answer(session_factory, turn, **kwargs)
    except Exception:
        logger.exception("Không lưu được câu trả lời của hội thoại %s", turn.conversation_id)
        return False
    return True


def _chat_error_metadata(kind: str, turn: _ChatTurn, exc: BaseException) -> dict[str, str]:
    """`metadata.error` lưu DB: loại lỗi, mã tham chiếu, tên lớp exception (không có text lỗi)."""
    return {"type": kind, "request_id": turn.request_id, "error_class": type(exc).__name__}


def _chat_error_event(message_template: str, turn: _ChatTurn) -> dict[str, str]:
    return {
        "type": "error",
        "message": message_template.format(request_id=turn.request_id),
        "request_id": turn.request_id,
    }


def _serialize_sources(sources: list) -> list[dict]:
    return [s.model_dump() if hasattr(s, "model_dump") else dict(s) for s in sources]


@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    response: Response = None,
    http_request: Request = None,
    session_factory: Callable[[], Session] = Depends(get_session_factory),
) -> ChatResponse:
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message must not be empty.")

    _require_embedding_ready()
    _enforce_chat_ip_limit(http_request)
    turn = _open_chat_turn(session_factory, request, http_request)
    try:
        turn.client.apply(response)
        if response is not None:
            response.headers[CHAT_REQUEST_ID_HEADER] = turn.request_id
        try:
            budget = LLMBudget(settings.llm_turn_deadline_seconds)
            result = rag_chain.answer(
                request.message, top_k=request.effective_top_k, history=turn.history, budget=budget
            )
        except Exception as exc:
            # Câu hỏi đã được lưu ở pha (a): ghi câu trả lời lỗi để giữ cặp hỏi - đáp, rồi
            # trả 503 với thông điệp chung; chi tiết chỉ ở log (cùng mã tham chiếu).
            logger.exception(
                "chat %s: answer failed (conversation %s)", turn.request_id, turn.conversation_id
            )
            _save_chat_answer_logged(
                session_factory,
                turn,
                answer="",
                assistant_metadata={"error": _chat_error_metadata("answer", turn, exc)},
                contexts=[],
            )
            raise HTTPException(
                status_code=503,
                detail=CHAT_INTERNAL_ERROR_DETAIL.format(request_id=turn.request_id),
                headers={CHAT_REQUEST_ID_HEADER: turn.request_id},
            ) from exc
        _save_chat_answer(
            session_factory,
            turn,
            answer=result["answer"],
            assistant_metadata={"sources": _serialize_sources(result["sources"])},
            contexts=result["contexts"],
            retrieval_debug=result["retrieval_debug"],
        )
    finally:
        turn.release_slot()

    return ChatResponse(
        conversation_id=turn.conversation_id,
        answer=result["answer"],
        sources=result["sources"],
    )


@dataclass
class _ChatStreamState:
    """Tiến độ của một lượt stream, dùng để lưu phần đã sinh khi client ngắt."""

    steps_log: list[dict[str, Any]] = field(default_factory=list)
    reasoning_parts: list[str] = field(default_factory=list)
    deltas: list[str] = field(default_factory=list)
    contexts: list[dict] = field(default_factory=list)
    sources: list = field(default_factory=list)
    retrieval_debug: dict[str, Any] | None = None
    saved: bool = False


def _iter_chat_stream_events(
    request: ChatRequest,
    turn: _ChatTurn,
    state: _ChatStreamState,
    session_factory: Callable[[], Session],
) -> Iterator[str]:
    """Pha (b), và pha (c) khi stream kết thúc bình thường; chạy trong worker thread."""
    reasoning_enabled = settings.llm_reasoning_stream_enabled
    retrieval: dict[str, Any] | None = None
    # Deadline chung cho rewrite + multi-query + sinh câu trả lời (tới chunk đầu tiên).
    budget = LLMBudget(settings.llm_turn_deadline_seconds)

    yield _ndjson({"type": "start", "conversation_id": turn.conversation_id})

    # Retrieval chạy trong generator để mỗi bước phát event ngay khi xong.
    try:
        for event in rag_chain.iter_retrieve_context(
            request.message, top_k=request.effective_top_k, history=turn.history, budget=budget
        ):
            if "result" in event:
                retrieval = event["result"]
                continue
            entry = {"status": "done", **event}
            state.steps_log.append(entry)
            yield _ndjson({"type": "step", **entry})
    except Exception as exc:
        # Đã gửi event start nên không thể trả HTTP 5xx nữa: báo lỗi qua event.
        logger.exception(
            "chat %s: retrieval failed (conversation %s)", turn.request_id, turn.conversation_id
        )
        state.saved = True
        _save_chat_answer_logged(
            session_factory,
            turn,
            answer="",
            assistant_metadata={
                "steps": state.steps_log,
                "error": _chat_error_metadata("retrieval", turn, exc),
            },
            contexts=[],
        )
        yield _ndjson(_chat_error_event(CHAT_INTERNAL_ERROR_DETAIL, turn))
        return

    assert retrieval is not None  # iter_retrieve_context luôn kết thúc bằng result
    contexts = retrieval["contexts"] if retrieval["strong_context"] else []
    sources = public_citations(contexts)
    state.contexts, state.sources = contexts, sources
    state.retrieval_debug = retrieval["retrieval_debug"]
    stream_error: LLMStreamError | None = None

    generate_started = time.perf_counter()
    generate_step: dict[str, Any] = {"step": "generate", "status": "start", "detail": {}, "elapsed_ms": 0}
    yield _ndjson({"type": "step", **generate_step})

    if not retrieval["guardrail_allowed"]:
        stream: Iterator[StreamDelta] = iter([StreamDelta(kind=CONTENT_DELTA, text=OUT_OF_SCOPE_ANSWER)])
    elif retrieval["strong_context"]:
        stream = stream_answer_deltas_with_llm(request.message, contexts, history=turn.history, budget=budget)
    else:
        stream = iter([StreamDelta(kind=CONTENT_DELTA, text=NO_CONTEXT_ANSWER)])

    try:
        for delta in stream:
            if delta.kind == REASONING_DELTA:
                if reasoning_enabled:
                    state.reasoning_parts.append(delta.text)
                    yield _ndjson({"type": "reasoning", "content": delta.text})
            else:
                state.deltas.append(delta.text)
                yield _ndjson({"type": "delta", "content": delta.text})
    except LLMStreamError as exc:
        # LLM lỗi sau khi đã stream một phần: báo lỗi cho client thay vì nối
        # thêm câu trả lời dự phòng vào phần text đã phát ra. Event `error` phát
        # sau khi lưu (bên dưới). Chi tiết lỗi chỉ ghi log.
        logger.warning(
            "chat %s: LLM stream interrupted after %d delta(s): %s",
            turn.request_id,
            len(state.deltas),
            describe_error(exc.__cause__ or exc),
        )
        stream_error = exc
    finally:
        # Client ngắt (GeneratorExit tại yield): đóng stream LLM ngay, không sinh tiếp.
        close_stream = getattr(stream, "close", None)
        if close_stream is not None:
            close_stream()

    generate_step = {
        "step": "generate",
        "status": "done",
        "detail": {},
        "elapsed_ms": round((time.perf_counter() - generate_started) * 1000),
    }
    state.steps_log.append(generate_step)

    raw_answer = "".join(state.deltas)
    if stream_error is not None:
        # Phần text nửa vời không phải câu trả lời hoàn chỉnh: bỏ qua chuẩn hóa trích dẫn.
        answer = raw_answer.strip()
    else:
        answer = _normalize_answer_citations(raw_answer, contexts) if contexts else raw_answer
        if is_refusal(answer):
            # Câu từ chối không kèm nguồn (RAG-22); contexts vẫn lưu để debug.
            sources = []
            state.sources = sources

    reasoning_text = "".join(state.reasoning_parts)
    assistant_metadata: dict[str, Any] = {
        "sources": _serialize_sources(sources),
        "steps": state.steps_log,
    }
    if reasoning_text:
        assistant_metadata["reasoning"] = reasoning_text
    if stream_error is not None:
        assistant_metadata["error"] = _chat_error_metadata("llm_stream", turn, stream_error)
    # Lưu trước event kết thúc: client nhận `done`/`error` là hội thoại đã có câu trả lời.
    state.saved = True
    _save_chat_answer_logged(
        session_factory,
        turn,
        answer=answer,
        assistant_metadata=assistant_metadata,
        contexts=contexts,
        retrieval_debug=state.retrieval_debug,
    )
    if stream_error is not None:
        # Event `error` là event kết thúc; client giữ phần text đã stream và
        # hiển thị nút thử lại, không ghi đè bằng `done`.
        yield _ndjson(_chat_error_event(CHAT_LLM_STREAM_ERROR_DETAIL, turn))
        return
    yield _ndjson({
        "type": "done",
        "answer": answer,
        "sources": sources,
        "conversation_id": turn.conversation_id,
        "reasoning": reasoning_text or None,
        "steps": state.steps_log,
    })


def _finish_chat_stream(
    producer: Iterator[str],
    session_factory: Callable[[], Session],
    turn: _ChatTurn,
    state: _ChatStreamState,
    failure: Exception | None,
) -> None:
    """Pha (c) khi stream không kết thúc bình thường: client ngắt hoặc lỗi bất ngờ."""
    try:
        producer.close()
    except Exception:
        logger.exception("Không đóng được stream chat của hội thoại %s", turn.conversation_id)
    if state.saved:
        return
    state.saved = True
    assistant_metadata: dict[str, Any] = {
        "sources": _serialize_sources(state.sources),
        "steps": state.steps_log,
    }
    reasoning_text = "".join(state.reasoning_parts)
    if reasoning_text:
        assistant_metadata["reasoning"] = reasoning_text
    if failure is None:
        assistant_metadata["interrupted"] = True
    else:
        assistant_metadata["error"] = _chat_error_metadata("internal", turn, failure)
    _save_chat_answer_logged(
        session_factory,
        turn,
        # Phần đã sinh dở dang: không chuẩn hóa trích dẫn.
        answer="".join(state.deltas).strip(),
        assistant_metadata=assistant_metadata,
        contexts=state.contexts,
        retrieval_debug=state.retrieval_debug,
    )


@router.post("/chat/stream")
def chat_stream(
    request: ChatRequest,
    http_request: Request = None,
    session_factory: Callable[[], Session] = Depends(get_session_factory),
) -> StreamingResponse:
    """Stream newline-delimited JSON events while preserving the normal chat contract.

    Event types: ``start``, ``step`` (tiến độ từng bước retrieval/generation),
    ``reasoning`` (thinking của model, khi bật cờ và model hỗ trợ), ``delta``
    (text câu trả lời), ``error`` (event kết thúc), ``done``.

    Câu hỏi được lưu trước khi stream; khi client ngắt giữa chừng, phần trả lời đã
    sinh được lưu với ``metadata.interrupted = true``.
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message must not be empty.")

    _require_embedding_ready()
    _enforce_chat_ip_limit(http_request)
    turn = _open_chat_turn(session_factory, request, http_request)

    async def event_stream() -> AsyncIterator[str]:
        # Async generator thay vì sync generator: Starlette không đóng sync generator
        # khi client ngắt (chỉ tới lúc GC). Async generator nhận CancelledError khi
        # đang chờ thread, hoặc GeneratorExit từ `_ClosingStreamingResponse` khi đang
        # dừng ở `yield`, nên `finally` chắc chắn chạy để lưu phần đã sinh.
        state = _ChatStreamState()
        producer = _iter_chat_stream_events(request, turn, state, session_factory)
        limiter = _get_chat_stream_limiter()
        failure: Exception | None = None
        try:
            while True:
                chunk = await anyio.to_thread.run_sync(next, producer, None, limiter=limiter)
                if chunk is None:
                    break
                yield chunk
        except Exception as exc:
            # Lỗi bất ngờ trong pha (b)/(c): kết thúc bằng event `error` chung (không lộ
            # text exception); chi tiết ở log cùng mã tham chiếu, lưu ở `finally`.
            failure = exc
            logger.error(
                "chat %s: stream failed (conversation %s)",
                turn.request_id,
                turn.conversation_id,
                exc_info=exc,
            )
            yield _ndjson(_chat_error_event(CHAT_INTERNAL_ERROR_DETAIL, turn))
        finally:
            # Không yield ở đây (generator đang bị đóng). Shield để việc đóng LLM và
            # ghi DB không bị hủy theo request đã ngắt.
            with anyio.CancelScope(shield=True):
                await anyio.to_thread.run_sync(
                    _finish_chat_stream, producer, session_factory, turn, state, failure, limiter=limiter
                )

    # Route tự trả StreamingResponse nên FastAPI không gộp cookie của response
    # inject: gắn Set-Cookie trực tiếp lên headers của stream cho phiên mới.
    stream_headers = {
        "X-Accel-Buffering": "no",
        "Cache-Control": "no-cache",
        CHAT_REQUEST_ID_HEADER: turn.request_id,
    }
    if turn.client.cookie_header is not None:
        stream_headers["Set-Cookie"] = turn.client.cookie_header

    # Nhả khóa lượt chat khi response kết thúc: sau `finally` của event_stream (đã lưu
    # câu trả lời) nên lượt kế tiếp đọc được câu trả lời này trong history.
    return _ClosingStreamingResponse(
        event_stream(),
        media_type="application/x-ndjson",
        headers=stream_headers,
        on_close=turn.release_slot,
    )


def _ndjson(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False) + "\n"


# ==========================================
# Lịch sử hội thoại
# ==========================================
def _serialize_conversation(conversation, message_count: int, owner: str | None = None) -> ConversationItem:
    return ConversationItem(
        id=conversation.id,
        title=conversation.title,
        message_count=message_count,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        owner=owner,
    )


@router.get("/conversations", response_model=ConversationListResponse)
def list_conversation_history(
    response: Response = None,
    http_request: Request = None,
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_session),
) -> ConversationListResponse:
    """Danh sách hội thoại của phiên hiện tại: tài khoản (ptit_user) hoặc ẩn danh (ptit_sid).

    Luôn lọc theo owner của phiên — kể cả khi trình duyệt đang có cookie admin.
    """
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    client = auth.get_client_session(http_request, session)
    client.apply(response)
    rows, total = list_conversations(session, limit=limit, offset=offset, user_id=client.owner_key)
    return ConversationListResponse(
        total=total,
        conversations=[_serialize_conversation(c, count) for c, count in rows],
    )


def _conversation_message(message: Message) -> ConversationMessage:
    """Một tin đã lưu -> ``ConversationMessage``; metadata thiếu/sai kiểu dùng mặc định."""
    # Citation/reasoning/steps được lưu trong metadata lúc sinh câu trả lời; hội
    # thoại cũ (trước khi có các trường này) trả về rỗng.
    metadata = message.message_metadata or {}
    raw_error = metadata.get("error")
    error = None
    if isinstance(raw_error, dict) and isinstance(raw_error.get("type"), str):
        request_id = raw_error.get("request_id")
        # Chỉ trả loại lỗi và mã tham chiếu; `error_class` là chi tiết nội bộ.
        error = ConversationMessageError(
            type=raw_error["type"],
            request_id=request_id if isinstance(request_id, str) else None,
        )
    return ConversationMessage(
        id=message.id,
        role=message.role,
        content=message.content,
        sources=metadata.get("sources", []) or [],
        reasoning=metadata.get("reasoning"),
        steps=metadata.get("steps", []) or [],
        interrupted=metadata.get("interrupted") is True,
        error=error,
        created_at=message.created_at,
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation_detail(
    conversation_id: str,
    response: Response = None,
    http_request: Request = None,
    session: Session = Depends(get_session),
) -> ConversationDetail:
    client = auth.get_client_session(http_request, session)
    client.apply(response)
    conversation = get_owned_conversation(session, conversation_id, client.owner_key)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy hội thoại.")

    messages = get_conversation_messages(session, conversation_id)
    return ConversationDetail(
        id=conversation.id,
        title=conversation.title,
        message_count=len(messages),
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[_conversation_message(message) for message in messages],
    )


@router.patch("/conversations/{conversation_id}", response_model=ConversationItem)
def rename_conversation_title(
    conversation_id: str,
    request: RenameConversationRequest,
    response: Response = None,
    http_request: Request = None,
    session: Session = Depends(get_session),
) -> ConversationItem:
    client = auth.get_client_session(http_request, session)
    client.apply(response)
    conversation = get_owned_conversation(session, conversation_id, client.owner_key)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy hội thoại.")
    conversation = rename_conversation(session, conversation_id, request.title.strip())
    if conversation is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy hội thoại.")
    session.commit()
    messages = get_conversation_messages(session, conversation_id)
    return _serialize_conversation(conversation, len(messages))


@router.delete("/conversations/{conversation_id}")
def remove_conversation(
    conversation_id: str,
    response: Response = None,
    http_request: Request = None,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    client = auth.get_client_session(http_request, session)
    client.apply(response)
    conversation = get_owned_conversation(session, conversation_id, client.owner_key)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy hội thoại.")
    if not delete_conversation(session, conversation_id):
        raise HTTPException(status_code=404, detail="Không tìm thấy hội thoại.")
    session.commit()
    return {"id": conversation_id, "deleted": True}


# ==========================================
# Hội thoại toàn hệ thống (admin, phục vụ FE-13)
# ==========================================
@router.get(
    "/admin/conversations",
    response_model=ConversationListResponse,
    dependencies=[Depends(require_admin)],
)
def admin_list_conversations(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    owner: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> ConversationListResponse:
    """Mọi hội thoại (kể cả của phiên khác và hội thoại cũ chưa có owner)."""
    rows, total = list_conversations(session, limit=limit, offset=offset, user_id=owner)
    return ConversationListResponse(
        total=total,
        conversations=[_serialize_conversation(c, count, owner=c.user_id) for c, count in rows],
    )


@router.get(
    "/admin/conversations/{conversation_id}",
    response_model=ConversationDetail,
    dependencies=[Depends(require_admin)],
)
def admin_get_conversation(
    conversation_id: str,
    session: Session = Depends(get_session),
) -> ConversationDetail:
    conversation = get_conversation(session, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy hội thoại.")

    messages = get_conversation_messages(session, conversation_id)
    return ConversationDetail(
        id=conversation.id,
        title=conversation.title,
        message_count=len(messages),
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        owner=conversation.user_id,
        messages=[_conversation_message(message) for message in messages],
    )
