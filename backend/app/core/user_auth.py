"""Tài khoản người dùng: băm mật khẩu và phiên cookie ``ptit_user`` (landing-user-auth).

- Mật khẩu băm bằng ``hashlib.scrypt`` (stdlib), salt 16 byte ngẫu nhiên; tham số
  ghi trong chuỗi hash ``scrypt$n$r$p$<salt_b64>$<hash_b64>`` để đổi tham số sau
  này vẫn kiểm được hash cũ.
- Token phiên ``u1.<user_id>.<exp>.<nonce>.<sig>`` ký HMAC-SHA256 bằng khóa dẫn xuất
  từ ``USER_SESSION_SECRET`` (khác khóa admin). Server không lưu phiên; mỗi request
  vẫn kiểm user còn tồn tại trong DB.
- Cookie người dùng không bao giờ mở được route admin: ``require_admin`` chỉ đọc
  ``ptit_admin`` với khóa ký riêng.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import re
import secrets
import time

from fastapi import Request, Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import User

logger = logging.getLogger(__name__)

USER_COOKIE_NAME = "ptit_user"
USER_COOKIE_PATH = "/api"
USER_OWNER_PREFIX = "user:"

# scrypt N=2^14, r=8, p=1: ~16 MB bộ nhớ, vài chục ms mỗi lần băm.
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 32
SCRYPT_SALT_BYTES = 16
# Giới hạn tham số khi đọc hash từ DB để chuỗi hỏng không làm treo request.
_SCRYPT_MAX_N = 2**20
_SCRYPT_MAX_MEM = 256 * 1024 * 1024

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128
FULL_NAME_MAX_LENGTH = 100
EMAIL_MAX_LENGTH = 254
# Kiểm tra định dạng tối thiểu (không có dịch vụ xác thực email): local@domain.tld,
# không khoảng trắng, tên miền gồm nhãn chữ/số/gạch ngang.
_EMAIL_RE = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}$"
)


def _random_user_session_secret() -> None:
    """Sinh khóa tạm khi chưa cấu hình USER_SESSION_SECRET (người dùng bị đăng xuất khi restart)."""
    if not settings.user_session_secret:
        settings.user_session_secret = secrets.token_urlsafe(32)
        logger.warning(
            "USER_SESSION_SECRET chưa cấu hình; đã sinh khóa tạm cho phiên này. "
            "Mọi phiên người dùng sẽ mất hiệu lực khi restart backend."
        )


_random_user_session_secret()


# ==========================================
# Chuẩn hoá và kiểm tra dữ liệu đăng ký
# ==========================================
def normalize_email(value: str) -> str:
    return value.strip().lower()


def is_valid_email(value: str) -> bool:
    return len(value) <= EMAIL_MAX_LENGTH and _EMAIL_RE.match(value) is not None


def is_allowed_email_domain(email: str) -> bool:
    domains = settings.allowed_email_domains
    if not domains:
        return True
    return email.rsplit("@", 1)[-1] in domains


# ==========================================
# Băm mật khẩu
# ==========================================
def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _scrypt(password: str, salt: bytes, n: int, r: int, p: int, dklen: int) -> bytes:
    return hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=dklen, maxmem=_SCRYPT_MAX_MEM
    )


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(SCRYPT_SALT_BYTES)
    digest = _scrypt(password, salt, SCRYPT_N, SCRYPT_R, SCRYPT_P, SCRYPT_DKLEN)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${_b64encode(salt)}${_b64encode(digest)}"


def verify_password(password: str, stored_hash: str | None) -> bool:
    """So khớp mật khẩu với hash đã lưu; hash hỏng/không nhận dạng được trả False."""
    if not isinstance(password, str) or not stored_hash:
        return False
    parts = stored_hash.split("$")
    if len(parts) != 6 or parts[0] != "scrypt":
        return False
    try:
        n, r, p = int(parts[1]), int(parts[2]), int(parts[3])
        salt = _b64decode(parts[4])
        expected = _b64decode(parts[5])
    except ValueError:
        return False
    if not (1 < n <= _SCRYPT_MAX_N and r > 0 and p > 0 and salt and expected):
        return False
    try:
        candidate = _scrypt(password, salt, n, r, p, len(expected))
    except ValueError:
        return False
    return hmac.compare_digest(candidate, expected)


_dummy_hash: str | None = None


def burn_password_check(password: str) -> None:
    """Băm mật khẩu với hash giả khi email không tồn tại.

    Giữ thời gian phản hồi của "email không tồn tại" tương đương "sai mật khẩu" để
    không liệt kê được email qua thời gian.
    """
    global _dummy_hash
    if _dummy_hash is None:
        _dummy_hash = hash_password(secrets.token_urlsafe(16))
    verify_password(password, _dummy_hash)


# ==========================================
# Token và cookie phiên người dùng
# ==========================================
def _signing_key() -> bytes:
    material = (settings.user_session_secret or "").encode("utf-8")
    return hashlib.sha256(b"ptit-user-session-v1\n" + material).digest()


def _signature(payload: str) -> str:
    return _b64encode(hmac.new(_signing_key(), payload.encode("utf-8"), hashlib.sha256).digest())


def sign_user_token(user_id: str, expires_at: float) -> str:
    """Ký token `u1.<user_id>.<exp>.<nonce>.<sig>`; tách riêng để test dựng token hết hạn."""
    payload = f"u1.{user_id}.{int(expires_at)}.{secrets.token_urlsafe(12)}"
    return f"{payload}.{_signature(payload)}"


def verify_user_token(token: str | None) -> str | None:
    """Trả user_id nếu token đúng chữ ký và còn hạn, ngược lại None."""
    if not token:
        return None
    parts = token.split(".")
    if len(parts) != 5 or parts[0] != "u1":
        return None
    _, user_id, exp_text, nonce, signature = parts
    if not user_id or not nonce or not signature:
        return None
    try:
        exp = int(exp_text)
    except ValueError:
        return None
    # Chữ ký tính trên đúng chuỗi nhận được nên các dạng int() lỏng không giả được.
    if not hmac.compare_digest(_signature(f"u1.{user_id}.{exp_text}.{nonce}"), signature):
        return None
    if exp <= time.time():
        return None
    return user_id


def _ttl_seconds() -> int:
    return int(settings.user_session_ttl_days * 24 * 3600)


def issue_user_cookie(response: Response, user: User) -> None:
    token = sign_user_token(user.id, time.time() + _ttl_seconds())
    response.set_cookie(
        USER_COOKIE_NAME,
        token,
        max_age=_ttl_seconds(),
        path=USER_COOKIE_PATH,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )


def clear_user_cookie(response: Response) -> None:
    response.delete_cookie(
        USER_COOKIE_NAME,
        path=USER_COOKIE_PATH,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )


def resolve_user(request: Request | None, session: Session | None) -> User | None:
    """User của cookie ptit_user hợp lệ; cookie sai/hết hạn/user đã xoá đều là None."""
    if request is None or session is None:
        return None
    user_id = verify_user_token(request.cookies.get(USER_COOKIE_NAME))
    if user_id is None:
        return None
    return session.get(User, user_id)


def user_owner_key(user_id: str) -> str:
    """Owner key ghi vào conversations.user_id cho hội thoại của tài khoản."""
    return USER_OWNER_PREFIX + user_id
