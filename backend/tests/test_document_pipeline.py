import shutil
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker, undefer
from sqlalchemy.pool import StaticPool

import app.parsers as parsers
from app.core.config import settings
from app.db.models import Base, Chunk, Document
from app.embeddings.models import HashEmbeddingModel
from app.ingestion import uploads
from app.ingestion.pipeline import DocumentStateError, IngestionPipeline
from app.ingestion.uploads import read_preview
from app.parsers import DocumentParseError, build_registry, docling, llamaparse


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


def _parse_and_chunk(pipeline: IngestionPipeline, path: Path, **kwargs) -> dict:
    parsed = pipeline.parse_path(path, **kwargs)
    return pipeline.chunk_document(parsed["id"])


def _upload_and_chunk(pipeline: IngestionPipeline, filename: str, content: bytes, **kwargs) -> dict:
    parsed = pipeline.parse_upload(filename, content, **kwargs)
    return pipeline.chunk_document(parsed["id"])


def test_parse_then_chunk_upserts_document_and_vectors(tmp_path: Path, monkeypatch) -> None:
    engine = _memory_engine()
    _patch_sessions(monkeypatch, engine)
    store = RecordingVectorStore()
    pipeline = IngestionPipeline(embedding_model=HashEmbeddingModel(), vector_store=store)
    source = tmp_path / "quy-che.md"
    source.write_text("# Học phí\nSinh viên đóng học phí theo quy định.", encoding="utf-8")

    first = _parse_and_chunk(pipeline, source)
    second = _parse_and_chunk(pipeline, source)

    assert first["title"] == "quy-che"
    assert first["status"] == "active"
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

    item = _parse_and_chunk(pipeline, source)
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
    first = _parse_and_chunk(pipeline, source)
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
    result = _parse_and_chunk(pipeline, moved, **kwargs)

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
                select(
                    Document.id,
                    Document.source_path,
                    Document.content_hash,
                    Document.status,
                    Document.parsed_text,
                    Document.document_metadata,
                ).order_by(Document.id)
            ).all(),
            session.execute(
                select(Chunk.id, Chunk.document_id, Chunk.text, Chunk.chunk_metadata).order_by(Chunk.id)
            ).all(),
        )


@pytest.mark.parametrize("replace_existing", [False, True])
@pytest.mark.parametrize("failure", ["conversion", "flush", "publish", "commit"])
def test_failed_upload_preserves_source_and_index(upload_pipeline, monkeypatch, replace_existing, failure):
    pipeline, engine, store, parsed_paths = upload_pipeline
    original = b"%PDF original source"
    if replace_existing:
        _upload_and_chunk(pipeline, "policy.pdf", original)
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
        pipeline.parse_upload("policy.pdf", b"%PDF broken replacement")

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
    first = _upload_and_chunk(pipeline, filename, signature + b" original")
    replacement = signature + b" updated content with a different size"

    second = pipeline.parse_upload(filename, replacement)
    assert second["status"] == "parsed"
    # The previous chunks keep serving until the replacement is chunked.
    assert second["chunk_count"] == first["chunk_count"]
    assert store.deleted == []
    second = pipeline.chunk_document(second["id"])

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
    _upload_and_chunk(pipeline, "broken.pdf", b"%PDF previously valid")
    _upload_and_chunk(pipeline, "ok.md", b"# Original\nOld text")
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
    pipeline.parse_upload("policy.pdf", b"%PDF policy")
    pipeline.parse_upload("ok.md", b"# Original\nOld text")
    (settings.documents_path / "ok.md").write_text("# Changed\nNew text", encoding="utf-8")

    result = pipeline.ingest_documents()

    assert result["documents"] == 2
    assert result["chunks"] > 0
    assert store.reset_calls == 1
    with sessionmaker(bind=engine)() as session:
        documents = session.scalars(select(Document)).all()
        assert len(documents) == 2
        assert {document.status for document in documents} == {"active"}
        assert all(document.parsed_text and document.parsed_at for document in documents)
        assert any("New text" in chunk.text for chunk in session.scalars(select(Chunk)).all())


def test_upload_parses_with_selected_parser_and_stores_it(upload_pipeline, monkeypatch):
    pipeline, engine, _store, docling_paths = upload_pipeline
    monkeypatch.setattr(settings, "llamaparse_enabled", True)
    monkeypatch.setattr(settings, "llama_cloud_api_key", "llx-test-key")
    monkeypatch.setattr(parsers, "registry", build_registry())
    monkeypatch.setattr(llamaparse, "convert_with_llamaparse", lambda path: "# LlamaParse\n\nNội dung từ LlamaParse")

    pipeline.parse_upload("chosen.pdf", b"%PDF chosen", parser_name="llamaparse")

    with sessionmaker(bind=engine)() as session:
        document = session.scalars(select(Document).options(undefer(Document.parsed_text))).one()
    assert document.document_metadata["parser"] == "llamaparse"
    assert "Nội dung từ LlamaParse" in document.parsed_text
    assert docling_paths == []
    with pytest.raises(DocumentParseError, match="không hỗ trợ"):
        pipeline.parse_upload("notes.md", b"# Notes", parser_name="llamaparse")


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
    chosen = pipeline.parse_upload("chosen.pdf", b"%PDF chosen")
    pipeline.parse_upload("other.pdf", b"%PDF other")
    chosen_path = settings.documents_path / "chosen.pdf"

    pipeline.parse_path(chosen_path, document_id=chosen["id"], parser_name="llamaparse")

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


def _fail_embedding(texts):
    raise AssertionError("the parse step must not embed")


def _document_row(engine, document_id: str) -> Document:
    with sessionmaker(bind=engine, expire_on_commit=False)() as session:
        return session.get(Document, document_id, options=[undefer(Document.parsed_text)])


def _chunk_texts(engine, document_id: str) -> list[str]:
    with sessionmaker(bind=engine)() as session:
        return list(
            session.scalars(select(Chunk.text).where(Chunk.document_id == document_id).order_by(Chunk.chunk_index))
        )


def test_upload_only_parses_and_waits_for_chunking(upload_pipeline, monkeypatch):
    pipeline, engine, store, _parsed_paths = upload_pipeline
    monkeypatch.setattr(pipeline.embedding_model, "embed", _fail_embedding)

    item = pipeline.parse_upload("policy.md", "# Học phí\nNội dung chờ kiểm tra".encode())

    assert item["status"] == "parsed"
    assert item["chunk_count"] == 0
    assert item["markdown_edited"] is False
    assert item["parsed_at"] is not None
    assert store.added == []
    document = _document_row(engine, item["id"])
    assert "Nội dung chờ kiểm tra" in document.parsed_text
    assert document.parsed_at is not None
    assert (settings.documents_path / "policy.md").is_file()


def test_parse_staged_upload_publishes_source(upload_pipeline, tmp_path: Path):
    pipeline, engine, _store, _parsed_paths = upload_pipeline
    staged = tmp_path / "staged-policy.md"
    staged.write_text("# Staged\nNội dung đã stage", encoding="utf-8")

    item = pipeline.parse_staged_upload(staged, parser_name="text")

    assert item["status"] == "parsed"
    assert item["file_name"] == "staged-policy.md"
    assert (settings.documents_path / "staged-policy.md").is_file()
    assert "Nội dung đã stage" in _document_row(engine, item["id"]).parsed_text


def test_parse_path_rejects_explicit_missing_document(upload_pipeline, tmp_path: Path):
    pipeline, _engine, _store, _parsed_paths = upload_pipeline
    source = tmp_path / "deleted.md"
    source.write_text("# Đã xóa\nNội dung", encoding="utf-8")

    with pytest.raises(DocumentStateError, match="đã bị xóa"):
        pipeline.parse_path(source, document_id="deleted-document")


def test_reparse_with_same_text_keeps_document_active(upload_pipeline, monkeypatch):
    pipeline, engine, store, _parsed_paths = upload_pipeline
    item = _upload_and_chunk(pipeline, "policy.pdf", b"%PDF stable text")
    monkeypatch.setattr(pipeline.embedding_model, "embed", _fail_embedding)

    reparsed = pipeline.parse_path(settings.documents_path / "policy.pdf", document_id=item["id"])

    assert reparsed["status"] == "active"
    assert reparsed["chunk_count"] == item["chunk_count"]


def test_chunk_document_reads_stored_markdown_without_parsing(upload_pipeline, monkeypatch):
    pipeline, engine, store, _parsed_paths = upload_pipeline
    item = pipeline.parse_upload("policy.pdf", b"%PDF stored parser output")
    # Chunking must not need the source, the parser cache or a parser at all.
    (settings.documents_path / "policy.pdf").unlink()
    shutil.rmtree(settings.converted_documents_path)

    def fail(*args, **kwargs):
        raise AssertionError("the chunk step must not parse")

    monkeypatch.setattr(docling, "convert_with_docling", fail)
    monkeypatch.setattr("app.ingestion.pipeline.read_document_text", fail)

    result = pipeline.chunk_document(item["id"])

    assert result["status"] == "active"
    assert result["chunk_count"] > 0
    texts = _chunk_texts(engine, item["id"])
    assert len(texts) == result["chunk_count"]
    assert any("stored parser output" in text for text in texts)
    assert len(store.added) == result["chunk_count"]


def test_chunk_document_requires_stored_markdown(upload_pipeline):
    pipeline, engine, _store, _parsed_paths = upload_pipeline
    with sessionmaker(bind=engine)() as session:
        # Indexed before parse results were stored.
        session.add(Document(id="legacy", source_path="data/legacy.md", content_hash="h", status="active"))
        session.commit()

    assert pipeline.chunk_document("missing") is None
    assert pipeline.save_markdown("missing", "# Sửa") is None
    with pytest.raises(DocumentStateError, match="chưa có bản parse"):
        pipeline.chunk_document("legacy")
    with pytest.raises(DocumentStateError, match="chưa có bản parse"):
        pipeline.save_markdown("legacy", "# Sửa")


def test_chunk_document_rejects_markdown_changed_while_embedding(upload_pipeline, monkeypatch):
    pipeline, engine, _store, _parsed_paths = upload_pipeline
    item = _upload_and_chunk(pipeline, "policy.md", "# Học phí\nBản đầu".encode())
    pipeline.save_markdown(item["id"], "# Học phí\nBản thứ hai")
    chunks_before = _chunk_texts(engine, item["id"])
    embed = pipeline.embedding_model.embed

    def embed_while_editing(texts):
        pipeline.save_markdown(item["id"], "# Học phí\nSửa trong lúc chia đoạn")
        return embed(texts)

    monkeypatch.setattr(pipeline.embedding_model, "embed", embed_while_editing)

    with pytest.raises(DocumentStateError, match="trong lúc chia đoạn"):
        pipeline.chunk_document(item["id"])

    assert _chunk_texts(engine, item["id"]) == chunks_before
    document = _document_row(engine, item["id"])
    assert document.status == "parsed"
    assert "Sửa trong lúc chia đoạn" in document.parsed_text


def test_save_markdown_marks_edit_and_chunk_step_uses_it(upload_pipeline, monkeypatch):
    pipeline, engine, _store, _parsed_paths = upload_pipeline
    item = _upload_and_chunk(pipeline, "policy.pdf", b"%PDF parser output")
    document = _document_row(engine, item["id"])

    with pytest.raises(DocumentStateError, match="đã thay đổi"):
        pipeline.save_markdown(item["id"], "# Sửa", base_hash="stale-hash")

    embed = pipeline.embedding_model.embed
    monkeypatch.setattr(pipeline.embedding_model, "embed", _fail_embedding)
    unchanged = pipeline.save_markdown(item["id"], document.parsed_text, base_hash=document.content_hash)
    assert unchanged["status"] == "active"
    assert unchanged["markdown_edited"] is False

    edited = pipeline.save_markdown(
        item["id"], "# Chính sách\n\nNội dung sửa tay", base_hash=document.content_hash
    )
    assert edited["status"] == "parsed"
    assert edited["markdown_edited"] is True
    assert edited["text"] == "# Chính sách\n\nNội dung sửa tay"
    assert edited["content_hash"] == _document_row(engine, item["id"]).content_hash != document.content_hash
    assert len(_chunk_texts(engine, item["id"])) == item["chunk_count"]

    monkeypatch.setattr(pipeline.embedding_model, "embed", embed)
    chunked = pipeline.chunk_document(item["id"])
    assert chunked["status"] == "active"
    assert chunked["markdown_edited"] is True
    assert all("sửa tay" in text for text in _chunk_texts(engine, item["id"]))


def test_bulk_parse_keeps_manual_edits_but_single_reparse_replaces_them(upload_pipeline):
    pipeline, engine, _store, _parsed_paths = upload_pipeline
    item = _upload_and_chunk(pipeline, "policy.pdf", b"%PDF parser output")
    pipeline.save_markdown(item["id"], "# Chính sách\n\nBản sửa tay")
    chunks_before = _chunk_texts(engine, item["id"])
    (settings.documents_path / "fresh.md").write_text("# Mới\nTài liệu mới thêm", encoding="utf-8")

    assert pipeline.parse_documents() == {"documents": 2}

    document = _document_row(engine, item["id"])
    assert document.parsed_text == "# Chính sách\n\nBản sửa tay"
    assert document.document_metadata["markdown_edited"] is True
    assert _chunk_texts(engine, item["id"]) == chunks_before
    with sessionmaker(bind=engine)() as session:
        fresh = session.scalars(select(Document).where(Document.source_path.like("%fresh.md"))).one()
        assert fresh.status == "parsed"

    pipeline.ingest_documents()

    document = _document_row(engine, item["id"])
    assert document.status == "active"
    assert document.parsed_text == "# Chính sách\n\nBản sửa tay"
    assert document.document_metadata["markdown_edited"] is True
    assert all("Bản sửa tay" in text for text in _chunk_texts(engine, item["id"]))

    reparsed = pipeline.parse_path(settings.documents_path / "policy.pdf", document_id=item["id"])

    assert reparsed["markdown_edited"] is False
    assert reparsed["status"] == "parsed"
    assert "parser output" in _document_row(engine, item["id"]).parsed_text


def test_chunk_documents_rechunks_from_stored_markdown(upload_pipeline, monkeypatch):
    pipeline, engine, store, _parsed_paths = upload_pipeline
    body = "\n\n".join(f"Đoạn {index}: " + "nội dung quy chế học vụ " * 6 for index in range(8))
    first = _upload_and_chunk(pipeline, "a.md", f"# Quy chế\n\n{body}".encode())
    second = pipeline.parse_upload("b.md", "# B\nChưa chia đoạn".encode())
    with sessionmaker(bind=engine)() as session:
        session.add(Document(id="legacy", source_path="data/legacy.md", content_hash="h", status="active"))
        session.commit()
    old_vectors = list(store.added)
    (settings.documents_path / "a.md").unlink()
    monkeypatch.setattr(settings, "parent_child_chunking_enabled", False)
    monkeypatch.setattr(settings, "chunk_size", 120)
    monkeypatch.setattr(settings, "chunk_overlap", 0)

    result = pipeline.chunk_documents()

    assert result["documents"] == 2
    assert result["skipped"] == 1
    assert result["chunks"] == len(_chunk_texts(engine, first["id"])) + len(_chunk_texts(engine, second["id"]))
    assert len(_chunk_texts(engine, first["id"])) > first["chunk_count"]
    assert _document_row(engine, first["id"]).status == "active"
    assert _document_row(engine, second["id"]).status == "active"
    assert _document_row(engine, "legacy").status == "active"
    assert set(store.deleted) == set(old_vectors)
    assert len(store.added) == len(old_vectors) + result["chunks"]
