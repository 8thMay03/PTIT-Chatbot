from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import Base, Dataset, Document
from app.db.repositories import (
    ChunkRecord,
    DatasetConflict,
    DatasetNotFound,
    DocumentRecord,
    apply_document_move,
    create_dataset,
    delete_dataset_records,
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
    return Session(engine)


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


def test_no_dataset_is_created_implicitly_and_list_sorts_by_name():
    session = _session()
    assert list_datasets(session) == []
    assert list_datasets_with_stats(session) == []
    create_dataset(session, "beta")
    create_dataset(session, "Alpha")
    session.commit()
    assert [d.name for d in list_datasets(session)] == ["Alpha", "beta"]
    assert all("is_default" not in p for p in list_datasets_with_stats(session))


def test_document_without_dataset_is_rejected():
    session = _session()
    try:
        save_parsed_document(session, _doc("d1", None, "data/a.md"))
        raise AssertionError("tài liệu phải thuộc một dataset")
    except ValueError:
        session.rollback()


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
    other = create_dataset(session, "Mặc định")
    session.commit()
    updated = update_dataset(session, created.id, name="Quy chế")
    session.commit()
    assert updated.name == "Quy chế"
    try:
        update_dataset(session, created.id, name="MẶC ĐỊNH")
        raise AssertionError("phải 409 trùng tên dataset khác")
    except DatasetConflict:
        session.rollback()
    assert other.name == "Mặc định"


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
    first = create_dataset(session, "Chung")
    other = create_dataset(session, "Khác")
    session.commit()
    save_parsed_document(session, _doc("d1", first.id, "data/a.md"))
    save_parsed_document(session, _doc("d2", other.id, "data/b.md"))
    session.commit()
    assert len(list_documents(session)) == 2
    assert len(list_documents(session, dataset_id=other.id)) == 1
    payloads = {p["id"]: p for p in list_datasets_with_stats(session)}
    assert payloads[first.id]["document_count"] == 1
    assert payloads[other.id]["document_count"] == 1
    assert payloads[other.id]["pending_count"] == 1
    assert get_dataset_with_stats(session, "missing") is None


def test_delete_legacy_default_dataset_and_missing():
    # Dòng `default` còn lại từ bản cũ giờ là dataset thường: xóa được cùng tài liệu.
    session = _session()
    session.add(Dataset(id="default", name="Mặc định"))
    session.commit()
    save_parsed_document(session, _doc("d1", "default", "data/a.md"))
    session.commit()
    count, source_paths, _vector_ids = delete_dataset_records(session, "default")
    session.commit()
    assert (count, source_paths) == (1, ["data/a.md"])
    assert session.get(Dataset, "default") is None
    assert session.get(Document, "d1") is None
    try:
        delete_dataset_records(session, "missing")
        raise AssertionError("phải 404")
    except DatasetNotFound:
        session.rollback()


def test_apply_document_move_updates_metadata():
    session = _session()
    source = create_dataset(session, "Nguồn")
    other = create_dataset(session, "Đích")
    session.commit()
    doc = save_parsed_document(session, _doc("d1", source.id, "data/a.md"))
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
