from app.core.config import settings


SYSTEM_PROMPT = """Bạn là chatbot tư vấn dựa trên tài liệu nội bộ PTIT.
Chỉ trả lời bằng thông tin có trong ngữ cảnh được cung cấp.
Nếu chưa đủ dữ liệu, hãy nói rõ là chưa tìm thấy thông tin trong tài liệu."""


def build_context_prompt(question: str, contexts: list[dict]) -> str:
    context_text = "\n\n".join(
        f"[{index + 1}] {item['text']}" for index, item in enumerate(contexts)
    )
    return f"Ngữ cảnh:\n{context_text}\n\nCâu hỏi: {question}\n\nTrả lời bằng tiếng Việt:"


def answer_with_llm(question: str, contexts: list[dict]) -> str:
    if not contexts:
        return "Mình chưa tìm thấy thông tin phù hợp trong kho tài liệu."

    if not settings.openai_api_key:
        return _extractive_answer(contexts)

    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_context_prompt(question, contexts)},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content or ""


def _extractive_answer(contexts: list[dict]) -> str:
    excerpts = []
    for item in contexts[:3]:
        text = " ".join(item["text"].split())
        excerpts.append(f"- {text[:700]}")

    return (
        "Chưa cấu hình OPENAI_API_KEY nên mình trả về các đoạn liên quan nhất:\n"
        + "\n".join(excerpts)
    )
