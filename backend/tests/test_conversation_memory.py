from types import SimpleNamespace

from app.api.schemas import ChatRequest
from app.api import routes
from app.db.repositories import limit_history


def test_limit_history_keeps_newest_messages_within_both_limits() -> None:
    messages = [
        {"role": "user", "content": "old question"},
        {"role": "assistant", "content": "old answer"},
        {"role": "user", "content": "new question"},
        {"role": "assistant", "content": "new answer"},
    ]

    history = limit_history(messages, max_messages=3, max_chars=22)

    assert history == [
        {"role": "user", "content": "new question"},
        {"role": "assistant", "content": "new answer"},
    ]


def test_limit_history_can_be_disabled_with_zero_budget() -> None:
    assert limit_history([{"role": "user", "content": "question"}], 0, 100) == []


def test_chat_persists_retrieval_debug_on_user_message(monkeypatch) -> None:
    retrieval_debug = {
        "rewritten_query": "điều kiện tốt nghiệp",
        "retrieved_chunks": [{"rank": 1, "chunk_id": "chunk-1", "score": 0.8}],
        "strong_context": True,
    }
    stored_messages = []

    monkeypatch.setattr(routes.settings, "conversation_memory_enabled", False)
    monkeypatch.setattr(
        routes,
        "ensure_conversation",
        lambda session, conversation_id, user_id, title: SimpleNamespace(id="conversation-1"),
    )
    monkeypatch.setattr(
        routes.rag_chain,
        "answer",
        lambda message, top_k, history: {
            "answer": "Câu trả lời [1]",
            "sources": [],
            "contexts": [],
            "retrieval_debug": retrieval_debug,
        },
    )

    def fake_add_message(session, conversation_id, role, content, metadata=None):
        stored_messages.append({"role": role, "content": content, "metadata": metadata})
        return SimpleNamespace(id=f"{role}-message")

    monkeypatch.setattr(routes, "add_message", fake_add_message)
    monkeypatch.setattr(routes, "add_message_sources", lambda *args: None)
    session = SimpleNamespace(commit=lambda: None)

    routes.chat(ChatRequest(message="Điều kiện tốt nghiệp?"), session=session)

    assert stored_messages[0] == {
        "role": "user",
        "content": "Điều kiện tốt nghiệp?",
        "metadata": {"retrieval_debug": retrieval_debug},
    }
