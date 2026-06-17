from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.schemas import ChatRequest, ChatResponse, IngestResponse
from app.db import get_session
from app.db.repositories import add_message, add_message_sources, ensure_conversation
from app.generation import rag_chain
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

    result = rag_chain.answer(request.message, top_k=request.top_k)
    conversation = ensure_conversation(
        session,
        request.conversation_id,
        user_id=request.user_id,
        title=request.message.strip()[:80],
    )
    add_message(session, conversation.id, "user", request.message)
    assistant_message = add_message(session, conversation.id, "assistant", result["answer"])
    add_message_sources(session, assistant_message.id, result["sources"])
    session.commit()

    return ChatResponse(conversation_id=conversation.id, **result)
