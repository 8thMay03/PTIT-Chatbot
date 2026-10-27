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

Owner key của request (``get_client_session``): cookie ``ptit_user`` hợp lệ
(``app.core.user_auth``) → ``user:<id>``, ngược lại ``anon:<hash(sid)>``.

Chặn dò mật khẩu (admin và người dùng) đếm theo IP thật của client: chỉ đọc
``X-Forwarded-For`` khi request tới từ proxy trong ``TRUSTED_PROXY_IPS``.
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import logging
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.core import user_auth
from app.core.config import settings

logger = logging.getLogger(__name__)

# ==========================================
# Phiên admin
# ==========================================
ADMIN_COOKIE_NAME = "ptit_admin"
ADMIN_COOKIE_PATH = "/api"
ADMIN_401_DETAIL = "Cần đăng nhập quản trị."

# Chặn dò mật khẩu admin trong bộ nhớ: quá 5 lần sai trong 5 phút theo IP thì 429.
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


# ==========================================
# Chặn dò mật khẩu (dùng chung admin/người dùng)
# ==========================================
class FailureLimiter:
    """Đếm lần thất bại theo khóa trong cửa sổ trượt (bộ nhớ, một worker).

    Ngưỡng/cửa sổ đọc qua callable để test và settings đổi lúc chạy vẫn có hiệu lực.
    """

    def __init__(self, max_failures: Callable[[], int], window_seconds: Callable[[], float]):
        self._max_failures = max_failures
        self._window_seconds = window_seconds
        self._failures: dict[str, list[float]] = {}

    def _prune(self, now: float) -> None:
        window = self._window_seconds()
        for key in list(self._failures):
            recent = [t for t in self._failures[key] if now - t < window]
            if recent:
                self._failures[key] = recent
            else:
                del self._failures[key]

    def is_blocked(self, key: str) -> bool:
        self._prune(time.monotonic())
        return len(self._failures.get(key, [])) >= self._max_failures()

    def record_failure(self, key: str) -> None:
        now = time.monotonic()
        self._prune(now)
        self._failures.setdefault(key, []).append(now)

    def clear(self, key: str) -> None:
        self._failures.pop(key, None)

    def reset(self) -> None:
        self._failures.clear()


admin_login_limiter = FailureLimiter(lambda: LOGIN_MAX_FAILURES, lambda: LOGIN_WINDOW_SECONDS)
# Đăng nhập người dùng: khóa theo IP + email, nên dò một tài khoản không khoá tài khoản khác
# và client ở IP khác vẫn đăng nhập được.
user_login_limiter = FailureLimiter(
    lambda: settings.user_auth_max_failures, lambda: settings.user_auth_window_seconds
)
# Đăng ký: đếm lần gặp email đã tồn tại theo IP (chống dò email qua 409).
user_register_limiter = FailureLimiter(
    lambda: settings.user_auth_max_failures, lambda: settings.user_auth_window_seconds
)


def _trusted_proxies() -> list[ipaddress.IPv4Network | ipaddress.IPv6Network | str]:
    entries: list[ipaddress.IPv4Network | ipaddress.IPv6Network | str] = []
    for raw in (settings.trusted_proxy_ips or "").split(","):
        value = raw.strip()
        if not value:
            continue
        try:
            entries.append(ipaddress.ip_network(value, strict=False))
        except ValueError:
            # Tên host không phải IP (ví dụ "testclient" của TestClient): so khớp nguyên văn.
            entries.append(value)
    return entries


def _is_trusted_proxy(host: str, trusted: list) -> bool:
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    for entry in trusted:
        if isinstance(entry, str):
            if host == entry:
                return True
        elif address is not None and address.version == entry.version and address in entry:
            return True
    return False


def client_ip(request: Request) -> str:
    """IP thật của client cho chặn dò.

    Chỉ tin ``X-Forwarded-For`` khi kết nối tới từ proxy tin cậy; đi từ phải sang
    trái bỏ qua các proxy tin cậy, phần tử đầu tiên không tin cậy là client. Gọi
    thẳng cổng backend từ ngoài không giả được IP vì header bị bỏ qua.
    """
    client = getattr(request, "client", None)
    peer = client.host if client else "unknown"
    trusted = _trusted_proxies()
    if not trusted or not _is_trusted_proxy(peer, trusted):
        return peer
    forwarded = [
        part.strip()
        for header in request.headers.getlist("x-forwarded-for")
        for part in header.split(",")
        if part.strip()
    ]
    for hop in reversed(forwarded):
        if not _is_trusted_proxy(hop, trusted):
            return hop
    return forwarded[0] if forwarded else peer


def is_login_throttled(request: Request) -> bool:
    return admin_login_limiter.is_blocked(client_ip(request))


def register_failed_login(request: Request) -> None:
    admin_login_limiter.record_failure(client_ip(request))


def register_successful_login(request: Request) -> None:
    admin_login_limiter.clear(client_ip(request))


def user_login_key(request: Request, email: str) -> str:
    return f"{client_ip(request)}|{email}"


def reset_login_attempts() -> None:
    """Xoá trạng thái chặn dò (dùng để cách ly test và sau khi đổi mật khẩu)."""
    admin_login_limiter.reset()
    user_login_limiter.reset()
    user_register_limiter.reset()


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

    Tiền tố "anon:" phân biệt với hội thoại của tài khoản ("user:<id>").
    """
    return "anon:" + hashlib.sha256(sid.encode("utf-8")).hexdigest()[:32]


def _new_client_session(sid: str, issued: bool, user_id: str | None = None) -> ClientSession:
    owner_key = user_auth.user_owner_key(user_id) if user_id else anon_owner_key(sid)
    return ClientSession(sid=sid, owner_key=owner_key, issued=issued, user_id=user_id)


@dataclass(frozen=True)
class ClientSession:
    """Phiên của request hiện tại.

    ``owner_key`` là ``user:<id>`` khi có cookie người dùng hợp lệ, ngược lại
    ``anon:<hash(sid)>``. ``anon_owner_key`` luôn là owner của sid (dùng khi chuyển
    hội thoại ẩn danh sang tài khoản). ``issued=True`` nghĩa là request chưa mang
    cookie ptit_sid hợp lệ và route cần gắn Set-Cookie cho sid vừa cấp.
    """

    sid: str
    owner_key: str
    issued: bool
    user_id: str | None = None

    @property
    def anon_owner_key(self) -> str:
        return anon_owner_key(self.sid)

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


def get_client_session(request: Request | None, session: Session | None = None) -> ClientSession:
    """Đọc cookie ptit_sid hợp lệ hoặc cấp sid mới (chưa ghi Set-Cookie).

    Có ``session`` (DB) thì cookie ptit_user hợp lệ trỏ tới user còn tồn tại quyết
    định owner ``user:<id>``; ptit_sid vẫn được giữ/cấp để đăng xuất quay về ẩn danh.

    Dùng trực tiếp trong route (thay vì Depends) để hàm route vẫn gọi được trong
    unit test không có Request: khi đó sid tạm không đánh dấu issued để không cấp
    cookie ngoài ngữ cảnh HTTP.
    """
    if request is not None:
        user = user_auth.resolve_user(request, session)
        user_id = user.id if user is not None else None
        raw = request.cookies.get(ANON_COOKIE_NAME)
        if _is_valid_sid(raw):
            return _new_client_session(raw, issued=False, user_id=user_id)
        return _new_client_session(secrets.token_urlsafe(32), issued=True, user_id=user_id)
    return _new_client_session(secrets.token_urlsafe(32), issued=False)


def issue_fresh_anon_session(response: Response) -> None:
    """Cấp ptit_sid mới (khi đăng xuất) để trình duyệt bắt đầu phiên ẩn danh khác."""
    _new_client_session(secrets.token_urlsafe(32), issued=True).apply(response)
