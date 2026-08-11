from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base, Document
from app.embeddings.models import HashEmbeddingModel
from app.ingestion.pipeline import IngestionPipeline


class RecordingVectorStore:
    collection_name = "test_documents"

    def __init__(self) -> None:
        self.added: list[str] = []
        self.deleted: list[str] = []
        self.reset_calls = 0

    def reset(self) -> None:
        self.reset_calls += 1
        self.added.clear()

    def add(self, chunks: list[dict], embeddings: list[list[float]]) -> None:
        self.added.extend(item["id"] for item in chunks)

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
