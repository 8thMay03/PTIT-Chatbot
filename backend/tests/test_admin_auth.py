"""Test xác thực admin và bảo vệ route quản trị (FE-06, AC-01).

Bao gồm: luồng đăng nhập/đăng xuất/phiên, cookie giả chữ ký hoặc hết hạn, fail
closed khi chưa cấu hình ADMIN_PASSWORD, ma trận tham số hoá trên từng route
quản trị (không cookie/sai cookie → 401; phiên hợp lệ → không 401/403), và test
quét `app.routes` đối chiếu `PUBLIC_API_ROUTES` để route mới thiếu bảo vệ làm
test đỏ.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.api import routes
from app.api.routes import PUBLIC_API_ROUTES
from app.core import auth
from app.core.config import settings
from app.ingestion.jobs import ParseJob
from app.main import app
from tests.conftest import ADMIN_TEST_PASSWORD

# (method, path, kwargs) cho mọi route quản trị. Doc id "doc-404"/job id không
# tồn tại khiến route trả 404/409 nghiệp vụ — điều quan trọng là KHÔNG phải 401.
ADMIN_ROUTE_TABLE = [
    ("GET", "/api/config", {}),
    ("PUT", "/api/config", {"json": {}}),
    ("POST", "/api/config/reset", {}),
    ("POST", "/api/config/test-llm", {"json": {"provider": "openai", "api_key": "sk-test"}}),
    ("POST", "/api/retrieval/test", {"json": {"query": "học phí"}}),
    ("POST", "/api/ingest", {}),
    ("POST", "/api/ingest/chunk", {}),
    ("GET", "/api/documents", {}),
    ("POST", "/api/documents", {"files": {"file": ("faq.md", b"# FAQ", "text/markdown")}}),
    ("GET", "/api/documents/doc-404", {}),
    ("DELETE", "/api/documents/doc-404", {}),
    ("GET", "/api/documents/doc-404/chunks", {}),
    ("GET", "/api/documents/doc-404/file", {}),
    ("GET", "/api/documents/doc-404/parsers", {}),
    ("POST", "/api/documents/doc-404/parse", {}),
    ("POST", "/api/documents/doc-404/chunk", {}),
    ("GET", "/api/documents/doc-404/markdown", {}),
    ("PUT", "/api/documents/doc-404/markdown", {"json": {"text": "# Sửa"}}),
    ("GET", "/api/parsers", {"params": {"file_name": "faq.md"}}),
    ("GET", "/api/parse-jobs", {}),
    ("GET", "/api/parse-jobs/job-404", {}),
    ("GET", "/api/admin/conversations", {}),
    ("GET", "/api/admin/conversations/conv-404", {}),
]


@pytest.fixture
def admin_route_mocks(monkeypatch):
    """Mock side-effect nặng (ingest/parse/LLM/retrieval/DB) để ma trận route chạy nhanh và an toàn."""

    def _fake_job(job_id="job-1", kind="upload", document_id=None):
        return ParseJob(
            id=job_id,
            kind=kind,
            status="queued",
            document_id=document_id,
            file_name="faq.md",
            parser_name=None,
            created_at=datetime.now(timezone.utc),
            progress=0,
            progress_message="Đang chờ trong hàng đợi",
        )

    monkeypatch.setattr(
        routes.ingestion_pipeline,
        "ingest_documents",
        lambda: {"documents": 0, "chunks": 0, "collection": "ptit"},
    )
    monkeypatch.setattr(
        routes.ingestion_pipeline,
        "chunk_documents",
        lambda: {"documents": 0, "chunks": 0, "collection": "ptit", "skipped": 0},
    )
    monkeypatch.setattr(routes.ingestion_pipeline, "chunk_document", lambda document_id: None)
    monkeypatch.setattr(
        routes.ingestion_pipeline, "delete_ingested_document", lambda document_id: None
    )
    monkeypatch.setattr(
        routes, "get_document_with_chunk_count", lambda session, document_id: None
    )
    monkeypatch.setattr(routes, "list_documents", lambda session: [])
    monkeypatch.setattr(
        routes.rag_chain,
        "retrieve_context",
        lambda query, top_k: {"contexts": [], "retrieval_debug": {}, "strong_context": False},
    )
    monkeypatch.setattr(
        routes.parse_jobs,
        "enqueue_upload",
        lambda filename, content, **options: _fake_job(),
    )
    fake_provider = SimpleNamespace(
        is_configured=lambda: True, generate=lambda messages, **kwargs: "OK PTIT"
    )
    monkeypatch.setattr(
        routes, "create_llm_provider_from_config", lambda **kwargs: fake_provider
    )
    return _fake_job


# ==========================================
# Test quét route (fail closed theo mặc định)
# ==========================================
def _iter_app_api_routes() -> list[tuple[str, str, APIRoute]]:
    """(method, path, route) của mọi route API trong app.

    FastAPI mới include router theo kiểu lazy (`_IncludedRouter` bọc
    `original_router`); bản cũ trả thẳng APIRoute trong app.routes — hỗ trợ cả hai.
    """
    found: list[tuple[str, str, APIRoute]] = []
    for route in app.routes:
        inner = getattr(route, "original_router", None)
        if inner is not None:
            for candidate in inner.routes:
                if isinstance(candidate, APIRoute):
                    for method in candidate.methods - {"HEAD", "OPTIONS"}:
                        found.append((method, f"/api{candidate.path}", candidate))
        elif isinstance(route, APIRoute) and route.path.startswith("/api/"):
            for method in route.methods - {"HEAD", "OPTIONS"}:
                found.append((method, route.path, route))
    return found


def _has_require_admin(route: APIRoute) -> bool:
    return any(
        getattr(dep, "dependency", None) is auth.require_admin
        for dep in getattr(route, "dependencies", [])
    )


def test_every_api_route_is_public_or_requires_admin() -> None:
    """Route ngoài PUBLIC_API_ROUTES buộc phải có require_admin."""
    scanned = _iter_app_api_routes()
    assert scanned, "Không quét được route nào — helper cần cập nhật theo FastAPI mới."

    unprotected = [
        (method, path)
        for method, path, route in scanned
        if (method, path) not in PUBLIC_API_ROUTES and not _has_require_admin(route)
    ]
    assert not unprotected, f"Route quản trị thiếu require_admin: {unprotected}"


def test_public_api_routes_all_exist() -> None:
    """Mọi route khai báo công khai phải tồn tại thật (chống lỗi tên đường dẫn)."""
    actual = {(method, path) for method, path, _ in _iter_app_api_routes()}
    missing = PUBLIC_API_ROUTES - actual
    assert not missing, f"PUBLIC_API_ROUTES khai báo route không tồn tại: {sorted(missing)}"


# ==========================================
# Luồng đăng nhập/đăng xuất/phiên
# ==========================================
def test_login_success_sets_http_only_cookie(admin_credentials) -> None:
    with TestClient(app) as test_client:
        response = test_client.post(
            "/api/admin/login", json={"password": ADMIN_TEST_PASSWORD}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["authenticated"] is True
    assert data["configured"] is True
    # expires_at dạng ISO 8601 có timezone.
    parsed = datetime.fromisoformat(data["expires_at"])
    assert parsed.tzinfo is not None

    cookie = response.headers["set-cookie"]
    cookie_lower = cookie.lower()
    assert "ptit_admin=" in cookie
    assert "httponly" in cookie_lower
    assert "samesite=strict" in cookie_lower
    assert "path=/api" in cookie_lower


def test_login_wrong_password_returns_401(admin_credentials, client) -> None:
    response = client.post("/api/admin/login", json={"password": "sai-mat-khau"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Mật khẩu không đúng."


def test_login_bruteforce_is_throttled(admin_credentials) -> None:
    test_client = TestClient(app)
    for _ in range(auth.LOGIN_MAX_FAILURES):
        response = test_client.post("/api/admin/login", json={"password": "sai"})
        assert response.status_code == 401

    throttled = test_client.post(
        "/api/admin/login", json={"password": ADMIN_TEST_PASSWORD}
    )
    assert throttled.status_code == 429
    assert "thử lại" in throttled.json()["detail"].lower()

    # Ngay cả mật khẩu đúng cũng bị chặn trong cửa sổ 5 phút.
    still_throttled = test_client.post(
        "/api/admin/login", json={"password": ADMIN_TEST_PASSWORD}
    )
    assert still_throttled.status_code == 429


def test_successful_login_clears_failure_counter(admin_credentials) -> None:
    test_client = TestClient(app)
    for _ in range(auth.LOGIN_MAX_FAILURES - 1):
        assert (
            test_client.post("/api/admin/login", json={"password": "sai"}).status_code == 401
        )
    # Lần cuối đúng mật khẩu trước khi chạm ngưỡng: đăng nhập thành công và xoá bộ đếm.
    response = test_client.post("/api/admin/login", json={"password": ADMIN_TEST_PASSWORD})
    assert response.status_code == 200
    # Bộ đếm đã xoá nên lần sai tiếp theo vẫn chỉ là 401.
    assert test_client.post("/api/admin/login", json={"password": "sai"}).status_code == 401


def test_logout_clears_cookie_and_session(admin_client) -> None:
    response = admin_client.post("/api/admin/logout")
    assert response.status_code == 200
    assert response.json()["authenticated"] is False
    # Cookie bị xoá: request quản trị tiếp theo phải 401.
    response = admin_client.get("/api/config")
    assert response.status_code == 401


def test_session_endpoint_reports_state(client, admin_client) -> None:
    # Chưa đăng nhập: vẫn 200 (route công khai), authenticated=false.
    response = client.get("/api/admin/session")
    assert response.status_code == 200
    assert response.json() == {
        "authenticated": False,
        "expires_at": None,
        "configured": True,
    }

    response = admin_client.get("/api/admin/session")
    assert response.status_code == 200
    data = response.json()
    assert data["authenticated"] is True
    assert data["configured"] is True
    assert datetime.fromisoformat(data["expires_at"]).tzinfo is not None


def test_changing_password_invalidates_sessions(admin_client, monkeypatch) -> None:
    assert admin_client.get("/api/config").status_code == 200
    # Khóa ký dẫn xuất từ cả mật khẩu: đổi mật khẩu làm token cũ mất hiệu lực.
    monkeypatch.setattr(settings, "admin_password", "mat-khau-moi")
    response = admin_client.get("/api/config")
    assert response.status_code == 401


# ==========================================
# Fail closed khi chưa cấu hình ADMIN_PASSWORD
# ==========================================
def test_unconfigured_admin_is_fail_closed(client, admin_route_mocks, api_db, monkeypatch) -> None:
    monkeypatch.setattr(settings, "admin_password", None)

    response = client.post("/api/admin/login", json={"password": "whatever"})
    assert response.status_code == 503
    assert "ADMIN_PASSWORD" in response.json()["detail"]

    session = client.get("/api/admin/session")
    assert session.status_code == 200
    assert session.json()["configured"] is False
    assert session.json()["authenticated"] is False

    # Mọi route quản trị vẫn bị chặn.
    response = client.get("/api/config")
    assert response.status_code == 401
    response = client.get("/api/documents")
    assert response.status_code == 401


# ==========================================
# Ma trận tham số hoá trên từng route quản trị
# ==========================================
def _set_admin_cookie(test_client: TestClient, token: str) -> None:
    test_client.cookies.set(auth.ADMIN_COOKIE_NAME, token, path=auth.ADMIN_COOKIE_PATH)


@pytest.mark.parametrize("cookie_mode", ["absent", "tampered", "expired"])
@pytest.mark.parametrize(("method", "path", "kwargs"), ADMIN_ROUTE_TABLE)
def test_admin_route_rejects_invalid_session(
    cookie_mode,
    method,
    path,
    kwargs,
    admin_credentials,
    admin_route_mocks,
    api_db,
    client,
) -> None:
    if cookie_mode == "tampered":
        token, _ = auth.issue_admin_session()
        # Đảo một ký tự chữ ký: cookie giả chữ ký.
        head, signature = token.rsplit(".", 1)
        flipped = "0" if signature[-1] != "0" else "1"
        _set_admin_cookie(client, f"{head}.{signature[:-1]}{flipped}")
    elif cookie_mode == "expired":
        _set_admin_cookie(client, auth.sign_admin_token(time.time() - 60))

    response = client.request(method, path, **kwargs)

    assert response.status_code == 401, (cookie_mode, method, path, response.text)
    assert response.json()["detail"] == auth.ADMIN_401_DETAIL


@pytest.mark.parametrize(("method", "path", "kwargs"), ADMIN_ROUTE_TABLE)
def test_admin_route_accepts_with_valid_session(
    method, path, kwargs, admin_client, admin_route_mocks, api_db
) -> None:
    response = admin_client.request(method, path, **kwargs)

    assert response.status_code not in (401, 403), (method, path, response.text)


def test_admin_routes_never_use_403_for_missing_session(client, admin_route_mocks, api_db) -> None:
    """Task này chỉ dùng 401 cho thiếu phiên (403 dành cho phân quyền sau này)."""
    for method, path, kwargs in ADMIN_ROUTE_TABLE:
        assert client.request(method, path, **kwargs).status_code == 401, (method, path)
