from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api import routes
from app.parsers import DocumentParseError
from app.ingestion.uploads import DocumentUploadError
from app.main import app


client = TestClient(app)


def test_rebuild_maps_conversion_error_to_422(monkeypatch):
    def fail():
        raise DocumentParseError("Không parse được tài liệu broken.pdf: conversion unavailable")

    monkeypatch.setattr(routes.ingestion_pipeline, "ingest_documents", fail)

    response = client.post("/api/ingest")

    assert response.status_code == 422
    assert "broken.pdf" in response.json()["detail"]


def test_list_documents_returns_serialized_items(monkeypatch) -> None:
    document = SimpleNamespace(
        id="doc-1",
        title="Sổ tay",
        source_path="data/so-tay.md",
        file_type="md",
        status="active",
        document_metadata={"size_bytes": 24},
        created_at=None,
        updated_at=None,
    )
    monkeypatch.setattr(routes, "list_documents", lambda session: [(document, 4)])
    monkeypatch.setattr(routes, "resolve_source_path", lambda source_path: None)

    response = client.get("/api/documents")

    assert response.status_code == 200
    payload = response.json()
    assert payload["documents"][0]["id"] == "doc-1"
    assert payload["documents"][0]["file_name"] == "so-tay.md"
    assert payload["documents"][0]["chunk_count"] == 4


def test_upload_document_uses_ingestion_pipeline(monkeypatch) -> None:
    monkeypatch.setattr(
        routes.ingestion_pipeline,
        "ingest_upload",
        lambda filename, content: {
            "id": "doc-1",
            "title": "faq",
            "file_name": "faq.md",
            "source_path": "data/faq.md",
            "file_type": "md",
            "status": "active",
            "chunk_count": 2,
            "size_bytes": len(content),
            "created_at": None,
            "updated_at": None,
        },
    )

    response = client.post(
        "/api/documents",
        files={"file": ("faq.md", b"# FAQ\n", "text/markdown")},
    )

    assert response.status_code == 200
    assert response.json()["file_name"] == "faq.md"
    assert response.json()["chunk_count"] == 2


def test_upload_document_maps_validation_errors(monkeypatch) -> None:
    def fail_upload(filename, content):
        raise DocumentUploadError("Chỉ hỗ trợ tài liệu .md, .txt.")

    monkeypatch.setattr(routes.ingestion_pipeline, "ingest_upload", fail_upload)

    response = client.post(
        "/api/documents",
        files={"file": ("notes.pdf", b"%PDF", "application/pdf")},
    )

    assert response.status_code == 400
    assert "Chỉ hỗ trợ" in response.json()["detail"]


def test_delete_document_returns_404_when_missing(monkeypatch) -> None:
    monkeypatch.setattr(
        routes.ingestion_pipeline, "delete_ingested_document", lambda document_id: None
    )

    response = client.delete("/api/documents/missing")

    assert response.status_code == 404


def test_parse_single_document_returns_404_when_missing(monkeypatch) -> None:
    monkeypatch.setattr(routes, "get_document_with_chunk_count", lambda session, doc_id: None)

    response = client.post("/api/documents/missing/parse")

    assert response.status_code == 404


def test_parse_single_document_passes_existing_identity(monkeypatch, tmp_path) -> None:
    source = tmp_path / "moved.docx"
    source.write_bytes(b"source is parsed by the pipeline")
    document = SimpleNamespace(id="historical-id", source_path="data/raw/moved.docx")
    monkeypatch.setattr(
        routes, "get_document_with_chunk_count", lambda session, doc_id: (document, 4)
    )
    monkeypatch.setattr(routes, "resolve_source_path", lambda source_path: source)
    calls = []

    def ingest_path(path, *, document_id=None):
        calls.append((path, document_id))
        return {
            "id": document_id or "new-path-id",
            "title": "moved",
            "file_name": "moved.docx",
            "source_path": document.source_path,
            "file_type": "docx",
            "status": "active",
            "chunk_count": 3,
            "size_bytes": source.stat().st_size,
            "created_at": None,
            "updated_at": None,
        }

    monkeypatch.setattr(routes.ingestion_pipeline, "ingest_path", ingest_path)

    response = client.post("/api/documents/historical-id/parse")

    assert response.status_code == 200
    assert response.json()["id"] == document.id
    assert calls == [(source, document.id)]


def test_parser_options_and_explicit_selection(monkeypatch, tmp_path) -> None:
    source = tmp_path / "note.md"
    source.write_text("hello", encoding="utf-8")
    document = SimpleNamespace(id="note", source_path=str(source))
    monkeypatch.setattr(routes, "get_document_with_chunk_count", lambda *args: (document, 1))
    monkeypatch.setattr(routes, "resolve_source_path", lambda *args: source)
    response = client.get("/api/documents/note/parsers")
    assert response.status_code == 200
    assert response.json() == {"parsers": [{"name": "text", "is_default": True}]}
    calls = []

    def reject(path, **options):
        calls.append(options)
        raise routes.DocumentParseError("unsupported selection")

    monkeypatch.setattr(routes.ingestion_pipeline, "ingest_path", reject)
    response = client.post("/api/documents/note/parse?parser_name=docling")
    assert response.status_code == 422
    assert calls == [{"document_id": "note", "parser_name": "docling"}]


def test_parser_options_missing_document(monkeypatch) -> None:
    monkeypatch.setattr(routes, "get_document_with_chunk_count", lambda *args: None)
    assert client.get("/api/documents/missing/parsers").status_code == 404


def test_get_document_returns_full_text(monkeypatch, tmp_path) -> None:
    doc_file = tmp_path / "full-doc.md"
    doc_file.write_text("# Full Document Content\nDetailed paragraphs.", encoding="utf-8")

    document = SimpleNamespace(
        id="doc-full",
        title="full-doc",
        source_path="full-doc.md",
        file_type="md",
        status="active",
        document_metadata=None,
        created_at=None,
        updated_at=None,
    )
    monkeypatch.setattr(
        routes, "get_document_with_chunk_count", lambda session, doc_id: (document, 10)
    )
    monkeypatch.setattr(routes, "resolve_source_path", lambda source_path: doc_file)
    monkeypatch.setattr(
        routes, "read_preview", lambda source_path: doc_file.read_text(encoding="utf-8")
    )

    response = client.get("/api/documents/doc-full")

    assert response.status_code == 200
    data = response.json()
    assert data["full_text"] == "# Full Document Content\nDetailed paragraphs."
    assert data["file_name"] == "full-doc.md"


def test_get_document_falls_back_to_chunks_when_source_missing(monkeypatch) -> None:
    document = SimpleNamespace(
        id="doc-chunks",
        title="chunks-doc",
        source_path="data/missing.md",
        file_type="md",
        status="active",
        document_metadata=None,
        created_at=None,
        updated_at=None,
    )
    monkeypatch.setattr(
        routes, "get_document_with_chunk_count", lambda session, doc_id: (document, 3)
    )
    monkeypatch.setattr(routes, "resolve_source_path", lambda source_path: None)
    monkeypatch.setattr(routes, "read_preview", lambda source_path: None)
    monkeypatch.setattr(routes, "get_document_preview_text", lambda session, doc_id: "Chunk 1")
    monkeypatch.setattr(
        routes, "get_document_full_text", lambda session, doc_id: "Chunk 1\n\nChunk 2\n\nChunk 3"
    )

    response = client.get("/api/documents/doc-chunks")

    assert response.status_code == 200
    data = response.json()
    assert data["full_text"] == "Chunk 1\n\nChunk 2\n\nChunk 3"
