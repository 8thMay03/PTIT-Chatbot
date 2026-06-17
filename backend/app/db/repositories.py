from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

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
    )
    session.add(message)
    session.execute(
        update(Conversation)
        .where(Conversation.id == conversation_id)
        .values(updated_at=func.now())
    )
    session.flush()
    return message


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
