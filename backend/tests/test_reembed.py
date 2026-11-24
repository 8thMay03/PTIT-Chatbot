"""Nhúng lại vector và chữ ký embedding (task 2026-11-24-reembed-documents).

- AC-01: chia đoạn ghi chữ ký mô hình; ``embed_chunks`` chỉ nhúng đoạn cần nhúng (hoặc mọi
  đoạn khi ``include_current``), không đổi đoạn, bỏ qua đoạn đổi nội dung trong lúc chạy.
- AC-02: job ``embed`` chạy nền có tiến độ; lỗi → ``failed``; trùng phạm vi → 409.
- AC-03: tìm kiếm vector bỏ vector của mô hình khác; retriever truyền chữ ký của runtime.
- AC-05: số đoạn/tài liệu cần nhúng ở tài liệu, dataset và ``GET /api/embeddings/status``;
  endpoint nhúng dataset/tài liệu/toàn kho.
- Dữ liệu cũ (chưa có chữ ký) được gán chữ ký mô hình chạy lúc khởi động.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.models import Base, Chunk, Dataset, Document
from app.db.repositories import count_stale_chunks_by_document, embedding_coverage
from app.embeddings import (
    EmbeddingModel,
    EmbeddingRuntime,
    EmbeddingUnavailableError,
    HashEmbeddingModel,
    embedding_runtime,
    embedding_signature,
)
from app.embeddings.runtime import RuntimeEmbeddingModel
from app.ingestion import pipeline as pipeline_module
from app.ingestion.jobs import ParseJob, ParseJobConflict, ParseJobManager
from app.ingestion.pipeline import IngestionPipeline
from app.ingestion.pipeline import adopt_unsigned_vectors as real_adopt_unsigned_vectors
from app.retrieval.retriever import Retriever
from app.vectordb.pgvector_store import PgVectorStore

TEXT = "# Chương 1\n\nĐiều 1. Sinh viên phải đăng ký học phần đúng hạn.\n\n# Chương 2\n\nĐiều 2. Học phí nộp theo kỳ.\n"


class _SignedModel(EmbeddingModel):
    """Giả lập mô hình runtime: vector kèm chữ ký."""

    def __init__(self, signature: str) -> None:
        self.signature = signature
        self.inner = HashEmbeddingModel(dimensions=settings.vector_dim)
        self.calls: list[list[str]] = []

    def embed(self, texts):
        self.calls.append(list(texts))
        return self.inner.embed(texts)

    def current_signature(self) -> str:
        return self.signature

    def embed_with_signature(self, texts, *, query=False):
        return self.embed(texts), self.signature


def _setup(monkeypatch, model: EmbeddingModel):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool, future=True)
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    monkeypatch.setattr(pipeline_module, "SessionLocal", TestSession)
    monkeypatch.setattr(pipeline_module, "init_db", lambda: None)
    monkeypatch.setattr(pipeline_module, "invalidate_bm25_cache", lambda: None)
    now = datetime.now(timezone.utc)
    with TestSession() as session:
        session.add_all([Dataset(id="ds1", name="A"), Dataset(id="ds2", name="B")])
        session.flush()
        for doc_id, dataset_id in (("d1", "ds1"), ("d2", "ds2")):
            session.add(
                Document(
                    id=doc_id,
                    dataset_id=dataset_id,
                    source_path=f"data/datasets/{dataset_id}/{doc_id}.md",
                    title=doc_id,
                    file_type="md",
                    content_hash=f"hash-{doc_id}",
                    status="parsed",
                    parsed_text=TEXT,
                    parsed_at=now,
                )
            )
        session.commit()
    pipe = IngestionPipeline(embedding_model=model, vector_store=PgVectorStore(TestSession))
    return pipe, TestSession


def _signatures(TestSession, document_id: str) -> list[str | None]:
    with TestSession() as session:
        return list(
            session.scalars(
                select(Chunk.embedding_signature).where(Chunk.document_id == document_id).order_by(Chunk.chunk_index)
            )
        )


# ==========================================
# AC-01: chữ ký khi chia đoạn và nhúng lại
# ==========================================
def test_chunking_stores_model_signature(monkeypatch) -> None:
    pipe, TestSession = _setup(monkeypatch, _SignedModel("old:model:1536"))
    pipe.chunk_document("d1")
    signatures = _signatures(TestSession, "d1")
    assert signatures and set(signatures) == {"old:model:1536"}


def test_unsigned_model_leaves_signature_empty(monkeypatch) -> None:
    pipe, TestSession = _setup(monkeypatch, HashEmbeddingModel(dimensions=settings.vector_dim))
    pipe.chunk_document("d1")
    assert set(_signatures(TestSession, "d1")) == {None}


def test_embed_chunks_only_refreshes_stale_chunks_in_scope(monkeypatch) -> None:
    old = _SignedModel("old:model:1536")
    pipe, TestSession = _setup(monkeypatch, old)
    pipe.chunk_documents()
    with TestSession() as session:
        before = {row.id: (row.text, row.search_text) for row in session.scalars(select(Chunk))}
        d1_count = sum(1 for _ in session.scalars(select(Chunk.id).where(Chunk.document_id == "d1")))

    new = _SignedModel("new:model:1536")
    pipe.embedding_model = new
    with TestSession() as session:
        assert embedding_coverage(session, "new:model:1536") == {
            "total_chunks": len(before),
            "stale_chunks": len(before),
            "stale_documents": 2,
        }

    progress: list[tuple[int, str]] = []
    result = pipe.embed_chunks(dataset_id="ds1", on_progress=lambda pct, msg: progress.append((pct, msg)))
    assert result == {"documents": 1, "chunks": d1_count, "skipped": 0}
    assert set(_signatures(TestSession, "d1")) == {"new:model:1536"}
    assert set(_signatures(TestSession, "d2")) == {"old:model:1536"}
    assert progress[-1] == (100, f"Đã nhúng {d1_count}/{d1_count} đoạn")
    # Không đổi đoạn: cùng id, cùng nội dung.
    with TestSession() as session:
        after = {row.id: (row.text, row.search_text) for row in session.scalars(select(Chunk))}
        assert after == before
        assert count_stale_chunks_by_document(session, "new:model:1536") == {"d2": len(before) - d1_count}

    # Đã khớp mô hình → không nhúng gì; include_current nhúng lại mọi đoạn của phạm vi.
    new.calls.clear()
    assert pipe.embed_chunks(dataset_id="ds1")["chunks"] == 0
    assert new.calls == []
    assert pipe.embed_chunks(document_id="d1", include_current=True)["chunks"] == d1_count

    # Toàn kho.
    assert pipe.embed_chunks()["documents"] == 1
    with TestSession() as session:
        assert embedding_coverage(session, "new:model:1536")["stale_chunks"] == 0


def test_embed_chunks_fills_missing_vectors(monkeypatch) -> None:
    model = _SignedModel("m:1")
    pipe, TestSession = _setup(monkeypatch, model)
    pipe.chunk_document("d1")
    with TestSession() as session:
        session.execute(update(Chunk).values(embedding=None))
        session.commit()
        assert embedding_coverage(session, "m:1")["stale_documents"] == 1
    assert pipe.embed_chunks()["documents"] == 1
    with TestSession() as session:
        assert session.scalar(select(Chunk.id).where(Chunk.embedding.is_(None))) is None


def test_embed_chunks_skips_chunk_changed_during_run(monkeypatch) -> None:
    pipe, TestSession = _setup(monkeypatch, _SignedModel("old:1"))
    pipe.chunk_document("d1")
    with TestSession() as session:
        first_id = session.scalar(select(Chunk.id).where(Chunk.document_id == "d1").order_by(Chunk.chunk_index))

    class _Rechunking(_SignedModel):
        def embed(self, texts):
            # Chia đoạn lại xảy ra giữa lúc đọc và lúc ghi vector.
            with TestSession() as session:
                session.execute(update(Chunk).where(Chunk.id == first_id).values(text="Nội dung mới"))
                session.commit()
            return super().embed(texts)

    pipe.embedding_model = _Rechunking("new:1")
    result = pipe.embed_chunks()
    assert result["skipped"] == 1
    with TestSession() as session:
        assert session.get(Chunk, first_id).embedding_signature == "old:1"


def test_embed_chunks_requires_usable_runtime(monkeypatch) -> None:
    runtime = EmbeddingRuntime()

    def broken():
        raise EmbeddingUnavailableError("Chưa có API key.")

    monkeypatch.setattr("app.embeddings.create_embedding_model", broken)
    pipe, _TestSession = _setup(monkeypatch, RuntimeEmbeddingModel(runtime))
    with pytest.raises(EmbeddingUnavailableError):
        pipe.embed_chunks()


# ==========================================
# AC-03: chữ ký runtime, lọc khi tìm kiếm
# ==========================================
def test_runtime_signature_follows_loaded_model(monkeypatch) -> None:
    runtime = EmbeddingRuntime()
    runtime.override(HashEmbeddingModel(dimensions=settings.vector_dim))
    assert runtime.signature() == embedding_signature()
    model = RuntimeEmbeddingModel(runtime)
    vectors, signature = model.embed_with_signature(["a"], query=True)
    assert len(vectors[0]) == settings.vector_dim and signature == embedding_signature()

    monkeypatch.setattr(settings, "embedding_provider", "openai_compatible")
    monkeypatch.setattr(settings, "embedding_model", "nomic-embed-text")
    monkeypatch.setattr(settings, "embedding_base_url", "http://localhost:11434/v1/")
    monkeypatch.setattr(settings, "embedding_dimension", 768)
    monkeypatch.setattr("app.embeddings.create_embedding_model", lambda: HashEmbeddingModel(settings.vector_dim))
    runtime.load()
    assert runtime.signature() == "openai_compatible:nomic-embed-text:768@http://localhost:11434/v1"
    # Base URL chỉ có nghĩa với openai_compatible.
    monkeypatch.setattr(settings, "embedding_provider", "voyage")
    assert embedding_signature() == "voyage:nomic-embed-text:768"


def test_vector_search_ignores_vectors_of_other_models(monkeypatch) -> None:
    pipe, TestSession = _setup(monkeypatch, _SignedModel("old:1"))
    pipe.chunk_documents()
    pipe.embedding_model = _SignedModel("new:1")
    pipe.embed_chunks(document_id="d1")
    store = PgVectorStore(TestSession)
    query = HashEmbeddingModel(dimensions=settings.vector_dim).embed(["Sinh viên đăng ký học phần"])[0]

    unfiltered = store.search(query, top_k=50)
    assert {item["document_id"] for item in unfiltered} == {"d1", "d2"}
    filtered = store.search(query, top_k=50, embedding_signature="new:1")
    assert filtered and {item["document_id"] for item in filtered} == {"d1"}
    assert store.search(query, top_k=50, dataset_ids=["ds2"], embedding_signature="new:1") == []

    # Nhúng lại hết → không còn vector lệch, đường truy vấn nhanh trả mọi đoạn.
    pipe.embed_chunks()
    assert {item["document_id"] for item in store.search(query, top_k=50, embedding_signature="new:1")} == {
        "d1",
        "d2",
    }


class _RecordingStore:
    collection_name = "test"

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def search(self, query_embedding, top_k, dataset_ids=None, **kwargs):
        self.calls.append(kwargs)
        return []


class _NoKeyword:
    def search(self, query, top_k, dataset_ids=None):
        return []


def test_retriever_passes_runtime_signature() -> None:
    store = _RecordingStore()
    Retriever(embedding_model=RuntimeEmbeddingModel(embedding_runtime), vector_store=store, keyword_search=_NoKeyword()).retrieve("học phí")
    assert store.calls == [{"embedding_signature": embedding_signature()}]

    plain = _RecordingStore()
    Retriever(
        embedding_model=HashEmbeddingModel(dimensions=settings.vector_dim), vector_store=plain, keyword_search=_NoKeyword()
    ).retrieve("học phí")
    assert plain.calls == [{}]


def test_startup_adopts_unsigned_vectors(monkeypatch) -> None:
    pipe, TestSession = _setup(monkeypatch, HashEmbeddingModel(dimensions=settings.vector_dim))
    pipe.chunk_documents()
    with TestSession() as session:
        session.execute(update(Chunk).where(Chunk.document_id == "d2").values(embedding=None))
        session.commit()

    monkeypatch.setattr(pipeline_module.embedding_runtime, "signature", lambda: "running:1")
    assert real_adopt_unsigned_vectors() == len(_signatures(TestSession, "d1"))
    assert set(_signatures(TestSession, "d1")) == {"running:1"}
    # Đoạn chưa có vector không được gán chữ ký.
    assert set(_signatures(TestSession, "d2")) == {None}

    monkeypatch.setattr(pipeline_module.embedding_runtime, "signature", lambda: None)
    assert real_adopt_unsigned_vectors() == 0


# ==========================================
# AC-02: job nhúng nền
# ==========================================
class _FakePipeline:
    def __init__(self, embed=None) -> None:
        self._embed = embed
        self.calls: list[dict] = []

    def embed_chunks(self, **options):
        self.calls.append(options)
        if self._embed is not None:
            return self._embed(**options)
        return {"documents": 1, "chunks": 3, "skipped": 0}


def _wait_for(manager: ParseJobManager, job_id: str, statuses: set[str], timeout: float = 3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = manager.get(job_id)
        if job is not None and job.status in statuses:
            return job
        time.sleep(0.01)
    raise AssertionError(f"job {job_id} did not reach {statuses}; last={manager.get(job_id)}")


def test_embed_job_runs_in_background_with_progress(tmp_path) -> None:
    release = threading.Event()

    def embed(*, dataset_id, document_id, include_current, on_progress):
        on_progress(40, "Đã nhúng 2/5 đoạn")
        release.wait(2)
        return {"documents": 2, "chunks": 5, "skipped": 0}

    pipeline = _FakePipeline(embed)
    manager = ParseJobManager(pipeline=pipeline, staging_root=tmp_path)
    job = manager.enqueue_embed(label="Quy chế", dataset_id="ds1", include_current=True)
    assert job.kind == "embed" and job.dataset_id == "ds1" and job.file_name == "Quy chế"

    running = _wait_for(manager, job.id, {"running"})
    deadline = time.monotonic() + 2
    while manager.get(job.id).progress < 40 and time.monotonic() < deadline:
        time.sleep(0.01)
    assert manager.get(job.id).progress_message == "Đã nhúng 2/5 đoạn"
    assert running.status == "running"
    # Trùng phạm vi đang chạy → từ chối; phạm vi khác vẫn xếp hàng được.
    with pytest.raises(ParseJobConflict, match="đang được nhúng"):
        manager.enqueue_embed(label="Quy chế", dataset_id="ds1")
    other = manager.enqueue_embed(label="Toàn bộ tài liệu")
    release.set()

    done = _wait_for(manager, job.id, {"succeeded"})
    assert done.progress == 100 and done.result == {"documents": 2, "chunks": 5, "skipped": 0}
    assert pipeline.calls[0]["dataset_id"] == "ds1" and pipeline.calls[0]["include_current"] is True
    _wait_for(manager, other.id, {"succeeded"})
    assert pipeline.calls[1]["dataset_id"] is None and pipeline.calls[1]["document_id"] is None
    # Job nhúng không chặn thao tác cần "không có job parse" của tài liệu.
    assert manager.active_for_document("d1") is None


def test_embed_job_failure_is_reported(tmp_path) -> None:
    def embed(**_options):
        raise EmbeddingUnavailableError("Mô hình nhúng chưa sẵn sàng.")

    manager = ParseJobManager(pipeline=_FakePipeline(embed), staging_root=tmp_path)
    job = manager.enqueue_embed(label="a.md", document_id="d1", dataset_id="ds1")
    failed = _wait_for(manager, job.id, {"failed"})
    assert failed.error == "Mô hình nhúng chưa sẵn sàng."
    assert failed.progress_message == "Nhúng thất bại"
    assert failed.document_id == "d1" and failed.dataset_id == "ds1"


# ==========================================
# AC-05: API
# ==========================================
def _seed_api(api_db) -> str:
    current = embedding_signature()
    vector = [0.0] * settings.vector_dim
    vector[0] = 1.0
    with api_db() as session:
        session.add(Dataset(id="ds1", name="Quy chế"))
        session.flush()
        for doc_id in ("d1", "d2"):
            session.add(
                Document(
                    id=doc_id,
                    dataset_id="ds1",
                    source_path=f"data/datasets/ds1/{doc_id}.md",
                    title=doc_id,
                    file_type="md",
                    content_hash=doc_id,
                    status="active",
                )
            )
        session.flush()
        rows = [("d1", 0, current), ("d1", 1, "old:model:1536"), ("d2", 0, current)]
        for doc_id, index, signature in rows:
            session.add(
                Chunk(
                    id=f"{doc_id}-{index}",
                    document_id=doc_id,
                    chunk_index=index,
                    text="x",
                    search_text="x",
                    vector_id=f"{doc_id}-{index}",
                    embedding=vector,
                    embedding_signature=signature,
                )
            )
        session.commit()
    return current


def _fake_job(**fields) -> ParseJob:
    base = {
        "id": "job-1",
        "kind": "embed",
        "status": "queued",
        "document_id": None,
        "file_name": "Quy chế",
        "parser_name": None,
        "dataset_id": "ds1",
        "created_at": datetime.now(timezone.utc),
    }
    base.update(fields)
    return ParseJob(**base)


def test_embedding_status_and_stale_counts(admin_client, api_db) -> None:
    _seed_api(api_db)
    status = admin_client.get("/api/embeddings/status")
    assert status.status_code == 200, status.text
    body = status.json()
    assert body["state"] == "ready"
    assert (body["total_chunks"], body["stale_chunks"], body["stale_documents"]) == (3, 1, 1)

    documents = {item["id"]: item for item in admin_client.get("/api/documents").json()["documents"]}
    assert documents["d1"]["stale_chunk_count"] == 1
    assert documents["d2"]["stale_chunk_count"] == 0
    assert admin_client.get("/api/documents/d1").json()["stale_chunk_count"] == 1

    dataset = admin_client.get("/api/datasets/ds1").json()
    assert (dataset["stale_document_count"], dataset["stale_chunk_count"]) == (1, 1)
    listed = admin_client.get("/api/datasets").json()["datasets"][0]
    assert listed["stale_chunk_count"] == 1


def test_embed_endpoints_enqueue_jobs(admin_client, api_db, monkeypatch) -> None:
    from app.api import routes

    _seed_api(api_db)
    calls: list[dict] = []

    def enqueue(**options):
        calls.append(options)
        return _fake_job(document_id=options.get("document_id"), file_name=options["label"])

    monkeypatch.setattr(routes.parse_jobs, "enqueue_embed", enqueue)

    response = admin_client.post("/api/datasets/ds1/embed")
    assert response.status_code == 202, response.text
    assert response.json()["kind"] == "embed"
    assert calls[-1] == {"label": "Quy chế", "dataset_id": "ds1", "include_current": False}

    response = admin_client.post("/api/documents/d1/embed?all=true")
    assert response.status_code == 202, response.text
    assert calls[-1] == {"label": "d1.md", "document_id": "d1", "dataset_id": "ds1", "include_current": True}

    assert admin_client.post("/api/embeddings/reembed").status_code == 202
    assert calls[-1] == {"label": "Toàn bộ tài liệu", "include_current": False}

    assert admin_client.post("/api/datasets/missing/embed").status_code == 404
    assert admin_client.post("/api/documents/missing/embed").status_code == 404


def test_embed_endpoint_errors(admin_client, api_db, monkeypatch) -> None:
    from app.api import routes

    _seed_api(api_db)

    def conflict(**_options):
        raise ParseJobConflict("“Quy chế” đang được nhúng; hãy chờ job hiện tại xong.")

    monkeypatch.setattr(routes.parse_jobs, "enqueue_embed", conflict)
    response = admin_client.post("/api/datasets/ds1/embed")
    assert response.status_code == 409
    assert "đang được nhúng" in response.json()["detail"]

    # Tài liệu chưa có đoạn → 409.
    with api_db() as session:
        session.add(
            Document(id="d3", dataset_id="ds1", source_path="data/datasets/ds1/d3.md", content_hash="d3", status="parsed")
        )
        session.commit()
    assert admin_client.post("/api/documents/d3/embed").status_code == 409

    # Embedder chưa sẵn sàng → 503, không xếp job.
    def broken():
        raise EmbeddingUnavailableError("Chưa có API key cho embedding.")

    embedding_runtime.reset()
    monkeypatch.setattr("app.embeddings.create_embedding_model", broken)
    response = admin_client.post("/api/embeddings/reembed")
    assert response.status_code == 503
    assert "Chưa có API key" in response.json()["detail"]


def test_embed_job_payload_serializes_result(admin_client, api_db, monkeypatch) -> None:
    from app.api import routes

    job = _fake_job(status="succeeded", result={"documents": 1, "chunks": 4, "skipped": 0}, progress=100)
    monkeypatch.setattr(routes.parse_jobs, "get", lambda job_id: job)
    response = admin_client.get("/api/parse-jobs/job-1")
    assert response.status_code == 200, response.text
    assert response.json()["result"] == {"documents": 1, "chunks": 4, "skipped": 0}


def test_embed_endpoints_require_admin(client) -> None:
    assert client.post("/api/datasets/ds1/embed").status_code == 401
    assert client.post("/api/embeddings/reembed").status_code == 401
    assert client.get("/api/embeddings/status").status_code == 401
