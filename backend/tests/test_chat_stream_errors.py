import json
from types import SimpleNamespace


from app.api import routes
from app.api.schemas import ChatRequest
from app.llm import LLMStreamError

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
    monkeypatch.setattr(
        routes.rag_chain,
        "retrieve_context",
        lambda message, top_k, history=None: dict(RETRIEVAL),
    )

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


async def test_stream_providers_error_before_first_token_returns_extractive_fallback(
    monkeypatch,
) -> None:
    stored_messages: list[dict] = []
    _prepare(monkeypatch, stored_messages)

    def fake_stream(question, contexts, history=None, provider=None):
        # Mô phỏng `stream_answer_with_llm` khi provider lỗi trước token đầu tiên:
        # toàn bộ câu trả lời dự phòng được yield như một delta bình thường.
        yield EXTRACTIVE_FALLBACK

    monkeypatch.setattr(routes, "stream_answer_with_llm", fake_stream)

    response = routes.chat_stream(
        ChatRequest(message="Học phí?"), session=SimpleNamespace(commit=lambda: None)
    )
    events = await _read_events(response)

    assert [event["type"] for event in events] == ["start", "delta", "done"]
    done_event = events[-1]
    assert done_event["answer"] == EXTRACTIVE_FALLBACK
    # Giống /chat: câu trả lời dự phòng được lưu bình thường, không đánh dấu lỗi.
    assistant = stored_messages[-1]
    assert assistant["role"] == "assistant"
    assert assistant["content"] == EXTRACTIVE_FALLBACK
    assert "error" not in assistant["metadata"]


async def test_stream_providers_error_after_tokens_emits_error_event_without_fallback(
    monkeypatch,
) -> None:
    stored_messages: list[dict] = []
    _prepare(monkeypatch, stored_messages)

    def fake_stream(question, contexts, history=None, provider=None):
        yield "Học "
        yield "phí "
        raise LLMStreamError("LLM streaming failed: boom")

    monkeypatch.setattr(routes, "stream_answer_with_llm", fake_stream)

    response = routes.chat_stream(
        ChatRequest(message="Học phí?"), session=SimpleNamespace(commit=lambda: None)
    )
    events = await _read_events(response)

    types = [event["type"] for event in events]
    assert types == ["start", "delta", "delta", "error"]
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
