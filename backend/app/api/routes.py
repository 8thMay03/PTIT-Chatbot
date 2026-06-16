from fastapi import APIRouter, HTTPException

from app.api.schemas import ChatRequest, ChatResponse, IngestResponse
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
def chat(request: ChatRequest) -> ChatResponse:
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message must not be empty.")

    result = rag_chain.answer(request.message, top_k=request.top_k)
    return ChatResponse(**result)
