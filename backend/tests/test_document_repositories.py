from dataclasses import replace

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.models import Base, Chunk, Document
from app.db.repositories import (
    ChunkRecord,
    DocumentRecord,
    delete_document,
    get_edited_markdown,
    list_documents,
    replace_document_chunks,
    save_parsed_document,
    serialize_document,
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
        parsed_text="# Handbook\nNội dung tài liệu",
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


def _index(session: Session, record: DocumentRecord, chunks: list[ChunkRecord]) -> Document:
    document = save_parsed_document(session, record)
    replace_document_chunks(session, document, chunks)
    session.commit()
    return document


def test_save_parsed_document_stores_text_without_chunks() -> None:
    session = _session()
    record, _chunks = _document()

    document = save_parsed_document(session, record)
    session.commit()

    assert document.status == "parsed"
    assert document.parsed_text == record.parsed_text
    assert document.parsed_at is not None
    assert list_documents(session)[0][1] == 0


def test_replace_document_chunks_activates_and_replaces() -> None:
    session = _session()
    record, chunks = _document()
    document = _index(session, record, chunks)
    assert document.status == "active"

    updated_chunks = [
        ChunkRecord(id="doc-1-chunk-0", document_id="doc-1", chunk_index=0, text="Nội dung mới", vector_id="doc-1-chunk-0"),
        ChunkRecord(id="doc-1-chunk-1", document_id="doc-1", chunk_index=1, text="Đoạn thứ hai", vector_id="doc-1-chunk-1"),
    ]
    replace_document_chunks(session, document, updated_chunks)
    session.commit()

    documents = list_documents(session)
    assert len(documents) == 1
    assert documents[0][0].id == "doc-1"
    assert documents[0][1] == 2
    assert session.get(Chunk, "doc-1-chunk-1").text == "Đoạn thứ hai"


def test_reparse_keeps_chunks_and_status_follows_content() -> None:
    session = _session()
    record, chunks = _document()
    _index(session, record, chunks)

    # Same text again: the chunks still match it.
    same = save_parsed_document(session, record)
    session.commit()
    assert same.status == "active"

    changed = save_parsed_document(session, replace(record, content_hash="def", parsed_text="# Mới"))
    session.commit()
    assert changed.status == "parsed"
    assert changed.parsed_text == "# Mới"
    # Old chunks keep serving retrieval until the chunk step replaces them.
    assert session.get(Chunk, "doc-1-chunk-0") is not None

    # Back to the indexed text is still "parsed": the chunks were not rebuilt in between.
    restored = save_parsed_document(session, record)
    session.commit()
    assert restored.status == "parsed"


def test_edited_markdown_and_serialized_flag() -> None:
    session = _session()
    record, _chunks = _document()
    save_parsed_document(session, record)
    edited, _ = _document("doc-2")
    edited = replace(
        edited,
        source_path="data/edited.md",
        metadata={"markdown_edited": True},
        parsed_text="# Sửa tay",
    )
    document = save_parsed_document(session, edited)
    session.commit()

    assert get_edited_markdown(session) == {"data/edited.md": "# Sửa tay"}
    assert serialize_document(document, 0)["markdown_edited"] is True
    assert serialize_document(session.get(Document, "doc-1"), 0)["markdown_edited"] is False


def test_delete_document_removes_chunks() -> None:
    session = _session()
    record, chunks = _document()
    _index(session, record, chunks)

    deleted = delete_document(session, "doc-1")
    session.commit()

    assert deleted is not None
    assert session.get(Document, "doc-1") is None
    assert session.scalars(select(Chunk)).all() == []
