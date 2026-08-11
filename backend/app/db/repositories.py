from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from pathlib import Path

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.db.models import Chunk, Conversation, Document, Message, MessageSource


@dataclass(frozen=True)
class DocumentRecord:
    id: str
    source_path: str
    title: str | None
    file_type: str | None
    content_hash: str
    metadata: dict | None = None


@dataclass(frozen=True)
class ChunkRecord:
    id: str
    document_id: str
    chunk_index: int
    text: str
    vector_id: str
    token_count: int | None = None
    metadata: dict | None = None


def replace_knowledge_base(
    session: Session,
    documents: list[DocumentRecord],
    chunks: list[ChunkRecord],
) -> None:
    session.execute(delete(Document))

    session.add_all(
        Document(
            id=document.id,
            source_path=document.source_path,
            title=document.title,
            file_type=document.file_type,
            content_hash=document.content_hash,
            status="active",
            document_metadata=document.metadata,
        )
        for document in documents
    )
    session.add_all(
        Chunk(
            id=chunk.id,
            document_id=chunk.document_id,
            chunk_index=chunk.chunk_index,
            text=chunk.text,
            token_count=chunk.token_count,
            vector_id=chunk.vector_id,
            chunk_metadata=chunk.metadata,
        )
        for chunk in chunks
    )


def list_documents(session: Session) -> list[tuple[Document, int]]:
    chunk_count = func.count(Chunk.id).label("chunk_count")
    rows = session.execute(
        select(Document, chunk_count)
        .outerjoin(Chunk, Chunk.document_id == Document.id)
        .group_by(Document.id)
        .order_by(Document.updated_at.desc(), Document.title.asc())
    ).all()
    return [(document, count) for document, count in rows]


def get_document_with_chunk_count(session: Session, document_id: str) -> tuple[Document, int] | None:
    chunk_count = func.count(Chunk.id).label("chunk_count")
    row = session.execute(
        select(Document, chunk_count)
        .outerjoin(Chunk, Chunk.document_id == Document.id)
        .where(Document.id == document_id)
        .group_by(Document.id)
    ).first()
    if row is None:
        return None
    return row[0], row[1]


def get_document_vector_ids(session: Session, document_id: str) -> list[str]:
    return list(session.scalars(select(Chunk.vector_id).where(Chunk.document_id == document_id)))


def upsert_document(
    session: Session,
    document: DocumentRecord,
    chunks: list[ChunkRecord],
) -> Document:
    existing = session.get(Document, document.id)
    if existing is None:
        existing = Document(
            id=document.id,
            source_path=document.source_path,
            title=document.title,
            file_type=document.file_type,
            content_hash=document.content_hash,
            status="active",
            document_metadata=document.metadata,
        )
        session.add(existing)
    else:
        existing.source_path = document.source_path
        existing.title = document.title
        existing.file_type = document.file_type
        existing.content_hash = document.content_hash
        existing.status = "active"
        existing.document_metadata = document.metadata
        existing.updated_at = datetime.now(timezone.utc)
        session.execute(delete(Chunk).where(Chunk.document_id == document.id))

    session.flush()
    session.add_all(
        Chunk(
            id=chunk.id,
            document_id=chunk.document_id,
            chunk_index=chunk.chunk_index,
            text=chunk.text,
            token_count=chunk.token_count,
            vector_id=chunk.vector_id,
            chunk_metadata=chunk.metadata,
        )
        for chunk in chunks
    )
    session.flush()
    return existing


def delete_document(session: Session, document_id: str) -> Document | None:
    document = session.get(Document, document_id)
    if document is None:
        return None
    session.delete(document)
    session.flush()
    return document


def get_document_preview_text(session: Session, document_id: str, limit: int = 2500) -> str | None:
    texts = list(
        session.scalars(
            select(Chunk.text)
            .where(Chunk.document_id == document_id)
            .order_by(Chunk.chunk_index)
            .limit(4)
        )
    )
    if not texts:
        return None
    joined = "\n\n".join(texts)
    if len(joined) <= limit:
        return joined
    return joined[:limit].rstrip() + "…"


def serialize_document(document: Document, chunk_count: int, size_bytes: int | None = None) -> dict:
    metadata = document.document_metadata or {}
    file_name = Path(document.source_path).name
    if size_bytes is None:
        raw_size = metadata.get("size_bytes")
        size_bytes = raw_size if isinstance(raw_size, int) else None
    return {
        "id": document.id,
        "title": document.title or Path(document.source_path).stem,
        "file_name": file_name,
        "source_path": document.source_path,
        "file_type": document.file_type,
        "status": document.status,
        "chunk_count": chunk_count,
        "size_bytes": size_bytes,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
    }


def ensure_conversation(
    session: Session,
    conversation_id: str | None,
    user_id: str | None = None,
    title: str | None = None,
) -> Conversation:
    if conversation_id:
        conversation = session.get(Conversation, conversation_id)
        if conversation:
            return conversation

    conversation = Conversation(id=conversation_id or str(uuid4()), user_id=user_id, title=title)
    session.add(conversation)
    session.flush()
    return conversation


def add_message(
    session: Session,
    conversation_id: str,
    role: str,
    content: str,
    metadata: dict | None = None,
) -> Message:
    message = Message(
        id=str(uuid4()),
        conversation_id=conversation_id,
        role=role,
        content=content,
        message_metadata=metadata,
        created_at=datetime.now(timezone.utc),
    )
    session.add(message)
    session.execute(
        update(Conversation)
        .where(Conversation.id == conversation_id)
        .values(updated_at=func.now())
    )
    session.flush()
    return message


def get_recent_conversation_history(
    session: Session,
    conversation_id: str,
    max_messages: int,
    max_chars: int,
) -> list[dict[str, str]]:
    if max_messages <= 0 or max_chars <= 0:
        return []

    messages = list(
        session.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(max_messages)
        )
    )
    chronological = [
        {"role": message.role, "content": message.content}
        for message in reversed(messages)
        if message.role in {"user", "assistant"}
    ]
    return limit_history(chronological, max_messages=max_messages, max_chars=max_chars)


def limit_history(
    messages: list[dict[str, str]],
    max_messages: int,
    max_chars: int,
) -> list[dict[str, str]]:
    """Keep the newest complete messages that fit within both memory limits."""
    if max_messages <= 0 or max_chars <= 0:
        return []

    selected: list[dict[str, str]] = []
    remaining_chars = max_chars
    for message in reversed(messages[-max_messages:]):
        content = message.get("content", "").strip()
        if not content or remaining_chars <= 0:
            continue
        if len(content) > remaining_chars:
            content = content[:remaining_chars].rstrip()
        selected.append({"role": message.get("role", "user"), "content": content})
        remaining_chars -= len(content)
    return list(reversed(selected))


def add_message_sources(session: Session, message_id: str, sources: list[dict]) -> None:
    if not sources:
        return

    chunk_ids = [source.get("chunk_id") for source in sources if source.get("chunk_id")]
    existing_chunk_ids = set(
        session.scalars(select(Chunk.id).where(Chunk.id.in_(chunk_ids))).all()
    ) if chunk_ids else set()

    session.add_all(
        MessageSource(
            id=str(uuid4()),
            message_id=message_id,
            chunk_id=source.get("chunk_id") if source.get("chunk_id") in existing_chunk_ids else None,
            score=source.get("score"),
            excerpt=source.get("text"),
        )
        for source in sources
    )
