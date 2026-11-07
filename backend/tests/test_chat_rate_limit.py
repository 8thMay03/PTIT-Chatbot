"""Chống lạm dụng route chat (BE-10).

- AC-01: câu hỏi dài hơn ``CHAT_MESSAGE_MAX_CHARS`` -> 422 tiếng Việt, không ghi DB.
- AC-02: hạn mức theo owner (phút/ngày) -> 429 + ``Retry-After``; hết thời gian chờ lại gửi được.
- AC-03: hạn mức theo IP không lách được bằng đổi cookie; IP theo ``TRUSTED_PROXY_IPS``.
- AC-04: mỗi owner một lượt đang chạy; khóa nhả sau done/error/ngắt/404 và hết TTL.
- AC-05: ngưỡng đọc từ settings; ``CHAT_RATE_LIMIT_ENABLED=false`` chỉ còn kiểm tra độ dài.
- Q-03: admin không bị hạn mức phút/ngày nhưng vẫn chỉ một lượt mỗi lần.

Retrieval/LLM được thay bằng bản giả; DB là SQLite tạm (``api_db``). Đồng hồ của limiter
được thay bằng đồng hồ giả để không phải chờ thật.
"""

from __future__ import annotations

import json
import secrets
import threading

import anyio
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from starlette.requests import Request

from app.api import routes
from app.api.schemas import ChatRequest
from app.core import rate_limit
from app.core.auth import anon_owner_key
from app.core.config import PROJECT_ROOT, Settings, settings
from app.db.models import Conversation, Message
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
CHAT_PATHS = ("/api/chat", "/api/chat/stream")


class FakeClock:
    def __init__(self, now: float = 1000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def clock(monkeypatch) -> FakeClock:
    fake = FakeClock()
    monkeypatch.setattr(rate_limit.chat_owner_limiter, "clock", fake)
    monkeypatch.setattr(rate_limit.chat_ip_limiter, "clock", fake)
    monkeypatch.setattr(rate_limit.chat_active_slots, "clock", fake)
    return fake


@pytest.fixture
def calls(monkeypatch) -> dict[str, int]:
    """Retrieval/LLM giả cho cả hai route; đếm số lần được gọi."""
    counter = {"answer": 0, "retrieve": 0, "llm": 0}

    def fake_answer(message, top_k, history, budget=None):
        counter["answer"] += 1
        return {"answer": "Trả lời", "sources": [], "contexts": [], "retrieval_debug": {}}

    def fake_iter_retrieve(message, top_k, history=None, budget=None):
        counter["retrieve"] += 1
        yield {"step": "retrieve", "detail": {}, "elapsed_ms": 1}
        yield {"result": dict(RETRIEVAL_RESULT)}

    def fake_stream(question, contexts, history=None, provider=None, budget=None):
        counter["llm"] += 1
        yield StreamDelta(kind=CONTENT_DELTA, text="Học phí PTIT [1]")

    monkeypatch.setattr(routes.rag_chain, "answer", fake_answer)
    monkeypatch.setattr(routes.rag_chain, "iter_retrieve_context", fake_iter_retrieve)
    monkeypatch.setattr(routes, "stream_answer_deltas_with_llm", fake_stream)
    return counter


def _new_sid() -> str:
    return secrets.token_urlsafe(32)


def _client(sid: str | None = None, **kwargs) -> TestClient:
    test_client = TestClient(app, **kwargs)
    test_client.cookies.set("ptit_sid", sid or _new_sid(), path="/api")
    return test_client


def _post(test_client: TestClient, path: str, message: str = "Học phí?", **extra):
    return test_client.post(path, json={"message": message, **extra})


def _parse_ndjson(body: str) -> list[dict]:
    return [json.loads(line) for line in body.splitlines() if line.strip()]


def _counts(factory) -> tuple[int, int]:
    with factory() as session:
        return (
            session.scalar(select(func.count()).select_from(Conversation)),
            session.scalar(select(func.count()).select_from(Message)),
        )


def _assert_rate_limited(response, retry_after: int | None = None) -> int:
    assert response.status_code == 429, response.text
    assert response.json()["detail"].startswith("Bạn đã gửi quá nhiều câu hỏi.")
    value = int(response.headers["Retry-After"])
    assert value >= 1
    if retry_after is not None:
        assert value == retry_after
    assert f"{value} giây" in response.json()["detail"]
    return value


# ==========================================
# AC-01: giới hạn độ dài
# ==========================================
@pytest.mark.parametrize("path", CHAT_PATHS)
def test_length_over_limit_is_rejected_without_side_effects(api_db, calls, path) -> None:
    response = _post(_client(), path, "a" * (settings.chat_message_max_chars + 1))

    assert response.status_code == 422
    [error] = response.json()["detail"]
    assert error["loc"] == ["body", "message"]
    assert error["msg"] == "Câu hỏi quá dài (tối đa 2000 ký tự)."
    assert _counts(api_db) == (0, 0)
    assert calls == {"answer": 0, "retrieve": 0, "llm": 0}
    # Request bị 422 không trừ hạn mức.
    assert rate_limit.chat_ip_limiter.tracked_keys() == 0


@pytest.mark.parametrize("path", CHAT_PATHS)
def test_length_exactly_at_limit_is_accepted(api_db, calls, path) -> None:
    response = _post(_client(), path, "a" * settings.chat_message_max_chars)

    assert response.status_code == 200, response.text
    assert _counts(api_db) == (1, 2)


def test_length_counts_whitespace(api_db, calls) -> None:
    response = _post(_client(), "/api/chat", "a" + " " * settings.chat_message_max_chars)

    assert response.status_code == 422


def test_length_limit_follows_settings(api_db, calls, monkeypatch) -> None:
    monkeypatch.setattr(settings, "chat_message_max_chars", 5)

    assert _post(_client(), "/api/chat", "12345").status_code == 200
    response = _post(_client(), "/api/chat", "123456")
    assert response.status_code == 422
    assert response.json()["detail"][0]["msg"] == "Câu hỏi quá dài (tối đa 5 ký tự)."


# ==========================================
# AC-02: hạn mức theo owner
# ==========================================
def test_owner_minute_limit_returns_429_then_recovers(api_db, calls, clock) -> None:
    owner = _client()
    for index in range(10):
        path = CHAT_PATHS[index % 2]
        assert _post(owner, path).status_code == 200, index

    for path in CHAT_PATHS:
        _assert_rate_limited(_post(owner, path), retry_after=6)
    # Phiên khác cùng IP không bị ảnh hưởng.
    assert _post(_client(), "/api/chat").status_code == 200

    conversations_before = _counts(api_db)
    _assert_rate_limited(_post(owner, "/api/chat"))
    assert _counts(api_db) == conversations_before

    clock.advance(6)
    assert _post(owner, "/api/chat/stream").status_code == 200
    _assert_rate_limited(_post(owner, "/api/chat"))


def test_owner_day_limit_returns_429_then_recovers(api_db, calls, clock, monkeypatch) -> None:
    monkeypatch.setattr(settings, "chat_rate_owner_per_minute", 0)
    monkeypatch.setattr(settings, "chat_rate_owner_per_day", 3)
    owner = _client()
    for _ in range(3):
        assert _post(owner, "/api/chat").status_code == 200

    retry_after = _assert_rate_limited(_post(owner, "/api/chat"), retry_after=86400 // 3)

    clock.advance(retry_after - 1)
    _assert_rate_limited(_post(owner, "/api/chat"))
    clock.advance(1)
    assert _post(owner, "/api/chat").status_code == 200


def test_owner_limit_follows_account_not_cookie(api_db, calls, register_user, monkeypatch) -> None:
    monkeypatch.setattr(settings, "chat_rate_owner_per_minute", 2)
    student = _client()
    register_user(student)
    assert _post(student, "/api/chat").status_code == 200
    assert _post(student, "/api/chat").status_code == 200

    # Đổi ptit_sid nhưng vẫn đăng nhập cùng tài khoản: owner là user:<id>, vẫn bị chặn.
    student.cookies.set("ptit_sid", _new_sid(), path="/api")
    _assert_rate_limited(_post(student, "/api/chat"))


def test_other_session_conversation_404_counts_toward_owner_quota(api_db, calls, monkeypatch) -> None:
    monkeypatch.setattr(settings, "chat_rate_owner_per_minute", 2)
    conversation_id = _post(_client(), "/api/chat").json()["conversation_id"]
    intruder = _client()

    for path in CHAT_PATHS:
        assert _post(intruder, path, conversation_id=conversation_id).status_code == 404
    _assert_rate_limited(_post(intruder, "/api/chat", conversation_id=conversation_id))


# ==========================================
# AC-03: hạn mức theo IP
# ==========================================
def test_ip_limit_cannot_be_bypassed_by_rotating_cookie(api_db, calls, clock, monkeypatch) -> None:
    monkeypatch.setattr(settings, "chat_rate_ip_per_minute", 3)
    for index in range(3):
        assert _post(_client(), CHAT_PATHS[index % 2]).status_code == 200

    for path in CHAT_PATHS:
        _assert_rate_limited(_post(_client(), path), retry_after=20)
    # Không cookie nào (phiên mới được cấp mỗi lần) cũng bị chặn.
    _assert_rate_limited(TestClient(app).post("/api/chat", json={"message": "Học phí?"}))
    assert _counts(api_db) == (3, 6)

    # IP khác không bị ảnh hưởng.
    assert _post(_client(client=("203.0.113.9", 50000)), "/api/chat").status_code == 200

    clock.advance(20)
    assert _post(_client(), "/api/chat").status_code == 200


def test_ip_day_limit(api_db, calls, monkeypatch) -> None:
    monkeypatch.setattr(settings, "chat_rate_ip_per_minute", 0)
    monkeypatch.setattr(settings, "chat_rate_ip_per_day", 2)
    for _ in range(2):
        assert _post(_client(), "/api/chat").status_code == 200

    _assert_rate_limited(_post(_client(), "/api/chat"), retry_after=43200)


def test_forwarded_for_is_used_only_from_trusted_proxy(api_db, calls, monkeypatch) -> None:
    monkeypatch.setattr(settings, "chat_rate_ip_per_minute", 1)

    # Không có proxy tin cậy: X-Forwarded-For bị bỏ qua, mọi request chung IP kết nối.
    untrusted = {"X-Forwarded-For": "198.51.100.1"}
    assert _client(headers=untrusted).post("/api/chat", json={"message": "Học phí?"}).status_code == 200
    spoofed = {"X-Forwarded-For": "198.51.100.2"}
    _assert_rate_limited(_client(headers=spoofed).post("/api/chat", json={"message": "Học phí?"}))

    # Request tới từ proxy tin cậy: mỗi client thật (X-Forwarded-For) có hạn mức riêng.
    monkeypatch.setattr(settings, "trusted_proxy_ips", "testclient")
    for client_ip in ("198.51.100.1", "198.51.100.2"):
        proxied = _client(headers={"X-Forwarded-For": client_ip})
        assert proxied.post("/api/chat", json={"message": "Học phí?"}).status_code == 200
        _assert_rate_limited(proxied.post("/api/chat", json={"message": "Học phí?"}))


# ==========================================
# AC-04: một lượt chat đang chạy mỗi owner
# ==========================================
def _assert_busy(response) -> None:
    assert response.status_code == 429, response.text
    assert response.json()["detail"] == routes.CHAT_BUSY_DETAIL
    assert response.headers["Retry-After"] == "1"


def _start_blocked_stream(monkeypatch, sid: str, make_client=None):
    """Mở một stream có LLM chờ ``release``; trả (release, thread, kết quả)."""
    make_client = make_client or _client
    llm_started = threading.Event()
    release = threading.Event()
    result: dict = {}

    def blocking_stream(question, contexts, history=None, provider=None, budget=None):
        llm_started.set()
        assert release.wait(10)
        yield StreamDelta(kind=CONTENT_DELTA, text="Học phí PTIT [1]")

    monkeypatch.setattr(routes, "stream_answer_deltas_with_llm", blocking_stream)

    def run() -> None:
        response = make_client(sid).post("/api/chat/stream", json={"message": "Câu đầu?"})
        result["status"] = response.status_code
        result["events"] = _parse_ndjson(response.text)

    thread = threading.Thread(target=run)
    thread.start()
    assert llm_started.wait(10)
    return release, thread, result


def test_second_turn_while_streaming_is_rejected_then_released(api_db, calls, monkeypatch) -> None:
    sid = _new_sid()
    release, thread, result = _start_blocked_stream(monkeypatch, sid)
    try:
        counts_while_streaming = _counts(api_db)
        for path in CHAT_PATHS:
            _assert_busy(_post(_client(sid), path))
        assert _counts(api_db) == counts_while_streaming
        # Owner khác vẫn chat được trong lúc đó.
        assert _post(_client(), "/api/chat").status_code == 200
    finally:
        release.set()
        thread.join(10)

    assert result["status"] == 200
    assert result["events"][-1]["type"] == "done"
    assert not rate_limit.chat_active_slots.is_active(anon_owner_key(sid))
    assert _post(_client(sid), "/api/chat/stream").status_code == 200


def test_busy_rejection_does_not_consume_owner_quota(api_db, calls, monkeypatch) -> None:
    monkeypatch.setattr(settings, "chat_rate_owner_per_minute", 2)
    sid = _new_sid()
    release, thread, _ = _start_blocked_stream(monkeypatch, sid)
    try:
        for _ in range(5):
            _assert_busy(_post(_client(sid), "/api/chat"))
    finally:
        release.set()
        thread.join(10)

    # Lượt stream đã dùng 1/2: còn đúng một lượt.
    assert _post(_client(sid), "/api/chat").status_code == 200
    _assert_rate_limited(_post(_client(sid), "/api/chat"))


def test_slot_released_after_sync_chat_error(api_db, monkeypatch) -> None:
    def failing_answer(message, top_k, history, budget=None):
        raise RuntimeError("llm down")

    monkeypatch.setattr(routes.rag_chain, "answer", failing_answer)
    sid = _new_sid()
    owner = TestClient(app, raise_server_exceptions=False)
    owner.cookies.set("ptit_sid", sid, path="/api")

    assert _post(owner, "/api/chat").status_code == 503
    assert not rate_limit.chat_active_slots.is_active(anon_owner_key(sid))


def test_slot_released_after_llm_stream_error(api_db, calls, monkeypatch) -> None:
    def failing_stream(question, contexts, history=None, provider=None, budget=None):
        yield StreamDelta(kind=CONTENT_DELTA, text="Học ")
        raise LLMStreamError("provider dropped")

    monkeypatch.setattr(routes, "stream_answer_deltas_with_llm", failing_stream)
    sid = _new_sid()

    events = _parse_ndjson(_post(_client(sid), "/api/chat/stream").text)

    assert events[-1]["type"] == "error"
    assert not rate_limit.chat_active_slots.is_active(anon_owner_key(sid))


def test_slot_released_after_retrieval_error(api_db, monkeypatch) -> None:
    def failing_retrieve(message, top_k, history=None, budget=None):
        raise RuntimeError("vector db down")
        yield  # pragma: no cover

    monkeypatch.setattr(routes.rag_chain, "iter_retrieve_context", failing_retrieve)
    sid = _new_sid()

    events = _parse_ndjson(_post(_client(sid), "/api/chat/stream").text)

    assert events[-1]["type"] == "error"
    assert not rate_limit.chat_active_slots.is_active(anon_owner_key(sid))


def test_slot_released_after_unexpected_stream_failure(api_db, calls, monkeypatch) -> None:
    def broken_stream(question, contexts, history=None, provider=None, budget=None):
        raise ValueError("unexpected")
        yield  # pragma: no cover

    monkeypatch.setattr(routes, "stream_answer_deltas_with_llm", broken_stream)
    sid = _new_sid()
    owner = TestClient(app, raise_server_exceptions=False)
    owner.cookies.set("ptit_sid", sid, path="/api")

    owner.post("/api/chat/stream", json={"message": "Học phí?"})

    assert not rate_limit.chat_active_slots.is_active(anon_owner_key(sid))


def test_slot_released_after_404_in_phase_a(api_db, calls) -> None:
    conversation_id = _post(_client(), "/api/chat").json()["conversation_id"]
    sid = _new_sid()

    for path in CHAT_PATHS:
        assert _post(_client(sid), path, conversation_id=conversation_id).status_code == 404
        assert not rate_limit.chat_active_slots.is_active(anon_owner_key(sid))
    assert _post(_client(sid), "/api/chat").status_code == 200


async def _asgi_stream(sid: str, disconnect_when, send_error: BaseException | None = None) -> list[dict]:
    """POST /api/chat/stream qua ASGI; ``http.disconnect`` khi ``disconnect_when(events)``.

    ``send_error``: ``send`` ném lỗi ngay ở ``http.response.start`` (body chưa chạy).
    """
    body = json.dumps({"message": "Học phí?"}).encode("utf-8")
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
        if send_error is not None and message["type"] == "http.response.start":
            raise send_error
        if message["type"] != "http.response.body":
            return
        buffer += message.get("body", b"")
        while b"\n" in buffer:
            line, buffer = buffer.split(b"\n", 1)
            if line.strip():
                events.append(json.loads(line))
        if disconnect_when(events):
            disconnect.set()

    scope = {
        "type": "http",
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


async def test_slot_released_after_client_disconnect(api_db, calls, monkeypatch) -> None:
    llm_closed = threading.Event()

    def slow_stream(question, contexts, history=None, provider=None, budget=None):
        try:
            for part in ["Học ", "phí ", "PTIT ", "là ", "bao ", "nhiêu"]:
                yield StreamDelta(kind=CONTENT_DELTA, text=part)
                llm_closed.wait(0.2)
        finally:
            llm_closed.set()

    monkeypatch.setattr(routes, "stream_answer_deltas_with_llm", slow_stream)
    sid = _new_sid()

    events = await _asgi_stream(sid, lambda evts: any(e["type"] == "delta" for e in evts))

    assert events[-1]["type"] != "done"
    assert llm_closed.is_set()
    assert not rate_limit.chat_active_slots.is_active(anon_owner_key(sid))


async def test_slot_released_when_body_never_starts(api_db, calls) -> None:
    sid = _new_sid()

    with pytest.raises(OSError):
        await _asgi_stream(sid, lambda evts: False, send_error=OSError("socket closed"))

    # event_stream chưa từng chạy (không có finally nào của nó chạy): on_close nhả khóa.
    assert calls["retrieve"] == 0
    assert not rate_limit.chat_active_slots.is_active(anon_owner_key(sid))


def _http_request(sid: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/chat/stream",
            "headers": [(b"cookie", f"ptit_sid={sid}".encode())],
            "client": ("testclient", 50000),
        }
    )


def test_slot_expires_when_response_never_runs(api_db, calls, clock) -> None:
    sid = _new_sid()

    # Response được tạo nhưng không bao giờ được gửi (worker lỗi trước khi chạy response).
    routes.chat_stream(ChatRequest(message="Học phí?"), http_request=_http_request(sid), session_factory=api_db)
    _assert_busy(_post(_client(sid), "/api/chat"))

    clock.advance(settings.chat_active_slot_ttl_seconds)
    assert _post(_client(sid), "/api/chat").status_code == 200


# ==========================================
# AC-05: cấu hình
# ==========================================
def test_disabled_rate_limit_keeps_only_length_check(api_db, calls, monkeypatch) -> None:
    monkeypatch.setattr(settings, "chat_rate_limit_enabled", False)
    monkeypatch.setattr(settings, "chat_rate_owner_per_minute", 1)
    monkeypatch.setattr(settings, "chat_rate_ip_per_minute", 1)
    owner = _client()

    for index in range(5):
        assert _post(owner, CHAT_PATHS[index % 2]).status_code == 200
    assert _post(owner, "/api/chat", "a" * (settings.chat_message_max_chars + 1)).status_code == 422

    # Không khóa lượt: lượt thứ hai trong lúc stream đầu đang chạy vẫn được nhận.
    sid = _new_sid()
    release, thread, _ = _start_blocked_stream(monkeypatch, sid)
    try:
        assert _post(_client(sid), "/api/chat").status_code == 200
    finally:
        release.set()
        thread.join(10)
    assert rate_limit.chat_owner_limiter.tracked_keys() == 0
    assert rate_limit.chat_ip_limiter.tracked_keys() == 0


def test_env_example_lists_every_chat_limit_setting_with_its_default() -> None:
    fields = {
        info.alias: name
        for name, info in Settings.model_fields.items()
        if name.startswith("chat_") and info.alias
    }
    assert len(fields) == 8
    lines = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
    values = dict(line.split("=", 1) for line in lines if line.split("=", 1)[0] in fields)

    assert set(values) == set(fields)
    parsed = Settings(_env_file=None, **values)
    for alias, name in fields.items():
        assert getattr(parsed, name) == Settings.model_fields[name].default, alias


# ==========================================
# Q-03: admin
# ==========================================
def test_admin_skips_quotas_but_keeps_single_turn(api_db, calls, login_admin, monkeypatch) -> None:
    monkeypatch.setattr(settings, "chat_rate_owner_per_minute", 1)
    monkeypatch.setattr(settings, "chat_rate_ip_per_minute", 1)
    sid = _new_sid()
    admin = login_admin(_client(sid))

    for index in range(4):
        assert _post(admin, CHAT_PATHS[index % 2]).status_code == 200

    release, thread, _ = _start_blocked_stream(
        monkeypatch, sid, make_client=lambda stream_sid: login_admin(_client(stream_sid))
    )
    try:
        _assert_busy(_post(admin, "/api/chat"))
    finally:
        release.set()
        thread.join(10)

    # Request admin không trừ hạn mức IP; khách cùng IP vẫn còn lượt của mình.
    assert _post(_client(), "/api/chat").status_code == 200
    _assert_rate_limited(_post(_client(), "/api/chat"))
