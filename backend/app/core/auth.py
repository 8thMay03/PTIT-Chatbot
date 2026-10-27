"""Xác thực admin và phiên ẩn danh cho backend (FE-06).

Hai cơ chế cookie HttpOnly dùng chung module này:

- ``ptit_admin``: phiên admin, token ký HMAC-SHA256 (stdlib), hết hạn theo
  ``ADMIN_SESSION_TTL_HOURS``. Server không lưu trạng thái phiên; đổi mật khẩu
  admin làm mất hiệu lực mọi phiên vì khóa ký dẫn xuất từ cả mật khẩu.
- ``ptit_sid``: phiên ẩn danh cho người dùng trang chat, cấp tự động ở các route
  chat/hội thoại. Owner key sinh từ sid (băm SHA-256) và ghi vào cột
  ``conversations.user_id`` để tách hội thoại giữa các trình duyệt.

Fail closed: chưa cấu hình ``ADMIN_PASSWORD`` thì login trả 503 và mọi route
admin luôn trả 401.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import time
from dataclasses import dataclass

from fastapi import HTTPException, Request, Response

from app.core.config import settings

logger = logging.getLogger(__name__)

# ==========================================
# Phiên admin
# ==========================================
ADMIN_COOKIE_NAME = "ptit_admin"
ADMIN_COOKIE_PATH = "/api"
ADMIN_401_DETAIL = "Cần đăng nhập quản trị."

# Chặn dò mật khẩu trong bộ nhớ: quá 5 lần sai trong 5 phút theo IP thì 429.
# Chỉ đúng khi chạy một worker uvicorn (cấu hình hiện tại); xem README.
LOGIN_MAX_FAILURES = 5
LOGIN_WINDOW_SECONDS = 300.0

# ==========================================
# Phiên ẩn danh (ptit_sid)
# ==========================================
ANON_COOKIE_NAME = "ptit_sid"
ANON_COOKIE_PATH = "/api"
ANON_COOKIE_MAX_AGE = 180 * 24 * 3600  # 180 ngày
ANON_SID_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")
# secrets.token_urlsafe(32) sinh đúng 43 ký tự; chấp nhận dải dài một chút.
ANON_SID_MIN_LENGTH = 32
ANON_SID_MAX_LENGTH = 128

_login_failures: dict[str, list[float]] = {}


def _random_admin_session_secret() -> None:
    """Sinh khóa tạm khi chưa cấu hình ADMIN_SESSION_SECRET (phiên mất khi restart)."""
    if not settings.admin_session_secret:
        settings.admin_session_secret = secrets.token_urlsafe(32)
        logger.warning(
            "ADMIN_SESSION_SECRET chưa cấu hình; đã sinh khóa tạm cho phiên này. "
            "Mọi phiên admin sẽ mất hiệu lực khi restart backend."
        )


_random_admin_session_secret()


def is_admin_configured() -> bool:
    return bool(settings.admin_password)


def _signing_key() -> bytes:
    """Khóa HMAC dẫn xuất từ secret VÀ mật khẩu admin.

    Đổi mật khẩu (restart với ADMIN_PASSWORD khác) làm mọi token cũ mất hiệu lực.
    """
    material = (
        f"{settings.admin_session_secret or ''}\n{settings.admin_password or ''}"
    ).encode("utf-8")
    return hashlib.sha256(b"ptit-admin-session-v1\n" + material).digest()


def sign_admin_token(expires_at: float) -> str:
    """Ký token `v1.<exp>.<nonce>.<sig>` cho thời điểm hết hạn (unix giây).

    Tách khỏi hàm cấp phiên để test dựng token hết hạn/hết hạn sớm.
    """
    exp = int(expires_at)
    nonce = secrets.token_urlsafe(12)
    payload = f"v1.{exp}.{nonce}"
    signature = hmac.new(_signing_key(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def verify_admin_token(token: str | None) -> float | None:
    """Trả về thời điểm hết hạn (unix giây) nếu token hợp lệ còn hạn, ngược lại None."""
    if not token:
        return None
    parts = token.split(".")
    if len(parts) != 4 or parts[0] != "v1":
        return None
    _, exp_text, nonce, signature = parts
    try:
        exp = int(exp_text)
    except ValueError:
        return None
    if not nonce or not signature:
        return None
    payload = f"v1.{exp_text}.{nonce}"
    expected = hmac.new(_signing_key(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return None
    if exp <= time.time():
        return None
    return float(exp)


def issue_admin_session() -> tuple[str, float]:
    """Cấp token phiên admin; trả về (token, thời điểm hết hạn unix)."""
    expires_at = time.time() + settings.admin_session_ttl_hours * 3600
    return sign_admin_token(expires_at), expires_at


def iso_expires_at(expires_at: float) -> str:
    """Thời điểm hết hạn dạng ISO 8601 (UTC) trả về client."""
    from datetime import datetime, timezone

    return datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat()


def issue_admin_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        ADMIN_COOKIE_NAME,
        token,
        max_age=int(settings.admin_session_ttl_hours * 3600),
        path=ADMIN_COOKIE_PATH,
        httponly=True,
        samesite="strict",
        secure=settings.cookie_secure,
    )


def clear_admin_cookie(response: Response) -> None:
    response.delete_cookie(
        ADMIN_COOKIE_NAME,
        path=ADMIN_COOKIE_PATH,
        httponly=True,
        samesite="strict",
        secure=settings.cookie_secure,
    )


def verify_admin_password(candidate: str | None) -> bool:
    password = settings.admin_password
    if not password or not isinstance(candidate, str):
        return False
    return hmac.compare_digest(password.encode("utf-8"), candidate.encode("utf-8"))


def client_ip(request: Request) -> str:
    client = getattr(request, "client", None)
    return client.host if client else "unknown"


def _prune_login_failures(now: float) -> None:
    for ip in list(_login_failures):
        recent = [t for t in _login_failures[ip] if now - t < LOGIN_WINDOW_SECONDS]
        if recent:
            _login_failures[ip] = recent
        else:
            del _login_failures[ip]


def is_login_throttled(request: Request) -> bool:
    now = time.monotonic()
    _prune_login_failures(now)
    return len(_login_failures.get(client_ip(request), [])) >= LOGIN_MAX_FAILURES


def register_failed_login(request: Request) -> None:
    now = time.monotonic()
    _prune_login_failures(now)
    _login_failures.setdefault(client_ip(request), []).append(now)


def register_successful_login(request: Request) -> None:
    _login_failures.pop(client_ip(request), None)


def reset_login_attempts() -> None:
    """Xoá trạng thái chặn dò (dùng để cách ly test và sau khi đổi mật khẩu)."""
    _login_failures.clear()


async def require_admin(request: Request) -> None:
    """Dependency cho route quản trị: 401 khi thiếu/sai/hết hạn cookie admin."""
    if not is_admin_configured():
        # Fail closed: chưa cấu hình mật khẩu thì không route admin nào hoạt động.
        raise HTTPException(status_code=401, detail=ADMIN_401_DETAIL)
    if verify_admin_token(request.cookies.get(ADMIN_COOKIE_NAME)) is None:
        raise HTTPException(status_code=401, detail=ADMIN_401_DETAIL)


# ==========================================
# Phiên ẩn danh ptit_sid
# ==========================================
def _is_valid_sid(value: str | None) -> bool:
    if not isinstance(value, str):
        return False
    if not (ANON_SID_MIN_LENGTH <= len(value) <= ANON_SID_MAX_LENGTH):
        return False
    return all(char in ANON_SID_CHARS for char in value)


def anon_owner_key(sid: str) -> str:
    """Owner key lưu vào conversations.user_id; không lưu sid gốc.

    Tiền tố "anon:" để phân biệt với user SSO nếu bổ sung sau này.
    """
    return "anon:" + hashlib.sha256(sid.encode("utf-8")).hexdigest()[:32]


def _new_client_session(sid: str, issued: bool) -> ClientSession:
    return ClientSession(sid=sid, owner_key=anon_owner_key(sid), issued=issued)


@dataclass(frozen=True)
class ClientSession:
    """Phiên ẩn danh của request hiện tại.

    ``issued=True`` nghĩa là request chưa mang cookie hợp lệ và route cần gắn
    Set-Cookie cho sid vừa cấp.
    """

    sid: str
    owner_key: str
    issued: bool

    def apply(self, response: Response | None) -> None:
        """Gán Set-Cookie cho phiên mới lên response; no-op nếu response là None.

        Dùng cho route thường (FastAPI gộp cookie của response inject vào response
        cuối). Route tự trả Response (StreamingResponse) phải dùng `cookie_header`.
        """
        if response is None or not self.issued:
            return
        response.set_cookie(
            ANON_COOKIE_NAME,
            self.sid,
            max_age=ANON_COOKIE_MAX_AGE,
            path=ANON_COOKIE_PATH,
            httponly=True,
            samesite="lax",
            secure=settings.cookie_secure,
        )

    @property
    def cookie_header(self) -> str | None:
        """Giá trị header Set-Cookie cho phiên mới, hoặc None nếu không cần cấp."""
        if not self.issued:
            return None
        parts = [
            f"{ANON_COOKIE_NAME}={self.sid}",
            f"Path={ANON_COOKIE_PATH}",
            f"Max-Age={ANON_COOKIE_MAX_AGE}",
            "HttpOnly",
            "SameSite=Lax",
        ]
        if settings.cookie_secure:
            parts.append("Secure")
        return "; ".join(parts)


def get_client_session(request: Request | None) -> ClientSession:
    """Đọc cookie ptit_sid hợp lệ hoặc cấp sid mới (chưa ghi Set-Cookie).

    Dùng trực tiếp trong route (thay vì Depends) để hàm route vẫn gọi được trong
    unit test không có Request: khi đó sid tạm không đánh dấu issued để không cấp
    cookie ngoài ngữ cảnh HTTP.
    """
    if request is not None:
        raw = request.cookies.get(ANON_COOKIE_NAME)
        if _is_valid_sid(raw):
            return _new_client_session(raw, issued=False)
        return _new_client_session(secrets.token_urlsafe(32), issued=True)
    return _new_client_session(secrets.token_urlsafe(32), issued=False)
