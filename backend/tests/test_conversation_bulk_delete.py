"""Test ``DELETE /api/conversations`` (student-settings, AC-05).

Xoá toàn bộ hội thoại của owner phiên hiện tại (tài khoản hoặc ẩn danh) kèm tin
nhắn; không đụng hội thoại của owner khác; cookie admin không đổi owner (giống
``GET /api/conversations``).
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db.models import Conversation, Message
from app.main import app
from tests.test_conversation_sessions import _chat, rag_mocks  # noqa: F401 (fixture)

OTHER_EMAIL = "ban@stu.ptit.edu.vn"


def _ids(test_client: TestClient) -> set[str]:
    response = test_client.get("/api/conversations")
    assert response.status_code == 200, response.text
    return {item["id"] for item in response.json()["conversations"]}


def test_deletes_all_anonymous_conversations_and_messages(api_db, rag_mocks) -> None:  # noqa: F811
    browser = TestClient(app)
    first = _chat(browser, "Học phí?").json()["conversation_id"]
    second = _chat(browser, "Lịch thi?").json()["conversation_id"]
    assert _ids(browser) == {first, second}

    response = browser.delete("/api/conversations")

    assert response.status_code == 200, response.text
    assert response.json() == {"deleted": 2}
    assert _ids(browser) == set()
    assert browser.get(f"/api/conversations/{first}").status_code == 404
    with api_db() as db:
        assert db.scalar(select(func.count(Message.id)).where(Message.conversation_id.in_([first, second]))) == 0


def test_owner_without_conversations_gets_zero(api_db) -> None:
    response = TestClient(app).delete("/api/conversations")

    assert response.status_code == 200, response.text
    assert response.json() == {"deleted": 0}


def test_does_not_touch_other_owners(api_db, rag_mocks, register_user) -> None:  # noqa: F811
    account = TestClient(app)
    register_user(account)
    account_id = _chat(account, "Điều kiện tốt nghiệp?").json()["conversation_id"]

    other_account = TestClient(app)
    register_user(other_account, email=OTHER_EMAIL)
    other_id = _chat(other_account, "Học bổng?").json()["conversation_id"]

    anonymous = TestClient(app)
    anonymous_id = _chat(anonymous, "Rèn luyện?").json()["conversation_id"]

    assert account.delete("/api/conversations").json() == {"deleted": 1}

    assert _ids(account) == set()
    assert _ids(other_account) == {other_id}
    assert _ids(anonymous) == {anonymous_id}
    with api_db() as db:
        assert db.get(Conversation, account_id) is None
        assert db.get(Conversation, other_id) is not None


def test_admin_cookie_does_not_change_owner(api_db, rag_mocks, admin_client) -> None:  # noqa: F811
    """Admin xoá toàn bộ ở trang chat chỉ xoá hội thoại của chính trình duyệt đó."""
    student = TestClient(app)
    student_id = _chat(student, "Học phần?").json()["conversation_id"]
    admin_own = _chat(admin_client, "Câu hỏi của admin").json()["conversation_id"]

    response = admin_client.delete("/api/conversations")

    assert response.status_code == 200, response.text
    assert response.json() == {"deleted": 1}
    assert _ids(student) == {student_id}
    with api_db() as db:
        assert db.get(Conversation, admin_own) is None
        assert db.get(Conversation, student_id) is not None


def test_single_delete_route_still_works(api_db, rag_mocks) -> None:  # noqa: F811
    """Route mới không đè ``DELETE /conversations/{id}``."""
    browser = TestClient(app)
    keep = _chat(browser, "Giữ lại").json()["conversation_id"]
    drop = _chat(browser, "Xoá đi").json()["conversation_id"]

    response = browser.delete(f"/api/conversations/{drop}")

    assert response.json() == {"id": drop, "deleted": True}
    assert _ids(browser) == {keep}
