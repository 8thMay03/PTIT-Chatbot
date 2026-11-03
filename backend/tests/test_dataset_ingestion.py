from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.event import listens_for
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.models import Base, Chunk, Document
from app.db.repositories import DatasetConflict, DatasetNotFound
from app.embeddings.models import HashEmbeddingModel
from app.ingestion import uploads
from app.ingestion.jobs import ParseJobManager
from app.ingestion.pipeline import IngestionPipeline, dataset_dir
from app.ingestion import pipeline as pipeline_module


def _memory_engine():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool, future=True)

    @listens_for(engine, "connect")
    def _fk(dbapi_connection, connection_record):  # noqa: ARG001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    from app.db.repositories import ensure_default_dataset

    with sessionmaker(bind=engine)() as session:
        ensure_default_dataset(session)
        session.commit()
    return engine


def _pipeline(tmp_path, monkeypatch):
    engine = _memory_engine()
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    monkeypatch.setattr("app.ingestion.pipeline.SessionLocal", TestSession)
    monkeypatch.setattr("app.ingestion.pipeline.init_db", lambda: None)
    monkeypatch.setattr("app.ingestion.pipeline.invalidate_bm25_cache", lambda: None)
    monkeypatch.setattr("app.ingestion.jobs.SessionLocal", TestSession, raising=False)
    monkeypatch.setattr(settings, "documents_path", tmp_path / "data")
    monkeypatch.setattr(settings, "converted_documents_path", tmp_path / "cache")
    # File test nằm ngoài PROJECT_ROOT thật nên phải dời PROJECT_ROOT về tmp_path,
    # giống test_document_pipeline cũ (resolve_source_path kiểm tra relative_to).
    monkeypatch.setattr(uploads, "settings", settings)
    monkeypatch.setattr("app.ingestion.uploads.PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(pipeline_module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(pipeline_module.settings, "documents_path", tmp_path / "data")
    store = _RecordingStore()
    pipe = IngestionPipeline(embedding_model=HashEmbeddingModel(), vector_store=store)
    return pipe, engine, store


class _RecordingStore:
    collection_name = "test_documents"

    def __init__(self):
        self.added = []
        self.deleted = []
        self.reset_calls = 0

    def reset(self):
        self.reset_calls += 1

    def add(self, chunks, embeddings):
        self.added.extend(item["id"] for item in chunks)

    def delete(self, ids):
        self.deleted.extend(ids)

    def search(self, query_embedding, top_k, dataset_ids=None):
        return []


def _upload(pipe, filename, content, dataset_id=None):
    kwargs = {"dataset_id": dataset_id} if dataset_id else {}
    parsed = pipe.parse_upload(filename, content, **kwargs)
    return pipe.chunk_document(parsed["id"])


def test_upload_to_dataset_and_same_name_isolation(tmp_path, monkeypatch):
    pipe, engine, _store = _pipeline(tmp_path, monkeypatch)
    from app.db.repositories import create_dataset

    with sessionmaker(bind=engine)() as session:
        ds = create_dataset(session, "Sổ tay")
        session.commit()
        ds_id = ds.id

    first = _upload(pipe, "chung.md", "# A\nNội dung A".encode(), dataset_id=ds_id)
    second = _upload(pipe, "chung.md", "# B\nNội dung B".encode())
    assert first["dataset_id"] == ds_id
    assert second["dataset_id"] == "default"
    assert first["id"] != second["id"]
    assert (dataset_dir(ds_id) / "chung.md").is_file()
    assert (dataset_dir("default") / "chung.md").is_file()
    # Cùng tên trong cùng dataset thay thế bản cũ.
    third = _upload(pipe, "chung.md", "# A2\nNội dung A2".encode(), dataset_id=ds_id)
    assert third["id"] == first["id"]
    assert third["dataset_id"] == ds_id


def test_get_documents_filter_by_dataset(tmp_path, monkeypatch):
    pipe, engine, _store = _pipeline(tmp_path, monkeypatch)
    from app.db.repositories import create_dataset, list_documents

    with sessionmaker(bind=engine)() as session:
        ds = create_dataset(session, "Lọc")
        session.commit()
        ds_id = ds.id
    _upload(pipe, "a.md", "# A".encode(), dataset_id=ds_id)
    _upload(pipe, "b.md", "# B".encode())
    with sessionmaker(bind=engine)() as session:
        assert len(list_documents(session)) == 2
        assert len(list_documents(session, dataset_id=ds_id)) == 1


def test_move_documents_keeps_id_and_chunks(tmp_path, monkeypatch):
    pipe, engine, store = _pipeline(tmp_path, monkeypatch)
    from app.db.repositories import create_dataset

    with sessionmaker(bind=engine)() as session:
        src = create_dataset(session, "Nguồn")
        dst = create_dataset(session, "Đích")
        session.commit()
        src_id, dst_id = src.id, dst.id
    item = _upload(pipe, "chuyen.md", "# Chuyển\nNội dung giữ nguyên".encode(), dataset_id=src_id)
    before_chunks = None
    with sessionmaker(bind=engine)() as session:
        before_chunks = list(session.scalars(select(Chunk.id).where(Chunk.document_id == item["id"])))
        before_embedding_calls = 0

    calls = []
    orig_embed = pipe.embedding_model.embed
    monkeypatch.setattr(pipe.embedding_model, "embed", lambda texts: calls.append(texts) or orig_embed(texts))
    result = pipe.move_documents([item["id"]], dst_id)
    assert result == {"moved": 1, "dataset_id": dst_id}
    assert calls == []
    with sessionmaker(bind=engine)() as session:
        doc = session.get(Document, item["id"])
        assert doc.dataset_id == dst_id
        assert doc.source_path == (dataset_dir(dst_id) / "chuyen.md").as_posix() or doc.source_path.endswith("chuyen.md")
        after = list(session.scalars(select(Chunk.id).where(Chunk.document_id == item["id"])))
        assert after == before_chunks
    assert (dataset_dir(dst_id) / "chuyen.md").is_file()
    assert not (dataset_dir(src_id) / "chuyen.md").exists()


def test_move_documents_conflict_and_rollback(tmp_path, monkeypatch):
    pipe, engine, _store = _pipeline(tmp_path, monkeypatch)
    from app.db.repositories import create_dataset

    with sessionmaker(bind=engine)() as session:
        src = create_dataset(session, "Nguồn")
        dst = create_dataset(session, "Đích")
        session.commit()
        src_id, dst_id = src.id, dst.id
    _upload(pipe, "trung.md", "# Đích".encode(), dataset_id=dst_id)
    item = _upload(pipe, "trung.md", "# Nguồn".encode(), dataset_id=src_id)
    with pytest.raises(DatasetConflict, match="đã có file"):
        pipe.move_documents([item["id"]], dst_id)
    with sessionmaker(bind=engine)() as session:
        assert session.get(Document, item["id"]).dataset_id == src_id
    assert (dataset_dir(src_id) / "trung.md").is_file()


def test_move_documents_missing_and_state(tmp_path, monkeypatch):
    pipe, engine, _store = _pipeline(tmp_path, monkeypatch)
    with pytest.raises(DatasetNotFound):
        pipe.move_documents(["missing"], "default")
    with pytest.raises(DatasetNotFound):
        pipe.move_documents(["missing"], "no-such")


def test_delete_dataset_removes_files_and_vectors(tmp_path, monkeypatch):
    pipe, engine, store = _pipeline(tmp_path, monkeypatch)
    from app.db.repositories import create_dataset

    with sessionmaker(bind=engine)() as session:
        ds = create_dataset(session, "Xóa")
        session.commit()
        ds_id = ds.id
    item = _upload(pipe, "xoa.md", "# Xóa\nNội dung tài liệu cần xóa khỏi dataset".encode(), dataset_id=ds_id)
    with sessionmaker(bind=engine)() as session:
        vector_ids = list(session.scalars(select(Chunk.vector_id).where(Chunk.document_id == item["id"])))
    assert vector_ids
    result = pipe.delete_dataset(ds_id)
    assert result["documents"] == 1
    with sessionmaker(bind=engine)() as session:
        assert session.get(Document, item["id"]) is None
    assert not (dataset_dir(ds_id) / "xoa.md").exists()
    assert set(store.deleted) >= set(vector_ids)


def test_delete_default_and_busy_job_conflict(tmp_path, monkeypatch):
    pipe, engine, _store = _pipeline(tmp_path, monkeypatch)
    with pytest.raises(DatasetConflict, match="mặc định"):
        pipe.delete_dataset("default")
    with pytest.raises(DatasetNotFound):
        pipe.delete_dataset("missing")
    # Dataset còn job parse → 409.
    from app.db.repositories import create_dataset

    with sessionmaker(bind=engine)() as session:
        ds = create_dataset(session, "Bận")
        session.commit()
        ds_id = ds.id
    item = _upload(pipe, "ban.md", "# Bận\nNội dung tài liệu đang parse dở".encode(), dataset_id=ds_id)

    class _Busy:
        status = "running"

    from app.ingestion.jobs import parse_jobs as _jobs

    monkeypatch.setattr(_jobs, "active_for_document", lambda doc_id: _Busy() if doc_id == item["id"] else None)
    with pytest.raises(DatasetConflict, match="đang parse"):
        pipe.move_documents([item["id"]], "default")
    with pytest.raises(DatasetConflict, match="đang parse"):
        pipe.delete_dataset(ds_id)


def test_chunk_and_parse_by_dataset(tmp_path, monkeypatch):
    pipe, engine, store = _pipeline(tmp_path, monkeypatch)
    from app.db.repositories import create_dataset

    with sessionmaker(bind=engine)() as session:
        ds = create_dataset(session, "Một phần")
        session.commit()
        ds_id = ds.id
    a = pipe.parse_upload("a.md", "# A".encode(), dataset_id=ds_id)
    b = pipe.parse_upload("b.md", "# B".encode())
    result = pipe.chunk_documents(dataset_id=ds_id)
    assert result["documents"] == 1
    with pytest.raises(DatasetNotFound):
        pipe.chunk_documents(dataset_id="missing")
    # Job nền thật sẽ parse lại song song với save_markdown bên dưới; chỉ ghi nhận lời gọi.
    from app.ingestion.jobs import parse_jobs as _jobs

    enqueued = []
    monkeypatch.setattr(
        _jobs, "enqueue_parse", lambda document_id, path, **kwargs: enqueued.append(document_id) or document_id
    )
    # Parse lại dataset: tài liệu đã chunk không có markdown_edited → enqueue được.
    parsed = pipe.enqueue_dataset_parse(ds_id)
    assert parsed["skipped_edited"] == 0
    assert enqueued == [a["id"]]
    # Sửa tay Markdown → lần parse dataset sau bỏ qua.
    pipe.save_markdown(a["id"], "# Sửa tay")
    parsed2 = pipe.enqueue_dataset_parse(ds_id)
    assert parsed2["skipped_edited"] == 1
    with pytest.raises(DatasetNotFound):
        pipe.enqueue_dataset_parse("missing")


def test_rebuild_keeps_dataset_and_id(tmp_path, monkeypatch):
    pipe, engine, _store = _pipeline(tmp_path, monkeypatch)
    from app.db.repositories import create_dataset

    with sessionmaker(bind=engine)() as session:
        ds = create_dataset(session, "Giữ")
        session.commit()
        ds_id = ds.id
    item = _upload(pipe, "giu.md", "# Giữ".encode(), dataset_id=ds_id)
    # Nạp lại toàn bộ từ đĩa phải giữ id + dataset.
    result = pipe.ingest_documents()
    assert result["documents"] >= 1
    with sessionmaker(bind=engine)() as session:
        doc = session.get(Document, item["id"])
        assert doc is not None
        assert doc.dataset_id == ds_id


def test_upload_job_key_includes_dataset_and_result_dataset(tmp_path, monkeypatch):
    pipe, engine, _store = _pipeline(tmp_path, monkeypatch)
    from app.db.repositories import create_dataset

    with sessionmaker(bind=engine)() as session:
        ds = create_dataset(session, "Job")
        session.commit()
        ds_id = ds.id
    manager = ParseJobManager(pipeline=pipe, staging_root=tmp_path / "staging")
    try:
        job = manager.enqueue_upload("job.md", "# Job".encode(), dataset_id=ds_id)
        assert job.dataset_id == ds_id
        # Upload cùng tên ở dataset khác không xung đột key.
        job2 = manager.enqueue_upload("job.md", "# Job".encode(), dataset_id="default")
        assert job2.dataset_id == "default"
    finally:
        # Job nền phải xong khi monkeypatch còn hiệu lực, nếu không nó ghi vào data/ và DB thật.
        manager._executor.shutdown(wait=True)
    assert manager.get(job.id).status == "succeeded"
    assert manager.get(job2.id).dataset_id == "default"
    assert (dataset_dir(ds_id) / "job.md").is_file()


def _seed_legacy(engine, tmp_path, rel_path: str, text: str, *, parser: str | None = None, with_file=True):
    """Tài liệu kho cũ thuộc default, nằm ngoài datasets/ (vd. data/raw/x.md)."""
    from app.db.repositories import DocumentRecord, save_parsed_document

    if with_file:
        (tmp_path / rel_path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel_path).write_text(text, encoding="utf-8")
    metadata = {"source": rel_path, "file_name": Path(rel_path).name}
    if parser is not None:
        metadata["parser"] = parser
    doc_id = "legacy-" + Path(rel_path).stem
    with sessionmaker(bind=engine)() as session:
        save_parsed_document(
            session,
            DocumentRecord(
                id=doc_id, dataset_id="default", source_path=rel_path, title=Path(rel_path).stem,
                file_type=Path(rel_path).suffix.lstrip("."), content_hash="h-" + doc_id,
                metadata=metadata, parsed_text=text,
            ),
        )
        session.commit()
    return doc_id


def test_dataset_parse_uses_stored_parser_and_counts_conflicts(tmp_path, monkeypatch):
    pipe, engine, _store = _pipeline(tmp_path, monkeypatch)
    from datetime import datetime, timezone

    from app.ingestion.jobs import ParseJob, ParseJobConflict, parse_jobs as _jobs

    kept = _seed_legacy(engine, tmp_path, "data/raw/giu-parser.md", "# Giữ", parser="text")
    gone = _seed_legacy(engine, tmp_path, "data/raw/het-parser.md", "# Hết", parser="khong-con")
    racing = _seed_legacy(engine, tmp_path, "data/raw/dang-dua.md", "# Đua")
    calls = []

    def fake_enqueue(document_id, path, *, file_name=None, parser_name=None):
        if document_id == racing:
            raise ParseJobConflict("đang parse")
        calls.append((document_id, parser_name))
        return ParseJob(
            id="job-" + document_id, kind="parse", status="queued", document_id=document_id,
            file_name=file_name, parser_name=parser_name, dataset_id="default",
            created_at=datetime.now(timezone.utc),
        )

    monkeypatch.setattr(_jobs, "enqueue_parse", fake_enqueue)
    monkeypatch.setattr(_jobs, "active_for_document", lambda doc_id: None)
    result = pipe.enqueue_dataset_parse("default")
    # Parser đã lưu được giữ; parser không còn đọc được file thì về mặc định (None).
    assert sorted(calls) == sorted([(kept, "text"), (gone, None)])
    assert result["skipped_busy"] == 1
    assert {job.document_id for job in result["jobs"]} == {kept, gone}
    assert all(job.dataset_id == "default" and job.created_at for job in result["jobs"])


def test_upload_same_name_replaces_legacy_document_in_place(tmp_path, monkeypatch):
    pipe, engine, _store = _pipeline(tmp_path, monkeypatch)
    legacy_id = _seed_legacy(engine, tmp_path, "data/raw/x.md", "# Cũ")

    result = pipe.parse_upload("X.md", "# Mới\nNội dung mới".encode())

    assert result["id"] == legacy_id
    assert result["dataset_id"] == "default"
    assert (tmp_path / "data/raw/x.md").read_text(encoding="utf-8").startswith("# Mới")
    assert not (dataset_dir("default") / "X.md").exists()
    with sessionmaker(bind=engine)() as session:
        docs = list(session.scalars(select(Document).where(Document.dataset_id == "default")))
        assert [(d.id, d.source_path) for d in docs] == [(legacy_id, "data/raw/x.md")]
    # Dataset khác không bị ảnh hưởng: cùng tên ở đó vẫn tạo tài liệu riêng.
    from app.db.repositories import create_dataset

    with sessionmaker(bind=engine)() as session:
        other = create_dataset(session, "Khác")
        session.commit()
        other_id = other.id
    separate = pipe.parse_upload("x.md", "# Khác".encode(), dataset_id=other_id)
    assert separate["id"] != legacy_id
    assert (dataset_dir(other_id) / "x.md").is_file()


def test_upload_replacing_legacy_document_restores_file_when_commit_fails(tmp_path, monkeypatch):
    pipe, engine, _store = _pipeline(tmp_path, monkeypatch)
    legacy_id = _seed_legacy(engine, tmp_path, "data/raw/x.md", "# Cũ")
    from sqlalchemy.orm import Session

    class FailingCommit(Session):
        def commit(self):
            raise RuntimeError("commit lỗi")

    monkeypatch.setattr(
        "app.ingestion.pipeline.SessionLocal", sessionmaker(bind=engine, class_=FailingCommit)
    )
    with pytest.raises(RuntimeError, match="commit lỗi"):
        pipe.parse_upload("x.md", "# Mới".encode())
    assert (tmp_path / "data/raw/x.md").read_text(encoding="utf-8") == "# Cũ"
    assert not (dataset_dir("default") / "x.md").exists()
    with sessionmaker(bind=engine)() as session:
        assert session.get(Document, legacy_id).parsed_text == "# Cũ"


def test_resolve_source_path_ignores_same_name_file_in_other_dataset(tmp_path, monkeypatch):
    pipe, engine, _store = _pipeline(tmp_path, monkeypatch)
    from app.db.repositories import create_dataset

    with sessionmaker(bind=engine)() as session:
        ds = create_dataset(session, "Khác")
        session.commit()
        ds_id = ds.id
    pipe.parse_upload("y.md", "# Của dataset khác".encode(), dataset_id=ds_id)
    other_file = dataset_dir(ds_id) / "y.md"
    assert other_file.is_file()
    # Tài liệu kho cũ đã mất file nguồn, trùng tên với file của dataset kia.
    legacy_id = _seed_legacy(engine, tmp_path, "data/raw/y.md", "# Cũ", with_file=False)

    assert uploads.resolve_source_path("data/raw/y.md") is None
    pipe.delete_ingested_document(legacy_id)
    assert other_file.is_file()
    # Fallback rglob vẫn sửa được đường dẫn cũ khi file chỉ đổi chỗ ngoài datasets/.
    (tmp_path / "data/processed").mkdir(parents=True)
    moved = tmp_path / "data/processed/z.md"
    moved.write_text("# Z", encoding="utf-8")
    assert uploads.resolve_source_path("data/raw/z.md") == moved.resolve()
