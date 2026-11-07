"""Lỗi của lượt chat không lộ chi tiết nội bộ cho client (BE-12, AC-04) và hai loại câu
trả lời dự phòng (AC-05).

Client chỉ nhận thông điệp chung kèm mã tham chiếu; cùng mã xuất hiện ở header
``X-Request-ID``, ``metadata.error`` và dòng log chứa chi tiết.
"""

from __future__ import annotations

import json
import logging

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api import routes
from app.db.models import Message
from app.generation.rag_chain import RagChain
from app.llm import BaseLLMProvider, CONTENT_DELTA, OpenAIProvider, StreamDelta
from app.main import app

SECRET = "secret-xyz-internal-detail"
LEAKED_KEY = "sk-test-leaked-0123456789abcdef"
NOT_CONFIGURED_PREFIX = "Chưa cấu hình mô hình ngôn ngữ (LLM)"
UNAVAILABLE_PREFIX = "Mô hình ngôn ngữ đang tạm thời gặp sự cố"

RETRIEVAL_RESULT = {
    "contexts": [{"source_name": "handbook.md", "heading": "Học phí", "section_path": "Học phí", "text": "Nội dung."}],
    "retrieval_debug": {"rewritten_query": "học phí", "strong_context": True},
    "strong_context": True,
    "guardrail_allowed": True,
}


class StrongRetriever:
    def retrieve(self, question: str, top_k: int, dataset_ids: list[str] | None = None) -> list[dict]:
        return [
            {
                "source_name": "handbook.md",
                "heading": "Học phí",
                "section_path": "Học phí",
                "chunk_id": "chunk-1",
                "text": "Học phí năm 2026 là 20 triệu đồng.",
                "vector_score": 0.9,
                "bm25_score": 5.0,
            }
        ]


class MidStreamFailingProvider(BaseLLMProvider):
    """Phát một delta rồi lỗi với thông điệp chứa key (như SDK có thể trả)."""

    def is_configured(self) -> bool:
        return True

    def generate(self, messages, temperature=0.0, max_tokens=None, budget=None, **kwargs) -> str:
        raise AssertionError("not used")

    def generate_stream(self, messages, temperature=0.2, max_tokens=None, budget=None, **kwargs):
        yield "Học phí "
        raise ValueError(f"Incorrect API key provided: {LEAKED_KEY} ({SECRET})")


def _events(response) -> list[dict]:
    return [json.loads(line) for line in response.text.splitlines() if line.strip()]


def _assistant_metadata(factory) -> dict:
    with factory() as session:
        messages = list(session.scalars(select(Message).order_by(Message.created_at, Message.id)))
    assistant = [m for m in messages if m.role == "assistant"]
    assert assistant, "assistant message must be saved"
    return assistant[-1].message_metadata


def _fake_retrieval(monkeypatch) -> None:
    def fake_iter_retrieve(message, top_k, history=None, budget=None):
        yield {"step": "retrieve", "detail": {}, "elapsed_ms": 1}
        yield {"result": dict(RETRIEVAL_RESULT)}

    monkeypatch.setattr(routes.rag_chain, "iter_retrieve_context", fake_iter_retrieve)


def _log_records_with(caplog, request_id: str) -> list[logging.LogRecord]:
    return [record for record in caplog.records if request_id in record.getMessage()]


def _record_text(record: logging.LogRecord) -> str:
    text = record.getMessage()
    if record.exc_info:
        text += "\n" + logging.Formatter().formatException(record.exc_info)
    return text


# ==========================================
# AC-04: /api/chat/stream
# ==========================================
def test_stream_retrieval_error_is_generic_with_request_id(api_db, monkeypatch, caplog) -> None:
    def failing_retrieve(message, top_k, history=None, budget=None):
        yield {"step": "query_rewrite", "detail": {}, "elapsed_ms": 1}
        raise RuntimeError(SECRET)

    monkeypatch.setattr(routes.rag_chain, "iter_retrieve_context", failing_retrieve)

    with caplog.at_level(logging.ERROR, logger="app.api.routes"):
        response = TestClient(app).post("/api/chat/stream", json={"message": "Học phí?"})

    error = _events(response)[-1]
    request_id = response.headers["X-Request-ID"]
    assert error == {
        "type": "error",
        "message": routes.CHAT_INTERNAL_ERROR_DETAIL.format(request_id=request_id),
        "request_id": request_id,
    }
    assert len(request_id) == 12
    assert SECRET not in response.text
    assert _assistant_metadata(api_db)["error"] == {
        "type": "retrieval",
        "request_id": request_id,
        "error_class": "RuntimeError",
    }
    # Chi tiết chỉ ở log, cùng mã tham chiếu.
    records = _log_records_with(caplog, request_id)
    assert any(SECRET in _record_text(record) for record in records)


def test_stream_llm_error_mid_answer_is_generic_and_key_free(api_db, monkeypatch, caplog) -> None:
    _fake_retrieval(monkeypatch)
    monkeypatch.setattr("app.generation.llm.get_llm_provider", lambda: MidStreamFailingProvider())

    with caplog.at_level(logging.WARNING):
        response = TestClient(app).post("/api/chat/stream", json={"message": "Học phí?"})

    events = _events(response)
    request_id = response.headers["X-Request-ID"]
    assert [e["type"] for e in events][-2:] == ["delta", "error"]
    assert events[-1]["message"] == routes.CHAT_LLM_STREAM_ERROR_DETAIL.format(request_id=request_id)
    assert events[-1]["request_id"] == request_id
    assert LEAKED_KEY not in response.text and SECRET not in response.text

    metadata = _assistant_metadata(api_db)
    assert metadata["error"] == {"type": "llm_stream", "request_id": request_id, "error_class": "LLMStreamError"}
    assert LEAKED_KEY not in json.dumps(metadata) and SECRET not in json.dumps(metadata)

    records = _log_records_with(caplog, request_id)
    assert any(SECRET in record.getMessage() for record in records)
    # Log có chi tiết nhưng key đã bị che.
    assert LEAKED_KEY not in caplog.text


def test_stream_unexpected_internal_error_ends_with_generic_error_event(api_db, monkeypatch, caplog) -> None:
    _fake_retrieval(monkeypatch)
    monkeypatch.setattr(
        routes,
        "stream_answer_deltas_with_llm",
        lambda question, contexts, history=None, provider=None, budget=None: iter(
            [StreamDelta(kind=CONTENT_DELTA, text="Học phí [1]")]
        ),
    )

    def broken_normalize(answer, contexts):
        raise RuntimeError(SECRET)

    monkeypatch.setattr(routes, "_normalize_answer_citations", broken_normalize)

    with caplog.at_level(logging.ERROR, logger="app.api.routes"):
        response = TestClient(app).post("/api/chat/stream", json={"message": "Học phí?"})

    events = _events(response)
    request_id = response.headers["X-Request-ID"]
    assert events[-1] == {
        "type": "error",
        "message": routes.CHAT_INTERNAL_ERROR_DETAIL.format(request_id=request_id),
        "request_id": request_id,
    }
    assert SECRET not in response.text
    assert _assistant_metadata(api_db)["error"] == {
        "type": "internal",
        "request_id": request_id,
        "error_class": "RuntimeError",
    }
    assert any(SECRET in _record_text(record) for record in _log_records_with(caplog, request_id))


def test_each_stream_turn_gets_its_own_request_id(api_db, monkeypatch) -> None:
    _fake_retrieval(monkeypatch)
    monkeypatch.setattr(
        routes,
        "stream_answer_deltas_with_llm",
        lambda question, contexts, history=None, provider=None, budget=None: iter(
            [StreamDelta(kind=CONTENT_DELTA, text="Học phí [1]")]
        ),
    )
    client = TestClient(app)

    ids = {client.post("/api/chat/stream", json={"message": "Học phí?"}).headers["X-Request-ID"] for _ in range(2)}

    assert len(ids) == 2


# ==========================================
# AC-04: /api/chat
# ==========================================
def test_chat_unexpected_error_returns_503_generic_detail(api_db, monkeypatch, caplog) -> None:
    def failing_answer(message, top_k, history, budget=None):
        raise RuntimeError(SECRET)

    monkeypatch.setattr(routes.rag_chain, "answer", failing_answer)

    with caplog.at_level(logging.ERROR, logger="app.api.routes"):
        response = TestClient(app, raise_server_exceptions=False).post("/api/chat", json={"message": "Học phí?"})

    assert response.status_code == 503
    request_id = response.headers["X-Request-ID"]
    assert response.json() == {"detail": f"Hệ thống đang bận, vui lòng thử lại sau. (Mã: {request_id})"}
    assert SECRET not in response.text
    assert _assistant_metadata(api_db)["error"] == {
        "type": "answer",
        "request_id": request_id,
        "error_class": "RuntimeError",
    }
    assert any(SECRET in _record_text(record) for record in _log_records_with(caplog, request_id))


def test_chat_success_has_request_id_header(api_db, monkeypatch) -> None:
    monkeypatch.setattr(
        routes.rag_chain,
        "answer",
        lambda message, top_k, history, budget=None: {"answer": "Trả lời", "sources": [], "contexts": [], "retrieval_debug": {}},
    )

    response = TestClient(app).post("/api/chat", json={"message": "Học phí?"})

    assert response.status_code == 200
    assert len(response.headers["X-Request-ID"]) == 12


# ==========================================
# AC-05: hai loại câu trả lời dự phòng
# ==========================================
@pytest.fixture
def real_chain(api_db, monkeypatch):
    monkeypatch.setattr(routes.settings, "guardrail_scope_enabled", False)
    monkeypatch.setattr(routes.settings, "reranker_enabled", False)
    monkeypatch.setattr(routes.settings, "query_rewrite_use_llm", False)
    monkeypatch.setattr(routes.settings, "multi_query_use_llm", False)
    monkeypatch.setattr(routes, "rag_chain", RagChain(retriever_=StrongRetriever()))


def _use_provider(monkeypatch, provider: BaseLLMProvider) -> None:
    monkeypatch.setattr("app.generation.llm.get_llm_provider", lambda: provider)


def _failing_openai() -> OpenAIProvider:
    transport = httpx.MockTransport(lambda request: httpx.Response(503, json={"error": {"message": "overloaded"}}))
    return OpenAIProvider(api_key="sk-test-configured-0123456789", http_client=httpx.Client(transport=transport))


@pytest.mark.parametrize("path", ["/api/chat", "/api/chat/stream"])
def test_fallback_says_not_configured_without_key(real_chain, monkeypatch, path) -> None:
    _use_provider(monkeypatch, OpenAIProvider(api_key=None))

    response = TestClient(app).post(path, json={"message": "Học phí bao nhiêu?"})

    answer = response.json()["answer"] if path == "/api/chat" else _events(response)[-1]["answer"]
    assert answer.startswith(NOT_CONFIGURED_PREFIX)


@pytest.mark.parametrize("path", ["/api/chat", "/api/chat/stream"])
def test_fallback_says_temporarily_unavailable_when_configured_llm_fails(real_chain, monkeypatch, path) -> None:
    monkeypatch.setattr("app.llm.base.time.sleep", lambda seconds: None)
    _use_provider(monkeypatch, _failing_openai())

    response = TestClient(app).post(path, json={"message": "Học phí bao nhiêu?"})

    answer = response.json()["answer"] if path == "/api/chat" else _events(response)[-1]["answer"]
    assert answer.startswith(UNAVAILABLE_PREFIX)
    assert "Chưa cấu hình" not in answer
    assert "Học phí năm 2026 là 20 triệu đồng." in answer
