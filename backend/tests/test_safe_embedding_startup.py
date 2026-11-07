"""Khởi động an toàn khi thiếu/lỗi embedding (BE-13), qua API.

- AC-01: ``import app.main`` và ``TestClient(app)`` (có lifespan) chạy được khi không có key;
  ``/api/health`` 200 với ``embedding: not_configured``.
- AC-02: chat/stream 503 trước hạn mức BE-10, không ghi DB, không gọi retrieval/LLM;
  route admin vẫn dùng được; route chia đoạn 503, không ghi chunk.
- AC-03: lưu key qua ``PUT /api/config`` hoặc chọn profile embedding → chat chạy ngay.
- AC-04/AC-05: mô hình tải lỗi hoặc trả sai số chiều → ``error``, không chunk nào được ghi.
- AC-06: embedder đã ``ready`` không bị thay khi cấu hình đổi.

Embedder OpenAI được thay bằng bản giả ở ``app.embeddings.embedder`` (factory thật vẫn
chạy, không gọi mạng); retrieval/LLM của chat là bản giả; DB là SQLite tạm.
"""

from __future__ import annotations

import json
import os
import secrets
import subprocess
import sys
from pathlib import Path
from typing import ClassVar

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import routes
from app.core import rate_limit
from app.core.config import settings
from app.db.models import Base, Chunk, Conversation, Dataset, Document, Message
from app.embeddings import EmbeddingModel, embedder, embedding_runtime
from app.embeddings.embedder import VECTOR_COLUMN_DIM
from app.ingestion import ingestion_pipeline
from app.main import app
from app.retrieval.retriever import retriever

BACKEND_DIR = Path(__file__).resolve().parents[1]
UNIT_TEST_KEY = "sk-unit-test-embedding-key-0123456789"
CHAT_PATHS = ("/api/chat", "/api/chat/stream")
DOC_ID = "doc-hoc-phi"
DATASET_ID = "ds-so-tay"


class _FakeOpenAIEmbedding(EmbeddingModel):
    """Thay ``OpenAIEmbeddingModel``: ghi lại khoá được dùng, trả vector ``dimensions`` chiều."""

    created: ClassVar[list[_FakeOpenAIEmbedding]] = []
    dimensions = VECTOR_COLUMN_DIM

    def __init__(self, model_name: str, api_key: str | None) -> None:
        self.model_name = model_name
        self.api_key = api_key
        self.texts: list[str] = []
        type(self).created.append(self)

    def embed(self, texts):
        self.texts.extend(texts)
        return [[0.01] * self.dimensions for _ in texts]


class _RecordingStore:
    def __init__(self) -> None:
        self.added: list[str] = []
        self.deleted: list[str] = []

    def add(self, chunks, embeddings):
        self.added.extend(item["id"] for item in chunks)

    def delete(self, ids):
        self.deleted.extend(ids)

    def search(self, query_embedding, top_k, dataset_ids=None):
        return []


@pytest.fixture(autouse=True)
def _restore_settings():
    snapshot = settings.model_dump()
    yield
    for field, value in snapshot.items():
        setattr(settings, field, value)


@pytest.fixture
def fake_openai(monkeypatch):
    monkeypatch.setattr(_FakeOpenAIEmbedding, "created", [])
    monkeypatch.setattr(embedder, "OpenAIEmbeddingModel", _FakeOpenAIEmbedding)
    return _FakeOpenAIEmbedding


@pytest.fixture
def not_configured(monkeypatch, fake_openai):
    """Embedding OpenAI không có key, runtime chưa tạo gì (như vừa khởi động)."""
    monkeypatch.setattr(settings, "embedding_provider", "openai")
    monkeypatch.setattr(settings, "embedding_model", "text-embedding-3-small")
    monkeypatch.setattr(settings, "embedding_api_key", None)
    monkeypatch.setattr(settings, "openai_api_key", None)
    monkeypatch.setattr(settings, "embedding_profile_id", None)
    monkeypatch.setattr(settings, "vector_dim", VECTOR_COLUMN_DIM)
    embedding_runtime.reset()
    assert embedding_runtime.status()["state"] == "not_configured"


@pytest.fixture
def encryption_key(monkeypatch):
    monkeypatch.setattr(settings, "config_encryption_key", Fernet.generate_key().decode())


@pytest.fixture
def db_ok(monkeypatch):
    monkeypatch.setattr(
        routes, "check_db_health", lambda: {"status": "ok", "database": "connected", "dialect": "sqlite"}
    )


@pytest.fixture
def chat_calls(monkeypatch) -> dict[str, list[str]]:
    """Retrieval/LLM giả; câu trả lời có dùng embedder chung như retrieval thật."""
    calls: dict[str, list[str]] = {"answer": [], "retrieve": []}

    def fake_answer(message, top_k, history):
        retriever.embedding_model.embed([message])
        calls["answer"].append(message)
        return {"answer": "Trả lời", "sources": [], "contexts": [], "retrieval_debug": {}}

    def fake_iter_retrieve(message, top_k, history=None):
        retriever.embedding_model.embed([message])
        calls["retrieve"].append(message)
        yield {"result": {"contexts": [], "retrieval_debug": {}, "strong_context": False, "guardrail_allowed": True}}

    monkeypatch.setattr(routes.rag_chain, "answer", fake_answer)
    monkeypatch.setattr(routes.rag_chain, "iter_retrieve_context", fake_iter_retrieve)
    monkeypatch.setattr(routes, "stream_answer_deltas_with_llm", lambda *args, **kwargs: iter(()))
    return calls


@pytest.fixture
def chunk_db(monkeypatch):
    """Pipeline chia đoạn dùng chung trên SQLite tạm, một tài liệu đã parse; embedder là runtime."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    with factory() as session:
        session.add(Dataset(id=DATASET_ID, name="Sổ tay"))
        session.add(
            Document(
                id=DOC_ID,
                dataset_id=DATASET_ID,
                source_path="data/ds-so-tay/hoc-phi.md",
                title="Học phí",
                file_type="md",
                content_hash="hash-v1",
                status="active",
                parsed_text="# Học phí\n\nHọc phí được đóng theo từng học kỳ.\n\n## Miễn giảm\n\nSinh viên được xét miễn giảm.",
            )
        )
        session.commit()
    store = _RecordingStore()
    monkeypatch.setattr("app.ingestion.pipeline.SessionLocal", factory)
    monkeypatch.setattr("app.ingestion.pipeline.init_db", lambda: None)
    monkeypatch.setattr("app.ingestion.pipeline.invalidate_bm25_cache", lambda: None)
    monkeypatch.setattr(ingestion_pipeline, "vector_store", store)
    yield factory, store
    engine.dispose()


def _chat_client() -> TestClient:
    test_client = TestClient(app)
    test_client.cookies.set("ptit_sid", secrets.token_urlsafe(32), path="/api")
    return test_client


def _chat_counts(factory) -> tuple[int, int]:
    with factory() as session:
        return (
            session.scalar(select(func.count()).select_from(Conversation)),
            session.scalar(select(func.count()).select_from(Message)),
        )


def _chunk_state(factory) -> tuple[int, str, object]:
    with factory() as session:
        document = session.get(Document, DOC_ID)
        chunks = session.scalar(select(func.count()).select_from(Chunk))
        return chunks, document.status, document.updated_at


def _health(test_client: TestClient) -> dict:
    response = test_client.get("/api/health")
    assert response.status_code == 200, response.text
    return response.json()


def _assert_chunk_routes_503(admin_client, factory, store, reason_part: str) -> None:
    before = _chunk_state(factory)
    for path in (f"/api/documents/{DOC_ID}/chunk", "/api/ingest/chunk", f"/api/datasets/{DATASET_ID}/chunk"):
        response = admin_client.post(path)
        assert response.status_code == 503, (path, response.text)
        detail = response.json()["detail"]
        assert detail.startswith("Mô hình nhúng chưa sẵn sàng:"), detail
        assert reason_part in detail
    assert _chunk_state(factory) == before
    assert before[0] == 0
    assert store.added == [] and store.deleted == []


# ==========================================
# AC-01: khởi động không có key
# ==========================================
def _run_without_key(tmp_path: Path, script: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    # Biến môi trường rỗng thắng giá trị trong .env; DB là SQLite tạm, không chạm DB dev.
    env.update(
        OPENAI_API_KEY="",
        EMBEDDING_API_KEY="",
        EMBEDDING_PROVIDER="openai",
        EMBEDDING_PROFILE_ID="",
        VECTOR_DIM=str(VECTOR_COLUMN_DIM),
        DATABASE_URL=f"sqlite:///{(tmp_path / 'startup.db').as_posix()}",
        PYTHONIOENCODING="utf-8",
    )
    return subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=180,
    )


def test_import_app_without_embedding_key(tmp_path) -> None:
    result = _run_without_key(tmp_path, "import app.main")
    assert result.returncode == 0, result.stderr


def test_lifespan_and_health_without_embedding_key(tmp_path) -> None:
    script = (
        "import json\n"
        "from fastapi.testclient import TestClient\n"
        "from app.main import app\n"
        "with TestClient(app) as client:\n"
        "    response = client.get('/api/health')\n"
        "    print('RESULT=' + json.dumps({'code': response.status_code, 'body': response.json()}))\n"
    )
    result = _run_without_key(tmp_path, script)
    assert result.returncode == 0, result.stderr
    line = next(item for item in result.stdout.splitlines() if item.startswith("RESULT="))
    payload = json.loads(line.removeprefix("RESULT="))
    assert payload["code"] == 200
    assert payload["body"]["embedding"] == "not_configured"
    assert payload["body"]["status"] == "degraded"
    assert payload["body"]["database"] == "connected"
    assert UNIT_TEST_KEY not in result.stdout + result.stderr


def test_health_reports_embedding_state(client, not_configured, db_ok, monkeypatch) -> None:
    data = _health(client)
    assert data["embedding"] == "not_configured"
    assert data["status"] == "degraded"
    # Route công khai không trả lý do lỗi.
    assert "reason" not in data and "API key" not in json.dumps(data, ensure_ascii=False)

    monkeypatch.setattr(settings, "openai_api_key", UNIT_TEST_KEY)
    data = _health(client)
    assert (data["status"], data["embedding"]) == ("ok", "ready")


# ==========================================
# AC-02: 503 khi embedding không dùng được
# ==========================================
@pytest.mark.parametrize("path", CHAT_PATHS)
def test_chat_returns_503_before_limits_and_db(path, not_configured, api_db, chat_calls) -> None:
    test_client = _chat_client()
    response = test_client.post(path, json={"message": "Học phí bao nhiêu?"})

    assert response.status_code == 503, response.text
    assert response.json()["detail"].startswith("Chatbot chưa sẵn sàng: mô hình nhúng (embedding)")
    assert "API key" not in response.json()["detail"]
    assert _chat_counts(api_db) == (0, 0)
    assert chat_calls == {"answer": [], "retrieve": []}
    assert rate_limit.chat_ip_limiter.tracked_keys() == 0
    assert rate_limit.chat_owner_limiter.tracked_keys() == 0


@pytest.mark.parametrize("path", CHAT_PATHS)
def test_chat_validation_errors_come_before_503(path, not_configured, api_db, chat_calls) -> None:
    test_client = _chat_client()
    assert test_client.post(path, json={"message": "   "}).status_code == 400
    assert test_client.post(path, json={}).status_code == 422


def test_admin_still_works_and_sees_reason(admin_client, not_configured) -> None:
    assert admin_client.get("/api/config").status_code == 200
    response = admin_client.get("/api/model-profiles")
    assert response.status_code == 200
    runtime = response.json()["embedding_runtime"]
    assert runtime["status"] == "not_configured"
    assert "API key" in runtime["load_error"]


def test_chunk_routes_return_503_without_writing(admin_client, not_configured, chunk_db) -> None:
    factory, store = chunk_db
    _assert_chunk_routes_503(admin_client, factory, store, "API key")
    response = admin_client.post("/api/retrieval/test", json={"query": "học phí"})
    assert response.status_code == 503


# ==========================================
# AC-03: cấu hình lúc chạy, không restart
# ==========================================
def test_saving_key_via_config_enables_chat_without_restart(
    admin_client, not_configured, encryption_key, api_db, chat_calls, db_ok, fake_openai
) -> None:
    test_client = _chat_client()
    assert test_client.post("/api/chat", json={"message": "Học phí?"}).status_code == 503

    response = admin_client.put("/api/config", json={"llm": {"openai_api_key": UNIT_TEST_KEY}})
    assert response.status_code == 200, response.text

    response = test_client.post("/api/chat", json={"message": "Học phí?"})
    assert response.status_code == 200, response.text
    assert chat_calls["answer"] == ["Học phí?"]
    assert [model.api_key for model in fake_openai.created] == [UNIT_TEST_KEY]
    assert fake_openai.created[0].texts == ["Học phí?"]
    assert _health(test_client)["embedding"] == "ready"
    assert admin_client.get("/api/model-profiles").json()["embedding_runtime"]["status"] == "ready"


def test_selecting_embedding_profile_applies_now_when_not_running(
    admin_client, not_configured, encryption_key, api_db, chat_calls, db_ok, fake_openai
) -> None:
    response = admin_client.post(
        "/api/model-profiles",
        json={
            "kind": "embedding",
            "name": "OpenAI small",
            "provider": "openai",
            "model": "text-embedding-3-small",
            "dimension": VECTOR_COLUMN_DIM,
            "api_key": UNIT_TEST_KEY,
        },
    )
    assert response.status_code == 201, response.text
    profile_id = response.json()["profiles"][0]["id"]

    response = admin_client.post("/api/model-profiles/activate", json={"kind": "embedding", "profile_id": profile_id})
    assert response.status_code == 200, response.text
    runtime = response.json()["embedding_runtime"]
    assert runtime["status"] == "ready"
    assert runtime["profile_id"] == profile_id
    assert runtime["restart_required"] is False
    assert runtime["load_error"] is None
    assert UNIT_TEST_KEY not in response.text

    assert _chat_client().post("/api/chat/stream", json={"message": "Học phí?"}).status_code == 200
    assert chat_calls["retrieve"] == ["Học phí?"]
    assert [model.api_key for model in fake_openai.created] == [UNIT_TEST_KEY]
    assert _health(admin_client)["embedding"] == "ready"


def test_broken_profile_reports_error_and_keeps_env_state(admin_client, not_configured, monkeypatch) -> None:
    def broken(model_name):
        raise OSError("không tải được")

    monkeypatch.setattr(embedder, "SentenceTransformerEmbeddingModel", broken)
    response = admin_client.post(
        "/api/model-profiles",
        json={
            "kind": "embedding",
            "name": "ST",
            "provider": "sentence-transformers",
            "model": "unit-test/st-model",
            "dimension": VECTOR_COLUMN_DIM,
        },
    )
    profile_id = response.json()["profiles"][0]["id"]
    response = admin_client.post("/api/model-profiles/activate", json={"kind": "embedding", "profile_id": profile_id})

    assert response.status_code == 200, response.text
    runtime = response.json()["embedding_runtime"]
    assert runtime["profile_id"] is None
    assert runtime["restart_required"] is True
    assert "unit-test/st-model" in runtime["load_error"] and "OSError" in runtime["load_error"]
    assert runtime["status"] == "not_configured"
    assert settings.embedding_provider == "openai"


# ==========================================
# AC-04, AC-05: lỗi mô hình và sai số chiều
# ==========================================
def test_sentence_transformers_failure_is_error_and_writes_nothing(
    admin_client, not_configured, chunk_db, monkeypatch
) -> None:
    def broken(model_name):
        raise OSError("không tải được")

    monkeypatch.setattr(embedder, "SentenceTransformerEmbeddingModel", broken)
    monkeypatch.setattr(settings, "embedding_provider", "sentence-transformers")
    monkeypatch.setattr(settings, "embedding_model", "unit-test/st-model")

    assert _health(admin_client)["embedding"] == "error"
    runtime = admin_client.get("/api/model-profiles").json()["embedding_runtime"]
    assert runtime["status"] == "error"
    assert "OSError" in runtime["load_error"]
    factory, store = chunk_db
    _assert_chunk_routes_503(admin_client, factory, store, "unit-test/st-model")


def test_wrong_dimension_vectors_are_never_written(
    admin_client, not_configured, chunk_db, api_db, chat_calls, monkeypatch
) -> None:
    monkeypatch.setattr(_FakeOpenAIEmbedding, "dimensions", 384)
    monkeypatch.setattr(settings, "openai_api_key", UNIT_TEST_KEY)
    factory, store = chunk_db

    response = admin_client.post(f"/api/documents/{DOC_ID}/chunk")
    assert response.status_code == 503, response.text
    assert "384" in response.json()["detail"]
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(Chunk)) == 0
    assert store.added == []

    assert _health(admin_client)["embedding"] == "error"
    assert _chat_client().post("/api/chat", json={"message": "Học phí?"}).status_code == 503
    _assert_chunk_routes_503(admin_client, factory, store, "384")


def test_vector_dim_mismatch_with_column_is_error(admin_client, not_configured, chunk_db, monkeypatch) -> None:
    monkeypatch.setattr(settings, "embedding_provider", "hash")
    monkeypatch.setattr(settings, "vector_dim", 768)
    runtime = admin_client.get("/api/model-profiles").json()["embedding_runtime"]
    assert runtime["status"] == "error"
    assert "VECTOR_DIM=768" in runtime["load_error"]
    factory, store = chunk_db
    _assert_chunk_routes_503(admin_client, factory, store, "VECTOR_DIM=768")


def test_hash_provider_chunks_with_vector_dim(admin_client, not_configured, chunk_db, monkeypatch) -> None:
    monkeypatch.setattr(settings, "embedding_provider", "hash")
    factory, store = chunk_db
    response = admin_client.post(f"/api/documents/{DOC_ID}/chunk")
    assert response.status_code == 200, response.text
    with factory() as session:
        embeddings = list(session.scalars(select(Chunk.embedding)))
    assert embeddings and all(len(vector) == VECTOR_COLUMN_DIM for vector in embeddings)
    assert len(store.added) == len(embeddings)


# ==========================================
# AC-06: embedder đã ready được ghim
# ==========================================
def test_ready_embedder_is_not_replaced_by_config_changes(
    admin_client, not_configured, encryption_key, fake_openai
) -> None:
    admin_client.put("/api/config", json={"llm": {"openai_api_key": UNIT_TEST_KEY}})
    running = embedding_runtime.get()
    assert running.api_key == UNIT_TEST_KEY

    response = admin_client.put(
        "/api/config",
        json={"llm": {"openai_api_key": "sk-unit-test-rotated-key"}, "embedding": {"model": "text-embedding-3-large"}},
    )
    assert response.status_code == 200, response.text
    assert embedding_runtime.get() is running
    assert len(fake_openai.created) == 1
    assert admin_client.get("/api/model-profiles").json()["embedding_runtime"]["status"] == "ready"
