"""Câu từ chối của chatbot và cách nhận diện chúng trong câu trả lời của LLM (RAG-22).

LLM hiếm khi lặp lại đúng nguyên văn câu từ chối: hay thêm "Xin lỗi, ...", đổi đuôi
"... trong tài liệu được cung cấp", in đậm hoặc dính kèm ``[n]``. Vì vậy câu từ chối
được nhận diện bằng *lõi* của câu chuẩn sau khi chuẩn hóa, không so khớp nguyên văn.
"""

import re
import unicodedata
from collections.abc import Collection

from app.guardrails import OUT_OF_SCOPE_ANSWER

NO_CONTEXT_ANSWER = "Chưa tìm thấy thông tin này trong tài liệu."

# Lõi (đã chuẩn hóa) của từng câu từ chối. Bỏ cụm đuôi như "trong tài liệu" để chịu
# được "trong các tài liệu", "trong tài liệu được cung cấp", "trong ngữ cảnh".
REFUSAL_CORES = (
    "chưa tìm thấy thông tin này",
    "không tìm thấy thông tin này",
    "chỉ hỗ trợ các câu hỏi liên quan đến ptit",
)

CITATION_RE = re.compile(r"\[(\d+)\]")
_MARKDOWN_EMPHASIS_RE = re.compile(r"[*_`]+")
_SENTENCE_BREAK_RE = re.compile(r"(?<=[.!?…])\s+|\n+")
_TRAILING_PUNCTUATION = " .!?…:;,"


def normalize_refusal_text(text: str) -> str:
    """Chuẩn hóa để so khớp: NFC, bỏ ``[n]`` và ký tự nhấn mạnh markdown, casefold."""

    text = unicodedata.normalize("NFC", text)
    text = CITATION_RE.sub(" ", text)
    text = _MARKDOWN_EMPHASIS_RE.sub("", text)
    text = re.sub(r"\s+", " ", text).casefold()
    return text.strip(_TRAILING_PUNCTUATION)


def is_refusal(answer: str, valid_ids: Collection[int] | None = None) -> bool:
    """Câu trả lời có phải câu từ chối (không có thông tin / ngoài phạm vi) không.

    Là từ chối khi câu đầu tiên chứa lõi của một câu từ chối và phần sau câu đầu không
    còn citation hợp lệ nào. ``valid_ids`` là tập số citation hợp lệ; ``None`` nghĩa là
    mọi ``[n]`` đều được coi là hợp lệ (dùng cho câu trả lời đã chuẩn hóa citation).
    Câu mở đầu bằng cụm từ chối rồi trả lời tiếp kèm ``[n]`` hợp lệ là trả lời một phần.
    """

    text = _MARKDOWN_EMPHASIS_RE.sub("", unicodedata.normalize("NFC", answer or "")).strip()
    if not text:
        return False
    sentences: list[str] = []
    for part in _SENTENCE_BREAK_RE.split(text):
        # "... tài liệu. [2]": phần chỉ có [n] thuộc về câu đứng trước.
        if sentences and not normalize_refusal_text(part):
            sentences[-1] = f"{sentences[-1]} {part}"
        elif part.strip():
            sentences.append(part)
    first, rest = sentences[0], " ".join(sentences[1:])
    normalized_first = normalize_refusal_text(first)
    if not any(core in normalized_first for core in REFUSAL_CORES):
        return False
    for match in CITATION_RE.finditer(rest):
        if valid_ids is None or int(match.group(1)) in valid_ids:
            return False
    return True
