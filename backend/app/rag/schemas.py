from pydantic import BaseModel, Field


class Source(BaseModel):
    source: str
    chunk_index: int
    text: str
    score: float | None = None


class ChatRequest(BaseModel):
    message: str
    top_k: int = Field(default=4, ge=1, le=10)


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]


class IngestResponse(BaseModel):
    documents: int
    chunks: int
    collection: str
