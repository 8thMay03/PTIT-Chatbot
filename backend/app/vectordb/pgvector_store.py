from __future__ import annotations

from typing import Any, Callable
import numpy as np
from sqlalchemy import or_, select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.db.models import Chunk
from app.db.session import SessionLocal


class PgVectorStore:
    """Vector storage and similarity search backed by PostgreSQL pgvector (with SQLite in-memory test fallback)."""

    collection_name = "ptit_documents"

    def __init__(self, session_factory: Callable[[], Session] | None = None) -> None:
        self.session_factory = session_factory or SessionLocal

    def reset(self) -> None:
        """Clear all stored vector embeddings."""
        with self.session_factory() as session:
            session.execute(update(Chunk).values(embedding=None))
            session.commit()

    def add(self, chunks: list[dict], embeddings: list[list[float]]) -> None:
        """Store embeddings for the given chunks."""
        if not chunks or not embeddings:
            return

        with self.session_factory() as session:
            for chunk_data, embedding in zip(chunks, embeddings):
                chunk_id = chunk_data.get("id") or chunk_data.get("chunk_id")
                vector_id = chunk_data.get("vector_id")
                if chunk_id:
                    session.execute(
                        update(Chunk)
                        .where(Chunk.id == chunk_id)
                        .values(embedding=embedding)
                    )
                elif vector_id:
                    session.execute(
                        update(Chunk)
                        .where(Chunk.vector_id == vector_id)
                        .values(embedding=embedding)
                    )
            session.commit()

    def delete(self, ids: list[str]) -> None:
        """Clear embeddings for chunks matching the given IDs or vector IDs."""
        if not ids:
            return

        with self.session_factory() as session:
            session.execute(
                update(Chunk)
                .where(or_(Chunk.id.in_(ids), Chunk.vector_id.in_(ids)))
                .values(embedding=None)
            )
            session.commit()

    def search(
        self, query_embedding: list[float], top_k: int, dataset_ids: list[str] | None = None
    ) -> list[dict]:
        """Perform cosine similarity search against stored chunk embeddings."""
        if top_k <= 0 or not query_embedding:
            return []

        with self.session_factory() as session:
            from app.db.models import Dataset, Document

            bind = session.get_bind()
            is_postgres = bind.dialect.name == "postgresql" if bind else False

            needs_filter = dataset_ids is not None or _needs_dataset_filter(session)
            if not needs_filter:
                # Đường nhanh: không join để baseline và query plan HNSW không đổi.
                if is_postgres:
                    cosine_distance = Chunk.embedding.cosine_distance(query_embedding)
                    query = (
                        select(
                            Chunk,
                            (1.0 - cosine_distance).label("score"),
                        )
                        .where(Chunk.embedding.is_not(None))
                        .order_by(cosine_distance.asc())
                        .limit(top_k)
                    )
                    rows = session.execute(query).all()
                    return [_format_chunk_context(chunk, float(score)) for chunk, score in rows]
                else:
                    # SQLite fallback for in-memory unit tests
                    chunks = list(session.scalars(select(Chunk).where(Chunk.embedding.is_not(None))))
                    if not chunks:
                        return []

                    q_vec = np.array(query_embedding, dtype=float)
                    q_norm = np.linalg.norm(q_vec)
                    scored: list[tuple[Chunk, float]] = []

                    for chunk in chunks:
                        if chunk.embedding is None:
                            continue
                        c_vec = np.array(chunk.embedding, dtype=float)
                        c_norm = np.linalg.norm(c_vec)
                        if q_norm > 0 and c_norm > 0:
                            sim = float(np.dot(q_vec, c_vec) / (q_norm * c_norm))
                        else:
                            sim = 0.0
                        scored.append((chunk, sim))

                    scored.sort(key=lambda item: (-item[1], item[0].chunk_index))
                    return [_format_chunk_context(chunk, score) for chunk, score in scored[:top_k]]

            allowed = _allowed_dataset_ids(session, dataset_ids)
            if not allowed:
                return []
            base = (
                select(Chunk, (1.0 - Chunk.embedding.cosine_distance(query_embedding)).label("score"))
                if is_postgres
                else select(Chunk)
            )
            query = (
                base.join(Document, Chunk.document_id == Document.id)
                .join(Dataset, Document.dataset_id == Dataset.id)
                .where(Chunk.embedding.is_not(None))
                .where(Dataset.enabled.is_(True))
                .where(Document.dataset_id.in_(allowed))
            )
            if is_postgres:
                cosine_distance = Chunk.embedding.cosine_distance(query_embedding)
                _enable_iterative_scan(session)
                query = query.order_by(cosine_distance.asc()).limit(top_k)
                rows = session.execute(query).all()
                return [_format_chunk_context(chunk, float(score)) for chunk, score in rows]
            else:
                chunks = list(session.scalars(query))
                if not chunks:
                    return []
                q_vec = np.array(query_embedding, dtype=float)
                q_norm = np.linalg.norm(q_vec)
                scored = []
                for chunk in chunks:
                    if chunk.embedding is None:
                        continue
                    c_vec = np.array(chunk.embedding, dtype=float)
                    c_norm = np.linalg.norm(c_vec)
                    sim = float(np.dot(q_vec, c_vec) / (q_norm * c_norm)) if q_norm > 0 and c_norm > 0 else 0.0
                    scored.append((chunk, sim))
                scored.sort(key=lambda item: (-item[1], item[0].chunk_index))
                return [_format_chunk_context(chunk, score) for chunk, score in scored[:top_k]]


def _enable_iterative_scan(session: Session) -> bool:
    """Bật hnsw.iterative_scan (pgvector ≥ 0.8) cho transaction hiện tại để truy vấn
    có lọc vẫn đủ top_k (RK-01).

    Chạy trong savepoint: pgvector cũ từ chối tham số này, và lỗi đó chỉ được
    rollback về savepoint thay vì làm hỏng transaction của câu SELECT sau đó.
    """
    try:
        with session.begin_nested():
            session.execute(text("SET LOCAL hnsw.iterative_scan = relaxed_order"))
    except DBAPIError:
        return False
    return True


def _needs_dataset_filter(session) -> bool:
    from app.db.models import Dataset

    disabled = session.scalar(select(Dataset.id).where(Dataset.enabled.is_(False)).limit(1))
    return disabled is not None


def _allowed_dataset_ids(session, dataset_ids: list[str] | None) -> list[str] | None:
    from app.db.models import Dataset

    enabled = list(session.scalars(select(Dataset.id).where(Dataset.enabled.is_(True))))
    if dataset_ids is None:
        return enabled
    wanted = set(dataset_ids)
    return [did for did in enabled if did in wanted]


def _format_chunk_context(chunk: Chunk, score: float) -> dict[str, Any]:
    metadata = chunk.chunk_metadata or {}
    context: dict[str, Any] = {
        "source": metadata.get("source", ""),
        "source_name": metadata.get("source_name", ""),
        "document_id": chunk.document_id,
        "chunk_id": chunk.id,
        "heading": metadata.get("heading", ""),
        "heading_level": metadata.get("heading_level"),
        "section_path": metadata.get("section_path", ""),
        "chunk_index": chunk.chunk_index,
        "text": chunk.text,
        "search_text": chunk.search_text or chunk.text,
        "score": max(0.0, min(1.0, score)),
    }
    if metadata.get("parent_id"):
        context.update(
            {
                "parent_id": metadata["parent_id"],
                "parent_index": int(metadata.get("parent_index", 0)),
                "child_index": int(metadata.get("child_index", 0)),
                "parent_text": metadata.get("parent_text", chunk.text),
                "chunk_type": metadata.get("chunk_type", "child"),
            }
        )
    return context
