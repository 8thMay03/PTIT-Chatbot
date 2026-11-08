"""Vòng đời session DB của route chat (BE-11).

- AC-01: trong lúc retrieval/LLM chạy, route chat (stream và non-stream) không giữ
  connection nào của engine.
- AC-02 (thu nhỏ): pool 2 + 0, ``pool_timeout`` 1s, 10 stream đồng thời không cạn pool.
- AC-03: client ngắt giữa stream -> câu hỏi + phần đã sinh được lưu, ``interrupted``.
- AC-04: ngắt trước delta / retrieval lỗi -> câu hỏi vẫn được lưu.
- AC-05: ``/api/chat`` lỗi khi trả lời -> câu hỏi vẫn được lưu, mã lỗi HTTP giữ nguyên.
- Q-01: câu trả lời bị ngắt không vào history của lượt sau.

Ngắt client được mô phỏng bằng cách gọi ASGI app trực tiếp: ``receive`` trả
``http.disconnect`` sau khi nhận đủ event (TestClient đọc hết body nên không ngắt được).
"""

from __future__ import annotations

import gc
import json
import secrets
import threading
import time

import anyio
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.orm import sessionmaker

from app.api import routes
from app.core.auth import anon_owner_key
from app.db import get_session, get_session_factory
from app.db.models import Base, Conversation, Message
from app.llm import CONTENT_DELTA, LLMStreamError, StreamDelta
from app.main import app

RETRIEVAL_RESULT = {
    "contexts": [
        {
            "source_name": "handbook.md",
            "heading": "Học phí",
            "section_path": "Học phí",
            "text": "Nội dung học phí.",
        }
    ],
    "retrieval_debug": {"rewritten_query": "học phí", "strong_context": True},
    "strong_context": True,
    "guardrail_allowed": True,
}


class _CheckoutCounter:
    """Đếm connection đang được mượn khỏi pool của engine test."""

    def __init__(self, engine) -> None:
        self._lock = threading.Lock()
        self.checked_out = 0
        event.listen(engine, "checkout", self._on_checkout)
        event.listen(engine, "checkin", self._on_checkin)

    def _on_checkout(self, *args) -> None:
        with self._lock:
            self.checked_out += 1

    def _on_checkin(self, *args) -> None:
        with self._lock:
            self.checked_out -= 1


def _make_db(tmp_path, **engine_options):
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'chat-lifecycle.db').as_posix()}",
        connect_args={"check_same_thread": False, "timeout": 10},
        **engine_options,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    counter = _CheckoutCounter(engine)

    def override_get_session():
        with factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_session_factory] = lambda: factory
    return engine, factory, counter


@pytest.fixture
def chat_db(tmp_path):
    engine, factory, counter = _make_db(tmp_path)
    try:
        yield factory, counter
    finally:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_session_factory, None)
        engine.dispose()


@pytest.fixture
def small_pool_db(tmp_path):
    engine, factory, counter = _make_db(tmp_path, pool_size=2, max_overflow=0, pool_timeout=1)
    try:
        yield factory, counter
    finally:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_session_factory, None)
        engine.dispose()


@pytest.fixture
def fake_retrieval(monkeypatch):
    def fake_iter_retrieve(message, top_k, history=None, budget=None):
        yield {"step": "retrieve", "detail": {}, "elapsed_ms": 1}
        yield {"result": dict(RETRIEVAL_RESULT)}

    monkeypatch.setattr(routes.rag_chain, "iter_retrieve_context", fake_iter_retrieve)


def _new_sid() -> str:
    return secrets.token_urlsafe(32)


def _client_with_sid(sid: str, **kwargs) -> TestClient:
    test_client = TestClient(app, **kwargs)
    test_client.cookies.set("ptit_sid", sid, path="/api")
    return test_client


def _parse_ndjson(body: str) -> list[dict]:
    return [json.loads(line) for line in body.splitlines() if line.strip()]


def _messages(factory, conversation_id: str) -> list[Message]:
    with factory() as session:
        return list(
            session.scalars(
                select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at)
            )
        )


async def _stream_then_disconnect(
    payload: dict, sid: str, disconnect_when, block_send_s: float = 0.0
) -> list[dict]:
    """POST /api/chat/stream qua ASGI; gửi ``http.disconnect`` khi ``disconnect_when(events)``.

    ``block_send_s`` > 0: ``send`` chặn thêm sau khi báo ngắt (client chậm/backpressure)
    để lệnh hủy rơi vào ``await send`` thay vì bên trong body iterator.
    """
    body = json.dumps(payload).encode("utf-8")
    events: list[dict] = []
    buffer = b""
    disconnect = anyio.Event()
    request_sent = False

    async def receive():
        nonlocal request_sent
        if not request_sent:
            request_sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        await disconnect.wait()
        return {"type": "http.disconnect"}

    async def send(message):
        nonlocal buffer
        if message["type"] != "http.response.body":
            return
        buffer += message.get("body", b"")
        while b"\n" in buffer:
            line, buffer = buffer.split(b"\n", 1)
            if line.strip():
                events.append(json.loads(line))
        if disconnect_when(events):
            disconnect.set()
            if block_send_s:
                await anyio.sleep(block_send_s)

    scope = {
        "type": "http",
        # Giống uvicorn (HTTP): spec 2.3 -> Starlette nghe http.disconnect và hủy stream.
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/chat/stream",
        "raw_path": b"/api/chat/stream",
        "root_path": "",
        "query_string": b"",
        "headers": [
            (b"host", b"testserver"),
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode()),
            (b"cookie", f"ptit_sid={sid}".encode()),
        ],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }
    with anyio.fail_after(10):
        await app(scope, receive, send)
    return events


# ==========================================
# AC-01: không giữ connection khi retrieval/LLM chạy
# ==========================================
def test_chat_stream_holds_no_connection_while_llm_streams(chat_db, monkeypatch) -> None:
    factory, counter = chat_db
    observed: list[tuple[str, int]] = []

    def fake_iter_retrieve(message, top_k, history=None, budget=None):
        observed.append(("retrieval", counter.checked_out))
        yield {"step": "retrieve", "detail": {}, "elapsed_ms": 1}
        observed.append(("retrieval", counter.checked_out))
        yield {"result": dict(RETRIEVAL_RESULT)}

    def fake_stream(question, contexts, history=None, provider=None, budget=None):
        for text_part in ["Học ", "phí ", "PTIT [1]"]:
            observed.append(("llm", counter.checked_out))
            yield StreamDelta(kind=CONTENT_DELTA, text=text_part)

    monkeypatch.setattr(routes.rag_chain, "iter_retrieve_context", fake_iter_retrieve)
    monkeypatch.setattr(routes, "stream_answer_deltas_with_llm", fake_stream)

    response = _client_with_sid(_new_sid()).post("/api/chat/stream", json={"message": "Học phí?"})

    assert response.status_code == 200
    events = _parse_ndjson(response.text)
    assert events[-1]["type"] == "done"
    assert [stage for stage, _ in observed] == ["retrieval", "retrieval", "llm", "llm", "llm"]
    assert all(count == 0 for _, count in observed), observed
    assert counter.checked_out == 0

    user, assistant = _messages(factory, events[0]["conversation_id"])
    assert (user.role, user.content) == ("user", "Học phí?")
    assert user.message_metadata == {"retrieval_debug": RETRIEVAL_RESULT["retrieval_debug"]}
    assert (assistant.role, assistant.content) == ("assistant", "Học phí PTIT [1]")
    assert "interrupted" not in assistant.message_metadata


def test_chat_sync_holds_no_connection_while_answering(chat_db, monkeypatch) -> None:
    factory, counter = chat_db
    observed: list[int] = []

    def fake_answer(message, top_k, history, budget=None):
        observed.append(counter.checked_out)
        return {
            "answer": "Trả lời [1]",
            "sources": [],
            "contexts": [],
            "retrieval_debug": {"rewritten_query": message},
        }

    monkeypatch.setattr(routes.rag_chain, "answer", fake_answer)

    response = TestClient(app).post("/api/chat", json={"message": "Học phí?"})

    assert response.status_code == 200
    assert observed == [0]
    assert counter.checked_out == 0
    # Phiên mới vẫn được cấp cookie như trước.
    assert "ptit_sid" in response.cookies
    user, assistant = _messages(factory, response.json()["conversation_id"])
    assert user.message_metadata == {"retrieval_debug": {"rewritten_query": "Học phí?"}}
    assert assistant.content == "Trả lời [1]"


# ==========================================
# AC-02 (thu nhỏ): nhiều stream đồng thời không cạn pool nhỏ
# ==========================================
def test_concurrent_streams_do_not_exhaust_small_pool(small_pool_db, fake_retrieval, monkeypatch) -> None:
    factory, counter = small_pool_db
    stream_count = 10

    def slow_stream(question, contexts, history=None, provider=None, budget=None):
        yield StreamDelta(kind=CONTENT_DELTA, text="Học phí ")
        time.sleep(2)
        yield StreamDelta(kind=CONTENT_DELTA, text="PTIT [1]")

    monkeypatch.setattr(routes, "stream_answer_deltas_with_llm", slow_stream)

    results: list[tuple[int, list[dict]]] = []
    errors: list[BaseException] = []
    lock = threading.Lock()

    def run_stream(index: int) -> None:
        try:
            response = _client_with_sid(_new_sid()).post(
                "/api/chat/stream", json={"message": f"Câu hỏi {index}?"}
            )
            with lock:
                results.append((response.status_code, _parse_ndjson(response.text)))
        except BaseException as exc:  # pragma: no cover - lỗi sẽ được assert bên dưới
            with lock:
                errors.append(exc)

    threads = [threading.Thread(target=run_stream, args=(i,)) for i in range(stream_count)]
    for thread in threads:
        thread.start()
    # Trong lúc các stream đang chờ LLM, route khác vẫn mượn được connection ngay.
    time.sleep(1)
    started = time.perf_counter()
    with factory() as session:
        assert session.execute(text("SELECT 1")).scalar() == 1
    assert time.perf_counter() - started < 1
    for thread in threads:
        thread.join(timeout=30)

    assert errors == []
    assert len(results) == stream_count
    for status_code, events in results:
        assert status_code == 200
        assert events[-1]["type"] == "done", events
    assert counter.checked_out == 0
    with factory() as session:
        conversations = list(session.scalars(select(Conversation)))
        assert len(conversations) == stream_count
        for conversation in conversations:
            roles = [m.role for m in _messages(factory, conversation.id)]
            assert roles == ["user", "assistant"]


# ==========================================
# AC-03 / Q-04: client ngắt giữa stream
# ==========================================
async def test_interrupted_stream_saves_partial_answer(chat_db, fake_retrieval, monkeypatch) -> None:
    factory, counter = chat_db
    produced: list[str] = []
    llm_closed = threading.Event()
    parts = ["Học ", "phí ", "PTIT ", "là ", "bao ", "nhiêu"]

    def slow_stream(question, contexts, history=None, provider=None, budget=None):
        try:
            for text_part in parts:
                produced.append(text_part)
                yield StreamDelta(kind=CONTENT_DELTA, text=text_part)
                time.sleep(0.2)
        finally:
            llm_closed.set()

    monkeypatch.setattr(routes, "stream_answer_deltas_with_llm", slow_stream)
    sid = _new_sid()

    events = await _stream_then_disconnect(
        {"message": "Học phí?"},
        sid,
        disconnect_when=lambda evs: sum(e["type"] == "delta" for e in evs) >= 2,
    )

    assert [e["type"] for e in events if e["type"] in {"done", "error"}] == []
    conversation_id = events[0]["conversation_id"]
    # Q-04: LLM bị đóng ngay, không sinh tiếp tới hết.
    assert llm_closed.is_set()
    assert len(produced) < len(parts)
    assert counter.checked_out == 0

    detail = _client_with_sid(sid).get(f"/api/conversations/{conversation_id}")
    assert detail.status_code == 200
    messages = detail.json()["messages"]
    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert messages[0]["content"] == "Học phí?"
    assert messages[1]["content"].startswith("Học phí")
    # FE-15: chi tiết hội thoại cho biết câu trả lời bị dừng.
    assert (messages[0]["interrupted"], messages[0]["error"]) == (False, None)
    assert (messages[1]["interrupted"], messages[1]["error"]) == (True, None)

    user, assistant = _messages(factory, conversation_id)
    assert assistant.message_metadata["interrupted"] is True
    assert assistant.content == "".join(produced).strip()
    assert user.message_metadata == {"retrieval_debug": RETRIEVAL_RESULT["retrieval_debug"]}


async def test_disconnect_during_send_saves_without_gc(chat_db, fake_retrieval, monkeypatch) -> None:
    """R-05: hủy rơi vào `await send` -> generator vẫn được đóng ngay, không chờ GC."""
    factory, counter = chat_db
    llm_closed = threading.Event()

    def slow_stream(question, contexts, history=None, provider=None, budget=None):
        try:
            for text_part in ["Học ", "phí ", "PTIT ", "là ", "bao ", "nhiêu"]:
                yield StreamDelta(kind=CONTENT_DELTA, text=text_part)
                time.sleep(0.05)
        finally:
            llm_closed.set()

    monkeypatch.setattr(routes, "stream_answer_deltas_with_llm", slow_stream)
    sid = _new_sid()

    gc_was_enabled = gc.isenabled()
    gc.disable()
    try:
        events = await _stream_then_disconnect(
            {"message": "Học phí?"},
            sid,
            disconnect_when=lambda evs: sum(e["type"] == "delta" for e in evs) >= 2,
            block_send_s=0.5,
        )
        # Kiểm tra ngay khi request kết thúc, trước mọi lần GC.
        assert llm_closed.is_set()
        assert counter.checked_out == 0
        user, assistant = _messages(factory, events[0]["conversation_id"])
    finally:
        if gc_was_enabled:
            gc.enable()

    assert user.content == "Học phí?"
    assert assistant.message_metadata["interrupted"] is True
    assert assistant.content.startswith("Học phí")


async def test_llm_stream_error_is_saved_before_error_event(chat_db, fake_retrieval, monkeypatch) -> None:
    """R-06: client ngắt ngay khi nhận event `error` -> vẫn lưu lỗi `llm_stream`, không phải `interrupted`."""
    factory, _ = chat_db

    def failing_stream(question, contexts, history=None, provider=None, budget=None):
        yield StreamDelta(kind=CONTENT_DELTA, text="Học phí ")
        raise LLMStreamError("LLM streaming failed: boom")

    monkeypatch.setattr(routes, "stream_answer_deltas_with_llm", failing_stream)

    events = await _stream_then_disconnect(
        {"message": "Học phí?"},
        _new_sid(),
        disconnect_when=lambda evs: any(e["type"] == "error" for e in evs),
        block_send_s=0.5,
    )

    request_id = events[-1]["request_id"]
    assert events[-1] == {
        "type": "error",
        "message": routes.CHAT_LLM_STREAM_ERROR_DETAIL.format(request_id=request_id),
        "request_id": request_id,
    }
    _, assistant = _messages(factory, events[0]["conversation_id"])
    assert assistant.content == "Học phí"
    assert assistant.message_metadata["error"] == {
        "type": "llm_stream",
        "request_id": request_id,
        "error_class": "LLMStreamError",
    }
    assert "interrupted" not in assistant.message_metadata


async def test_interrupted_answer_is_excluded_from_next_turn_history(chat_db, fake_retrieval, monkeypatch) -> None:
    factory, _ = chat_db
    monkeypatch.setattr(routes.settings, "conversation_memory_enabled", True)

    def slow_stream(question, contexts, history=None, provider=None, budget=None):
        for text_part in ["Câu ", "trả ", "lời ", "dở ", "dang"]:
            yield StreamDelta(kind=CONTENT_DELTA, text=text_part)
            time.sleep(0.2)

    monkeypatch.setattr(routes, "stream_answer_deltas_with_llm", slow_stream)
    sid = _new_sid()
    events = await _stream_then_disconnect(
        {"message": "Câu hỏi đầu?"},
        sid,
        disconnect_when=lambda evs: any(e["type"] == "delta" for e in evs),
    )
    conversation_id = events[0]["conversation_id"]

    captured_history: list[list[dict]] = []

    def fake_answer(message, top_k, history, budget=None):
        captured_history.append(history)
        return {"answer": "Trả lời", "sources": [], "contexts": [], "retrieval_debug": {}}

    monkeypatch.setattr(routes.rag_chain, "answer", fake_answer)

    def post_followup() -> int:
        return _client_with_sid(sid).post(
            "/api/chat", json={"message": "Câu hỏi sau?", "conversation_id": conversation_id}
        ).status_code

    assert await anyio.to_thread.run_sync(post_followup) == 200

    assert captured_history == [[{"role": "user", "content": "Câu hỏi đầu?"}]]
    roles = [m.role for m in _messages(factory, conversation_id)]
    assert roles == ["user", "assistant", "user", "assistant"]


# ==========================================
# AC-04: ngắt trước delta / retrieval lỗi
# ==========================================
async def test_disconnect_before_delta_keeps_question(chat_db, monkeypatch) -> None:
    factory, counter = chat_db
    llm_calls: list[str] = []

    def slow_retrieve(message, top_k, history=None, budget=None):
        yield {"step": "query_rewrite", "detail": {}, "elapsed_ms": 1}
        time.sleep(0.3)
        yield {"step": "retrieve", "detail": {}, "elapsed_ms": 300}
        time.sleep(0.3)
        yield {"result": dict(RETRIEVAL_RESULT)}

    def fake_stream(question, contexts, history=None, provider=None, budget=None):
        llm_calls.append(question)
        yield StreamDelta(kind=CONTENT_DELTA, text="không được gọi")

    monkeypatch.setattr(routes.rag_chain, "iter_retrieve_context", slow_retrieve)
    monkeypatch.setattr(routes, "stream_answer_deltas_with_llm", fake_stream)
    sid = _new_sid()

    events = await _stream_then_disconnect(
        {"message": "Học phí?"},
        sid,
        disconnect_when=lambda evs: any(e["type"] == "step" for e in evs),
    )

    assert not any(e["type"] == "delta" for e in events)
    assert llm_calls == []
    assert counter.checked_out == 0
    user, assistant = _messages(factory, events[0]["conversation_id"])
    assert (user.role, user.content) == ("user", "Học phí?")
    # Retrieval chưa xong: chưa có retrieval_debug.
    assert user.message_metadata == {}
    assert (assistant.role, assistant.content) == ("assistant", "")
    assert assistant.message_metadata["interrupted"] is True
    restored = _client_with_sid(sid).get(f"/api/conversations/{events[0]['conversation_id']}").json()
    assert [(m["content"], m["interrupted"]) for m in restored["messages"]] == [("Học phí?", False), ("", True)]


def test_retrieval_error_keeps_question_and_records_error(chat_db, monkeypatch) -> None:
    factory, _ = chat_db

    def failing_retrieve(message, top_k, history=None, budget=None):
        yield {"step": "query_rewrite", "detail": {}, "elapsed_ms": 1}
        raise RuntimeError("vector store down")

    monkeypatch.setattr(routes.rag_chain, "iter_retrieve_context", failing_retrieve)
    sid = _new_sid()

    response = _client_with_sid(sid).post("/api/chat/stream", json={"message": "Học phí?"})

    events = _parse_ndjson(response.text)
    assert [e["type"] for e in events] == ["start", "step", "error"]
    request_id = events[-1]["request_id"]
    assert response.headers["X-Request-ID"] == request_id
    assert events[-1]["message"] == routes.CHAT_INTERNAL_ERROR_DETAIL.format(request_id=request_id)
    assert "vector store down" not in response.text
    user, assistant = _messages(factory, events[0]["conversation_id"])
    assert user.content == "Học phí?"
    assert assistant.content == ""
    assert assistant.message_metadata["error"] == {
        "type": "retrieval",
        "request_id": request_id,
        "error_class": "RuntimeError",
    }
    assert "interrupted" not in assistant.message_metadata
    # FE-15: mở lại hội thoại thấy lỗi + mã tham chiếu, không lộ tên lớp exception.
    detail = _client_with_sid(sid).get(f"/api/conversations/{events[0]['conversation_id']}")
    restored = detail.json()["messages"][1]
    assert restored["error"] == {"type": "retrieval", "request_id": request_id}
    assert restored["interrupted"] is False
    assert "error_class" not in detail.text
    assert "RuntimeError" not in detail.text


def test_empty_error_answer_is_excluded_from_next_turn_history(chat_db, monkeypatch) -> None:
    """R-07: câu trả lời rỗng của lượt lỗi không vào history (câu hỏi vẫn giữ).

    Hiện do ``limit_history`` bỏ tin nhắn rỗng; test giữ hành vi này khi lượt lỗi
    bắt đầu lưu assistant rỗng (Q-03).
    """
    factory, _ = chat_db
    monkeypatch.setattr(routes.settings, "conversation_memory_enabled", True)

    def failing_retrieve(message, top_k, history=None, budget=None):
        raise RuntimeError("vector store down")
        yield  # pragma: no cover - biến hàm thành generator

    monkeypatch.setattr(routes.rag_chain, "iter_retrieve_context", failing_retrieve)
    sid = _new_sid()
    events = _parse_ndjson(
        _client_with_sid(sid).post("/api/chat/stream", json={"message": "Câu hỏi lỗi?"}).text
    )
    assert events[-1]["type"] == "error"
    conversation_id = events[0]["conversation_id"]

    captured_history: list[list[dict]] = []

    def fake_answer(message, top_k, history, budget=None):
        captured_history.append(history)
        return {"answer": "Trả lời", "sources": [], "contexts": [], "retrieval_debug": {}}

    monkeypatch.setattr(routes.rag_chain, "answer", fake_answer)
    response = _client_with_sid(sid).post(
        "/api/chat", json={"message": "Câu hỏi sau?", "conversation_id": conversation_id}
    )

    assert response.status_code == 200
    assert captured_history == [[{"role": "user", "content": "Câu hỏi lỗi?"}]]


# ==========================================
# AC-05: /api/chat lỗi khi trả lời
# ==========================================
def test_chat_sync_answer_error_keeps_question_and_status(chat_db, monkeypatch) -> None:
    factory, _ = chat_db

    def failing_answer(message, top_k, history, budget=None):
        raise RuntimeError("retrieval exploded")

    monkeypatch.setattr(routes.rag_chain, "answer", failing_answer)

    response = TestClient(app, raise_server_exceptions=False).post("/api/chat", json={"message": "Học phí?"})

    # BE-12 (Q-03): 503 với thông điệp chung + mã tham chiếu thay vì 500.
    assert response.status_code == 503
    request_id = response.headers["X-Request-ID"]
    assert response.json() == {"detail": routes.CHAT_INTERNAL_ERROR_DETAIL.format(request_id=request_id)}
    with factory() as session:
        (conversation,) = list(session.scalars(select(Conversation)))
    user, assistant = _messages(factory, conversation.id)
    assert user.content == "Học phí?"
    assert assistant.content == ""
    assert assistant.message_metadata["error"] == {
        "type": "answer",
        "request_id": request_id,
        "error_class": "RuntimeError",
    }


def test_chat_rejects_other_session_conversation_without_writing(chat_db, monkeypatch) -> None:
    factory, _ = chat_db
    monkeypatch.setattr(
        routes.rag_chain,
        "answer",
        lambda message, top_k, history, budget=None: {"answer": "Trả lời", "sources": [], "contexts": [], "retrieval_debug": {}},
    )
    owner = _client_with_sid(_new_sid())
    conversation_id = owner.post("/api/chat", json={"message": "Câu hỏi?"}).json()["conversation_id"]

    intruder = _client_with_sid(_new_sid())
    for path in ("/api/chat", "/api/chat/stream"):
        response = intruder.post(path, json={"message": "Xen vào", "conversation_id": conversation_id})
        assert response.status_code == 404
    assert len(_messages(factory, conversation_id)) == 2


# ==========================================
# Pha (c) lỗi DB: log, không làm hỏng stream
# ==========================================
def test_stream_logs_answer_save_failure(chat_db, fake_retrieval, monkeypatch, caplog) -> None:
    factory, counter = chat_db
    monkeypatch.setattr(
        routes,
        "stream_answer_deltas_with_llm",
        lambda question, contexts, history=None, provider=None, budget=None: iter([StreamDelta(kind=CONTENT_DELTA, text="Trả lời")]),
    )
    original_add_message = routes.add_message

    def flaky_add_message(session, conversation_id, role, content, metadata=None):
        if role == "assistant":
            raise RuntimeError("db write failed")
        return original_add_message(session, conversation_id, role, content, metadata=metadata)

    monkeypatch.setattr(routes, "add_message", flaky_add_message)

    with caplog.at_level("ERROR", logger="app.api.routes"):
        response = _client_with_sid(_new_sid()).post("/api/chat/stream", json={"message": "Học phí?"})

    events = _parse_ndjson(response.text)
    assert events[-1]["type"] == "done"
    conversation_id = events[0]["conversation_id"]
    assert any(conversation_id in record.getMessage() for record in caplog.records)
    assert counter.checked_out == 0
    # Câu hỏi đã được lưu ở pha (a); câu trả lời không lưu được (đã rollback).
    assert [m.role for m in _messages(factory, conversation_id)] == ["user"]


# ==========================================
# FE-15: metadata interrupted/error trong chi tiết hội thoại
# ==========================================
def test_conversation_detail_reads_status_metadata_defensively(chat_db, admin_client) -> None:
    """Metadata thiếu hoặc sai kiểu -> mặc định; route admin trả cùng trường."""
    factory, _ = chat_db
    sid = _new_sid()
    cases = [
        (None, False, None),
        ({}, False, None),
        ({"interrupted": True}, True, None),
        ({"interrupted": "yes"}, False, None),
        (
            {"error": {"type": "llm_stream", "request_id": "abc123", "error_class": "LLMStreamError"}},
            False,
            {"type": "llm_stream", "request_id": "abc123"},
        ),
        ({"error": {"type": "internal", "request_id": 42}}, False, {"type": "internal", "request_id": None}),
        ({"error": {"request_id": "abc"}}, False, None),
        ({"error": "boom"}, False, None),
    ]
    with factory() as session:
        conversation = routes.ensure_conversation(session, None, user_id=anon_owner_key(sid))
        conversation_id = conversation.id
        for metadata, _, _ in cases:
            routes.add_message(session, conversation_id, "assistant", "", metadata=metadata)
        session.commit()

    expected = [(interrupted, error) for _, interrupted, error in cases]
    for response in (
        _client_with_sid(sid).get(f"/api/conversations/{conversation_id}"),
        admin_client.get(f"/api/admin/conversations/{conversation_id}"),
    ):
        assert response.status_code == 200, response.text
        assert [(m["interrupted"], m["error"]) for m in response.json()["messages"]] == expected
        assert "error_class" not in response.text
