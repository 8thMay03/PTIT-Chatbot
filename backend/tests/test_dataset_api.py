from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_dataset_crud_and_guards(login_admin, api_db, monkeypatch):
    login_admin(client)
    try:
        # List có default.
        response = client.get("/api/datasets")
        assert response.status_code == 200
        ids = [d["id"] for d in response.json()["datasets"]]
        assert "default" in ids
        default = next(d for d in response.json()["datasets"] if d["id"] == "default")
        assert default["is_default"] is True

        # Tạo.
        response = client.post("/api/datasets", json={"name": "Sổ tay", "description": "K2024"})
        assert response.status_code == 201, response.text
        ds_id = response.json()["id"]
        assert response.json()["document_count"] == 0

        # Trùng tên (không phân biệt hoa/thường) → 409.
        assert client.post("/api/datasets", json={"name": "sổ TAY"}).status_code == 409
        # Tên quá dài / rỗng → 422.
        assert client.post("/api/datasets", json={"name": "   "}).status_code == 422
        assert client.post("/api/datasets", json={"name": "x" * 101}).status_code == 422

        # Xem + sửa.
        assert client.get(f"/api/datasets/{ds_id}").status_code == 200
        assert client.get("/api/datasets/missing").status_code == 404
        response = client.patch(f"/api/datasets/{ds_id}", json={"name": "Quy chế", "enabled": False})
        assert response.status_code == 200
        assert response.json()["name"] == "Quy chế"
        assert response.json()["enabled"] is False
        assert client.patch(f"/api/datasets/{ds_id}", json={"name": "Mặc định"}).status_code == 409
        assert client.patch("/api/datasets/missing", json={"name": "X"}).status_code == 404

        # Không xóa được default → 409; dataset không tồn tại → 404.
        assert client.delete("/api/datasets/default").status_code == 409
        assert client.delete("/api/datasets/missing").status_code == 404
        # Xóa dataset rỗng: pipeline dùng SessionLocal (DB thật) nên mock để dùng api_db.
        from app.db.repositories import delete_dataset_records

        def fake_delete(dataset_id: str):
            with api_db() as session:
                count, _paths, _vecs = delete_dataset_records(session, dataset_id)
                session.commit()
            return {"id": dataset_id, "deleted": True, "documents": count}

        monkeypatch.setattr("app.api.routes.ingestion_pipeline.delete_dataset", fake_delete)
        response = client.delete(f"/api/datasets/{ds_id}")
        assert response.status_code == 200
        assert response.json()["documents"] == 0
        assert client.get(f"/api/datasets/{ds_id}").status_code == 404
    finally:
        client.cookies.clear()


def test_documents_filter_and_upload_dataset(login_admin, api_db, monkeypatch):
    login_admin(client)
    try:
        ds_id = client.post("/api/datasets", json={"name": "Lọc"}).json()["id"]
        # Seed tài liệu trực tiếp vào test DB (upload chạy job nền bất đồng bộ).
        from app.db.repositories import DocumentRecord, save_parsed_document

        with api_db() as session:
            save_parsed_document(
                session,
                DocumentRecord(
                    id="doc-loc", dataset_id=ds_id, source_path="data/loc.md",
                    title="Lọc", file_type="md", content_hash="h1",
                    metadata={"size_bytes": 5}, parsed_text="# Lọc",
                ),
            )
            save_parsed_document(
                session,
                DocumentRecord(
                    id="doc-def", dataset_id="default", source_path="data/macdinh.md",
                    title="Mặc định", file_type="md", content_hash="h2",
                    metadata={"size_bytes": 5}, parsed_text="# M",
                ),
            )
            session.commit()

        # Tải lên vào dataset chỉ định (mock job nền để kiểm tra dataset_id).
        from app.api import routes as routes_module
        from app.ingestion.jobs import ParseJob
        from datetime import datetime, timezone

        calls = []

        def fake_enqueue(filename, content, **options):
            calls.append((filename, options.get("dataset_id")))
            return ParseJob(
                id="job-1", kind="upload", status="queued", document_id=None,
                file_name=filename, parser_name=options.get("parser_name"),
                dataset_id=options.get("dataset_id"),
                created_at=datetime.now(timezone.utc),
            )

        monkeypatch.setattr(routes_module.parse_jobs, "enqueue_upload", fake_enqueue)
        response = client.post(
            "/api/documents",
            files={"file": ("loc.md", "# Lọc\n".encode(), "text/markdown")},
            data={"dataset_id": ds_id},
        )
        assert response.status_code == 202, response.text
        assert response.json()["dataset_id"] == ds_id
        response = client.post(
            "/api/documents", files={"file": ("macdinh.md", "# M\n".encode(), "text/markdown")}
        )
        assert response.json()["dataset_id"] == "default"
        assert calls[0] == ("loc.md", ds_id)
        # Upload vào dataset không tồn tại → 404.
        response = client.post(
            "/api/documents",
            files={"file": ("x.md", "# X".encode(), "text/markdown")},
            data={"dataset_id": "missing"},
        )
        assert response.status_code == 404
        # Lọc danh sách.
        assert client.get("/api/documents", params={"dataset_id": "missing"}).status_code == 404
        filtered = client.get("/api/documents", params={"dataset_id": ds_id}).json()["documents"]
        assert filtered
        assert all(d["dataset_id"] == ds_id for d in filtered)
        assert any(d["id"] == "doc-loc" for d in filtered)
    finally:
        client.cookies.clear()


def test_move_documents_api(login_admin, api_db):
    login_admin(client)
    try:
        src = client.post("/api/datasets", json={"name": "Nguồn"}).json()["id"]
        dst = client.post("/api/datasets", json={"name": "Đích"}).json()["id"]
        assert client.post("/api/documents/move", json={"document_ids": [], "dataset_id": dst}).status_code == 422
        assert client.post("/api/documents/move", json={"document_ids": ["x"], "dataset_id": "missing"}).status_code == 404
    finally:
        client.cookies.clear()


def test_toggle_dataset_refreshes_shared_bm25_index(login_admin, api_db, monkeypatch):
    from app.db.repositories import (
        ChunkRecord,
        DocumentRecord,
        ensure_default_dataset,
        replace_document_chunks,
        save_parsed_document,
    )
    from app.retrieval import bm25 as bm25_module

    login_admin(client)
    try:
        with api_db() as session:
            ensure_default_dataset(session)
            session.commit()
        ds_id = client.post("/api/datasets", json={"name": "Học bổng"}).json()["id"]
        # BM25 cần ≥3 tài liệu để IDF của từ hiếm > 0.
        docs = [
            (ds_id, "d-hb", "học bổng khuyến khích"),
            ("default", "d-hp", "học phí tín chỉ"),
            ("default", "d-tv", "thư viện giáo trình"),
        ]
        with api_db() as session:
            for dataset_id, doc_id, text in docs:
                stored = save_parsed_document(
                    session,
                    DocumentRecord(
                        id=doc_id, dataset_id=dataset_id, source_path=f"data/{doc_id}.md",
                        title=doc_id, file_type="md", content_hash="h-" + doc_id,
                        metadata={}, parsed_text=text,
                    ),
                )
                replace_document_chunks(
                    session,
                    stored,
                    [ChunkRecord(id=f"{doc_id}::chunk-0", document_id=doc_id, chunk_index=0,
                                 text=text, vector_id=f"{doc_id}::chunk-0", search_text=text, metadata={})],
                )
            session.commit()
        monkeypatch.setattr(bm25_module, "SessionLocal", api_db)
        bm25_module.invalidate_bm25_cache()
        search = bm25_module.BM25Search()

        def hits():
            return {r["document_id"] for r in search.search("học bổng", top_k=5)}

        assert "d-hb" in hits()
        assert client.patch(f"/api/datasets/{ds_id}", json={"enabled": False}).status_code == 200
        assert "d-hb" not in hits()
        assert client.patch(f"/api/datasets/{ds_id}", json={"enabled": True}).status_code == 200
        assert "d-hb" in hits()
    finally:
        client.cookies.clear()


def test_dataset_parse_returns_parse_job_items(login_admin, api_db, monkeypatch):
    from datetime import datetime, timezone

    from app.api import routes as routes_module
    from app.ingestion.jobs import ParseJob

    created = datetime.now(timezone.utc)
    job = ParseJob(
        id="job-1", kind="parse", status="queued", document_id="doc-1",
        file_name="a.md", parser_name="text", dataset_id="ds-1", created_at=created,
    )
    monkeypatch.setattr(
        routes_module.ingestion_pipeline,
        "enqueue_dataset_parse",
        lambda dataset_id: {"jobs": [job], "skipped_edited": 1, "skipped_busy": 2},
    )
    login_admin(client)
    try:
        response = client.post("/api/datasets/ds-1/parse")
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["skipped_edited"] == 1
        assert body["skipped_busy"] == 2
        [item] = body["jobs"]
        assert item["id"] == "job-1"
        assert item["kind"] == "parse"
        assert item["file_name"] == "a.md"
        assert item["dataset_id"] == "ds-1"
        assert item["document_id"] == "doc-1"
        assert item["created_at"]
        assert item["progress"] == 0
    finally:
        client.cookies.clear()


def test_dataset_chunk_parse_validation(login_admin, api_db):
    login_admin(client)
    try:
        assert client.post("/api/datasets/missing/chunk").status_code == 404
        assert client.post("/api/datasets/missing/parse").status_code == 404
        response = client.post("/api/retrieval/test", json={"query": "học phí", "dataset_ids": ["default"]})
        assert response.status_code == 200
        assert response.json()["retrieval_debug"].get("dataset_ids") == ["default"]
    finally:
        client.cookies.clear()
