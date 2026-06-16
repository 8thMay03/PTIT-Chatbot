from app.core.config import settings
from app.generation.prompts import SYSTEM_PROMPT, build_context_prompt


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
