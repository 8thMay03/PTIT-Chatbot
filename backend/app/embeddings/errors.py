"""Lỗi của mô hình nhúng; tách riêng để ``models``/``api_clients`` dùng mà không import vòng."""


class EmbeddingUnavailableError(RuntimeError):
    """Không dùng được mô hình nhúng.

    ``reason`` hiện cho admin nên chỉ chứa provider/model, loại exception, số chiều —
    không bao giờ kèm chuỗi lỗi thô của SDK (có thể chứa một phần API key).
    """

    state = "error"

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class EmbeddingNotConfiguredError(EmbeddingUnavailableError):
    """Thiếu cấu hình bắt buộc (ví dụ API key của provider openai)."""

    state = "not_configured"


class EmbeddingAPIError(EmbeddingUnavailableError):
    """Một lần gọi dịch vụ embedding qua API thất bại (timeout, mạng, HTTP lỗi, response sai).

    Lỗi tạm thời của một request: không làm embedder chuyển ``error``. ``reason`` chỉ gồm
    nhà cung cấp, mô hình, loại lỗi/mã HTTP — không chứa khoá, nội dung gửi đi hay response thô.
    """

    def __init__(self, reason: str, status_code: int | None = None) -> None:
        super().__init__(reason)
        self.status_code = status_code
