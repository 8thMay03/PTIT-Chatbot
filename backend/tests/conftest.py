"""Fixtures dùng chung cho test backend (FE-06).

- ``admin_credentials``: bật mật khẩu admin trên settings CHỈ trong phạm vi test
  (monkeypatch tự phục hồi); test không dùng fixture này vẫn thấy hành vi fail
  closed mặc định.
- ``login_admin``: đăng nhập admin cho một TestClient bất kỳ.
- ``client``: TestClient cookie jar riêng, chưa đăng nhập.
- ``admin_client``: TestClient đã có cookie phiên admin hợp lệ.
- ``api_db``: thay dependency ``get_session`` bằng SQLite tạm trong ``tmp_path``
  để test hội thoại không ghi vào DB dev.
- ``register_user`` / ``login_user``: đăng ký/đăng nhập tài khoản người dùng cho một
  TestClient (landing-user-auth); cần ``api_db``.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core import auth
from app.core.config import settings
from app.db import get_session
from app.db.models import Base
from app.main import app

ADMIN_TEST_PASSWORD = "unit-test-admin-password"
ADMIN_TEST_SECRET = "unit-test-session-secret"
USER_TEST_PASSWORD = "mat-khau-sinh-vien-1"


@pytest.fixture(autouse=True)
def _isolated_admin_login_state():
    """Mỗi test bắt đầu/kết thúc với bộ đếm chặn dò mật khẩu sạch (admin và người dùng)."""
    auth.reset_login_attempts()
    yield
    auth.reset_login_attempts()


@pytest.fixture
def admin_credentials(monkeypatch):
    monkeypatch.setattr(settings, "admin_password", ADMIN_TEST_PASSWORD)
    monkeypatch.setattr(settings, "admin_session_secret", ADMIN_TEST_SECRET)


@pytest.fixture
def login_admin(admin_credentials):
    """Đăng nhập admin trên TestClient được truyền vào rồi trả lại client đó."""

    def _login(test_client: TestClient) -> TestClient:
        response = test_client.post(
            "/api/admin/login", json={"password": ADMIN_TEST_PASSWORD}
        )
        assert response.status_code == 200, response.text
        return test_client

    return _login


@pytest.fixture
def client():
    """TestClient với cookie jar riêng, chưa đăng nhập admin."""
    return TestClient(app)


@pytest.fixture
def admin_client(login_admin):
    """TestClient đã đăng nhập admin (cookie ptit_admin hợp lệ)."""
    return login_admin(TestClient(app))


@pytest.fixture
def api_db(tmp_path):
    """Chạy app với get_session trỏ sang SQLite tạm; trả về session factory để seed dữ liệu."""
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'api-test.db').as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    test_session_factory = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )

    def override_get_session():
        with test_session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    try:
        yield test_session_factory
    finally:
        app.dependency_overrides.pop(get_session, None)
        engine.dispose()


@pytest.fixture
def register_user(api_db):
    """Đăng ký tài khoản trên TestClient được truyền vào; trả response JSON."""

    def _register(
        test_client: TestClient,
        email: str = "sv@stu.ptit.edu.vn",
        password: str = USER_TEST_PASSWORD,
        full_name: str = "Nguyễn Văn A",
    ) -> dict:
        response = test_client.post(
            "/api/auth/register",
            json={"email": email, "password": password, "full_name": full_name},
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _register


@pytest.fixture
def login_user(api_db):
    """Đăng nhập tài khoản có sẵn trên TestClient được truyền vào; trả response JSON."""

    def _login(
        test_client: TestClient,
        email: str = "sv@stu.ptit.edu.vn",
        password: str = USER_TEST_PASSWORD,
    ) -> dict:
        response = test_client.post("/api/auth/login", json={"email": email, "password": password})
        assert response.status_code == 200, response.text
        return response.json()

    return _login
