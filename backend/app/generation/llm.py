import re

from app.core.config import settings
from app.generation.citations import numbered_contexts, public_citations
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
    answer = response.choices[0].message.content or ""
    return _normalize_answer_citations(answer, contexts)


def _extractive_answer(contexts: list[dict]) -> str:
    excerpts = []
    for item, (citation_id, _) in zip(contexts[:3], numbered_contexts(contexts)[:3]):
        text = " ".join(item["text"].split())
        excerpts.append(f"- {text[:700]} [{citation_id}]")

    return (
        "Chưa cấu hình OPENAI_API_KEY nên mình trả về các đoạn liên quan nhất:\n"
        + "\n".join(excerpts)
    )


def _normalize_answer_citations(answer: str, contexts: list[dict]) -> str:
    """Remove invented citation numbers and ensure grounded answers cite a valid source."""
    valid_ids = {citation["citation_id"] for citation in public_citations(contexts)}
    if not answer.strip() or not valid_ids:
        return answer.strip()

    def keep_valid(match: re.Match[str]) -> str:
        return match.group(0) if int(match.group(1)) in valid_ids else ""

    normalized = re.sub(r"\[(\d+)\]", keep_valid, answer).strip()
    if normalized == "Chưa tìm thấy thông tin này trong tài liệu.":
        return normalized

    cited_ids = {int(value) for value in re.findall(r"\[(\d+)\]", normalized)}
    if not cited_ids:
        normalized = f"{normalized} [{min(valid_ids)}]"
    return normalized
