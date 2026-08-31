import json
import time
from collections.abc import Iterator
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.api.schemas import (
    ChatRequest,
    ChatResponse,
    ChunkItem,
    DocumentChunksResponse,
    DocumentDeleteResponse,
    DocumentDetail,
    DocumentItem,
    DocumentListResponse,
    FullConfigResponse,
    IngestResponse,
    RetrievalTestRequest,
    TestLLMRequest,
    TestLLMResponse,
    UpdateConfigRequest,
)
from app.db import check_db_health, get_session
from app.core.config import get_runtime_config_dict, reset_runtime_config, settings, update_runtime_config
from app.db.repositories import (
    add_message,
    add_message_sources,
    ensure_conversation,
    get_document_chunks,
    get_document_preview_text,
    get_document_with_chunk_count,
    get_recent_conversation_history,
    list_documents,
    serialize_document,
)
from app.generation.rag_chain import rag_chain
from app.guardrails import OUT_OF_SCOPE_ANSWER, filter_safe_history
from app.generation.citations import public_citations
from app.generation.llm import _normalize_answer_citations, stream_answer_with_llm
from app.ingestion import ingestion_pipeline
from app.ingestion.uploads import DocumentUploadError, read_preview, resolve_source_path
from app.llm.factory import create_llm_provider_from_config

router = APIRouter()


@router.get("/health")
def health() -> dict[str, Any]:
    db_health = check_db_health()
    is_ok = db_health.get("status") == "ok"
    return {
        "status": "ok" if is_ok else "degraded",
        "database": db_health.get("database", "unknown"),
        "database_type": db_health.get("dialect", "unknown"),
    }



@router.get("/config", response_model=FullConfigResponse)
def get_config() -> FullConfigResponse:
    return FullConfigResponse(**get_runtime_config_dict())


@router.put("/config", response_model=FullConfigResponse)
def update_config(request: UpdateConfigRequest) -> FullConfigResponse:
    payload = request.model_dump(exclude_unset=True)
    updated = update_runtime_config(payload)
    return FullConfigResponse(**updated)


@router.post("/config/reset", response_model=FullConfigResponse)
def reset_config() -> FullConfigResponse:
    reset_data = reset_runtime_config()
    return FullConfigResponse(**reset_data)


@router.post("/config/test-llm", response_model=TestLLMResponse)
def test_llm(request: TestLLMRequest) -> TestLLMResponse:
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



@router.post("/retrieval/test")
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


@router.post("/ingest", response_model=IngestResponse)
def ingest() -> IngestResponse:
    result = ingestion_pipeline.ingest_documents()
    return IngestResponse(**result)


@router.get("/documents", response_model=DocumentListResponse)
def get_documents(session: Session = Depends(get_session)) -> DocumentListResponse:
    documents = [
        DocumentItem(**_document_payload(document, chunk_count))
        for document, chunk_count in list_documents(session)
    ]
    return DocumentListResponse(documents=documents)


@router.get("/documents/{document_id}", response_model=DocumentDetail)
def get_document(document_id: str, session: Session = Depends(get_session)) -> DocumentDetail:
    row = get_document_with_chunk_count(session, document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")

    document, chunk_count = row
    source_p = resolve_source_path(document.source_path)
    full_text = None
    if source_p is not None and source_p.is_file():
        try:
            full_text = source_p.read_text(encoding="utf-8")
        except Exception:
            full_text = None
    preview = read_preview(document.source_path) or get_document_preview_text(session, document.id)
    if full_text is None:
        full_text = preview
    return DocumentDetail(**_document_payload(document, chunk_count), preview=preview, full_text=full_text)


@router.get("/documents/{document_id}/chunks", response_model=DocumentChunksResponse)
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


@router.get("/documents/{document_id}/file")
def download_document(document_id: str, session: Session = Depends(get_session)) -> FileResponse:
    row = get_document_with_chunk_count(session, document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")

    document, _chunk_count = row
    path = resolve_source_path(document.source_path)
    if path is None or not path.is_file():
        raise HTTPException(status_code=404, detail="File nguồn không còn trên đĩa.")

    return FileResponse(
        path,
        filename=path.name,
        media_type="text/plain; charset=utf-8",
    )


@router.post("/documents", response_model=DocumentItem)
async def upload_document(file: UploadFile = File(...)) -> DocumentItem:
    try:
        payload = ingestion_pipeline.ingest_upload(file.filename or "", await file.read())
    except DocumentUploadError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    return DocumentItem(**payload)


@router.post("/documents/{document_id}/parse", response_model=DocumentItem)
def parse_single_document(document_id: str, session: Session = Depends(get_session)) -> DocumentItem:
    row = get_document_with_chunk_count(session, document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")
    document, _chunk_count = row
    path = resolve_source_path(document.source_path)
    if path is None or not path.is_file():
        raise HTTPException(status_code=404, detail="File nguồn không tồn tại trên đĩa.")

    result = ingestion_pipeline.ingest_path(path)
    return DocumentItem(**result)


@router.delete("/documents/{document_id}", response_model=DocumentDeleteResponse)
def remove_document(document_id: str) -> DocumentDeleteResponse:
    result = ingestion_pipeline.delete_ingested_document(document_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")
    return DocumentDeleteResponse(**result)


def _document_payload(document, chunk_count: int) -> dict:
    path = resolve_source_path(document.source_path)
    size_bytes = path.stat().st_size if path is not None and path.is_file() else None
    return serialize_document(document, chunk_count, size_bytes)


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, session: Session = Depends(get_session)) -> ChatResponse:
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message must not be empty.")

    conversation = ensure_conversation(
        session,
        request.conversation_id,
        user_id=request.user_id,
        title=request.message.strip()[:80],
    )
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
    assistant_message = add_message(session, conversation.id, "assistant", result["answer"])
    add_message_sources(session, assistant_message.id, result["contexts"])
    session.commit()

    return ChatResponse(
        conversation_id=conversation.id,
        answer=result["answer"],
        sources=result["sources"],
    )


@router.post("/chat/stream")
def chat_stream(request: ChatRequest, session: Session = Depends(get_session)) -> StreamingResponse:
    """Stream newline-delimited JSON events while preserving the normal chat contract."""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message must not be empty.")

    conversation = ensure_conversation(
        session,
        request.conversation_id,
        user_id=request.user_id,
        title=request.message.strip()[:80],
    )
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
    retrieval = rag_chain.retrieve_context(request.message, top_k=request.effective_top_k, history=history)

    def event_stream() -> Iterator[str]:
        contexts = retrieval["contexts"] if retrieval["strong_context"] else []
        sources = public_citations(contexts)
        deltas: list[str] = []
        yield _ndjson({"type": "start", "conversation_id": conversation.id})

        if not retrieval["guardrail_allowed"]:
            stream = iter([OUT_OF_SCOPE_ANSWER])
        elif retrieval["strong_context"]:
            stream = stream_answer_with_llm(request.message, contexts, history=history)
        else:
            stream = iter(["Chưa tìm thấy thông tin này trong tài liệu."])

        for delta in stream:
            deltas.append(delta)
            yield _ndjson({"type": "delta", "content": delta})

        raw_answer = "".join(deltas)
        answer = _normalize_answer_citations(raw_answer, contexts) if contexts else raw_answer
        add_message(
            session,
            conversation.id,
            "user",
            request.message,
            metadata={"retrieval_debug": retrieval["retrieval_debug"]},
        )
        assistant_message = add_message(session, conversation.id, "assistant", answer)
        add_message_sources(session, assistant_message.id, contexts)
        session.commit()
        yield _ndjson({
            "type": "done",
            "answer": answer,
            "sources": sources,
            "conversation_id": conversation.id,
        })

    return StreamingResponse(
        event_stream(),
        media_type="application/x-ndjson",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


def _ndjson(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False) + "\n"
