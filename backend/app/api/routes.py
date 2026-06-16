from fastapi import APIRouter, HTTPException

from app.rag.schemas import ChatRequest, ChatResponse, IngestResponse
from app.rag.service import rag_service

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/ingest", response_model=IngestResponse)
def ingest() -> IngestResponse:
    result = rag_service.ingest_documents()
    return IngestResponse(**result)


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message must not be empty.")

    result = rag_service.answer(request.message, top_k=request.top_k)
    return ChatResponse(**result)
