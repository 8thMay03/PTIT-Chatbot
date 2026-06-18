from pydantic import BaseModel, Field


class Source(BaseModel):
    source: str
    source_name: str | None = None
    document_id: str | None = None
    chunk_id: str | None = None
    heading: str | None = None
    heading_level: int | None = None
    section_path: str | None = None
    chunk_index: int
    text: str
    score: float | None = None


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    user_id: str | None = None
    top_k: int = Field(default=4, ge=1, le=10)


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    sources: list[Source]


class IngestResponse(BaseModel):
    documents: int
    chunks: int
    collection: str
