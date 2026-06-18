import re

from app.core.config import settings


REWRITE_SYSTEM_PROMPT = """Bạn chuyển câu hỏi tiếng Việt thành một truy vấn tìm kiếm tài liệu PTIT.
Chỉ trả về một truy vấn duy nhất, không trả lời câu hỏi và không giải thích.
Giữ nguyên tên riêng, mã môn, con số, mốc thời gian và thuật ngữ quan trọng.
Mở rộng từ viết tắt khi chắc chắn và loại bỏ lời chào hoặc lời dẫn hội thoại.
Truy vấn phải ngắn gọn, tự nhiên và có thể đứng độc lập."""

ABBREVIATIONS = {
    "đkhp": "đăng ký học phần",
    "ctsv": "công tác sinh viên",
    "bhyt": "bảo hiểm y tế",
    "gpa": "điểm trung bình gpa",
    "cpa": "điểm trung bình tích lũy cpa",
    "sv": "sinh viên",
    "gv": "giảng viên",
}

CONVERSATIONAL_PREFIXES = (
    r"xin (?:cho )?hỏi",
    r"cho (?:mình|tôi|em) hỏi",
    r"(?:mình|tôi|em) (?:muốn|cần) hỏi",
    r"bạn có thể (?:cho (?:mình|tôi|em) )?biết",
    r"hãy cho (?:mình|tôi|em) biết",
)


class VietnameseQueryRewriter:
    def rewrite(self, question: str, history: list[dict[str, str]] | None = None) -> str:
        history = history or []
        fallback = rule_based_rewrite(question)
        fallback = _resolve_rule_based_follow_up(fallback, history)
        if not settings.query_rewrite_use_llm or not settings.openai_api_key:
            return fallback

        try:
            return _rewrite_with_llm(fallback, history) or fallback
        except Exception:
            return fallback


def rule_based_rewrite(question: str) -> str:
    """Normalize Vietnamese conversational questions into compact search queries."""
    rewritten = " ".join(question.casefold().split()).strip()
    prefix_pattern = rf"^(?:{'|'.join(CONVERSATIONAL_PREFIXES)})[,:;.!?\s-]*"
    rewritten = re.sub(prefix_pattern, "", rewritten, count=1)

    for abbreviation, expansion in ABBREVIATIONS.items():
        rewritten = re.sub(rf"\b{re.escape(abbreviation)}\b", expansion, rewritten)

    rewritten = rewritten.replace("đăng ký đăng ký học phần", "đăng ký học phần")
    rewritten = re.sub(r"\s+(?:ạ|nhé|vậy|được không)[.!?\s]*$", "", rewritten)
    rewritten = re.sub(r"\s+", " ", rewritten).strip(" ,:;.!?-")
    return rewritten or " ".join(question.split()).strip()


def _resolve_rule_based_follow_up(query: str, history: list[dict[str, str]]) -> str:
    follow_up_pattern = r"^(?:còn|thế còn|vậy|trường hợp (?:này|đó)|quy định (?:này|đó)|nó)\b"
    if not re.search(follow_up_pattern, query):
        return query

    previous_user_message = next(
        (
            message.get("content", "")
            for message in reversed(history)
            if message.get("role") == "user" and message.get("content", "").strip()
        ),
        "",
    )
    if not previous_user_message:
        return query
    previous_query = rule_based_rewrite(previous_user_message)
    return f"{previous_query} {query}"[:500]


def _rewrite_with_llm(query: str, history: list[dict[str, str]]) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    history_text = "\n".join(
        f"{message.get('role', 'user')}: {message.get('content', '')}"
        for message in history
    )
    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": REWRITE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Lịch sử:\n{history_text or '(trống)'}\n\nCâu hỏi mới:\n{query}",
            },
        ],
        temperature=0,
        max_tokens=100,
    )
    rewritten = (response.choices[0].message.content or "").strip().strip('"`')
    return " ".join(rewritten.split())[:500]
