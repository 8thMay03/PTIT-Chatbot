from __future__ import annotations

from app.vectordb.base import VectorStore
from app.vectordb.pgvector_store import PgVectorStore


def create_vector_store() -> VectorStore:
    return PgVectorStore()


__all__ = ["PgVectorStore", "VectorStore", "create_vector_store"]
