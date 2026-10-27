"""Test hội thoại theo tài khoản người dùng (landing-user-auth, AC-04).

Hai client đăng nhập cùng tài khoản thấy cùng lịch sử; tài khoản khác hoặc client
ẩn danh nhận 404 và không nối tin nhắn được; hội thoại ẩn danh của trình duyệt hiện
tại chuyển sang tài khoản khi đăng ký/đăng nhập (không đụng trình duyệt khác); đăng
xuất quay về phiên ẩn danh mới; admin thấy owner ``user:<id>``.
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.db.models import Conversation, User
from app.main import app
from tests.conftest import USER_TEST_PASSWORD
from tests.test_conversation_sessions import _chat, _stream, rag_mocks  # noqa: F401 (fixture)

EMAIL = "sv@stu.ptit.edu.vn"
OTHER_EMAIL = "ban@stu.ptit.edu.vn"


def _ids(test_client: TestClient) -> set[str]:
    response = test_client.get("/api/conversations")
    assert response.status_code == 200, response.text
    return {item["id"] for item in response.json()["conversations"]}


def test_same_account_on_two_devices_sees_same_history(
    api_db, rag_mocks, register_user, login_user  # noqa: F811
) -> None:
    laptop = TestClient(app)
    phone = TestClient(app)
    register_user(laptop)
    login_user(phone)

    from_laptop = _chat(laptop, "Học phí kỳ này?").json()["conversation_id"]
    phone_response = _stream(phone, "Lịch thi?")
    assert phone_response.status_code == 200, phone_response.text
    from_phone = json.loads(phone_response.text.splitlines()[0])["conversation_id"]

    assert _ids(laptop) == _ids(phone) == {from_laptop, from_phone}
    # Nối tiếp hội thoại tạo trên thiết bị khác của cùng tài khoản.
    assert _chat(phone, "Hỏi tiếp", conversation_id=from_laptop).status_code == 200
    assert laptop.get(f"/api/conversations/{from_laptop}").json()["message_count"] == 4


def test_other_account_and_anonymous_get_404(
    api_db, rag_mocks, register_user  # noqa: F811
) -> None:
    owner = TestClient(app)
    register_user(owner)
    conversation_id = _chat(owner, "Điều kiện tốt nghiệp?").json()["conversation_id"]

    other_account = TestClient(app)
    register_user(other_account, email=OTHER_EMAIL)
    anonymous = TestClient(app)

    for intruder in (other_account, anonymous):
        assert conversation_id not in _ids(intruder)
        assert intruder.get(f"/api/conversations/{conversation_id}").status_code == 404
        assert (
            intruder.patch(f"/api/conversations/{conversation_id}", json={"title": "Đổi"}).status_code
            == 404
        )
        assert intruder.delete(f"/api/conversations/{conversation_id}").status_code == 404
        assert _chat(intruder, "Nối", conversation_id=conversation_id).status_code == 404
        assert _stream(intruder, "Nối", conversation_id=conversation_id).status_code == 404

    detail = owner.get(f"/api/conversations/{conversation_id}").json()
    assert detail["message_count"] == 2
    assert detail["title"] != "Đổi"


def test_anonymous_conversations_are_claimed_on_register(
    api_db, rag_mocks, register_user  # noqa: F811
) -> None:
    browser = TestClient(app)
    anon_id = _chat(browser, "Hỏi trước khi đăng ký").json()["conversation_id"]

    user_id = register_user(browser)["user"]["id"]

    assert _ids(browser) == {anon_id}
    with api_db() as db:
        assert db.get(Conversation, anon_id).user_id == f"user:{user_id}"
    # Thiết bị khác của cùng tài khoản cũng thấy.
    other_device = TestClient(app)
    other_device.post("/api/auth/login", json={"email": EMAIL, "password": USER_TEST_PASSWORD})
    assert _ids(other_device) == {anon_id}


def test_anonymous_conversations_are_claimed_on_login_without_touching_others(
    api_db, rag_mocks, register_user, login_user  # noqa: F811
) -> None:
    register_user(TestClient(app))
    browser = TestClient(app)
    bystander = TestClient(app)
    anon_id = _chat(browser, "Hỏi ẩn danh").json()["conversation_id"]
    bystander_id = _chat(bystander, "Hội thoại của người khác").json()["conversation_id"]

    login_user(browser)

    assert anon_id in _ids(browser)
    assert bystander_id not in _ids(browser)
    # Trình duyệt khác vẫn giữ hội thoại ẩn danh của mình.
    assert _ids(bystander) == {bystander_id}


def test_logout_returns_to_fresh_anonymous_session(
    api_db, rag_mocks, register_user, login_user  # noqa: F811
) -> None:
    browser = TestClient(app)
    register_user(browser)
    account_id = _chat(browser, "Hỏi khi đã đăng nhập").json()["conversation_id"]

    assert browser.post("/api/auth/logout").status_code == 200

    assert _ids(browser) == set()
    assert browser.get(f"/api/conversations/{account_id}").status_code == 404
    guest_id = _chat(browser, "Hỏi sau khi đăng xuất").json()["conversation_id"]
    assert _ids(browser) == {guest_id}

    # Đăng nhập lại: thấy hội thoại tài khoản và nhận hội thoại khách vừa tạo.
    login_user(browser)
    assert _ids(browser) == {account_id, guest_id}


def test_deleted_user_cookie_falls_back_to_anonymous(
    api_db, rag_mocks, register_user  # noqa: F811
) -> None:
    browser = TestClient(app)
    user_id = register_user(browser)["user"]["id"]
    account_id = _chat(browser, "Câu hỏi").json()["conversation_id"]
    with api_db() as db:
        db.delete(db.get(User, user_id))
        db.commit()

    assert browser.get("/api/conversations").status_code == 200
    assert _ids(browser) == set()
    assert browser.get(f"/api/conversations/{account_id}").status_code == 404


def test_admin_sees_account_owner_key(
    api_db, rag_mocks, register_user, admin_client  # noqa: F811
) -> None:
    browser = TestClient(app)
    user_id = register_user(browser)["user"]["id"]
    conversation_id = _chat(browser, "Câu của tài khoản").json()["conversation_id"]

    listing = admin_client.get("/api/admin/conversations", params={"owner": f"user:{user_id}"})
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert listing.json()["conversations"][0]["owner"] == f"user:{user_id}"
    detail = admin_client.get(f"/api/admin/conversations/{conversation_id}")
    assert detail.json()["owner"] == f"user:{user_id}"
