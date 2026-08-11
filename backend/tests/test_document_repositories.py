from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.models import Base, Chunk, Document
from app.db.repositories import (
    ChunkRecord,
    DocumentRecord,
    delete_document,
    list_documents,
    upsert_document,
)


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _document(doc_id: str = "doc-1", title: str = "Handbook") -> tuple[DocumentRecord, list[ChunkRecord]]:
    record = DocumentRecord(
        id=doc_id,
        source_path="data/handbook.md",
        title=title,
        file_type="md",
        content_hash="abc",
        metadata={"size_bytes": 12},
    )
    chunks = [
        ChunkRecord(
            id=f"{doc_id}-chunk-0",
            document_id=doc_id,
            chunk_index=0,
            text="Nội dung tài liệu",
            vector_id=f"{doc_id}-chunk-0",
            token_count=3,
        )
    ]
    return record, chunks


def test_upsert_document_inserts_and_replaces_chunks() -> None:
    session = _session()
    record, chunks = _document()

    upsert_document(session, record, chunks)
    session.commit()

    updated_chunks = [
        ChunkRecord(
            id="doc-1-chunk-0",
            document_id="doc-1",
            chunk_index=0,
            text="Nội dung mới",
            vector_id="doc-1-chunk-0",
        ),
        ChunkRecord(
            id="doc-1-chunk-1",
            document_id="doc-1",
            chunk_index=1,
            text="Đoạn thứ hai",
            vector_id="doc-1-chunk-1",
        ),
    ]
    upsert_document(session, record, updated_chunks)
    session.commit()

    documents = list_documents(session)
    assert len(documents) == 1
    document, chunk_count = documents[0]
    assert document.id == "doc-1"
    assert chunk_count == 2
    assert session.get(Chunk, "doc-1-chunk-1") is not None


def test_delete_document_removes_chunks() -> None:
    session = _session()
    record, chunks = _document()
    upsert_document(session, record, chunks)
    session.commit()

    deleted = delete_document(session, "doc-1")
    session.commit()

    assert deleted is not None
    assert session.get(Document, "doc-1") is None
    assert session.scalars(select(Chunk)).all() == []
