"""Deadline tổng cho phần LLM của một lượt chat (BE-12, AC-02).

Đồng hồ giả: ``LLMBudget`` nhận ``clock``; ``time.sleep`` của backoff tiến đồng hồ; transport
giả "treo" bằng cách tiến đồng hồ đúng bằng read timeout của request rồi ném
``httpx.ReadTimeout``. Không có lời gọi mạng hay chờ thật.
"""

from __future__ import annotations

import json

import httpx
import pytest

from app.api import routes
from app.generation.multi_query import MULTI_QUERY_SYSTEM_PROMPT, VietnameseMultiQueryGenerator
from app.generation.query_rewriter import REWRITE_SYSTEM_PROMPT, VietnameseQueryRewriter
from app.generation.rag_chain import RagChain
from app.llm import LLMBudget, LLMDeadlineExceeded, OpenAIProvider
from app.main import app
from fastapi.testclient import TestClient

DEADLINE = 60.0
UNAVAILABLE_PREFIX = "Mô hình ngôn ngữ đang tạm thời gặp sự cố"


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


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
            }
        ]


def _step(request: httpx.Request) -> str:
    """Bước gọi LLM, suy từ system prompt của request."""
    system = json.loads(request.content)["messages"][0]["content"]
    if system == REWRITE_SYSTEM_PROMPT:
        return "rewrite"
    if system == MULTI_QUERY_SYSTEM_PROMPT:
        return "multi_query"
    return "answer"


class LLMTransport(httpx.MockTransport):
    """Ghi lại (bước, read timeout) của từng request; ``behaviour`` quyết định response."""

    def __init__(self, clock: FakeClock, behaviour: str) -> None:
        self.clock = clock
        self.behaviour = behaviour
        self.calls: list[tuple[str, float]] = []
        self.bodies: list[dict] = []
        super().__init__(self._handle)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        read_timeout = request.extensions["timeout"]["read"]
        self.calls.append((_step(request), read_timeout))
        self.bodies.append(json.loads(request.content))
        if self.behaviour == "hang":
            self.clock.now += read_timeout
            raise httpx.ReadTimeout("timed out", request=request)
        return httpx.Response(503, json={"error": {"message": "overloaded"}})


@pytest.fixture
def clock(monkeypatch) -> FakeClock:
    fake = FakeClock()
    monkeypatch.setattr("app.llm.base.time.sleep", fake.sleep)
    return fake


@pytest.fixture
def llm_steps_enabled(monkeypatch) -> None:
    monkeypatch.setattr("app.core.config.settings.query_rewrite_use_llm", True)
    monkeypatch.setattr("app.core.config.settings.multi_query_enabled", True)
    monkeypatch.setattr("app.core.config.settings.multi_query_use_llm", True)
    monkeypatch.setattr("app.core.config.settings.guardrail_scope_enabled", False)
    monkeypatch.setattr("app.core.config.settings.reranker_enabled", False)


def _provider(transport: httpx.MockTransport) -> OpenAIProvider:
    return OpenAIProvider(
        api_key="sk-test-budget-key",
        model_name="gpt-test",
        timeout=30.0,
        max_retries=2,
        http_client=httpx.Client(transport=transport),
    )


def _chain(provider: OpenAIProvider) -> RagChain:
    return RagChain(
        retriever_=StrongRetriever(),
        query_rewriter=VietnameseQueryRewriter(llm_provider=provider),
        multi_query_generator=VietnameseMultiQueryGenerator(llm_provider=provider),
        llm_provider=provider,
    )


# ==========================================
# LLMBudget
# ==========================================
def test_budget_remaining_child_and_degraded_propagation() -> None:
    clock = FakeClock()
    budget = LLMBudget(60, clock=clock)
    assert budget.remaining() == pytest.approx(60)

    child = budget.child(10)
    clock.now += 4
    assert child.remaining() == pytest.approx(6)
    assert budget.remaining() == pytest.approx(56)
    # Budget con không sống lâu hơn cha.
    assert budget.child(1000).remaining() == pytest.approx(56)

    child.degraded = True
    assert budget.degraded is True

    clock.now += 100
    assert budget.expired() and child.expired()


def test_optional_step_budget() -> None:
    clock = FakeClock()
    budget = LLMBudget(60, clock=clock)

    step = budget.optional_step(attempt_timeout=30)
    assert step is not None and step.remaining() == pytest.approx(30)

    clock.now += 52  # còn 8s < 30/3
    assert budget.optional_step(attempt_timeout=30) is None

    fresh = LLMBudget(60, clock=clock)
    fresh.degraded = True
    assert fresh.optional_step(attempt_timeout=30) is None

    assert LLMBudget.unlimited().optional_step(attempt_timeout=30) is not None


def test_attempt_timeout_is_capped_by_remaining_and_budget_not_sent_to_api(clock) -> None:
    transport = LLMTransport(clock, behaviour="hang")
    provider = _provider(transport)

    with pytest.raises(Exception):
        provider.generate([{"role": "user", "content": "Học phí?"}], budget=LLMBudget(12, clock=clock))

    # 12s còn lại < LLM_TIMEOUT 30s: lần thử đầu chỉ được 12s, không còn thời gian thử lại.
    assert [timeout for _, timeout in transport.calls] == [pytest.approx(12)]
    assert all("budget" not in body for body in transport.bodies)


def test_expired_budget_skips_call_without_request(clock) -> None:
    transport = LLMTransport(clock, behaviour="hang")
    budget = LLMBudget(0.5, clock=clock)

    with pytest.raises(LLMDeadlineExceeded):
        _provider(transport).generate([{"role": "user", "content": "Học phí?"}], budget=budget)

    assert transport.calls == []
    assert budget.degraded is True


# ==========================================
# Một lượt chat trong rag_chain
# ==========================================
def test_hanging_llm_turn_finishes_within_deadline(clock, llm_steps_enabled) -> None:
    transport = LLMTransport(clock, behaviour="hang")
    started = clock.now

    result = _chain(_provider(transport)).answer("Học phí bao nhiêu?", budget=LLMBudget(DEADLINE, clock=clock))

    assert clock.now - started <= DEADLINE + 1e-6
    assert result["answer"].startswith(UNAVAILABLE_PREFIX)
    # Rewrite chỉ được nửa thời gian (30s) rồi đánh dấu LLM sập -> multi-query bỏ LLM;
    # sinh câu trả lời dùng phần còn lại.
    assert transport.calls == [("rewrite", pytest.approx(30)), ("answer", pytest.approx(30))]


def test_failed_optional_step_marks_degraded_and_skips_multi_query(clock, llm_steps_enabled) -> None:
    transport = LLMTransport(clock, behaviour="503")
    budget = LLMBudget(DEADLINE, clock=clock)
    started = clock.now

    result = _chain(_provider(transport)).answer("Học phí bao nhiêu?", budget=budget)

    steps = [step for step, _ in transport.calls]
    assert steps.count("rewrite") == 3
    assert "multi_query" not in steps
    # Bước sinh câu trả lời vẫn được thử (bước bắt buộc).
    assert steps.count("answer") >= 1
    assert budget.degraded is True
    assert result["answer"].startswith(UNAVAILABLE_PREFIX)
    assert clock.now - started <= DEADLINE


def test_little_time_left_skips_optional_steps(clock, llm_steps_enabled) -> None:
    transport = LLMTransport(clock, behaviour="hang")

    result = _chain(_provider(transport)).answer("Học phí bao nhiêu?", budget=LLMBudget(8, clock=clock))

    assert transport.calls == [("answer", pytest.approx(8))]
    assert result["answer"].startswith(UNAVAILABLE_PREFIX)


def test_without_budget_behaviour_is_unchanged(clock, llm_steps_enabled) -> None:
    transport = LLMTransport(clock, behaviour="503")

    _chain(_provider(transport)).answer("Học phí bao nhiêu?")

    steps = [step for step, _ in transport.calls]
    # Không có budget (gọi trực tiếp/eval): mỗi bước thử đủ 1 + LLM_MAX_RETRIES lần.
    assert steps == ["rewrite"] * 3 + ["multi_query"] * 3 + ["answer"] * 3


# ==========================================
# Route chat
# ==========================================
@pytest.fixture
def hanging_chat(api_db, clock, llm_steps_enabled, monkeypatch) -> LLMTransport:
    transport = LLMTransport(clock, behaviour="hang")
    provider = _provider(transport)
    monkeypatch.setattr(routes, "rag_chain", _chain(provider))
    monkeypatch.setattr("app.generation.llm.get_llm_provider", lambda: provider)
    monkeypatch.setattr(routes, "LLMBudget", lambda seconds: LLMBudget(seconds, clock=clock))
    monkeypatch.setattr(routes.settings, "llm_turn_deadline_seconds", DEADLINE)
    return transport


def test_chat_route_returns_fallback_before_deadline(hanging_chat, clock) -> None:
    started = clock.now

    response = TestClient(app).post("/api/chat", json={"message": "Học phí bao nhiêu?"})

    assert response.status_code == 200
    assert response.json()["answer"].startswith(UNAVAILABLE_PREFIX)
    assert clock.now - started <= DEADLINE + 1e-6
    assert response.headers["X-Request-ID"]


def test_chat_stream_returns_fallback_before_deadline(hanging_chat, clock) -> None:
    started = clock.now

    response = TestClient(app).post("/api/chat/stream", json={"message": "Học phí bao nhiêu?"})

    events = [json.loads(line) for line in response.text.splitlines() if line.strip()]
    assert events[-1]["type"] == "done"
    assert events[-1]["answer"].startswith(UNAVAILABLE_PREFIX)
    assert clock.now - started <= DEADLINE + 1e-6
    steps = [step for step, _ in hanging_chat.calls]
    assert steps == ["rewrite", "answer"]
