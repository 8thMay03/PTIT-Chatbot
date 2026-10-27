"""Test tài khoản người dùng: đăng ký, đăng nhập, phiên, chặn dò (landing-user-auth, AC-02/AC-03).

Bao gồm: chuẩn hoá email và 409 khi trùng; 422 theo trường (định dạng email, mật
khẩu ngắn, tên trống, ngoài tên miền); hash scrypt có salt trong DB; 401 giống hệt
cho sai mật khẩu và email không tồn tại; 429 theo IP + email không khoá client
khác (cả khi đứng sau proxy tin cậy — rút kinh nghiệm R-01 FE-06); cookie hỏng/hết
hạn/user đã xoá coi là chưa đăng nhập; cookie người dùng không mở route admin.
"""

from __future__ import annotations

import base64
import time

import pytest
from fastapi.testclient import TestClient

from app.core import auth, user_auth
from app.core.config import settings
from app.db.models import User
from app.main import app
from tests.conftest import ADMIN_TEST_PASSWORD, USER_TEST_PASSWORD
from tests.test_admin_auth import ADMIN_ROUTE_TABLE, admin_route_mocks  # noqa: F401 (fixture)

EMAIL = "sv@stu.ptit.edu.vn"


def _register_payload(**overrides) -> dict:
    payload = {"email": EMAIL, "password": USER_TEST_PASSWORD, "full_name": "Nguyễn Văn A"}
    payload.update(overrides)
    return payload


def _error_fields(response) -> dict[str, str]:
    """{tên trường: thông điệp} từ lỗi 422 định dạng mặc định FastAPI."""
    return {item["loc"][-1]: item["msg"] for item in response.json()["detail"]}


def _set_user_cookie(test_client: TestClient, token: str) -> None:
    # Bỏ cookie server đã đặt (domain testserver.local) để chỉ còn token của test.
    test_client.cookies.delete(user_auth.USER_COOKIE_NAME)
    test_client.cookies.set(user_auth.USER_COOKIE_NAME, token, path=user_auth.USER_COOKIE_PATH)


# ==========================================
# Băm mật khẩu
# ==========================================
def test_hash_password_uses_salted_scrypt() -> None:
    first = user_auth.hash_password(USER_TEST_PASSWORD)
    second = user_auth.hash_password(USER_TEST_PASSWORD)

    assert first != second  # salt ngẫu nhiên
    scheme, n, r, p, salt, digest = first.split("$")
    assert (scheme, n, r, p) == ("scrypt", str(user_auth.SCRYPT_N), "8", "1")
    assert len(base64.urlsafe_b64decode(salt + "==")) == user_auth.SCRYPT_SALT_BYTES
    assert USER_TEST_PASSWORD not in first
    assert user_auth.verify_password(USER_TEST_PASSWORD, first)
    assert not user_auth.verify_password(USER_TEST_PASSWORD + "x", first)


@pytest.mark.parametrize(
    "stored",
    [
        None,
        "",
        "plain-text-password",
        "bcrypt$12$abc",
        "scrypt$abc$8$1$c2FsdA$aGFzaA",
        "scrypt$16384$8$1$!!!$aGFzaA",
        "scrypt$999999999$8$1$c2FsdA$aGFzaA",  # N quá lớn: từ chối thay vì treo request
        "scrypt$16384$8$1$$",
    ],
)
def test_verify_password_rejects_malformed_hash(stored) -> None:
    assert user_auth.verify_password(USER_TEST_PASSWORD, stored) is False


# ==========================================
# Đăng ký (AC-02)
# ==========================================
def test_register_creates_user_sets_cookie_and_hides_hash(api_db, client) -> None:
    response = client.post(
        "/api/auth/register",
        json=_register_payload(email="  SV.Moi@Stu.PTIT.edu.vn ", full_name="  Trần   Thị B "),
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["authenticated"] is True
    assert data["registration_enabled"] is True
    user = data["user"]
    assert set(user) == {"id", "email", "full_name", "created_at"}
    assert user["email"] == "sv.moi@stu.ptit.edu.vn"
    assert user["full_name"] == "Trần Thị B"
    assert "password" not in response.text and USER_TEST_PASSWORD not in response.text

    cookies = response.headers.get_list("set-cookie")
    user_cookie = next(c for c in cookies if c.startswith("ptit_user="))
    lowered = user_cookie.lower()
    assert "httponly" in lowered
    assert "samesite=lax" in lowered
    assert "path=/api" in lowered
    assert f"max-age={int(settings.user_session_ttl_days * 86400)}" in lowered

    # Cookie vừa cấp dùng được ngay.
    me = client.get("/api/auth/me").json()
    assert me["authenticated"] is True
    assert me["user"]["id"] == user["id"]


def test_register_stores_scrypt_hash_not_plain_password(api_db, client) -> None:
    client.post("/api/auth/register", json=_register_payload())

    with api_db() as db:
        stored = db.query(User).one()
    assert stored.email == EMAIL
    assert stored.password_hash.startswith(f"scrypt${user_auth.SCRYPT_N}$8$1$")
    salt = stored.password_hash.split("$")[4]
    assert salt
    assert USER_TEST_PASSWORD not in stored.password_hash
    assert user_auth.verify_password(USER_TEST_PASSWORD, stored.password_hash)


def test_register_duplicate_email_is_409_case_insensitive(api_db, client) -> None:
    assert client.post("/api/auth/register", json=_register_payload()).status_code == 201

    other = TestClient(app)
    response = other.post(
        "/api/auth/register", json=_register_payload(email=" SV@STU.PTIT.EDU.VN")
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Email đã được đăng ký."
    with api_db() as db:
        assert db.query(User).count() == 1


@pytest.mark.parametrize(
    ("overrides", "field", "message"),
    [
        ({"email": "khong-phai-email"}, "email", "Email không đúng định dạng."),
        ({"email": "a@b"}, "email", "Email không đúng định dạng."),
        ({"email": "a b@ptit.edu.vn"}, "email", "Email không đúng định dạng."),
        ({"password": "1234567"}, "password", "Mật khẩu phải có ít nhất 8 ký tự."),
        ({"password": "x" * 129}, "password", "Mật khẩu tối đa 128 ký tự."),
        ({"full_name": "   "}, "full_name", "Vui lòng nhập họ tên."),
        ({"full_name": "A" * 101}, "full_name", "Họ tên tối đa 100 ký tự."),
    ],
)
def test_register_invalid_input_is_422_per_field(api_db, client, overrides, field, message) -> None:
    response = client.post("/api/auth/register", json=_register_payload(**overrides))

    assert response.status_code == 422, response.text
    assert _error_fields(response)[field] == message
    assert "ptit_user" not in response.headers.get("set-cookie", "")
    with api_db() as db:
        assert db.query(User).count() == 0


def test_register_missing_fields_is_422(api_db, client) -> None:
    response = client.post("/api/auth/register", json={"email": EMAIL})
    assert response.status_code == 422
    assert {"password", "full_name"} <= set(_error_fields(response))


def test_register_respects_email_domain_allowlist(api_db, client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "user_email_domains", "stu.ptit.edu.vn, @PTIT.edu.vn")

    outside = client.post("/api/auth/register", json=_register_payload(email="sv@gmail.com"))
    assert outside.status_code == 422
    assert _error_fields(outside)["email"] == (
        "Chỉ chấp nhận email thuộc tên miền: stu.ptit.edu.vn, ptit.edu.vn."
    )
    # Tên miền con khác không được tính là khớp.
    sub = client.post("/api/auth/register", json=_register_payload(email="sv@evil.stu.ptit.edu.vn"))
    assert sub.status_code == 422

    assert client.post("/api/auth/register", json=_register_payload()).status_code == 201
    staff = TestClient(app).post(
        "/api/auth/register", json=_register_payload(email="gv@ptit.edu.vn")
    )
    assert staff.status_code == 201


def test_register_disabled_returns_503(api_db, client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "user_registration_enabled", False)

    response = client.post("/api/auth/register", json=_register_payload())
    assert response.status_code == 503
    assert client.get("/api/auth/me").json()["registration_enabled"] is False


def test_register_duplicate_probing_is_throttled_per_ip(api_db, client) -> None:
    client.post("/api/auth/register", json=_register_payload())
    prober = TestClient(app)
    for _ in range(settings.user_auth_max_failures):
        assert prober.post("/api/auth/register", json=_register_payload()).status_code == 409

    blocked = prober.post(
        "/api/auth/register", json=_register_payload(email="email-moi@stu.ptit.edu.vn")
    )
    assert blocked.status_code == 429
    assert "thử lại" in blocked.json()["detail"]


# ==========================================
# Đăng nhập (AC-03)
# ==========================================
def test_login_success_sets_cookie_and_updates_last_login(api_db, register_user) -> None:
    register_user(TestClient(app))
    other_device = TestClient(app)

    response = other_device.post(
        "/api/auth/login", json={"email": " SV@stu.ptit.edu.vn ", "password": USER_TEST_PASSWORD}
    )

    assert response.status_code == 200, response.text
    assert response.json()["authenticated"] is True
    assert response.json()["user"]["email"] == EMAIL
    assert "ptit_user=" in response.headers["set-cookie"]
    assert other_device.get("/api/auth/me").json()["user"]["email"] == EMAIL
    with api_db() as db:
        assert db.query(User).one().last_login_at is not None


def test_wrong_password_and_unknown_email_get_identical_401(api_db, register_user) -> None:
    register_user(TestClient(app))

    wrong_password = TestClient(app).post(
        "/api/auth/login", json={"email": EMAIL, "password": "sai-mat-khau-roi"}
    )
    unknown_email = TestClient(app).post(
        "/api/auth/login", json={"email": "khong-ton-tai@stu.ptit.edu.vn", "password": "sai-mat-khau-roi"}
    )

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json() == {"detail": "Email hoặc mật khẩu không đúng."}
    assert "ptit_user" not in wrong_password.headers.get("set-cookie", "")


def test_unknown_email_still_runs_a_password_hash(api_db, client, monkeypatch) -> None:
    """Email không tồn tại vẫn băm mật khẩu để thời gian phản hồi không lộ email."""
    calls = []
    real_verify = user_auth.verify_password
    monkeypatch.setattr(
        user_auth, "verify_password", lambda pw, h: calls.append(h) or real_verify(pw, h)
    )

    response = client.post("/api/auth/login", json={"email": "ai@ptit.edu.vn", "password": "abcdefgh"})

    assert response.status_code == 401
    assert len(calls) == 1 and calls[0].startswith("scrypt$")


def test_login_bruteforce_is_throttled_without_locking_others(api_db, register_user) -> None:
    register_user(TestClient(app))
    register_user(TestClient(app), email="ban@stu.ptit.edu.vn")
    attacker = TestClient(app)

    for _ in range(settings.user_auth_max_failures):
        response = attacker.post("/api/auth/login", json={"email": EMAIL, "password": "sai-mat-khau"})
        assert response.status_code == 401

    # Cùng IP + email: kể cả mật khẩu đúng cũng 429 trong cửa sổ.
    blocked = attacker.post("/api/auth/login", json={"email": EMAIL, "password": USER_TEST_PASSWORD})
    assert blocked.status_code == 429
    assert "thử lại" in blocked.json()["detail"]

    # Tài khoản khác trên cùng IP không bị khoá.
    other_account = attacker.post(
        "/api/auth/login", json={"email": "ban@stu.ptit.edu.vn", "password": USER_TEST_PASSWORD}
    )
    assert other_account.status_code == 200


def test_login_throttle_behind_trusted_proxy_uses_real_client_ip(
    api_db, register_user, monkeypatch
) -> None:
    """R-01 FE-06: sau proxy tin cậy, client khác (IP thật khác) vẫn đăng nhập được."""
    monkeypatch.setattr(settings, "trusted_proxy_ips", "testclient,10.0.0.0/8")
    register_user(TestClient(app))

    attacker = TestClient(app, headers={"X-Forwarded-For": "203.0.113.66"})
    for _ in range(settings.user_auth_max_failures):
        assert (
            attacker.post("/api/auth/login", json={"email": EMAIL, "password": "sai"}).status_code
            == 401
        )
    assert (
        attacker.post(
            "/api/auth/login", json={"email": EMAIL, "password": USER_TEST_PASSWORD}
        ).status_code
        == 429
    )

    # Chủ tài khoản ở IP khác (qua hai lớp proxy tin cậy) không bị ảnh hưởng.
    owner = TestClient(app, headers={"X-Forwarded-For": "198.51.100.7, 10.1.2.3"})
    response = owner.post("/api/auth/login", json={"email": EMAIL, "password": USER_TEST_PASSWORD})
    assert response.status_code == 200, response.text


def test_forwarded_for_is_ignored_from_untrusted_peer(api_db, register_user, monkeypatch) -> None:
    """Gọi thẳng backend không giả được IP: XFF bị bỏ qua khi peer không phải proxy tin cậy."""
    monkeypatch.setattr(settings, "trusted_proxy_ips", "10.0.0.1")
    register_user(TestClient(app))

    for index in range(settings.user_auth_max_failures):
        spoofing = TestClient(app, headers={"X-Forwarded-For": f"203.0.113.{index}"})
        assert (
            spoofing.post("/api/auth/login", json={"email": EMAIL, "password": "sai"}).status_code
            == 401
        )
    fresh_spoof = TestClient(app, headers={"X-Forwarded-For": "198.51.100.200"})
    response = fresh_spoof.post(
        "/api/auth/login", json={"email": EMAIL, "password": USER_TEST_PASSWORD}
    )
    assert response.status_code == 429


def test_successful_login_clears_failure_counter(api_db, register_user) -> None:
    register_user(TestClient(app))
    device = TestClient(app)
    for _ in range(settings.user_auth_max_failures - 1):
        device.post("/api/auth/login", json={"email": EMAIL, "password": "sai"})
    assert (
        device.post("/api/auth/login", json={"email": EMAIL, "password": USER_TEST_PASSWORD}).status_code
        == 200
    )
    assert device.post("/api/auth/login", json={"email": EMAIL, "password": "sai"}).status_code == 401


# ==========================================
# Phiên: me / logout / cookie hỏng
# ==========================================
def test_me_without_cookie_is_unauthenticated(api_db, client) -> None:
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json() == {"authenticated": False, "user": None, "registration_enabled": True}


@pytest.mark.parametrize("cookie_mode", ["garbage", "tampered", "expired", "deleted_user", "admin_token"])
def test_me_treats_invalid_cookie_as_logged_out(
    api_db, register_user, admin_credentials, cookie_mode
) -> None:
    test_client = TestClient(app)
    user_id = register_user(test_client)["user"]["id"]
    if cookie_mode == "garbage":
        _set_user_cookie(test_client, "khong.phai.token")
    elif cookie_mode == "tampered":
        token = user_auth.sign_user_token(user_id, time.time() + 3600)
        head, signature = token.rsplit(".", 1)
        _set_user_cookie(test_client, f"{head}.{'A' if signature[0] != 'A' else 'B'}{signature[1:]}")
    elif cookie_mode == "expired":
        _set_user_cookie(test_client, user_auth.sign_user_token(user_id, time.time() - 60))
    elif cookie_mode == "deleted_user":
        with api_db() as db:
            db.delete(db.get(User, user_id))
            db.commit()
    elif cookie_mode == "admin_token":
        token, _ = auth.issue_admin_session()
        _set_user_cookie(test_client, token)

    response = test_client.get("/api/auth/me")

    assert response.status_code == 200
    assert response.json()["authenticated"] is False
    assert response.json()["user"] is None


def test_token_for_other_user_id_cannot_be_forged(api_db, register_user) -> None:
    """Đổi user_id trong token giữ nguyên chữ ký → chữ ký sai → chưa đăng nhập."""
    test_client = TestClient(app)
    user_id = register_user(test_client)["user"]["id"]
    victim_id = register_user(TestClient(app), email="nan-nhan@stu.ptit.edu.vn")["user"]["id"]
    token = user_auth.sign_user_token(user_id, time.time() + 3600)
    forged = token.replace(user_id, victim_id)
    _set_user_cookie(test_client, forged)

    assert test_client.get("/api/auth/me").json()["authenticated"] is False


def test_logout_clears_user_cookie_and_rotates_anonymous_session(api_db, register_user) -> None:
    test_client = TestClient(app)
    register_user(test_client)
    old_sid = test_client.cookies.get("ptit_sid")
    assert old_sid

    response = test_client.post("/api/auth/logout")

    assert response.status_code == 200
    assert response.json()["authenticated"] is False
    cookies = response.headers.get_list("set-cookie")
    cleared = next(c for c in cookies if c.startswith("ptit_user="))
    assert "max-age=0" in cleared.lower()
    assert any(c.startswith("ptit_sid=") for c in cookies)
    assert test_client.cookies.get("ptit_sid") != old_sid
    assert test_client.get("/api/auth/me").json()["authenticated"] is False


def test_logout_without_session_still_succeeds(api_db, client) -> None:
    response = client.post("/api/auth/logout")
    assert response.status_code == 200
    assert response.json()["authenticated"] is False


# ==========================================
# Cookie người dùng không leo thang thành admin
# ==========================================
@pytest.mark.parametrize(("method", "path", "kwargs"), ADMIN_ROUTE_TABLE)
def test_user_cookie_cannot_open_admin_routes(
    method, path, kwargs, admin_credentials, admin_route_mocks, api_db, register_user  # noqa: F811
) -> None:
    test_client = TestClient(app)
    register_user(test_client)
    # Thêm cả cookie ptit_admin chứa token người dùng: khóa ký khác nhau nên vẫn bị từ chối.
    test_client.cookies.set(
        auth.ADMIN_COOKIE_NAME,
        test_client.cookies.get(user_auth.USER_COOKIE_NAME),
        path=auth.ADMIN_COOKIE_PATH,
    )

    response = test_client.request(method, path, **kwargs)

    assert response.status_code == 401, (method, path, response.text)
    assert response.json()["detail"] == auth.ADMIN_401_DETAIL


def test_admin_login_throttle_behind_trusted_proxy_does_not_lock_other_clients(
    admin_credentials, monkeypatch
) -> None:
    """R-01 FE-06: client ẩn danh gửi sai 5 lần không khoá admin ở IP khác qua proxy."""
    monkeypatch.setattr(settings, "trusted_proxy_ips", "testclient")
    attacker = TestClient(app, headers={"X-Forwarded-For": "10.0.0.66"})
    for _ in range(auth.LOGIN_MAX_FAILURES):
        assert attacker.post("/api/admin/login", json={"password": "sai"}).status_code == 401
    assert (
        attacker.post("/api/admin/login", json={"password": ADMIN_TEST_PASSWORD}).status_code == 429
    )

    admin = TestClient(app, headers={"X-Forwarded-For": "10.0.0.1"})
    assert admin.post("/api/admin/login", json={"password": ADMIN_TEST_PASSWORD}).status_code == 200
