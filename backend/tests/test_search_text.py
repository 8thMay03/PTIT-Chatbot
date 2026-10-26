"""RAG-06: embedding và BM25 dùng trường `search_text` (header ngữ cảnh + text)."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.models import Base, Chunk, Document
from app.embeddings.models import HashEmbeddingModel
from app.ingestion.pipeline import IngestionPipeline
from app.retrieval.bm25 import BM25Search
from app.vectordb.pgvector_store import PgVectorStore


class RecordingEmbeddingModel(HashEmbeddingModel):
    def __init__(self) -> None:
        super().__init__()
        self.embedded: list[str] = []

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.embedded.extend(texts)
        return super().embed(texts)


class NullVectorStore:
    collection_name = "test_documents"

    def reset(self) -> None:
        pass

    def add(self, chunks, embeddings) -> None:
        pass


def _patch_pipeline_sessions(monkeypatch, engine) -> None:
    test_session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    monkeypatch.setattr("app.ingestion.pipeline.SessionLocal", test_session)
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


@pytest.mark.parametrize("embedding_input_field", ["text", "search_text"])
def test_pipeline_embeds_configured_field(
    tmp_path: Path, monkeypatch, embedding_input_field: str
) -> None:
    monkeypatch.setattr(settings, "embedding_input_field", embedding_input_field)
    engine = _memory_engine()
    _patch_pipeline_sessions(monkeypatch, engine)
    embedding_model = RecordingEmbeddingModel()
    pipeline = IngestionPipeline(embedding_model=embedding_model, vector_store=NullVectorStore())
    source = tmp_path / "BHYT huong dan.md"
    source.write_text(
        "# Quy trình đóng bảo hiểm y tế\n\nSinh viên nộp hồ sơ tại phòng một cửa trong tháng đầu khóa học.",
        encoding="utf-8",
    )

    pipeline.chunk_document(pipeline.parse_path(source)["id"])

    assert embedding_model.embedded, "pipeline phải gọi embedding model"
    for embedded in embedding_model.embedded:
        # "BHYT" chỉ nằm trong tên tài liệu: embedding dùng search_text thì
        # vector input phải chứa nó; dùng text thì không.
        assert ("BHYT huong dan" in embedded) == (embedding_input_field == "search_text")
        assert "phòng một cửa" in embedded

    with sessionmaker(bind=engine)() as session:
        chunks = session.scalars(select(Chunk).order_by(Chunk.chunk_index)).all()
        assert chunks
        for chunk in chunks:
            assert chunk.search_text.startswith("BHYT huong dan > Quy trình đóng bảo hiểm y tế\n")
            assert not chunk.text.startswith("BHYT huong dan")
            assert chunk.search_text.endswith(chunk.text)


def test_pipeline_payload_search_text_matches_record(tmp_path: Path, monkeypatch) -> None:
    engine = _memory_engine()
    _patch_pipeline_sessions(monkeypatch, engine)
    pipeline = IngestionPipeline(embedding_model=HashEmbeddingModel(), vector_store=NullVectorStore())
    source = tmp_path / "quy-che.md"
    source.write_text(
        "# Học phí\n\nHọc phí theo tín chỉ được thu đầu mỗi học kỳ.",
        encoding="utf-8",
    )

    pipeline.chunk_document(pipeline.parse_path(source)["id"])

    with sessionmaker(bind=engine)() as session:
        chunks = session.scalars(select(Chunk)).all()
        assert chunks
        for chunk in chunks:
            assert chunk.search_text.startswith("quy-che > Học phí\n")
            assert chunk.search_text.endswith(chunk.text)


def test_bm25_ranks_by_search_text_not_display_text(monkeypatch) -> None:
    search = BM25Search()
    # Term "BHYT" chỉ nằm trong search_text của chunk 1 (và trong text hiển thị
    # của chunk 2 — phải bị bỏ qua khi lập chỉ mục).
    chunks = [
        {
            "chunk_id": "1",
            "text": "Sinh viên nộp hồ sơ tại phòng một cửa trong tháng đầu khóa học.",
            "search_text": "Hướng dẫn BHYT > Quy trình đóng bảo hiểm y tế\nSinh viên nộp hồ sơ tại phòng một cửa trong tháng đầu khóa học.",
            "parent_id": "p1",
            "parent_text": "Hướng dẫn BHYT",
        },
        {
            "chunk_id": "2",
            "text": "BHYT chỉ xuất hiện trong text hiển thị nhưng không có trong search_text.",
            "search_text": "Thông báo khác > Mục khác\nNội dung không liên quan đến bảo hiểm.",
            "parent_id": "p2",
            "parent_text": "Thông báo khác",
        },
        {
            "chunk_id": "3",
            "text": "Lịch thi giữa kỳ.",
            "search_text": "Sổ tay > Lịch thi\nLịch thi giữa kỳ.",
            "parent_id": "p3",
            "parent_text": "Sổ tay",
        },
    ]

    monkeypatch.setattr(search, "_load_chunks", lambda: chunks)

    results = search.search("BHYT", top_k=3)

    assert results
    assert results[0]["chunk_id"] == "1"
    assert all(result["chunk_id"] != "2" for result in results)


def test_bm25_search_text_falls_back_to_text(monkeypatch) -> None:
    search = BM25Search()
    chunks = [
        {"chunk_id": "1", "text": "quy định học phí"},
        {"chunk_id": "2", "text": "thông tin thư viện"},
        {"chunk_id": "3", "text": "lịch học sinh viên"},
    ]
    monkeypatch.setattr(search, "_load_chunks", lambda: chunks)

    assert search.search("học phí", top_k=1)[0]["chunk_id"] == "1"


def test_pgvector_context_exposes_search_text() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    store = PgVectorStore(session_factory=factory)

    with factory() as session:
        session.add(
            Document(
                id="doc-1",
                source_path="data/doc.md",
                title="Doc",
                file_type="md",
                content_hash="h",
                status="active",
            )
        )
        session.add(
            Chunk(
                id="c1",
                document_id="doc-1",
                chunk_index=0,
                text="Nội dung hiển thị.",
                search_text="Doc > Mục một\nNội dung hiển thị.",
                vector_id="v1",
            )
        )
        session.add(
            Chunk(
                id="c2",
                document_id="doc-1",
                chunk_index=1,
                text="Chunk cũ chưa có search_text.",
                search_text="",
                vector_id="v2",
            )
        )
        session.commit()
        store.add([{"id": "c1"}, {"id": "c2"}], [[1.0, 0.0], [0.0, 1.0]])

    results = store.search([1.0, 0.0], top_k=2)
    by_id = {result["chunk_id"]: result for result in results}
    assert by_id["c1"]["search_text"].startswith("Doc > Mục một")
    assert by_id["c2"]["search_text"] == "Chunk cũ chưa có search_text."
