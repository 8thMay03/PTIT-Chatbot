from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import Base, Document
from app.db.repositories import (
    DEFAULT_DATASET_ID,
    ChunkRecord,
    DatasetConflict,
    DatasetNotFound,
    DocumentRecord,
    apply_document_move,
    create_dataset,
    delete_dataset_records,
    ensure_default_dataset,
    get_dataset_with_stats,
    list_datasets,
    list_datasets_with_stats,
    list_documents,
    save_parsed_document,
    update_dataset,
)


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    ensure_default_dataset(session)
    session.commit()
    return session


def _doc(doc_id="doc-1", dataset_id=None, source="data/a.md"):
    return DocumentRecord(
        id=doc_id,
        dataset_id=dataset_id,
        source_path=source,
        title="A",
        file_type="md",
        content_hash="h-" + doc_id,
        metadata={"size_bytes": 10},
        parsed_text="# A",
    )


def test_default_dataset_exists_and_first():
    session = _session()
    datasets = list_datasets(session)
    assert datasets[0].id == DEFAULT_DATASET_ID
    assert datasets[0].name == "Mặc định"


def test_create_update_duplicate_case_insensitive():
    session = _session()
    created = create_dataset(session, "  Sổ tay  ", "mô tả")
    session.commit()
    assert created.name == "Sổ tay"
    try:
        create_dataset(session, "sổ TAY")
        raise AssertionError("phải 409 trùng tên")
    except DatasetConflict:
        session.rollback()
    updated = update_dataset(session, created.id, name="Quy chế")
    session.commit()
    assert updated.name == "Quy chế"
    try:
        update_dataset(session, created.id, name="MẶC ĐỊNH")
        raise AssertionError("phải 409 trùng default")
    except DatasetConflict:
        session.rollback()


def test_validate_name_and_description():
    session = _session()
    for bad in ["", "   ", "x" * 101, "a\x00b"]:
        try:
            create_dataset(session, bad)
            raise AssertionError(f"phải từ chối {bad!r}")
        except (DatasetConflict, ValueError):
            session.rollback()
    try:
        create_dataset(session, "ok", "x" * 501)
        raise AssertionError("mô tả quá dài phải 422/409")
    except (DatasetConflict, ValueError):
        session.rollback()


def test_list_documents_filter_and_stats():
    session = _session()
    other = create_dataset(session, "Khác")
    session.commit()
    save_parsed_document(session, _doc("d1", DEFAULT_DATASET_ID, "data/a.md"))
    save_parsed_document(session, _doc("d2", other.id, "data/b.md"))
    session.commit()
    assert len(list_documents(session)) == 2
    assert len(list_documents(session, dataset_id=other.id)) == 1
    payloads = {p["id"]: p for p in list_datasets_with_stats(session)}
    assert payloads[DEFAULT_DATASET_ID]["document_count"] == 1
    assert payloads[other.id]["document_count"] == 1
    assert payloads[other.id]["pending_count"] == 1
    assert get_dataset_with_stats(session, "missing") is None


def test_delete_default_forbidden_and_missing():
    session = _session()
    try:
        delete_dataset_records(session, DEFAULT_DATASET_ID)
        raise AssertionError("không được xóa default")
    except DatasetConflict:
        session.rollback()
    try:
        delete_dataset_records(session, "missing")
        raise AssertionError("phải 404")
    except DatasetNotFound:
        session.rollback()


def test_apply_document_move_updates_metadata():
    session = _session()
    other = create_dataset(session, "Đích")
    session.commit()
    doc = save_parsed_document(session, _doc("d1", DEFAULT_DATASET_ID, "data/a.md"))
    session.commit()
    apply_document_move(session, doc, other.id, "data/datasets/%s/a.md" % other.id)
    session.commit()
    updated = session.get(Document, "d1")
    assert updated.dataset_id == other.id
    assert updated.source_path.endswith("a.md")
    assert updated.document_metadata["source"].endswith("a.md")


def test_chunk_record_ids_use_document_id():
    # ID chunk suy từ document_id, không từ source_path (S-02).
    from app.ingestion.pipeline import _chunk_records

    records, payload = _chunk_records("doc-uuid", "data/datasets/d1/a.md", "A", "# A\n\nNội dung")
    assert records
    assert all(r.id.startswith("doc-uuid::") for r in records)
    assert all(r.document_id == "doc-uuid" for r in records)
    assert payload[0]["metadata"]["document_id"] == "doc-uuid"
