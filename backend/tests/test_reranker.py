import logging

import httpx
import pytest

from app.retrieval import reranker as reranker_module
from app.retrieval.reranker import Reranker, heuristic_rerank


def test_heuristic_reranker_promotes_exact_query_coverage(monkeypatch) -> None:
    monkeypatch.setattr("app.retrieval.reranker.settings.reranker_vector_weight", 0.45)
    monkeypatch.setattr("app.retrieval.reranker.settings.reranker_bm25_weight", 0.35)
    monkeypatch.setattr("app.retrieval.reranker.settings.reranker_lexical_weight", 0.20)
    contexts = [
        {
            "chunk_id": "semantic",
            "text": "Thông tin đào tạo chung.",
            "heading": "Đào tạo",
            "vector_score": 0.8,
            "bm25_score": 0.2,
            "score": 0.02,
        },
        {
            "chunk_id": "tuition",
            "text": "Quy định về mức trần học phí.",
            "heading": "Học phí",
            "vector_score": 0.7,
            "bm25_score": 8.0,
            "score": 0.018,
        },
    ]

    results = heuristic_rerank("mức trần học phí", contexts, top_k=2)

    assert results[0]["chunk_id"] == "tuition"
    assert results[0]["rerank_score"] > results[1]["rerank_score"]
    assert results[0]["rrf_score"] == 0.018


# ==========================================
# Rerank API (chuẩn /rerank của Cohere) và quay về heuristic
# ==========================================
API_KEY = "rk-unit-test-secret-key-0123456789"
QUERY = "câu hỏi bí mật về học phí"
TEXTS = ["Đoạn A nói về thư viện.", "Đoạn B nói về học phí.", "Đoạn C nói về ký túc xá."]


def _contexts() -> list[dict]:
    return [
        {"chunk_id": f"c{index}", "text": text, "score": 0.01 * (index + 1), "vector_score": 0.5, "bm25_score": 1.0}
        for index, text in enumerate(TEXTS)
    ]


@pytest.fixture
def api_settings(monkeypatch):
    target = reranker_module.settings
    monkeypatch.setattr(target, "reranker_provider", "rerank_api")
    monkeypatch.setattr(target, "reranker_model", "rerank-unit-test")
    monkeypatch.setattr(target, "reranker_base_url", "https://api.cohere.com/v2/")
    monkeypatch.setattr(target, "reranker_api_key", API_KEY)
    monkeypatch.setattr(target, "llm_base_url_allowlist", "https://api.cohere.com")
    return target


def _fake_post(monkeypatch, response=None, exc=None):
    calls: list[dict] = []

    def fake(url, **kwargs):
        calls.append({"url": url, **kwargs})
        if exc is not None:
            raise exc
        return response

    monkeypatch.setattr(reranker_module.httpx, "post", fake)
    return calls


def _response(status=200, **kwargs) -> httpx.Response:
    return httpx.Response(status, request=httpx.Request("POST", "https://api.cohere.com/v2/rerank"), **kwargs)


def test_rerank_api_sends_cohere_request_and_sorts_by_relevance(api_settings, monkeypatch) -> None:
    results = [{"index": 1, "relevance_score": 0.91}, {"index": 2, "relevance_score": 0.40}]
    calls = _fake_post(monkeypatch, _response(json={"results": results}))

    ranked = Reranker().rerank(QUERY, _contexts(), top_k=2)

    [call] = calls
    assert call["url"] == "https://api.cohere.com/v2/rerank"
    assert call["json"] == {"model": "rerank-unit-test", "query": QUERY, "documents": TEXTS, "top_n": 2}
    assert call["headers"]["Authorization"] == f"Bearer {API_KEY}"
    assert call["timeout"] == reranker_module.RERANK_API_TIMEOUT_SECONDS == 8.0
    assert [item["chunk_id"] for item in ranked] == ["c1", "c2"]
    assert ranked[0]["rerank_score"] == ranked[0]["score"] == 0.91
    assert ranked[0]["rrf_score"] == 0.02


def test_rerank_api_without_key_sends_no_authorization(api_settings, monkeypatch) -> None:
    api_settings.reranker_api_key = None
    results = [
        {"index": 0, "relevance_score": 0.2},
        {"index": 2, "relevance_score": 0.7},
        {"index": 1, "relevance_score": 0.5},
    ]
    calls = _fake_post(monkeypatch, _response(json={"results": results}))

    ranked = Reranker().rerank(QUERY, _contexts(), top_k=2)

    assert "Authorization" not in calls[0]["headers"]
    assert [item["chunk_id"] for item in ranked] == ["c2", "c1"]


@pytest.mark.parametrize(
    ("response", "exc", "reason"),
    [
        (None, httpx.ReadTimeout("timed out"), "timeout"),
        (None, httpx.ConnectError("refused"), "ConnectError"),
        (_response(401, json={"message": "invalid api token"}), None, "HTTP 401"),
        (_response(500, text="boom"), None, "HTTP 500"),
        (_response(302, headers={"location": "http://169.254.169.254/"}), None, "HTTP 302"),
        (_response(text="not json"), None, "invalid_json"),
        (_response(json={"data": []}), None, "invalid_response"),
        (_response(json={"results": [{"index": 7, "relevance_score": 0.9}]}), None, "invalid_index"),
        (_response(json={"results": [{"index": 0, "relevance_score": "high"}]}), None, "invalid_score"),
    ],
)
def test_rerank_api_failure_falls_back_to_heuristic_and_logs_safely(
    api_settings, monkeypatch, caplog, response, exc, reason
) -> None:
    _fake_post(monkeypatch, response, exc)
    contexts = _contexts()

    with caplog.at_level(logging.WARNING, logger="app.retrieval.reranker"):
        ranked = Reranker().rerank(QUERY, contexts, top_k=2)

    assert ranked == heuristic_rerank(QUERY, contexts, top_k=2)
    [record] = [r for r in caplog.records if r.name == "app.retrieval.reranker"]
    message = record.getMessage()
    assert "rerank_api" in message and "rerank-unit-test" in message and "api.cohere.com" in message
    assert reason in message
    assert API_KEY not in message and QUERY not in message
    assert not any(text in message for text in TEXTS)


def test_rerank_api_rejects_url_outside_allowlist_without_calling(api_settings, monkeypatch, caplog) -> None:
    api_settings.reranker_base_url = "http://169.254.169.254/latest"
    calls = _fake_post(monkeypatch, _response(json={"results": [{"index": 0, "relevance_score": 1.0}]}))

    with caplog.at_level(logging.WARNING, logger="app.retrieval.reranker"):
        ranked = Reranker().rerank(QUERY, _contexts(), top_k=2)

    assert calls == []
    assert ranked == heuristic_rerank(QUERY, _contexts(), top_k=2)
    assert "url_not_allowed" in caplog.text


def test_cross_encoder_failure_logs_and_falls_back(monkeypatch, caplog) -> None:
    monkeypatch.setattr(reranker_module.settings, "reranker_provider", "cross-encoder")
    monkeypatch.setattr(reranker_module.settings, "reranker_model", "unit-test/missing-model")

    def broken(self, query, contexts, top_k):
        raise OSError(f"cannot load model for {query}")

    monkeypatch.setattr(Reranker, "_cross_encoder_rerank", broken)
    contexts = _contexts()

    with caplog.at_level(logging.WARNING, logger="app.retrieval.reranker"):
        ranked = Reranker().rerank(QUERY, contexts, top_k=2)

    assert ranked == heuristic_rerank(QUERY, contexts, top_k=2)
    [record] = [r for r in caplog.records if r.name == "app.retrieval.reranker"]
    message = record.getMessage()
    assert "cross-encoder" in message and "unit-test/missing-model" in message and "OSError" in message
    assert QUERY not in message
