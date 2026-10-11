from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base, Chunk, Document
from app.embeddings.models import HashEmbeddingModel
from app.ingestion.pipeline import IngestionPipeline


class RecordingVectorStore:
    collection_name = "test_documents"

    def __init__(self) -> None:
        self.added: list[str] = []
        self.payloads: list[dict] = []
        self.deleted: list[str] = []
        self.reset_calls = 0

    def reset(self) -> None:
        self.reset_calls += 1
        self.added.clear()

    def add(self, chunks: list[dict], embeddings: list[list[float]]) -> None:
        self.added.extend(item["id"] for item in chunks)
        self.payloads.extend(chunks)

    def delete(self, ids: list[str]) -> None:
        self.deleted.extend(ids)

    def search(self, query_embedding: list[float], top_k: int) -> list[dict]:
        return []


def _patch_sessions(monkeypatch, engine) -> None:
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    monkeypatch.setattr("app.ingestion.pipeline.SessionLocal", TestSession)
    monkeypatch.setattr("app.ingestion.pipeline.init_db", lambda: None)
    monkeypatch.setattr("app.ingestion.pipeline.invalidate_bm25_cache", lambda: None)


def _memory_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )

    @event.listens_for(engine, "connect")
    def _fk(dbapi_connection, connection_record) -> None:  # noqa: ARG001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    return engine


def test_ingest_path_upserts_document_and_vectors(tmp_path: Path, monkeypatch) -> None:
    engine = _memory_engine()
    _patch_sessions(monkeypatch, engine)
    store = RecordingVectorStore()
    pipeline = IngestionPipeline(embedding_model=HashEmbeddingModel(), vector_store=store)
    source = tmp_path / "quy-che.md"
    source.write_text("# Học phí\nSinh viên đóng học phí theo quy định.", encoding="utf-8")

    first = pipeline.ingest_path(source)
    second = pipeline.ingest_path(source)

    assert first["title"] == "quy-che"
    assert first["chunk_count"] >= 1
    assert second["id"] == first["id"]
    assert store.deleted
    with sessionmaker(bind=engine)() as session:
        assert session.get(Document, first["id"]) is not None


def test_delete_ingested_document_removes_db_file_and_vectors(tmp_path: Path, monkeypatch) -> None:
    engine = _memory_engine()
    _patch_sessions(monkeypatch, engine)
    monkeypatch.setattr("app.core.config.settings.documents_path", tmp_path)
    monkeypatch.setattr("app.ingestion.uploads.settings.documents_path", tmp_path)
    monkeypatch.setattr("app.ingestion.uploads.PROJECT_ROOT", tmp_path)
    store = RecordingVectorStore()
    pipeline = IngestionPipeline(embedding_model=HashEmbeddingModel(), vector_store=store)
    source = tmp_path / "faq.md"
    source.write_text("Câu hỏi thường gặp về học phí.", encoding="utf-8")

    item = pipeline.ingest_path(source)
    result = pipeline.delete_ingested_document(item["id"])

    assert result == {"id": item["id"], "deleted": True}
    assert not source.exists()
    assert store.deleted
    with sessionmaker(bind=engine)() as session:
        assert session.get(Document, item["id"]) is None


@pytest.mark.parametrize(
    ("sync_source_path", "explicit_id"),
    [(False, True), (True, True), (True, False)],
)
def test_reparse_moved_document_preserves_identity(
    tmp_path: Path, monkeypatch, sync_source_path: bool, explicit_id: bool
) -> None:
    engine = _memory_engine()
    _patch_sessions(monkeypatch, engine)
    store = RecordingVectorStore()
    pipeline = IngestionPipeline(embedding_model=HashEmbeddingModel(), vector_store=store)
    source = tmp_path / "quy-che.md"
    source.write_text("# Học phí\nNội dung cũ.", encoding="utf-8")
    first = pipeline.ingest_path(source)
    old_vector_ids = list(store.added)
    with sessionmaker(bind=engine)() as session:
        created_at = session.get(Document, first["id"]).created_at

    moved = tmp_path / "raw" / source.name
    moved.parent.mkdir()
    source.rename(moved)
    moved.write_text("# Học phí\nNội dung mới sau khi chuyển thư mục.", encoding="utf-8")
    if sync_source_path:
        # GET document detail may repair source_path before the user reparses.
        with sessionmaker(bind=engine)() as session:
            session.get(Document, first["id"]).source_path = moved.as_posix()
            session.commit()

    store.added.clear()
    store.payloads.clear()
    kwargs = {"document_id": first["id"]} if explicit_id else {}
    result = pipeline.ingest_path(moved, **kwargs)

    assert result["id"] == first["id"]
    assert result["source_path"] == moved.as_posix()
    assert set(store.deleted) == set(old_vector_ids)
    assert set(store.added).isdisjoint(old_vector_ids)
    with sessionmaker(bind=engine)() as session:
        documents = session.scalars(select(Document)).all()
        assert len(documents) == 1
        assert documents[0].id == first["id"]
        assert documents[0].created_at == created_at
        assert documents[0].document_metadata["source"] == moved.as_posix()
        chunks = session.scalars(select(Chunk)).all()
        assert len(chunks) == result["chunk_count"] > 0
        assert {chunk.vector_id for chunk in chunks} == set(store.added)
        assert all(chunk.document_id == first["id"] for chunk in chunks)
        assert all("Nội dung mới" in chunk.text for chunk in chunks)
        assert all(chunk.chunk_metadata["document_id"] == first["id"] for chunk in chunks)
        assert all(chunk.chunk_metadata["source"] == moved.as_posix() for chunk in chunks)
    assert all(item["metadata"]["document_id"] == first["id"] for item in store.payloads)
