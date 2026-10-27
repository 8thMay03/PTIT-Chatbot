"""Test phiên ẩn danh và quyền sở hữu hội thoại (FE-06, AC-03).

Hai client với cookie jar riêng (hai "trình duyệt") không thấy/sửa/xoá/nối tiếp
hội thoại của nhau; user_id client tự gửi bị bỏ qua; `/chat/stream` gắn Set-Cookie
trực tiếp trên response stream; admin xem được mọi hội thoại qua
`/api/admin/conversations*`.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.api import routes
from app.db.models import Conversation, Message
from app.llm import CONTENT_DELTA, StreamDelta
from app.main import app


@pytest.fixture
def rag_mocks(monkeypatch):
    """Mock LLM/retrieval để test hội thoại không cần model thật."""

    def fake_answer(message, top_k, history):
        return {
            "answer": f"Trả lời cho: {message}",
            "sources": [],
            "contexts": [],
            "retrieval_debug": {"rewritten_query": message, "strong_context": False},
        }

    monkeypatch.setattr(routes.rag_chain, "answer", fake_answer)

    def fake_iter_retrieve(message, top_k, history=None):
        yield {
            "result": {
                "contexts": [
                    {
                        "source_name": "handbook.md",
                        "heading": "Học phí",
                        "section_path": "Học phí",
                        "text": "Nội dung học phí.",
                    }
                ],
                "retrieval_debug": {"rewritten_query": message, "strong_context": True},
                "strong_context": True,
                "guardrail_allowed": True,
            }
        }

    monkeypatch.setattr(routes.rag_chain, "iter_retrieve_context", fake_iter_retrieve)

    def fake_stream(question, contexts, history=None, provider=None):
        return iter([StreamDelta(kind=CONTENT_DELTA, text=f"Trả lời stream cho: {question}")])

    monkeypatch.setattr(routes, "stream_answer_deltas_with_llm", fake_stream)


def _chat(test_client: TestClient, message: str = "Học phí thế nào?", **extra):
    payload = {"message": message, **extra}
    return test_client.post("/api/chat", json=payload)


def _stream(test_client: TestClient, message: str = "Học phí thế nào?", **extra):
    payload = {"message": message, **extra}
    return test_client.post("/api/chat/stream", json=payload)


def _set_sid(test_client: TestClient, sid: str) -> None:
    test_client.cookies.set("ptit_sid", sid, path="/api")


# ==========================================
# Cấp cookie phiên ẩn danh
# ==========================================
def test_chat_issues_ptit_sid_cookie_for_new_session(client, rag_mocks) -> None:
    response = _chat(client)

    assert response.status_code == 200, response.text
    cookie = response.headers["set-cookie"]
    cookie_lower = cookie.lower()
    assert "ptit_sid=" in cookie
    assert "httponly" in cookie_lower
    assert "samesite=lax" in cookie_lower
    assert "path=/api" in cookie_lower

    # Request thứ hai mang cookie cũ: không cấp sid mới nữa.
    response = _chat(client, message="Câu thứ hai")
    assert response.status_code == 200
    assert "ptit_sid" not in response.headers.get("set-cookie", "")


def test_chat_stream_sets_cookie_directly_on_stream_response(client, rag_mocks) -> None:
    """StreamingResponse không đi qua response inject: Set-Cookie phải gắn thẳng."""
    response = _stream(client)

    assert response.status_code == 200, response.text
    cookie = response.headers["set-cookie"]
    assert "ptit_sid=" in cookie
    assert "httponly" in cookie.lower()
    assert "samesite=lax" in cookie.lower()
    # Stream vẫn giữ hợp đồng NDJSON.
    lines = [line for line in response.text.splitlines() if line.strip()]
    assert lines
    first_event = json.loads(lines[0])
    assert first_event["type"] == "start"
    assert any(json.loads(line)["type"] == "done" for line in lines)

    # Cookie stream được dùng cho request chat thường tiếp theo.
    listing = client.get("/api/conversations")
    assert listing.status_code == 200
    assert listing.json()["total"] == 1


def test_malformed_sid_is_replaced_with_new_session(client, rag_mocks) -> None:
    _set_sid(client, "!" * 40)  # đúng độ dài nhưng ký tự ngoài bảng chữ của sid
    listing = client.get("/api/conversations")

    assert listing.status_code == 200
    # Giá trị sai định dạng bị cấp sid mới.
    assert "ptit_sid=" in listing.headers["set-cookie"]


# ==========================================
# Isolation giữa hai phiên
# ==========================================
def test_conversations_are_scoped_to_session(api_db, rag_mocks) -> None:
    alice = TestClient(app)
    bob = TestClient(app)

    response = _chat(alice, "Học phí đại học?")
    assert response.status_code == 200
    conversation_id = response.json()["conversation_id"]

    # Alice thấy hội thoại của mình, Bob thì không.
    alice_list = alice.get("/api/conversations")
    assert alice_list.status_code == 200
    assert alice_list.json()["total"] == 1
    assert alice_list.json()["conversations"][0]["id"] == conversation_id

    bob_list = bob.get("/api/conversations")
    assert bob_list.status_code == 200
    assert bob_list.json()["total"] == 0
    assert bob_list.json()["conversations"] == []


def test_cross_session_read_update_delete_return_404(api_db, rag_mocks) -> None:
    alice = TestClient(app)
    bob = TestClient(app)

    conversation_id = _chat(alice, "Điều kiện tốt nghiệp?").json()["conversation_id"]

    assert bob.get(f"/api/conversations/{conversation_id}").status_code == 404
    assert (
        bob.patch(f"/api/conversations/{conversation_id}", json={"title": "Đổi tên"}).status_code
        == 404
    )
    assert bob.delete(f"/api/conversations/{conversation_id}").status_code == 404

    # Hội thoại của Alice vẫn nguyên vẹn sau các attempt của Bob.
    detail = alice.get(f"/api/conversations/{conversation_id}")
    assert detail.status_code == 200
    assert detail.json()["message_count"] == 2
    assert detail.json()["title"] != "Đổi tên"

    # Alice tự đổi tên/xoá được của mình.
    assert (
        alice.patch(f"/api/conversations/{conversation_id}", json={"title": "Câu hỏi học phí"}).status_code
        == 200
    )


def test_chat_cannot_append_to_foreign_conversation(api_db, rag_mocks) -> None:
    alice = TestClient(app)
    bob = TestClient(app)

    conversation_id = _chat(alice, "Cảnh báo học tập?").json()["conversation_id"]

    bob_response = _chat(bob, "Tiếp tục hội thoại của người khác", conversation_id=conversation_id)
    assert bob_response.status_code == 404
    assert bob_response.json()["detail"] == "Không tìm thấy hội thoại."

    # Không có tin nhắn nào được nối thêm vào hội thoại của Alice.
    detail = alice.get(f"/api/conversations/{conversation_id}")
    assert detail.json()["message_count"] == 2


def test_chat_stream_cannot_append_to_foreign_conversation(api_db, rag_mocks) -> None:
    alice = TestClient(app)
    bob = TestClient(app)

    conversation_id = _chat(alice, "Khen thưởng?").json()["conversation_id"]

    bob_response = _stream(bob, "Nối tiếp bằng stream", conversation_id=conversation_id)
    assert bob_response.status_code == 404
    assert bob_response.json()["detail"] == "Không tìm thấy hội thoại."

    detail = alice.get(f"/api/conversations/{conversation_id}")
    assert detail.json()["message_count"] == 2


def test_chat_stream_appends_to_own_conversation(api_db, rag_mocks) -> None:
    alice = TestClient(app)

    conversation_id = _chat(alice, "Câu đầu?").json()["conversation_id"]
    response = _stream(alice, "Câu thứ hai?", conversation_id=conversation_id)

    assert response.status_code == 200, response.text
    detail = alice.get(f"/api/conversations/{conversation_id}")
    assert detail.json()["message_count"] == 4


def test_client_supplied_user_id_is_ignored(api_db, rag_mocks) -> None:
    alice = TestClient(app)
    bob = TestClient(app)

    # Alice khai user_id giả "victim" — bị bỏ qua hoàn toàn.
    response = _chat(alice, "user_id giả", user_id="victim-user-id")
    assert response.status_code == 200
    conversation_id = response.json()["conversation_id"]

    # Bob không thấy hội thoại dù Alice khai user_id tùy ý.
    assert bob.get("/api/conversations").json()["total"] == 0
    assert bob.get(f"/api/conversations/{conversation_id}").status_code == 404

    # Owner thực là anon key của phiên Alice, không phải giá trị client gửi.
    listing = alice.get("/api/conversations")
    assert listing.json()["total"] == 1


def test_student_listing_filters_by_session_even_with_admin_cookie(
    api_db, rag_mocks, admin_client
) -> None:
    """Sidebar chat của admin chỉ hiện hội thoại của chính trình duyệt đó."""
    alice = TestClient(app)
    conversation_id = _chat(alice, "Học phần?").json()["conversation_id"]

    admin_listing = admin_client.get("/api/conversations")
    assert admin_listing.status_code == 200
    assert admin_listing.json()["total"] == 0

    admin_conversations = admin_client.get("/api/admin/conversations")
    assert admin_conversations.json()["total"] >= 1
    assert any(
        item["id"] == conversation_id for item in admin_conversations.json()["conversations"]
    )


# ==========================================
# Admin xem mọi hội thoại
# ==========================================
def test_admin_sees_all_conversations_with_owner(api_db, rag_mocks, admin_client) -> None:
    alice = TestClient(app)
    bob = TestClient(app)
    alice_id = _chat(alice, "Câu của Alice?").json()["conversation_id"]
    bob_id = _chat(bob, "Câu của Bob?").json()["conversation_id"]

    listing = admin_client.get("/api/admin/conversations")
    assert listing.status_code == 200
    payload = listing.json()
    assert payload["total"] >= 2
    ids = {item["id"] for item in payload["conversations"]}
    assert {alice_id, bob_id} <= ids
    # Mỗi item kèm owner key (không phải sid gốc).
    for item in payload["conversations"]:
        assert item["owner"].startswith("anon:")

    detail = admin_client.get(f"/api/admin/conversations/{alice_id}")
    assert detail.status_code == 200
    assert detail.json()["owner"].startswith("anon:")
    assert detail.json()["message_count"] == 2

    assert admin_client.get("/api/admin/conversations/conv-khong-ton-tai").status_code == 404

    # Lọc theo owner.
    alice_owner = next(
        item["owner"] for item in payload["conversations"] if item["id"] == alice_id
    )
    filtered = admin_client.get("/api/admin/conversations", params={"owner": alice_owner})
    assert filtered.json()["total"] == 1
    assert filtered.json()["conversations"][0]["id"] == alice_id


def test_legacy_unowned_conversations_hidden_from_students_visible_to_admin(
    api_db, rag_mocks, admin_client
) -> None:
    """Hội thoại cũ (user_id rỗng) không hiện với sinh viên; admin vẫn xem được."""
    with api_db() as db:
        db.add(Conversation(id="legacy-conv", user_id=None, title="Hội thoại cũ"))
        db.add(
            Message(
                id="legacy-msg",
                conversation_id="legacy-conv",
                role="user",
                content="Câu hỏi cũ",
            )
        )
        db.commit()

    student = TestClient(app)
    listing = student.get("/api/conversations")
    assert listing.status_code == 200
    assert all(item["id"] != "legacy-conv" for item in listing.json()["conversations"])
    assert student.get("/api/conversations/legacy-conv").status_code == 404

    admin_listing = admin_client.get("/api/admin/conversations")
    assert any(
        item["id"] == "legacy-conv" for item in admin_listing.json()["conversations"]
    )
    admin_detail = admin_client.get("/api/admin/conversations/legacy-conv")
    assert admin_detail.status_code == 200
    assert admin_detail.json()["owner"] is None
