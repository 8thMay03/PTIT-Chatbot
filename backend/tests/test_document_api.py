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
        "parse_upload",
        lambda filename, content: {
            "id": "doc-1",
            "title": "faq",
            "file_name": "faq.md",
            "source_path": "data/faq.md",
            "file_type": "md",
            "status": "parsed",
            "chunk_count": 0,
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
    assert response.json()["status"] == "parsed"
    assert response.json()["chunk_count"] == 0


def test_upload_document_maps_validation_errors(monkeypatch) -> None:
    def fail_upload(filename, content):
        raise DocumentUploadError("Chỉ hỗ trợ tài liệu .md, .txt.")

    monkeypatch.setattr(routes.ingestion_pipeline, "parse_upload", fail_upload)

    response = client.post(
        "/api/documents",
        files={"file": ("notes.pdf", b"%PDF", "application/pdf")},
    )

    assert response.status_code == 400
    assert "Chỉ hỗ trợ" in response.json()["detail"]


def test_delete_document_returns_404_when_missing(monkeypatch) -> None:
    monkeypatch.setattr(routes.ingestion_pipeline, "delete_ingested_document", lambda document_id: None)

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
    monkeypatch.setattr(routes, "get_document_with_chunk_count", lambda session, doc_id: (document, 4))
    monkeypatch.setattr(routes, "resolve_source_path", lambda source_path: source)
    calls = []

    def parse_path(path, *, document_id=None):
        calls.append((path, document_id))
        return {
            "id": document_id or "new-path-id",
            "title": "moved",
            "file_name": "moved.docx",
            "source_path": document.source_path,
            "file_type": "docx",
            "status": "parsed",
            "chunk_count": 3,
            "size_bytes": source.stat().st_size,
            "created_at": None,
            "updated_at": None,
        }

    monkeypatch.setattr(routes.ingestion_pipeline, "parse_path", parse_path)

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

    monkeypatch.setattr(routes.ingestion_pipeline, "parse_path", reject)
    response = client.post("/api/documents/note/parse?parser_name=docling")
    assert response.status_code == 422
    assert calls == [{"document_id": "note", "parser_name": "docling"}]


def test_parser_options_by_file_name_before_upload(monkeypatch) -> None:
    from app.parsers.registry import ParserRegistry

    class Stub:
        extensions = frozenset({".pdf"})

        def __init__(self, name: str) -> None:
            self.name = name

    monkeypatch.setattr(routes, "registry", ParserRegistry([Stub("docling"), Stub("llamaparse")]))

    response = client.get("/api/parsers", params={"file_name": "Sổ tay.PDF"})

    assert response.status_code == 200
    assert response.json() == {
        "parsers": [{"name": "docling", "is_default": True}, {"name": "llamaparse", "is_default": False}]
    }
    assert client.get("/api/parsers", params={"file_name": "notes.xyz"}).json() == {"parsers": []}
    assert client.get("/api/parsers").status_code == 422


def test_upload_document_passes_selected_parser(monkeypatch) -> None:
    calls = []

    def reject(filename, content, **options):
        calls.append((filename, options))
        raise DocumentParseError("Parser 'llamaparse' chưa được đăng ký.")

    monkeypatch.setattr(routes.ingestion_pipeline, "parse_upload", reject)

    response = client.post(
        "/api/documents",
        files={"file": ("policy.pdf", b"%PDF", "application/pdf")},
        data={"parser_name": "llamaparse"},
    )

    assert response.status_code == 422
    assert "llamaparse" in response.json()["detail"]
    assert calls == [("policy.pdf", {"parser_name": "llamaparse"})]


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
        parsed_text=None,
        document_metadata=None,
        created_at=None,
        updated_at=None,
    )
    monkeypatch.setattr(routes, "get_document_with_chunk_count", lambda session, doc_id: (document, 10))
    monkeypatch.setattr(routes, "resolve_source_path", lambda source_path: doc_file)
    monkeypatch.setattr(routes, "read_preview", lambda source_path, **_: doc_file.read_text(encoding="utf-8"))

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
        parsed_text=None,
        document_metadata=None,
        created_at=None,
        updated_at=None,
    )
    monkeypatch.setattr(routes, "get_document_with_chunk_count", lambda session, doc_id: (document, 3))
    monkeypatch.setattr(routes, "resolve_source_path", lambda source_path: None)
    monkeypatch.setattr(routes, "read_preview", lambda source_path, **_: None)
    monkeypatch.setattr(routes, "get_document_preview_text", lambda session, doc_id: "Chunk 1")
    monkeypatch.setattr(routes, "get_document_full_text", lambda session, doc_id: "Chunk 1\n\nChunk 2\n\nChunk 3")

    response = client.get("/api/documents/doc-chunks")

    assert response.status_code == 200
    data = response.json()
    assert data["full_text"] == "Chunk 1\n\nChunk 2\n\nChunk 3"



def test_get_document_reads_text_with_stored_parser(monkeypatch, tmp_path) -> None:
    import app.parsers as parsers
    from app.parsers.registry import ParserRegistry

    class Stub:
        extensions = frozenset({".custom"})

        def __init__(self, name: str) -> None:
            self.name = name

        def parse(self, path, *, convert=True):
            return f"# From {self.name}\n"

    monkeypatch.setattr(parsers, "registry", ParserRegistry([Stub("default"), Stub("alternative")]))
    source = tmp_path / "chosen.custom"
    source.write_bytes(b"data")
    document = SimpleNamespace(
        id="doc-chosen",
        title="chosen",
        source_path="chosen.custom",
        file_type="custom",
        status="active",
        parsed_text=None,
        document_metadata={"parser": "alternative"},
        created_at=None,
        updated_at=None,
    )
    preview_calls = []
    monkeypatch.setattr(routes, "get_document_with_chunk_count", lambda session, doc_id: (document, 1))
    monkeypatch.setattr(routes, "resolve_source_path", lambda source_path: source)
    monkeypatch.setattr(
        routes, "read_preview", lambda source_path, **kwargs: preview_calls.append(kwargs) or "preview"
    )

    response = client.get("/api/documents/doc-chosen")

    assert response.status_code == 200
    assert response.json()["full_text"] == "# From alternative\n"
    assert preview_calls == [{"parser_name": "alternative"}]


def _source_file_document(monkeypatch, source) -> None:
    document = SimpleNamespace(id="doc-file", source_path=source.name)
    monkeypatch.setattr(routes, "get_document_with_chunk_count", lambda session, doc_id: (document, 1))
    monkeypatch.setattr(routes, "resolve_source_path", lambda source_path: source)


def test_document_file_downloads_as_attachment_by_default(monkeypatch, tmp_path) -> None:
    source = tmp_path / "policy.pdf"
    source.write_bytes(b"%PDF-1.7 body")
    _source_file_document(monkeypatch, source)

    response = client.get("/api/documents/doc-file/file")

    assert response.status_code == 200
    assert response.content == b"%PDF-1.7 body"
    assert response.headers["content-disposition"].startswith("attachment;")


def test_document_file_inline_for_original_view(monkeypatch, tmp_path) -> None:
    source = tmp_path / "Sổ tay.pdf"
    source.write_bytes(b"%PDF-1.7 body")
    _source_file_document(monkeypatch, source)

    response = client.get("/api/documents/doc-file/file", params={"inline": "true"})

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"].startswith("inline;")
    assert response.headers["x-content-type-options"] == "nosniff"


def test_document_file_inline_text_is_plain_text(monkeypatch, tmp_path) -> None:
    source = tmp_path / "notes.md"
    source.write_text("# <script>alert(1)</script>", encoding="utf-8")
    _source_file_document(monkeypatch, source)

    response = client.get("/api/documents/doc-file/file", params={"inline": "true"})

    assert response.headers["content-type"] == "text/plain; charset=utf-8"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_document_file_missing_source_returns_404(monkeypatch, tmp_path) -> None:
    _source_file_document(monkeypatch, tmp_path / "gone.pdf")

    assert client.get("/api/documents/doc-file/file", params={"inline": "true"}).status_code == 404


def _stored_document(**overrides):
    values = dict(
        id="doc-md",
        title="policy",
        source_path="data/policy.pdf",
        file_type="pdf",
        status="parsed",
        content_hash="hash-1",
        parsed_text="# Chính sách\n\nNội dung đã parse.",
        parsed_at=None,
        document_metadata={"markdown_edited": True},
        created_at=None,
        updated_at=None,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def _document_item(**overrides) -> dict:
    item = {
        "id": "doc-md",
        "title": "policy",
        "file_name": "policy.pdf",
        "source_path": "data/policy.pdf",
        "file_type": "pdf",
        "status": "active",
        "markdown_edited": False,
        "chunk_count": 5,
        "size_bytes": 10,
        "created_at": None,
        "updated_at": None,
    }
    item.update(overrides)
    return item


def test_get_document_prefers_stored_markdown(monkeypatch) -> None:
    document = _stored_document(parsed_text="# Stored\n" + "x" * 3000)
    monkeypatch.setattr(routes, "get_document_with_chunk_count", lambda session, doc_id: (document, 2))
    monkeypatch.setattr(routes, "resolve_source_path", lambda source_path: None)

    def fail(*args, **kwargs):
        raise AssertionError("stored Markdown must not be re-read from the parser cache")

    monkeypatch.setattr(routes, "read_document_text", fail)
    monkeypatch.setattr(routes, "read_preview", fail)

    response = client.get("/api/documents/doc-md")

    assert response.status_code == 200
    data = response.json()
    assert data["full_text"] == document.parsed_text
    assert data["preview"].startswith("# Stored") and data["preview"].endswith("…")
    assert len(data["preview"]) <= routes.PREVIEW_CHAR_LIMIT + 1
    assert data["status"] == "parsed"
    assert data["markdown_edited"] is True


def test_chunk_single_document(monkeypatch) -> None:
    calls = []

    def chunk(document_id):
        calls.append(document_id)
        if document_id == "missing":
            return None
        if document_id == "legacy":
            raise routes.DocumentStateError("Tài liệu chưa có bản parse đã lưu.")
        return _document_item(id=document_id)

    monkeypatch.setattr(routes.ingestion_pipeline, "chunk_document", chunk)

    response = client.post("/api/documents/doc-md/chunk")
    assert response.status_code == 200
    assert response.json()["status"] == "active"
    assert client.post("/api/documents/missing/chunk").status_code == 404
    response = client.post("/api/documents/legacy/chunk")
    assert response.status_code == 409
    assert "chưa có bản parse" in response.json()["detail"]
    assert calls == ["doc-md", "missing", "legacy"]


def test_chunk_all_documents(monkeypatch) -> None:
    monkeypatch.setattr(
        routes.ingestion_pipeline,
        "chunk_documents",
        lambda: {"documents": 3, "chunks": 42, "skipped": 1, "collection": "ptit"},
    )

    response = client.post("/api/ingest/chunk")

    assert response.status_code == 200
    assert response.json() == {"documents": 3, "chunks": 42, "skipped": 1, "collection": "ptit"}

    def conflict():
        raise routes.DocumentStateError("Tài liệu vừa được parse lại trong lúc chia đoạn.")

    monkeypatch.setattr(routes.ingestion_pipeline, "chunk_documents", conflict)
    assert client.post("/api/ingest/chunk").status_code == 409


def test_get_document_markdown(monkeypatch) -> None:
    documents = {"doc-md": _stored_document(), "legacy": _stored_document(id="legacy", parsed_text=None)}
    monkeypatch.setattr(
        routes,
        "get_document_with_chunk_count",
        lambda session, doc_id: (documents[doc_id], 1) if doc_id in documents else None,
    )

    response = client.get("/api/documents/doc-md/markdown")

    assert response.status_code == 200
    assert response.json() == {
        "document_id": "doc-md",
        "text": "# Chính sách\n\nNội dung đã parse.",
        "content_hash": "hash-1",
        "status": "parsed",
        "parsed_at": None,
        "markdown_edited": True,
    }
    assert client.get("/api/documents/missing/markdown").status_code == 404
    assert client.get("/api/documents/legacy/markdown").status_code == 409


def test_update_document_markdown(monkeypatch) -> None:
    calls = []

    def save(document_id, text, *, base_hash=None):
        calls.append((document_id, text, base_hash))
        if document_id == "missing":
            return None
        if base_hash == "stale":
            raise routes.DocumentStateError("Markdown của tài liệu đã thay đổi.")
        return {
            "document_id": document_id,
            "text": text,
            "content_hash": "hash-2",
            "status": "parsed",
            "parsed_at": None,
            "markdown_edited": True,
        }

    monkeypatch.setattr(routes.ingestion_pipeline, "save_markdown", save)

    response = client.put("/api/documents/doc-md/markdown", json={"text": "# Sửa tay", "base_hash": "hash-1"})
    assert response.status_code == 200
    assert response.json()["status"] == "parsed"
    assert response.json()["markdown_edited"] is True
    # The new hash lets the editor detect a conflicting change on its next save.
    assert response.json()["content_hash"] == "hash-2"
    assert client.put("/api/documents/doc-md/markdown", json={"text": "# Sửa", "base_hash": "stale"}).status_code == 409
    assert client.put("/api/documents/missing/markdown", json={"text": "# Sửa"}).status_code == 404
    assert client.put("/api/documents/doc-md/markdown", json={"text": "  \n "}).status_code == 422
    assert calls == [
        ("doc-md", "# Sửa tay", "hash-1"),
        ("doc-md", "# Sửa", "stale"),
        ("missing", "# Sửa", None),
    ]
