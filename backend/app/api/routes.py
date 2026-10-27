import json
import time
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.schemas import (
    AdminLoginRequest,
    AdminSessionResponse,
    AuthSessionResponse,
    AuthUser,
    ChatRequest,
    ChatResponse,
    ChunkAllResponse,
    ChunkItem,
    ConversationDetail,
    ConversationItem,
    ConversationListResponse,
    ConversationMessage,
    DocumentChunksResponse,
    DocumentDeleteResponse,
    DocumentDetail,
    DocumentItem,
    DocumentListResponse,
    DocumentMarkdown,
    FullConfigResponse,
    IngestResponse,
    LoginRequest,
    ParseJobItem,
    ParseJobListResponse,
    RegisterRequest,
    RenameConversationRequest,
    RetrievalTestRequest,
    TestLLMRequest,
    TestLLMResponse,
    UpdateConfigRequest,
    UpdateMarkdownRequest,
)
from app.core import auth, user_auth
from app.core.auth import require_admin
from app.core.config import (
    PROJECT_ROOT,
    ConfigValidationError,
    get_runtime_config_dict,
    reset_runtime_config,
    settings,
    update_runtime_config,
    validate_llm_url,
)
from app.db import check_db_health, get_session
from app.db.repositories import (
    add_message,
    add_message_sources,
    claim_anonymous_conversations,
    create_user,
    delete_conversation,
    ensure_conversation,
    get_conversation,
    get_conversation_messages,
    get_document_chunks,
    get_document_full_text,
    get_document_preview_text,
    get_document_with_chunk_count,
    get_owned_conversation,
    get_recent_conversation_history,
    get_user_by_email,
    list_conversations,
    list_documents,
    rename_conversation,
    serialize_document,
    serialize_markdown,
)
from app.generation.citations import public_citations
from app.generation.llm import (
    _normalize_answer_citations,
    stream_answer_deltas_with_llm,
)
from app.generation.rag_chain import rag_chain
from app.guardrails import OUT_OF_SCOPE_ANSWER, filter_safe_history
from app.ingestion import ingestion_pipeline
from app.ingestion.jobs import ParseJob, ParseJobConflict, parse_jobs
from app.ingestion.pipeline import DocumentStateError
from app.ingestion.uploads import (
    PREVIEW_CHAR_LIMIT,
    DocumentUploadError,
    read_preview,
    resolve_source_path,
)
from app.llm import CONTENT_DELTA, REASONING_DELTA, LLMStreamError, StreamDelta
from app.llm.factory import create_llm_provider_from_config
from app.parsers import (
    DocumentParseError,
    read_document_text,
    registry,
    resolve_parser_name,
)

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
    db_health = check_db_health()
    is_ok = db_health.get("status") == "ok"
    return {
        "status": "ok" if is_ok else "degraded",
        "database": db_health.get("database", "unknown"),
        "database_type": db_health.get("dialect", "unknown"),
    }


# ==========================================
# Phiên quản trị (FE-06)
# ==========================================
@router.post("/admin/login", response_model=AdminSessionResponse)
def admin_login(
    payload: AdminLoginRequest,
    request: Request,
    response: Response,
) -> AdminSessionResponse:
    if not auth.is_admin_configured():
        raise HTTPException(status_code=503, detail="Chưa cấu hình ADMIN_PASSWORD.")
    if auth.is_login_throttled(request):
        raise HTTPException(
            status_code=429,
            detail="Quá nhiều lần đăng nhập sai. Vui lòng thử lại sau ít phút.",
        )
    if not auth.verify_admin_password(payload.password):
        auth.register_failed_login(request)
        raise HTTPException(status_code=401, detail="Mật khẩu không đúng.")
    auth.register_successful_login(request)
    token, expires_at = auth.issue_admin_session()
    auth.issue_admin_cookie(response, token)
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
USER_LOGIN_FAILED_DETAIL = "Email hoặc mật khẩu không đúng."
USER_THROTTLED_DETAIL = "Quá nhiều lần thử. Vui lòng thử lại sau ít phút."
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
    if get_user_by_email(session, payload.email) is not None:
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
    return FullConfigResponse(**get_runtime_config_dict())


@router.put("/config", response_model=FullConfigResponse, dependencies=[Depends(require_admin)])
def update_config(request: UpdateConfigRequest) -> FullConfigResponse:
    payload = request.model_dump(exclude_unset=True)
    try:
        updated = update_runtime_config(payload)
    except ConfigValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return FullConfigResponse(**updated)


@router.post("/config/reset", response_model=FullConfigResponse, dependencies=[Depends(require_admin)])
def reset_config() -> FullConfigResponse:
    reset_data = reset_runtime_config()
    return FullConfigResponse(**reset_data)


@router.post("/config/test-llm", response_model=TestLLMResponse, dependencies=[Depends(require_admin)])
def test_llm(request: TestLLMRequest) -> TestLLMResponse:
    # Kiểm URL trước khi tạo provider: request ngoài allowlist bị từ chối, key
    # đang lưu không bao giờ được gửi tới host lạ.
    try:
        validate_llm_url(request.base_url)
        validate_llm_url(request.endpoint)
    except ConfigValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    start_time = time.perf_counter()
    try:
        provider_instance = create_llm_provider_from_config(
            provider=request.provider,
            model=request.model,
            api_key=request.api_key,
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



@router.post("/retrieval/test", dependencies=[Depends(require_admin)])
def test_retrieval(request: RetrievalTestRequest) -> dict:
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query must not be empty.")
    result = rag_chain.retrieve_context(request.query, top_k=request.top_k)
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
    return IngestResponse(**result)


@router.post("/ingest/chunk", response_model=ChunkAllResponse, dependencies=[Depends(require_admin)])
def chunk_all_documents() -> ChunkAllResponse:
    """Re-chunk every document from its stored Markdown, e.g. after changing chunk settings."""
    try:
        result = ingestion_pipeline.chunk_documents()
    except DocumentStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ChunkAllResponse(**result)


@router.get("/documents", response_model=DocumentListResponse, dependencies=[Depends(require_admin)])
def get_documents(session: Session = Depends(get_session)) -> DocumentListResponse:
    documents = [
        DocumentItem(**_document_payload(document, chunk_count))
        for document, chunk_count in list_documents(session)
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
    file: UploadFile = File(...), parser_name: str | None = Form(default=None, min_length=1)
) -> ParseJobItem:
    """Validate and stage the upload, then parse it in a background job.

    Only the cheap validation and the staging write happen before the response;
    conversion/parse of large PDFs no longer blocks the client. The source file
    is published into DOCUMENTS_PATH by the job after parsing and committing.
    """
    try:
        options = {"parser_name": parser_name} if parser_name is not None else {}
        job = parse_jobs.enqueue_upload(file.filename or "", file.file.read(), **options)
    except DocumentUploadError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except ParseJobConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return _parse_job_payload(job)


@router.get("/parse-jobs", response_model=ParseJobListResponse, dependencies=[Depends(require_admin)])
def list_parse_jobs(
    document_id: str | None = Query(default=None),
    active_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
) -> ParseJobListResponse:
    jobs = parse_jobs.list(document_id=document_id, active_only=active_only, limit=limit)
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


def _parse_job_payload(job: ParseJob) -> ParseJobItem:
    return ParseJobItem(
        id=job.id,
        kind=job.kind,
        status=job.status,
        document_id=job.document_id,
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


@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    response: Response = None,
    http_request: Request = None,
    session: Session = Depends(get_session),
) -> ChatResponse:
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message must not be empty.")

    # Phiên (tài khoản hoặc ẩn danh) quyết định owner; user_id client gửi bị bỏ qua.
    client = auth.get_client_session(http_request, session)
    conversation = ensure_conversation(
        session,
        request.conversation_id,
        user_id=client.owner_key,
        title=request.message.strip()[:80],
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy hội thoại.")
    client.apply(response)
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
    history = filter_safe_history(history)
    result = rag_chain.answer(request.message, top_k=request.effective_top_k, history=history)
    add_message(
        session,
        conversation.id,
        "user",
        request.message,
        metadata={"retrieval_debug": result["retrieval_debug"]},
    )
    assistant_message = add_message(
        session,
        conversation.id,
        "assistant",
        result["answer"],
        metadata={"sources": [s.model_dump() if hasattr(s, "model_dump") else dict(s) for s in result["sources"]]},
    )
    add_message_sources(session, assistant_message.id, result["contexts"])
    session.commit()

    return ChatResponse(
        conversation_id=conversation.id,
        answer=result["answer"],
        sources=result["sources"],
    )


@router.post("/chat/stream")
def chat_stream(
    request: ChatRequest,
    http_request: Request = None,
    session: Session = Depends(get_session),
) -> StreamingResponse:
    """Stream newline-delimited JSON events while preserving the normal chat contract.

    Event types: ``start``, ``step`` (tiến độ từng bước retrieval/generation),
    ``reasoning`` (thinking của model, khi bật cờ và model hỗ trợ), ``delta``
    (text câu trả lời), ``error`` (event kết thúc), ``done``.
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message must not be empty.")

    # Phiên (tài khoản hoặc ẩn danh) quyết định owner; user_id client gửi bị bỏ qua.
    client = auth.get_client_session(http_request, session)
    conversation = ensure_conversation(
        session,
        request.conversation_id,
        user_id=client.owner_key,
        title=request.message.strip()[:80],
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy hội thoại.")
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
    history = filter_safe_history(history)

    def event_stream() -> Iterator[str]:
        steps_log: list[dict[str, Any]] = []
        reasoning_parts: list[str] = []
        reasoning_enabled = settings.llm_reasoning_stream_enabled
        retrieval: dict[str, Any] | None = None

        yield _ndjson({"type": "start", "conversation_id": conversation.id})

        # Retrieval chạy trong generator để mỗi bước phát event ngay khi xong.
        try:
            for event in rag_chain.iter_retrieve_context(
                request.message, top_k=request.effective_top_k, history=history
            ):
                if "result" in event:
                    retrieval = event["result"]
                    continue
                entry = {"status": "done", **event}
                steps_log.append(entry)
                yield _ndjson({"type": "step", **entry})
        except Exception as exc:
            # Đã gửi event start nên không thể trả HTTP 500 nữa: báo lỗi qua event.
            yield _ndjson({"type": "error", "message": f"Retrieval failed: {exc}"})
            return

        assert retrieval is not None  # iter_retrieve_context luôn kết thúc bằng result
        contexts = retrieval["contexts"] if retrieval["strong_context"] else []
        sources = public_citations(contexts)
        deltas: list[str] = []
        stream_error: str | None = None

        generate_started = time.perf_counter()
        generate_step: dict[str, Any] = {"step": "generate", "status": "start", "detail": {}, "elapsed_ms": 0}
        yield _ndjson({"type": "step", **generate_step})

        if not retrieval["guardrail_allowed"]:
            stream: Iterator[StreamDelta] = iter([StreamDelta(kind=CONTENT_DELTA, text=OUT_OF_SCOPE_ANSWER)])
        elif retrieval["strong_context"]:
            stream = stream_answer_deltas_with_llm(request.message, contexts, history=history)
        else:
            stream = iter([StreamDelta(kind=CONTENT_DELTA, text="Chưa tìm thấy thông tin này trong tài liệu.")])

        try:
            for delta in stream:
                if delta.kind == REASONING_DELTA:
                    if reasoning_enabled:
                        reasoning_parts.append(delta.text)
                        yield _ndjson({"type": "reasoning", "content": delta.text})
                else:
                    deltas.append(delta.text)
                    yield _ndjson({"type": "delta", "content": delta.text})
        except LLMStreamError as exc:
            # LLM lỗi sau khi đã stream một phần: báo lỗi cho client thay vì nối
            # thêm câu trả lời dự phòng vào phần text đã phát ra.
            stream_error = str(exc) or "LLM streaming failed."
            yield _ndjson({"type": "error", "message": stream_error})

        generate_step = {
            "step": "generate",
            "status": "done",
            "detail": {},
            "elapsed_ms": round((time.perf_counter() - generate_started) * 1000),
        }
        steps_log.append(generate_step)

        reasoning_text = "".join(reasoning_parts)
        assistant_metadata: dict[str, Any] = {
            "sources": [s.model_dump() if hasattr(s, "model_dump") else dict(s) for s in sources],
            "steps": steps_log,
        }
        if reasoning_text:
            assistant_metadata["reasoning"] = reasoning_text
        if stream_error:
            assistant_metadata["error"] = {
                "type": "llm_stream",
                "message": stream_error,
            }

        raw_answer = "".join(deltas)
        if stream_error:
            # Phần text nửa vời không phải câu trả lời hoàn chỉnh: bỏ qua chuẩn
            # hóa trích dẫn (thuộc tính này có thể tự nối thêm "[1]" cho ảo).
            answer = raw_answer.strip()
        else:
            answer = _normalize_answer_citations(raw_answer, contexts) if contexts else raw_answer
        add_message(
            session,
            conversation.id,
            "user",
            request.message,
            metadata={"retrieval_debug": retrieval["retrieval_debug"]},
        )
        assistant_message = add_message(
            session,
            conversation.id,
            "assistant",
            answer,
            metadata=assistant_metadata,
        )
        add_message_sources(session, assistant_message.id, contexts)
        session.commit()
        if stream_error:
            # Event `error` đã gửi ở trên là event kết thúc; client giữ phần text
            # đã stream và hiển thị nút thử lại, không ghi đè bằng `done`.
            return
        yield _ndjson({
            "type": "done",
            "answer": answer,
            "sources": sources,
            "conversation_id": conversation.id,
            "reasoning": reasoning_text or None,
            "steps": steps_log,
        })

    # Route tự trả StreamingResponse nên FastAPI không gộp cookie của response
    # inject: gắn Set-Cookie trực tiếp lên headers của stream cho phiên mới.
    stream_headers = {"X-Accel-Buffering": "no", "Cache-Control": "no-cache"}
    if client.cookie_header is not None:
        stream_headers["Set-Cookie"] = client.cookie_header

    return StreamingResponse(
        event_stream(),
        media_type="application/x-ndjson",
        headers=stream_headers,
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
        messages=[
            ConversationMessage(
                id=message.id,
                role=message.role,
                content=message.content,
                # Citation được lưu trong metadata lúc sinh câu trả lời; hội thoại
                # cũ (trước khi có trường này) sẽ trả về danh sách rỗng.
                sources=(message.message_metadata or {}).get("sources", []) or [],
                reasoning=(message.message_metadata or {}).get("reasoning"),
                steps=(message.message_metadata or {}).get("steps", []) or [],
                created_at=message.created_at,
            )
            for message in messages
        ],
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
        messages=[
            ConversationMessage(
                id=message.id,
                role=message.role,
                content=message.content,
                sources=(message.message_metadata or {}).get("sources", []) or [],
                reasoning=(message.message_metadata or {}).get("reasoning"),
                steps=(message.message_metadata or {}).get("steps", []) or [],
                created_at=message.created_at,
            )
            for message in messages
        ],
    )
