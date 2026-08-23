import logging
import re
from collections.abc import Iterator

from app.core.config import settings
from app.generation.citations import numbered_contexts, public_citations
from app.guardrails import OUT_OF_SCOPE_ANSWER
from app.generation.prompts import SYSTEM_PROMPT, build_context_prompt
from app.llm import BaseLLMProvider, get_llm_provider

logger = logging.getLogger(__name__)


def answer_with_llm(
    question: str,
    contexts: list[dict],
    history: list[dict[str, str]] | None = None,
    provider: BaseLLMProvider | None = None,
) -> str:
    if not contexts:
        return "Mình chưa tìm thấy thông tin phù hợp trong kho tài liệu."

    llm = provider or get_llm_provider()
    if not llm.is_configured():
        return _extractive_answer(contexts)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_context_prompt(question, contexts, history)},
    ]
    try:
        answer = llm.generate(messages, temperature=settings.llm_temperature)
    except Exception as exc:
        logger.warning("LLM generation failed: %s. Falling back to extractive answer.", exc)
        return _extractive_answer(contexts)

    return _normalize_answer_citations(answer, contexts)


def stream_answer_with_llm(
    question: str,
    contexts: list[dict],
    history: list[dict[str, str]] | None = None,
    provider: BaseLLMProvider | None = None,
) -> Iterator[str]:
    """Yield answer deltas as they arrive from the model."""
    if not contexts:
        yield "Mình chưa tìm thấy thông tin phù hợp trong kho tài liệu."
        return

    llm = provider or get_llm_provider()
    if not llm.is_configured():
        yield _extractive_answer(contexts)
        return

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_context_prompt(question, contexts, history)},
    ]
    try:
        yield from llm.generate_stream(messages, temperature=0.2)
    except Exception as exc:
        logger.warning("LLM streaming failed: %s. Falling back to extractive answer.", exc)
        yield _extractive_answer(contexts)


def _extractive_answer(contexts: list[dict]) -> str:
    excerpts = []
    for item, (citation_id, _) in zip(contexts[:3], numbered_contexts(contexts)[:3]):
        text = " ".join(item["text"].split())
        excerpts.append(f"- {text[:700]} [{citation_id}]")

    return (
        "Chưa cấu hình API Key cho LLM nên mình trả về các đoạn liên quan nhất:\n"
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
    if normalized in {"Chưa tìm thấy thông tin này trong tài liệu.", OUT_OF_SCOPE_ANSWER}:
        return normalized

    cited_ids = {int(value) for value in re.findall(r"\[(\d+)\]", normalized)}
    if not cited_ids:
        normalized = f"{normalized} [{min(valid_ids)}]"
    return normalized
