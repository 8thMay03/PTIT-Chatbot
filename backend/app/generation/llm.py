import logging
import re
from collections.abc import Collection, Iterator

from app.core.config import settings
from app.generation.citations import numbered_contexts, public_citations
from app.generation.prompts import SYSTEM_PROMPT, build_context_prompt
from app.generation.refusal import CITATION_RE, NO_CONTEXT_ANSWER, is_refusal
from app.llm import (
    CONTENT_DELTA,
    BaseLLMProvider,
    LLMBudget,
    LLMStreamError,
    StreamDelta,
    describe_error,
    get_llm_provider,
)
from app.llm.base import error_status_code

logger = logging.getLogger(__name__)

# Lý do trả câu trả lời dự phòng extractive (BE-12): chưa cấu hình LLM, hoặc LLM đã cấu
# hình nhưng lỗi/hết deadline. Lỗi cấu hình phía provider (401/403, key sai) cũng là
# "unavailable" với người dùng; chi tiết nằm ở log và trang admin "thử kết nối".
FALLBACK_NOT_CONFIGURED = "not_configured"
FALLBACK_UNAVAILABLE = "unavailable"
_FALLBACK_INTROS = {
    FALLBACK_NOT_CONFIGURED: "Chưa cấu hình mô hình ngôn ngữ (LLM) nên mình trả về các đoạn liên quan nhất:",
    FALLBACK_UNAVAILABLE: "Mô hình ngôn ngữ đang tạm thời gặp sự cố nên mình trả về các đoạn liên quan nhất:",
}

# Model không hỗ trợ mức suy luận (ví dụ gpt-4.1-mini với `reasoning_effort`, Gemini
# 2.0 với `thinkingConfig`) trả 400/422: gửi lại một lần không kèm tham số đó.
_UNSUPPORTED_PARAM_STATUS = frozenset({400, 422})


def _effort_kwargs(reasoning_effort: str | None) -> dict[str, str]:
    return {"reasoning_effort": reasoning_effort} if reasoning_effort else {}


def _rejected_effort(exc: Exception, reasoning_effort: str | None) -> bool:
    if not reasoning_effort or error_status_code(exc) not in _UNSUPPORTED_PARAM_STATUS:
        return False
    logger.info(
        "LLM rejected reasoning_effort=%s (%s); retrying without it.", reasoning_effort, describe_error(exc)
    )
    return True


def answer_with_llm(
    question: str,
    contexts: list[dict],
    history: list[dict[str, str]] | None = None,
    provider: BaseLLMProvider | None = None,
    budget: LLMBudget | None = None,
    reasoning_effort: str | None = None,
) -> str:
    """``reasoning_effort``: một giá trị của ``REASONING_EFFORTS``; None = model tự quyết."""
    if not contexts:
        return NO_CONTEXT_ANSWER

    llm = provider or get_llm_provider()
    if not llm.is_configured():
        return _extractive_answer(contexts, FALLBACK_NOT_CONFIGURED)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_context_prompt(question, contexts, history)},
    ]
    try:
        try:
            answer = llm.generate(
                messages, temperature=settings.llm_temperature, budget=budget, **_effort_kwargs(reasoning_effort)
            )
        except Exception as exc:
            if not _rejected_effort(exc, reasoning_effort):
                raise
            answer = llm.generate(messages, temperature=settings.llm_temperature, budget=budget)
    except Exception as exc:
        logger.warning("LLM generation failed: %s. Falling back to extractive answer.", describe_error(exc))
        return _extractive_answer(contexts, FALLBACK_UNAVAILABLE)

    return _normalize_answer_citations(answer, contexts)


def stream_answer_deltas_with_llm(
    question: str,
    contexts: list[dict],
    history: list[dict[str, str]] | None = None,
    provider: BaseLLMProvider | None = None,
    budget: LLMBudget | None = None,
    reasoning_effort: str | None = None,
) -> Iterator[StreamDelta]:
    """Yield typed answer deltas (content + reasoning) as they arrive.

    ``reasoning_effort`` như ở ``answer_with_llm``; model từ chối tham số này trước
    token đầu tiên thì stream lại không kèm nó.

    - Lỗi trước token đầu tiên: yield câu trả lời dự phòng extractive (giống ``answer_with_llm``).
    - Lỗi sau khi đã stream một phần: raise :class:`LLMStreamError` để caller (ví dụ
      ``/chat/stream``) gửi event báo lỗi thay vì nối thêm text dự phòng lộn xộn.
    """
    if not contexts:
        yield StreamDelta(kind=CONTENT_DELTA, text=NO_CONTEXT_ANSWER)
        return

    llm = provider or get_llm_provider()
    if not llm.is_configured():
        yield StreamDelta(kind=CONTENT_DELTA, text=_extractive_answer(contexts, FALLBACK_NOT_CONFIGURED))
        return

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_context_prompt(question, contexts, history)},
    ]
    emitted = 0
    try:
        try:
            for delta in llm.generate_stream_deltas(
                messages, temperature=settings.llm_temperature, budget=budget, **_effort_kwargs(reasoning_effort)
            ):
                emitted += 1
                yield delta
        except Exception as exc:
            if emitted or not _rejected_effort(exc, reasoning_effort):
                raise
            for delta in llm.generate_stream_deltas(messages, temperature=settings.llm_temperature, budget=budget):
                emitted += 1
                yield delta
    except Exception as exc:
        if emitted == 0:
            logger.warning(
                "LLM streaming failed before first token: %s. Falling back to extractive answer.",
                describe_error(exc),
            )
            yield StreamDelta(kind=CONTENT_DELTA, text=_extractive_answer(contexts, FALLBACK_UNAVAILABLE))
            return
        logger.warning("LLM streaming failed after %d token(s): %s.", emitted, describe_error(exc))
        # Không nhét thông điệp của provider vào lỗi: chỉ tên lớp + mã HTTP.
        status = error_status_code(exc)
        raise LLMStreamError(
            f"LLM streaming failed: {type(exc).__name__}" + (f" (HTTP {status})" if status is not None else ""),
            status_code=status,
        ) from exc


def stream_answer_with_llm(
    question: str,
    contexts: list[dict],
    history: list[dict[str, str]] | None = None,
    provider: BaseLLMProvider | None = None,
    budget: LLMBudget | None = None,
    reasoning_effort: str | None = None,
) -> Iterator[str]:
    """Yield answer text deltas only (reasoning deltas are filtered out)."""
    for delta in stream_answer_deltas_with_llm(
        question, contexts, history=history, provider=provider, budget=budget, reasoning_effort=reasoning_effort
    ):
        if delta.kind == CONTENT_DELTA:
            yield delta.text


def _extractive_answer(contexts: list[dict], reason: str = FALLBACK_UNAVAILABLE) -> str:
    excerpts = []
    for item, (citation_id, _) in zip(contexts[:3], numbered_contexts(contexts)[:3]):
        text = " ".join(item["text"].split())
        excerpts.append(f"- {text[:700]} [{citation_id}]")

    return _FALLBACK_INTROS[reason] + "\n" + "\n".join(excerpts)


def _normalize_answer_citations(answer: str, contexts: list[dict]) -> str:
    """Remove invented citation numbers; never add one (RAG-22).

    Câu từ chối mất mọi ``[n]``. Câu trả lời không có ``[n]`` được giữ nguyên: số
    citation tự gắn (trước đây là ``[1]``) trỏ vào nguồn không hỗ trợ câu đó.
    """
    valid_ids = {citation["citation_id"] for citation in public_citations(contexts)}
    if is_refusal(answer, valid_ids):
        return _strip_citations(answer, keep_ids=())
    return _strip_citations(answer, keep_ids=valid_ids)


def _strip_citations(answer: str, keep_ids: Collection[int]) -> str:
    def replace(match: re.Match[str]) -> str:
        return match.group(0) if int(match.group(2)) in keep_ids else ""

    # Xóa cả khoảng trắng ngay trước [n] để không để lại "tài liệu ." sau khi bỏ số.
    return re.sub(rf"([ \t]*){CITATION_RE.pattern}", replace, answer).strip()
