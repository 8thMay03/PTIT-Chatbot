"""Mã hoá secret (API key) trước khi lưu cấu hình runtime vào Postgres.

Dùng Fernet (AES-128-CBC + HMAC-SHA256, có xác thực) với khoá trong
``CONFIG_ENCRYPTION_KEY``. Khoá chỉ nằm trong env, không bao giờ vào DB, nên lộ
bản sao DB không lộ API key.

Xoay khoá: đặt nhiều khoá phân tách bằng dấu phẩy, khoá mới đứng đầu. Khoá đầu
dùng để mã hoá; mọi khoá đều giải mã được. Lần lưu cấu hình kế tiếp mã hoá lại
toàn bộ secret bằng khoá mới, sau đó có thể bỏ khoá cũ.

Tạo khoá:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from app.core.config import settings


class SecretEncryptionUnavailable(RuntimeError):
    """Thiếu hoặc sai ``CONFIG_ENCRYPTION_KEY``: không được lưu secret."""


class SecretDecryptionError(ValueError):
    """Bản mã không giải được bằng khoá hiện có (khoá đã đổi hoặc dữ liệu hỏng)."""


def _cipher() -> MultiFernet:
    raw = (settings.config_encryption_key or "").strip()
    keys = [key.strip() for key in raw.split(",") if key.strip()]
    if not keys:
        raise SecretEncryptionUnavailable(
            "Chưa cấu hình CONFIG_ENCRYPTION_KEY nên không thể lưu API key. "
            "Thêm khoá vào .env rồi khởi động lại backend."
        )
    try:
        return MultiFernet([Fernet(key.encode("ascii")) for key in keys])
    except (ValueError, UnicodeEncodeError) as exc:
        # Không đưa giá trị khoá vào thông báo lỗi.
        raise SecretEncryptionUnavailable(
            "CONFIG_ENCRYPTION_KEY không hợp lệ (cần khoá Fernet base64 32 byte)."
        ) from exc


def is_secret_encryption_configured() -> bool:
    try:
        _cipher()
    except SecretEncryptionUnavailable:
        return False
    return True


def encrypt_secret(plaintext: str) -> str:
    return _cipher().encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt_secret(token: str) -> str:
    try:
        return _cipher().decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeError) as exc:
        raise SecretDecryptionError("Không giải mã được secret bằng CONFIG_ENCRYPTION_KEY hiện tại.") from exc
