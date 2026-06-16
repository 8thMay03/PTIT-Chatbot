SYSTEM_PROMPT = """Bạn là chatbot tư vấn dựa trên tài liệu nội bộ PTIT.
Chỉ trả lời bằng thông tin có trong ngữ cảnh được cung cấp.
Nếu chưa đủ dữ liệu, hãy nói rõ là chưa tìm thấy thông tin trong tài liệu."""


def build_context_prompt(question: str, contexts: list[dict]) -> str:
    context_text = "\n\n".join(
        f"[{index + 1}] {item['text']}" for index, item in enumerate(contexts)
    )
    return f"Ngữ cảnh:\n{context_text}\n\nCâu hỏi: {question}\n\nTrả lời bằng tiếng Việt:"
