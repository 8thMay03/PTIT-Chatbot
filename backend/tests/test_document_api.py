from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api import routes
from app.ingestion.uploads import DocumentUploadError
from app.main import app


client = TestClient(app)


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
    monkeypatch.setattr(routes.ingestion_pipeline, "delete_ingested_document", lambda document_id: None)

    response = client.delete("/api/documents/missing")

    assert response.status_code == 404
