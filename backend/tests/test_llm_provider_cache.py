"""Tái dùng provider LLM theo dấu vân tay cấu hình (BE-12, AC-03).

``openai.OpenAI`` được thay bằng client giả đếm số lần khởi tạo, nên không có request
mạng; cache được reset mỗi test bởi fixture autouse trong conftest.
"""

from __future__ import annotations

import threading
from types import SimpleNamespace

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.api import routes
from app.core.config import settings
from app.core.config_store import PERSISTED_FIELDS
from app.generation.rag_chain import RagChain
from app.llm import BaseLLMProvider, OpenAIProvider, get_llm_provider, register_llm_provider
from app.llm.factory import LLM_SETTINGS_FIELDS
from app.main import app


class FakeOpenAI:
    """Thay ``openai.OpenAI``: ghi lại tham số khởi tạo, trả completion cố định."""

    instances: list[FakeOpenAI] = []

    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.calls = 0
        FakeOpenAI.instances.append(self)
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **params):
        self.calls += 1
        message = SimpleNamespace(content="Học phí là 20 triệu [1]")
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class StrongRetriever:
    def retrieve(self, question: str, top_k: int, dataset_ids: list[str] | None = None) -> list[dict]:
        return [
            {
                "source_name": "handbook.md",
                "heading": "Học phí",
                "section_path": "Học phí",
                "chunk_id": "chunk-1",
                "text": "Học phí năm 2026 là 20 triệu đồng.",
                "vector_score": 0.9,
                "bm25_score": 5.0,
                "bm25_norm_score": 0.6,
            }
        ]


@pytest.fixture(autouse=True)
def _restore_settings():
    snapshot = settings.model_dump()
    yield
    for field, value in snapshot.items():
        setattr(settings, field, value)


@pytest.fixture
def fake_openai(monkeypatch):
    FakeOpenAI.instances = []
    monkeypatch.setattr("openai.OpenAI", FakeOpenAI)
    settings.llm_provider = "openai"
    settings.openai_api_key = "sk-test-cache-key-0123456789"
    settings.openai_model = "gpt-cache-test"
    settings.openai_base_url = None
    return FakeOpenAI


@pytest.fixture
def chat_with_llm_steps(api_db, fake_openai, monkeypatch):
    """Lượt chat thật qua route, cả ba bước (rewrite, multi-query, trả lời) gọi LLM."""
    settings.query_rewrite_use_llm = True
    settings.multi_query_enabled = True
    settings.multi_query_use_llm = True
    settings.guardrail_scope_enabled = False
    settings.reranker_enabled = False
    monkeypatch.setattr(routes, "rag_chain", RagChain(retriever_=StrongRetriever()))
    return fake_openai


def test_llm_settings_fields_cover_persisted_llm_fields() -> None:
    llm_prefixes = ("llm_", "openai_", "gemini_", "azure_openai_", "openai_compatible_")
    # llm_temperature được đọc lúc gọi, không lúc tạo provider; llm_profile_id chỉ là lựa
    # chọn, chọn profile chép các trường provider/model/key vào settings.
    not_provider_fields = {"llm_temperature", "llm_profile_id"}
    persisted_llm = {f for f in PERSISTED_FIELDS if f.startswith(llm_prefixes)} - not_provider_fields
    assert persisted_llm <= set(LLM_SETTINGS_FIELDS)
    assert set(LLM_SETTINGS_FIELDS) <= set(settings.model_dump())


def test_same_config_returns_same_provider(fake_openai) -> None:
    first = get_llm_provider()
    assert get_llm_provider() is first
    assert get_llm_provider("openai") is first

    first.generate([{"role": "user", "content": "a"}])
    get_llm_provider().generate([{"role": "user", "content": "b"}])

    assert len(fake_openai.instances) == 1
    assert fake_openai.instances[0].calls == 2
    # Một tầng retry: SDK không tự retry.
    assert fake_openai.instances[0].kwargs["max_retries"] == 0


def test_two_chat_turns_share_one_provider_and_client(chat_with_llm_steps) -> None:
    client = TestClient(app)
    for message in ("Học phí bao nhiêu?", "Còn học phí kỳ sau?"):
        response = client.post("/api/chat", json={"message": message})
        assert response.status_code == 200
        assert response.json()["answer"].startswith("Học phí là 20 triệu")

    assert len(chat_with_llm_steps.instances) == 1
    # Hai lượt x (rewrite + multi-query + trả lời).
    assert chat_with_llm_steps.instances[0].calls == 6


def test_put_config_model_change_creates_new_provider(chat_with_llm_steps, admin_client) -> None:
    before = get_llm_provider()
    assert admin_client.post("/api/chat", json={"message": "Học phí bao nhiêu?"}).status_code == 200
    assert get_llm_provider() is before

    response = admin_client.put("/api/config", json={"llm": {"openai_model": "gpt-cache-test-2"}})
    assert response.status_code == 200, response.text

    after = get_llm_provider()
    assert after is not before
    assert after.model_name == "gpt-cache-test-2"
    assert admin_client.post("/api/chat", json={"message": "Học phí bao nhiêu?"}).status_code == 200
    assert len(chat_with_llm_steps.instances) == 2


def test_key_change_creates_new_provider(fake_openai) -> None:
    before = get_llm_provider()
    settings.openai_api_key = "sk-test-cache-key-rotated-9876543210"
    after = get_llm_provider()

    assert after is not before
    assert after.api_key == "sk-test-cache-key-rotated-9876543210"


def test_activating_llm_profile_creates_new_provider(fake_openai, admin_client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "config_encryption_key", Fernet.generate_key().decode())
    before = get_llm_provider()

    created = admin_client.post(
        "/api/model-profiles",
        json={
            "kind": "llm",
            "name": "GPT profile",
            "provider": "openai",
            "model": "gpt-profile-model",
            "api_key": "sk-test-profile-key-0123456789",
        },
    )
    assert created.status_code == 201, created.text
    profile = next(p for p in created.json()["profiles"] if p["name"] == "GPT profile")
    activated = admin_client.post("/api/model-profiles/activate", json={"kind": "llm", "profile_id": profile["id"]})
    assert activated.status_code == 200, activated.text

    after = get_llm_provider()
    assert after is not before
    assert after.model_name == "gpt-profile-model"


def test_concurrent_callers_get_one_instance(fake_openai) -> None:
    results: list[BaseLLMProvider] = []
    barrier = threading.Barrier(20)

    def worker() -> None:
        barrier.wait()
        provider = get_llm_provider()
        provider.generate([{"role": "user", "content": "x"}])
        results.append(provider)

    threads = [threading.Thread(target=worker) for _ in range(20)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(10)

    assert len(results) == 20
    assert len({id(provider) for provider in results}) == 1
    # Client SDK được tạo một lần dù 20 thread cùng gọi lần đầu.
    assert len(fake_openai.instances) == 1


def test_register_provider_replaces_cached_instance() -> None:
    class Custom(OpenAIProvider):
        pass

    register_llm_provider("cache_custom", lambda: Custom(api_key="sk-a"))
    first = get_llm_provider("cache_custom")
    assert get_llm_provider("cache_custom") is first

    register_llm_provider("cache_custom", lambda: Custom(api_key="sk-b"))
    second = get_llm_provider("cache_custom")
    assert second is not first
    assert second.api_key == "sk-b"
