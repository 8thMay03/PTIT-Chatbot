from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base, Chunk, Document
from app.core.config import settings
from app.embeddings.models import HashEmbeddingModel
from app.ingestion import uploads
import app.parsers as parsers
from app.ingestion.uploads import read_preview
from app.parsers import DocumentParseError, build_registry, docling, llamaparse
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


@pytest.fixture
def upload_pipeline(tmp_path: Path, monkeypatch):
    engine = _memory_engine()
    _patch_sessions(monkeypatch, engine)
    monkeypatch.setattr(settings, "documents_path", tmp_path / "data")
    monkeypatch.setattr(settings, "converted_documents_path", tmp_path / "cache")
    parsed_paths = []

    def convert(path):
        parsed_paths.append(path)
        return "# Policy\n\n" + path.read_bytes().decode("utf-8", errors="replace")

    monkeypatch.setattr(docling, "convert_with_docling", convert)
    store = RecordingVectorStore()
    pipeline = IngestionPipeline(embedding_model=HashEmbeddingModel(), vector_store=store)
    return pipeline, engine, store, parsed_paths


def _stored_records(engine):
    with sessionmaker(bind=engine)() as session:
        return (
            session.execute(
                select(Document.id, Document.source_path, Document.content_hash, Document.document_metadata)
                .order_by(Document.id)
            ).all(),
            session.execute(
                select(Chunk.id, Chunk.document_id, Chunk.text, Chunk.chunk_metadata).order_by(Chunk.id)
            ).all(),
        )


@pytest.mark.parametrize("replace_existing", [False, True])
@pytest.mark.parametrize("failure", ["conversion", "embedding", "flush", "publish", "commit"])
def test_failed_upload_preserves_source_and_index(upload_pipeline, monkeypatch, replace_existing, failure):
    pipeline, engine, store, parsed_paths = upload_pipeline
    original = b"%PDF original source"
    if replace_existing:
        pipeline.ingest_upload("policy.pdf", original)
    source = settings.documents_path / "policy.pdf"
    before = _stored_records(engine)
    old_vectors = list(store.added)

    def fail(*args, **kwargs):
        if failure == "conversion":
            parsed_paths.append(args[0])
            raise DocumentParseError("injected conversion failure")
        raise RuntimeError("injected failure")

    if failure == "conversion":
        monkeypatch.setattr(docling, "convert_with_docling", fail)
    elif failure == "embedding":
        monkeypatch.setattr(pipeline.embedding_model, "embed", fail)
    elif failure == "publish":
        monkeypatch.setattr(uploads, "copy2", fail)
    else:
        class FailingSession(Session):
            def flush(self, *args, **kwargs):
                super().flush(*args, **kwargs)
                if failure == "flush":
                    fail()

            def commit(self):
                fail()

        monkeypatch.setattr("app.ingestion.pipeline.SessionLocal", sessionmaker(bind=engine, class_=FailingSession))

    with pytest.raises(RuntimeError, match="injected"):
        pipeline.ingest_upload("policy.pdf", b"%PDF broken replacement")

    assert source.exists() is replace_existing
    if replace_existing:
        assert source.read_bytes() == original
    assert _stored_records(engine) == before
    assert store.added == old_vectors
    assert store.deleted == []
    assert store.reset_calls == 0
    if settings.documents_path.exists():
        assert list(settings.documents_path.iterdir()) == ([source] if replace_existing else [])
    assert all(not path.exists() for path in parsed_paths if path != source)


@pytest.mark.parametrize(("filename", "signature"), [("policy.pdf", b"%PDF"), ("policy.docx", b"PK\x03\x04")])
def test_upload_replacement_publishes_final_source_and_metadata(upload_pipeline, filename, signature):
    pipeline, engine, store, parsed_paths = upload_pipeline
    source = settings.documents_path / filename
    first = pipeline.ingest_upload(filename, signature + b" original")
    replacement = signature + b" updated content with a different size"

    second = pipeline.ingest_upload(filename, replacement)

    assert second["id"] == first["id"]
    assert source.read_bytes() == replacement
    assert second["size_bytes"] == len(replacement)
    assert second["source_path"] == source.as_posix()
    assert second["file_name"] == filename
    assert list(settings.documents_path.iterdir()) == [source]
    assert len(parsed_paths) == 2
    assert all(not path.exists() for path in parsed_paths)
    with sessionmaker(bind=engine)() as session:
        document = session.get(Document, first["id"])
        assert document.document_metadata["size_bytes"] == len(replacement)
        assert document.document_metadata["source"] == source.as_posix()
        chunks = session.scalars(select(Chunk)).all()
        assert chunks and all("updated content" in chunk.text for chunk in chunks)
        assert all(chunk.chunk_metadata["source"] == source.as_posix() for chunk in chunks)
    assert store.deleted
    assert all(item["metadata"]["source"] == source.as_posix() for item in store.payloads)


def test_rebuild_parse_failure_preserves_entire_index(upload_pipeline, monkeypatch):
    pipeline, engine, store, _parsed_paths = upload_pipeline
    pipeline.ingest_upload("broken.pdf", b"%PDF previously valid")
    pipeline.ingest_upload("ok.md", b"# Original\nOld text")
    before = _stored_records(engine)
    old_vectors = list(store.added)
    (settings.documents_path / "broken.pdf").write_bytes(b"%PDF now broken")
    (settings.documents_path / "ok.md").write_text("# Changed\nNew text", encoding="utf-8")

    def fail(path):
        raise DocumentParseError("conversion unavailable")

    monkeypatch.setattr(docling, "convert_with_docling", fail)
    embedding_calls = []
    monkeypatch.setattr(pipeline.embedding_model, "embed", lambda texts: embedding_calls.append(texts) or [])

    with pytest.raises(DocumentParseError, match="broken.pdf"):
        pipeline.ingest_documents()

    assert _stored_records(engine) == before
    assert store.added == old_vectors
    assert store.deleted == []
    assert store.reset_calls == 0
    assert embedding_calls == []


def test_rebuild_valid_documents_replaces_index(upload_pipeline):
    pipeline, engine, store, _parsed_paths = upload_pipeline
    pipeline.ingest_upload("policy.pdf", b"%PDF policy")
    pipeline.ingest_upload("ok.md", b"# Original\nOld text")
    (settings.documents_path / "ok.md").write_text("# Changed\nNew text", encoding="utf-8")

    result = pipeline.ingest_documents()

    assert result["documents"] == 2
    assert result["chunks"] > 0
    assert store.reset_calls == 1
    with sessionmaker(bind=engine)() as session:
        assert len(session.scalars(select(Document)).all()) == 2
        assert any("New text" in chunk.text for chunk in session.scalars(select(Chunk)).all())


def test_upload_parses_with_selected_parser_and_stores_it(upload_pipeline, monkeypatch):
    pipeline, engine, _store, docling_paths = upload_pipeline
    monkeypatch.setattr(settings, "llamaparse_enabled", True)
    monkeypatch.setattr(settings, "llama_cloud_api_key", "llx-test-key")
    monkeypatch.setattr(parsers, "registry", build_registry())
    monkeypatch.setattr(llamaparse, "convert_with_llamaparse", lambda path: "# LlamaParse\n\nNội dung từ LlamaParse")

    pipeline.ingest_upload("chosen.pdf", b"%PDF chosen", parser_name="llamaparse")

    with sessionmaker(bind=engine)() as session:
        document = session.scalars(select(Document)).one()
        chunks = session.scalars(select(Chunk)).all()
    assert document.document_metadata["parser"] == "llamaparse"
    assert any("Nội dung từ LlamaParse" in chunk.text for chunk in chunks)
    assert docling_paths == []
    with pytest.raises(DocumentParseError, match="không hỗ trợ"):
        pipeline.ingest_upload("notes.md", b"# Notes", parser_name="llamaparse")


def test_parser_choice_is_stored_and_kept_by_preview_and_full_reload(upload_pipeline, monkeypatch):
    pipeline, engine, _store, docling_paths = upload_pipeline
    monkeypatch.setattr(settings, "llamaparse_enabled", True)
    monkeypatch.setattr(settings, "llama_cloud_api_key", "llx-test-key")
    monkeypatch.setattr(parsers, "registry", build_registry())
    remote_calls = []

    def convert(path):
        remote_calls.append(path.name)
        return "# LlamaParse\n\nNội dung từ LlamaParse"

    monkeypatch.setattr(llamaparse, "convert_with_llamaparse", convert)
    chosen = pipeline.ingest_upload("chosen.pdf", b"%PDF chosen")
    pipeline.ingest_upload("other.pdf", b"%PDF other")
    chosen_path = settings.documents_path / "chosen.pdf"

    pipeline.ingest_path(chosen_path, document_id=chosen["id"], parser_name="llamaparse")

    def stored_parsers():
        with sessionmaker(bind=engine)() as session:
            rows = session.execute(select(Document.source_path, Document.document_metadata)).all()
        return {Path(source).name: metadata["parser"] for source, metadata in rows}

    assert stored_parsers() == {"chosen.pdf": "llamaparse", "other.pdf": "docling"}
    # tmp_path lies outside the project root that resolve_source_path accepts.
    monkeypatch.setattr(uploads, "resolve_source_path", lambda source_path: chosen_path)
    assert "Nội dung từ LlamaParse" in read_preview(chosen["source_path"], parser_name="llamaparse")
    assert "Nội dung từ LlamaParse" not in read_preview(chosen["source_path"])

    pipeline.ingest_documents()

    assert stored_parsers() == {"chosen.pdf": "llamaparse", "other.pdf": "docling"}
    with sessionmaker(bind=engine)() as session:
        texts = {
            Path(chunk.chunk_metadata["source"]).name: chunk.text for chunk in session.scalars(select(Chunk)).all()
        }
    assert "Nội dung từ LlamaParse" in texts["chosen.pdf"]
    assert "Nội dung từ LlamaParse" not in texts["other.pdf"]
    # Reload and preview read the cache: one remote parse, no re-conversion.
    assert remote_calls == ["chosen.pdf"]
    assert [path.name for path in docling_paths] == ["chosen.pdf", "other.pdf"]
