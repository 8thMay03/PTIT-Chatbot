import pytest
from pydantic import ValidationError

from app.api.schemas import ChatRequest


def test_chat_request_uses_configured_default_top_k(monkeypatch) -> None:
    monkeypatch.setattr("app.api.schemas.settings.retrieval_default_top_k", 6)

    request = ChatRequest(message="Question")

    assert request.top_k is None
    assert request.effective_top_k == 6


def test_chat_request_rejects_top_k_above_configured_limit(monkeypatch) -> None:
    monkeypatch.setattr("app.api.schemas.settings.retrieval_max_top_k", 8)

    with pytest.raises(ValidationError):
        ChatRequest(message="Question", top_k=9)
