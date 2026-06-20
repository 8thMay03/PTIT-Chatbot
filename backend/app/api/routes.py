import json
from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.schemas import ChatRequest, ChatResponse, IngestResponse
from app.db import get_session
from app.core.config import settings
from app.db.repositories import (
    add_message,
    add_message_sources,
    ensure_conversation,
    get_recent_conversation_history,
)
from app.generation.rag_chain import rag_chain
from app.generation.citations import public_citations
from app.generation.llm import _normalize_answer_citations, stream_answer_with_llm
from app.ingestion import ingestion_pipeline

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/ingest", response_model=IngestResponse)
def ingest() -> IngestResponse:
    result = ingestion_pipeline.ingest_documents()
    return IngestResponse(**result)


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
    result = rag_chain.answer(request.message, top_k=request.top_k, history=history)
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
    retrieval = rag_chain.retrieve_context(request.message, top_k=request.top_k, history=history)

    def event_stream() -> Iterator[str]:
        contexts = retrieval["contexts"] if retrieval["strong_context"] else []
        sources = public_citations(contexts)
        deltas: list[str] = []
        yield _ndjson({"type": "start", "conversation_id": conversation.id})

        if retrieval["strong_context"]:
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
