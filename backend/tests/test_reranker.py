import logging

import httpx
import pytest

from app.retrieval import reranker as reranker_module
from app.retrieval.reranker import (
    RerankAPIError,
    Reranker,
    call_rerank_api,
    heuristic_rerank,
)


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


# ==========================================
# Nhà cung cấp riêng: Cohere, Jina, Voyage, Pinecone, HF TEI
# ==========================================
def _use_provider(monkeypatch, provider, *, base_url=None, api_key=API_KEY, model="rerank-unit-test"):
    target = reranker_module.settings
    monkeypatch.setattr(target, "reranker_provider", provider)
    monkeypatch.setattr(target, "reranker_model", model)
    monkeypatch.setattr(target, "reranker_base_url", base_url)
    monkeypatch.setattr(target, "reranker_api_key", api_key)
    # Allowlist không chứa host của hãng: URL cố định không phụ thuộc allowlist.
    monkeypatch.setattr(target, "llm_base_url_allowlist", "http://tei.local:8080")


@pytest.mark.parametrize(
    ("provider", "url", "body", "response"),
    [
        (
            "cohere",
            "https://api.cohere.com/v2/rerank",
            {"model": "rerank-unit-test", "query": QUERY, "documents": TEXTS, "top_n": 2},
            {"results": [{"index": 1, "relevance_score": 0.91}, {"index": 2, "relevance_score": 0.4}]},
        ),
        (
            "jina",
            "https://api.jina.ai/v1/rerank",
            {"model": "rerank-unit-test", "query": QUERY, "documents": TEXTS, "top_n": 2, "return_documents": False},
            {"results": [{"index": 1, "relevance_score": 0.91}, {"index": 2, "relevance_score": 0.4}]},
        ),
        (
            "voyage",
            "https://api.voyageai.com/v1/rerank",
            {"model": "rerank-unit-test", "query": QUERY, "documents": TEXTS, "top_k": 2},
            {"object": "list", "data": [{"index": 1, "relevance_score": 0.91}, {"index": 2, "relevance_score": 0.4}]},
        ),
    ],
)
def test_vendor_rerank_request_and_response(monkeypatch, provider, url, body, response) -> None:
    # Base URL còn sót trong settings không được dùng: khoá chỉ đi tới URL cố định của hãng.
    _use_provider(monkeypatch, provider, base_url="https://evil.example.com/v1")
    calls = _fake_post(monkeypatch, _response(json=response))

    ranked = Reranker().rerank(QUERY, _contexts(), top_k=2)

    [call] = calls
    assert call["url"] == url
    assert call["json"] == body
    assert call["headers"]["Authorization"] == f"Bearer {API_KEY}"
    assert [item["chunk_id"] for item in ranked] == ["c1", "c2"]
    assert ranked[0]["rerank_score"] == 0.91


def test_pinecone_request_uses_api_key_header_and_document_objects(monkeypatch) -> None:
    _use_provider(monkeypatch, "pinecone", model="bge-reranker-v2-m3")
    data = [{"index": 2, "score": 0.8}, {"index": 0, "score": 0.1}]
    calls = _fake_post(monkeypatch, _response(json={"model": "bge-reranker-v2-m3", "data": data}))

    ranked = Reranker().rerank(QUERY, _contexts(), top_k=2)

    [call] = calls
    assert call["url"] == "https://api.pinecone.io/rerank"
    assert call["headers"]["Api-Key"] == API_KEY
    assert call["headers"]["X-Pinecone-Api-Version"] == reranker_module.PINECONE_API_VERSION
    assert "Authorization" not in call["headers"]
    assert call["json"] == {
        "model": "bge-reranker-v2-m3",
        "query": QUERY,
        "documents": [{"text": text} for text in TEXTS],
        "top_n": 2,
        "return_documents": False,
    }
    assert [(item["chunk_id"], item["rerank_score"]) for item in ranked] == [("c2", 0.8), ("c0", 0.1)]


def test_tei_request_sorts_all_scores_and_keeps_top_n(monkeypatch) -> None:
    _use_provider(monkeypatch, "tei", base_url="http://tei.local:8080/", api_key=None, model="BAAI/bge-reranker-v2-m3")
    scores = [{"index": 0, "score": 0.2}, {"index": 1, "score": 0.05}, {"index": 2, "score": 0.9}]
    calls = _fake_post(monkeypatch, _response(json=scores))

    ranked = Reranker().rerank(QUERY, _contexts(), top_k=2)

    [call] = calls
    assert call["url"] == "http://tei.local:8080/rerank"
    assert call["json"] == {"query": QUERY, "texts": TEXTS}
    assert "Authorization" not in call["headers"]
    assert [item["chunk_id"] for item in ranked] == ["c2", "c0"]

    result = call_rerank_api(
        provider="tei",
        base_url="http://tei.local:8080",
        model="m",
        api_key="tei-key",
        query=QUERY,
        documents=TEXTS,
        top_n=1,
    )
    assert result == [(2, 0.9)]
    assert calls[-1]["headers"]["Authorization"] == "Bearer tei-key"


def test_tei_base_url_still_checked_against_allowlist(monkeypatch, caplog) -> None:
    _use_provider(monkeypatch, "tei", base_url="http://169.254.169.254/latest", api_key=None)
    calls = _fake_post(monkeypatch, _response(json=[{"index": 0, "score": 1.0}]))

    with caplog.at_level(logging.WARNING, logger="app.retrieval.reranker"):
        ranked = Reranker().rerank(QUERY, _contexts(), top_k=2)

    assert calls == []
    assert ranked == heuristic_rerank(QUERY, _contexts(), top_k=2)
    assert "url_not_allowed" in caplog.text


@pytest.mark.parametrize("provider", ["cohere", "jina", "voyage", "pinecone"])
def test_vendor_without_key_falls_back_without_calling(monkeypatch, caplog, provider) -> None:
    _use_provider(monkeypatch, provider, api_key=None)
    calls = _fake_post(monkeypatch, _response(json={}))

    with caplog.at_level(logging.WARNING, logger="app.retrieval.reranker"):
        ranked = Reranker().rerank(QUERY, _contexts(), top_k=2)

    assert calls == []
    assert ranked == heuristic_rerank(QUERY, _contexts(), top_k=2)
    message = caplog.records[-1].getMessage()
    assert "missing_api_key" in message and provider in message
    # Host của URL cố định có trong log để admin biết dịch vụ nào lỗi.
    assert reranker_module.FIXED_RERANK_URLS[provider].split("/")[2] in message


@pytest.mark.parametrize(
    ("provider", "payload"),
    [
        # Mỗi dịch vụ chỉ đọc đúng khoá mảng và trường điểm của mình.
        ("voyage", {"results": [{"index": 0, "relevance_score": 0.5}]}),
        ("cohere", {"data": [{"index": 0, "relevance_score": 0.5}]}),
        ("pinecone", {"data": [{"index": 0, "relevance_score": 0.5}]}),
        ("tei", {"results": [{"index": 0, "score": 0.5}]}),
        ("tei", [{"index": 3, "score": 0.5}]),
        ("tei", [{"index": 0, "score": "0.5"}]),
    ],
)
def test_vendor_malformed_response_raises(monkeypatch, provider, payload) -> None:
    _fake_post(monkeypatch, _response(json=payload))
    with pytest.raises(RerankAPIError):
        call_rerank_api(
            provider=provider,
            base_url="http://tei.local:8080",
            model="m",
            api_key=API_KEY,
            query=QUERY,
            documents=TEXTS,
            top_n=2,
        )


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
