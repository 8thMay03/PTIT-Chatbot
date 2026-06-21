from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


OUT_OF_SCOPE_ANSWER = (
    "Mình chỉ hỗ trợ các câu hỏi liên quan đến PTIT và nội dung trong sổ tay sinh viên. "
    "Bạn có thể hỏi về học phí, học phần, thi cử, học bổng, rèn luyện, thủ tục sinh viên "
    "hoặc điều kiện tốt nghiệp."
)


@dataclass(frozen=True)
class ScopeDecision:
    allowed: bool
    reason: str


DOMAIN_TERMS = (
    "ptit",
    "học viện",
    "nhà trường",
    "sinh viên",
    "học tập",
    "khóa học",
    "học kỳ",
    "học phần",
    "môn học",
    "tín chỉ",
    "chương trình đào tạo",
    "chương trình",
    "đào tạo",
    "ngành học",
    "mã ngành",
    "ngành công nghệ",
    "ngành an toàn",
    "ngành marketing",
    "đăng ký môn",
    "đăng ký học",
    "học phí",
    "lệ phí",
    "học bổng",
    "tốt nghiệp",
    "cảnh báo học",
    "điểm trung bình",
    "điểm chữ",
    "thang điểm",
    "bảng điểm",
    "khiếu nại điểm",
    "cải thiện điểm",
    "học lại",
    "xếp loại",
    "gpa",
    "cpa",
    "thi cử",
    "kỳ thi",
    "thi hộ",
    "phúc khảo",
    "bảo lưu",
    "thôi học",
    "nghỉ học",
    "chuyển ngành",
    "chuyển trường",
    "rèn luyện",
    "kỷ luật",
    "khen thưởng",
    "thẻ sinh viên",
    "ký túc xá",
    "thư viện",
    "đoàn thanh niên",
    "công tác sinh viên",
    "thủ tục",
    "giấy xác nhận",
    "chứng chỉ",
    "chuẩn đầu ra",
    "giảng đường",
    "giảng viên",
    "giảng dạy",
    "lớp học",
    "vào lớp",
    "khảo thí",
    "thực tập",
    "cố vấn học tập",
    "thời khóa biểu",
    "lịch học",
    "lịch thi",
    "địa chỉ trường",
    "cơ sở đào tạo",
    "phòng đào tạo",
)

FOLLOW_UP_PATTERNS = (
    r"^(?:còn|thế còn|vậy|trường hợp này|trường hợp đó|quy định này|quy định đó|nó)\b",
    r"^(?:bao nhiêu|khi nào|ở đâu|tại sao|như thế nào|có được không|cần gì)\b",
)

BLOCKED_PATTERNS = (
    ("code_generation", r"\b(?:viết|tạo|sinh|làm)\s+(?:cho\s+(?:tôi|mình|em)\s+)?(?:mã|code|script|chương trình)\b"),
    ("code_generation", r"\b(?:python|javascript|java|c\+\+|html|css|sql)\b.*\b(?:code|mã|script|lập trình)\b"),
    ("prompt_injection", r"\b(?:bỏ qua|quên đi|phớt lờ)\b.*\b(?:hướng dẫn|chỉ dẫn|prompt|quy tắc)\b"),
    ("prompt_injection", r"\b(?:system prompt|developer message|chỉ dẫn hệ thống)\b"),
    ("creative_request", r"\b(?:viết|sáng tác)\s+(?:một\s+)?(?:bài thơ|truyện|kịch bản|bài hát)\b"),
    ("general_task", r"\b(?:dịch|tóm tắt)\s+(?:đoạn|văn bản|bài viết)\s+(?:này|sau)\b"),
    ("general_task", r"\b(?:giải|làm)\s+(?:giúp\s+)?(?:bài toán|bài tập lập trình)\b"),
)


def check_scope(
    question: str,
    history: list[dict[str, str]] | None = None,
) -> ScopeDecision:
    """Apply a deterministic domain gate before retrieval and generation."""
    normalized = _normalize(question)
    if not normalized:
        return ScopeDecision(False, "empty")

    for reason, pattern in BLOCKED_PATTERNS:
        if re.search(pattern, normalized):
            return ScopeDecision(False, reason)

    if _contains_domain_term(normalized):
        return ScopeDecision(True, "ptit_domain")

    if any(re.search(pattern, normalized) for pattern in FOLLOW_UP_PATTERNS):
        previous_user_questions = (
            _normalize(message.get("content", ""))
            for message in reversed(history or [])
            if message.get("role") == "user"
        )
        if any(_contains_domain_term(previous) for previous in previous_user_questions):
            return ScopeDecision(True, "ptit_follow_up")

    return ScopeDecision(False, "outside_ptit_domain")


def _contains_domain_term(text: str) -> bool:
    return any(term in text for term in DOMAIN_TERMS)


def _normalize(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())
