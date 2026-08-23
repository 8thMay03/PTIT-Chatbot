import re

from app.core.config import settings


MULTI_QUERY_SYSTEM_PROMPT = """Tạo các truy vấn tìm kiếm tiếng Việt khác nhau cho câu hỏi về tài liệu PTIT.
Mỗi dòng chỉ chứa một truy vấn, không đánh số, không giải thích và không trả lời câu hỏi.
Giữ nguyên tên riêng, mã môn, con số và mốc thời gian.
Các truy vấn phải diễn đạt khác nhau nhưng giữ đúng ý định ban đầu."""

STOP_WORDS = {
    "ai", "bao", "biết", "có", "cho", "gì", "khi", "không", "là", "nào",
    "như", "ở", "sao", "thế", "thì", "tôi", "và", "về", "đâu", "được",
}

DOMAIN_EXPANSIONS = {
    "học phí": "học phí mức thu thời hạn đóng học phí",
    "cảnh báo học tập": "cảnh báo học tập cảnh báo học vụ điều kiện",
    "đăng ký học phần": "đăng ký học phần đăng ký môn học tín chỉ",
    "tốt nghiệp": "điều kiện xét công nhận tốt nghiệp",
    "học bổng": "điều kiện tiêu chuẩn xét học bổng",
}


from app.llm import BaseLLMProvider, get_llm_provider


class VietnameseMultiQueryGenerator:
    def __init__(self, llm_provider: BaseLLMProvider | None = None) -> None:
        self.llm_provider = llm_provider

    def generate(self, query: str) -> list[str]:
        if not settings.multi_query_enabled:
            return [query]

        queries = [query]
        llm = self.llm_provider or get_llm_provider()
        if settings.multi_query_use_llm and llm.is_configured():
            try:
                queries.extend(_generate_with_llm(query, llm=llm))
            except Exception:
                queries.extend(_rule_based_variants(query))
        else:
            queries.extend(_rule_based_variants(query))

        return _unique_queries(queries)[: settings.multi_query_count]


def _rule_based_variants(query: str) -> list[str]:
    terms = re.findall(r"\w+", query.casefold(), flags=re.UNICODE)
    keyword_query = " ".join(term for term in terms if term not in STOP_WORDS)
    variants = [keyword_query]

    expanded = query
    for phrase, expansion in DOMAIN_EXPANSIONS.items():
        if phrase in query:
            expanded = expanded.replace(phrase, expansion)
    if expanded != query:
        variants.append(expanded)
    return variants


def _generate_with_llm(query: str, llm: BaseLLMProvider | None = None) -> list[str]:
    provider = llm or get_llm_provider()
    messages = [
        {"role": "system", "content": MULTI_QUERY_SYSTEM_PROMPT},
        {"role": "user", "content": query},
    ]
    content = provider.generate(
        messages=messages,
        temperature=0.3,
        max_tokens=180,
    )
    return [re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", line) for line in content.splitlines()]


def _unique_queries(queries: list[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for query in queries:
        normalized = " ".join(query.split()).strip(" `\"'-")
        key = normalized.casefold()
        if normalized and key not in seen:
            seen.add(key)
            unique.append(normalized[:500])
    return unique
