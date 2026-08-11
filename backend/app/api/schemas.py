from datetime import datetime

from pydantic import BaseModel, Field


class Source(BaseModel):
    citation_id: int
    source_name: str
    heading: str | None = None
    section_path: str | None = None
    article: str | None = None
    clauses: list[str] = Field(default_factory=list)
    points: list[str] = Field(default_factory=list)
    locator: str | None = None


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


class DocumentItem(BaseModel):
    id: str
    title: str
    file_name: str
    source_path: str
    file_type: str | None = None
    status: str = "active"
    chunk_count: int = 0
    size_bytes: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DocumentDetail(DocumentItem):
    preview: str | None = None


class DocumentListResponse(BaseModel):
    documents: list[DocumentItem]


class DocumentDeleteResponse(BaseModel):
    id: str
    deleted: bool = True
