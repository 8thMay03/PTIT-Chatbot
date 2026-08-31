from __future__ import annotations

from app.core.config import settings
from app.vectordb.base import VectorStore
from app.vectordb.chroma_store import ChromaVectorStore
from app.vectordb.pgvector_store import PgVectorStore


def create_vector_store(store_type: str | None = None) -> VectorStore:
    selected = store_type or getattr(settings, "vector_store_type", "pgvector")
    if selected == "chroma":
        return ChromaVectorStore(settings.vector_db_path)
    return PgVectorStore()


__all__ = ["ChromaVectorStore", "PgVectorStore", "VectorStore", "create_vector_store"]
