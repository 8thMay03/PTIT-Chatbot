from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Base, Chunk, Document
from app.vectordb.base import VectorStore
from app.vectordb.pgvector_store import PgVectorStore
from app.vectordb import create_vector_store


@pytest.fixture
def memory_session_factory():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return factory


def test_pgvector_store_add_search_and_delete(memory_session_factory) -> None:
    store = PgVectorStore(session_factory=memory_session_factory)

    with memory_session_factory() as session:
        doc = Document(
            id="doc-1",
            source_path="data/doc1.md",
            title="Doc 1",
            file_type="md",
            content_hash="h1",
            status="active",
        )
        session.add(doc)
        c1 = Chunk(
            id="chunk-1",
            document_id="doc-1",
            chunk_index=0,
            text="Học phí PTIT năm 2024",
            vector_id="vec-1",
            chunk_metadata={"heading": "Học phí", "parent_id": "p-1"},
        )
        c2 = Chunk(
            id="chunk-2",
            document_id="doc-1",
            chunk_index=1,
            text="Quy chế thi đại học",
            vector_id="vec-2",
            chunk_metadata={"heading": "Quy chế"},
        )
        session.add_all([c1, c2])
        session.commit()

    # Add embeddings (chunk-1 closer to [1, 0, 0], chunk-2 closer to [0, 1, 0])
    store.add(
        [{"id": "chunk-1"}, {"id": "chunk-2"}],
        [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
    )

    # Search with query embedding [0.9, 0.1, 0.0]
    results = store.search([0.9, 0.1, 0.0], top_k=2)
    assert len(results) == 2
    assert results[0]["chunk_id"] == "chunk-1"
    assert results[0]["score"] > results[1]["score"]
    assert results[0]["parent_id"] == "p-1"

    # Delete chunk-1 vector
    store.delete(["chunk-1"])
    results_after_delete = store.search([0.9, 0.1, 0.0], top_k=2)
    assert len(results_after_delete) == 1
    assert results_after_delete[0]["chunk_id"] == "chunk-2"

    # Reset
    store.reset()
    assert store.search([0.9, 0.1, 0.0], top_k=2) == []


def test_create_vector_store_factory() -> None:
    pg_store = create_vector_store()
    assert isinstance(pg_store, PgVectorStore)
