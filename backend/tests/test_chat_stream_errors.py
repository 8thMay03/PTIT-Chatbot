import json
from types import SimpleNamespace

import pytest

from app.api import routes
from app.api.schemas import ChatRequest
from app.llm import CONTENT_DELTA, LLMStreamError, REASONING_DELTA, StreamDelta

EXTRACTIVE_FALLBACK = (
    "Chưa cấu hình API Key cho LLM nên mình trả về các đoạn liên quan nhất:\n"
    "- Nội dung học phí. [1]"
)

RETRIEVAL = {
    "contexts": [
        {
            "source_name": "handbook.md",
            "heading": "Học phí",
            "section_path": "Học phí",
            "text": "Nội dung học phí.",
        }
    ],
    "retrieval_debug": {
        "rewritten_query": "học phí",
        "retrieved_chunks": [],
        "strong_context": True,
    },
    "strong_context": True,
    "guardrail_allowed": True,
}


def _prepare(monkeypatch, stored_messages) -> None:
    monkeypatch.setattr(routes.settings, "conversation_memory_enabled", False)
    monkeypatch.setattr(
        routes,
        "ensure_conversation",
        lambda session, conversation_id, user_id, title: SimpleNamespace(id="conversation-err-1"),
    )

    def fake_iter_retrieve(message, top_k, history=None):
        yield {"result": dict(RETRIEVAL)}

    monkeypatch.setattr(routes.rag_chain, "iter_retrieve_context", fake_iter_retrieve)

    def fake_add_message(session, conversation_id, role, content, metadata=None):
        stored_messages.append({"role": role, "content": content, "metadata": metadata})
        return SimpleNamespace(id=f"{role}-message")

    monkeypatch.setattr(routes, "add_message", fake_add_message)
    monkeypatch.setattr(routes, "add_message_sources", lambda *args: None)


async def _read_events(response) -> list[dict]:
    events = []
    async for line in response.body_iterator:
        if line.strip():
            events.append(json.loads(line))
    return events


async def test_stream_providers_error_before_first_token_returns_extractive_fallback(monkeypatch) -> None:
    stored_messages: list[dict] = []
    _prepare(monkeypatch, stored_messages)

    def fake_stream(question, contexts, history=None, provider=None):
        # Mô phỏng `stream_answer_deltas_with_llm` khi provider lỗi trước token
        # đầu tiên: toàn bộ câu trả lời dự phòng được yield như một delta thường.
        yield StreamDelta(kind=CONTENT_DELTA, text=EXTRACTIVE_FALLBACK)

    monkeypatch.setattr(routes, "stream_answer_deltas_with_llm", fake_stream)

    response = routes.chat_stream(ChatRequest(message="Học phí?"), session=SimpleNamespace(commit=lambda: None))
    events = await _read_events(response)

    # Bước retrieval bị mock bỏ qua nên chỉ còn event step "generate".
    assert [event["type"] for event in events] == ["start", "step", "delta", "done"]
    done_event = events[-1]
    assert done_event["answer"] == EXTRACTIVE_FALLBACK
    # Giống /chat: câu trả lời dự phòng được lưu bình thường, không đánh dấu lỗi.
    assistant = stored_messages[-1]
    assert assistant["role"] == "assistant"
    assert assistant["content"] == EXTRACTIVE_FALLBACK
    assert "error" not in assistant["metadata"]


async def test_stream_providers_error_after_tokens_emits_error_event_without_fallback(monkeypatch) -> None:
    stored_messages: list[dict] = []
    _prepare(monkeypatch, stored_messages)

    def fake_stream(question, contexts, history=None, provider=None):
        yield StreamDelta(kind=CONTENT_DELTA, text="Học ")
        yield StreamDelta(kind=CONTENT_DELTA, text="phí ")
        raise LLMStreamError("LLM streaming failed: boom")

    monkeypatch.setattr(routes, "stream_answer_deltas_with_llm", fake_stream)

    response = routes.chat_stream(ChatRequest(message="Học phí?"), session=SimpleNamespace(commit=lambda: None))
    events = await _read_events(response)

    types = [event["type"] for event in events]
    assert types == ["start", "step", "delta", "delta", "error"]
    assert not any(EXTRACTIVE_FALLBACK in event.get("content", "") for event in events)

    error_event = events[-1]
    assert error_event["message"] == "LLM streaming failed: boom"

    assistant = stored_messages[-1]
    assert assistant["role"] == "assistant"
    # Không nối thêm câu trả lời dự phòng: chỉ phần text đã stream được lưu.
    assert assistant["content"] == "Học phí"
    assert assistant["metadata"]["error"]["message"] == "LLM streaming failed: boom"
    assert assistant["metadata"]["error"]["type"] == "llm_stream"
    assert "sources" in assistant["metadata"]


async def test_stream_emits_step_events_and_persists_timeline(monkeypatch) -> None:
    stored_messages: list[dict] = []
    _prepare(monkeypatch, stored_messages)

    def fake_iter_retrieve(message, top_k, history=None):
        yield {"step": "query_rewrite", "detail": {"rewritten_query": "học phí"}, "elapsed_ms": 3}
        yield {"step": "retrieve", "detail": {"candidate_count": 5}, "elapsed_ms": 12}
        yield {"result": dict(RETRIEVAL)}

    monkeypatch.setattr(routes.rag_chain, "iter_retrieve_context", fake_iter_retrieve)
    monkeypatch.setattr(
        routes,
        "stream_answer_deltas_with_llm",
        lambda question, contexts, history=None, provider=None: iter(
            [StreamDelta(kind=CONTENT_DELTA, text="Trả lời [1]")]
        ),
    )

    response = routes.chat_stream(ChatRequest(message="Học phí?"), session=SimpleNamespace(commit=lambda: None))
    events = await _read_events(response)

    step_events = [event for event in events if event["type"] == "step"]
    assert [(event["step"], event["status"]) for event in step_events] == [
        ("query_rewrite", "done"),
        ("retrieve", "done"),
        ("generate", "start"),
    ]
    assert all(isinstance(event["elapsed_ms"], int) for event in step_events)

    done_event = next(event for event in events if event["type"] == "done")
    persisted_steps = done_event["steps"]
    assert [entry["step"] for entry in persisted_steps] == ["query_rewrite", "retrieve", "generate"]
    # Bước generate được ghi lại với status done và elapsed_ms thực tế.
    assert persisted_steps[-1]["status"] == "done"
    assert persisted_steps[-1]["elapsed_ms"] >= 0

    assistant = stored_messages[-1]
    assert assistant["metadata"]["steps"] == persisted_steps


async def test_stream_emits_reasoning_events_and_persists_reasoning(monkeypatch) -> None:
    stored_messages: list[dict] = []
    _prepare(monkeypatch, stored_messages)
    monkeypatch.setattr(routes.settings, "llm_reasoning_stream_enabled", True)

    def fake_stream(question, contexts, history=None, provider=None):
        yield StreamDelta(kind=REASONING_DELTA, text="Người dùng hỏi học phí, ")
        yield StreamDelta(kind=REASONING_DELTA, text="tìm trong kho điều học phí.")
        yield StreamDelta(kind=CONTENT_DELTA, text="Trả lời [1]")

    monkeypatch.setattr(routes, "stream_answer_deltas_with_llm", fake_stream)

    response = routes.chat_stream(ChatRequest(message="Học phí?"), session=SimpleNamespace(commit=lambda: None))
    events = await _read_events(response)

    reasoning_events = [event for event in events if event["type"] == "reasoning"]
    assert "".join(event["content"] for event in reasoning_events) == (
        "Người dùng hỏi học phí, tìm trong kho điều học phí."
    )
    # Reasoning phát trước phần câu trả lời.
    assert events.index(reasoning_events[-1]) < next(
        i for i, event in enumerate(events) if event["type"] == "delta"
    )

    done_event = next(event for event in events if event["type"] == "done")
    assert done_event["reasoning"] == "Người dùng hỏi học phí, tìm trong kho điều học phí."

    assistant = stored_messages[-1]
    assert assistant["metadata"]["reasoning"] == "Người dùng hỏi học phí, tìm trong kho điều học phí."


async def test_stream_hides_reasoning_when_disabled(monkeypatch) -> None:
    stored_messages: list[dict] = []
    _prepare(monkeypatch, stored_messages)
    monkeypatch.setattr(routes.settings, "llm_reasoning_stream_enabled", False)

    def fake_stream(question, contexts, history=None, provider=None):
        yield StreamDelta(kind=REASONING_DELTA, text="Suy luận bí mật")
        yield StreamDelta(kind=CONTENT_DELTA, text="Trả lời [1]")

    monkeypatch.setattr(routes, "stream_answer_deltas_with_llm", fake_stream)

    response = routes.chat_stream(ChatRequest(message="Học phí?"), session=SimpleNamespace(commit=lambda: None))
    events = await _read_events(response)

    assert not any(event["type"] == "reasoning" for event in events)
    done_event = next(event for event in events if event["type"] == "done")
    assert done_event["reasoning"] is None
    assistant = stored_messages[-1]
    assert "reasoning" not in assistant["metadata"]
