from __future__ import annotations

import logging
import math
import re
from typing import Any
from urllib.parse import urlsplit

import httpx

from app.core.config import ConfigValidationError, settings, validate_llm_url

logger = logging.getLogger(__name__)

# Thời gian chờ tối đa của một lần gọi /rerank; quá hạn thì câu hỏi dùng heuristic (D-04).
RERANK_API_TIMEOUT_SECONDS = 8.0

# Reranker gọi dịch vụ ngoài: điểm tuyệt đối (dùng được cho confidence gate) và gửi nội dung
# đoạn tài liệu ra ngoài. ``rerank_api`` là endpoint chuẩn Cohere bất kỳ do admin nhập.
API_RERANK_PROVIDERS = ("rerank_api", "cohere", "jina", "voyage", "pinecone", "tei")
RERANK_PROVIDER_LABELS = {
    "rerank_api": "Rerank API",
    "cohere": "Cohere",
    "jina": "Jina AI",
    "voyage": "Voyage AI",
    "pinecone": "Pinecone",
    "tei": "HF TEI",
}
# Dịch vụ của từng hãng: URL cố định trong code (không qua allowlist) và bắt buộc API key.
FIXED_RERANK_URLS = {
    "cohere": "https://api.cohere.com/v2/rerank",
    "jina": "https://api.jina.ai/v1/rerank",
    "voyage": "https://api.voyageai.com/v1/rerank",
    "pinecone": "https://api.pinecone.io/rerank",
}
KEY_REQUIRED_RERANK_PROVIDERS = frozenset(FIXED_RERANK_URLS)
# Base URL do admin nhập (tới trước ``/rerank``), kiểm qua allowlist mỗi lần gọi.
BASE_URL_RERANK_PROVIDERS = frozenset({"rerank_api", "tei"})
# Pinecone bắt buộc chọn phiên bản API; thiếu header thì dùng bản cũ nhất còn hỗ trợ.
PINECONE_API_VERSION = "2026-07"


class RerankAPIError(Exception):
    """Gọi /rerank thất bại. ``reason`` chỉ gồm loại lỗi/mã HTTP: an toàn để ghi log
    (không chứa khoá, câu hỏi hay nội dung đoạn)."""

    def __init__(self, reason: str, status_code: int | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.status_code = status_code


class Reranker:
    """Rerank hybrid candidates with a local heuristic, a CrossEncoder or a rerank API."""

    def __init__(self) -> None:
        self._cross_encoder: Any | None = None
        self._loaded_model_name: str | None = None

    def rerank(self, query: str, contexts: list[dict], top_k: int) -> list[dict]:
        if not contexts or top_k <= 0:
            return []

        provider = settings.reranker_provider
        if provider == "cross-encoder" or provider in API_RERANK_PROVIDERS:
            try:
                if provider == "cross-encoder":
                    return self._cross_encoder_rerank(query, contexts, top_k)
                return self._api_rerank(query, contexts, top_k)
            except Exception as exc:
                _log_fallback(provider, exc)

        return heuristic_rerank(query, contexts, top_k)

    def _api_rerank(self, query: str, contexts: list[dict], top_k: int) -> list[dict]:
        ranked = call_rerank_api(
            provider=settings.reranker_provider,
            base_url=settings.reranker_base_url,
            model=settings.reranker_model,
            api_key=settings.reranker_api_key,
            query=query,
            documents=[str(context.get("text") or "") for context in contexts],
            top_n=min(top_k, len(contexts)),
        )
        reranked = []
        for index, score in ranked:
            item = contexts[index].copy()
            item["rrf_score"] = contexts[index].get("score")
            item["rerank_score"] = score
            item["score"] = score
            reranked.append(item)
        reranked.sort(key=lambda item: -item["rerank_score"])
        return reranked[:top_k]

    def _cross_encoder_rerank(
        self,
        query: str,
        contexts: list[dict],
        top_k: int,
    ) -> list[dict]:
        if self._cross_encoder is None or self._loaded_model_name != settings.reranker_model:
            from sentence_transformers import CrossEncoder

            self._cross_encoder = CrossEncoder(settings.reranker_model)
            self._loaded_model_name = settings.reranker_model

        pairs = [(query, context.get("text", "")) for context in contexts]
        scores = self._cross_encoder.predict(pairs)
        reranked = []
        for context, score in zip(contexts, scores):
            item = context.copy()
            item["rrf_score"] = context.get("score")
            item["rerank_score"] = float(score)
            item["score"] = float(score)
            reranked.append(item)
        reranked.sort(key=lambda item: -item["rerank_score"])
        return reranked[:top_k]


def call_rerank_api(
    *,
    provider: str = "rerank_api",
    base_url: str | None,
    model: str | None,
    api_key: str | None,
    query: str,
    documents: list[str],
    top_n: int,
    timeout: float = RERANK_API_TIMEOUT_SECONDS,
) -> list[tuple[int, float]]:
    """Xếp hạng lại ``documents`` qua dịch vụ ``provider``; trả về ``[(index, điểm)]``.

    Lỗi bất kỳ (thiếu cấu hình, URL ngoài allowlist, timeout, mạng, HTTP không thành công,
    response sai định dạng, ``index`` ngoài phạm vi) raise ``RerankAPIError``.
    """
    url, headers, body = build_rerank_request(
        provider=provider,
        base_url=base_url,
        model=model,
        api_key=api_key,
        query=query,
        documents=documents,
        top_n=top_n,
    )
    try:
        # Không theo redirect: đích chuyển hướng không qua allowlist.
        response = httpx.post(url, json=body, headers=headers, timeout=timeout)
    except httpx.TimeoutException:
        raise RerankAPIError("timeout") from None
    except httpx.HTTPError as exc:
        raise RerankAPIError(type(exc).__name__) from None

    if not response.is_success:
        raise RerankAPIError(f"HTTP {response.status_code}", status_code=response.status_code)
    try:
        payload = response.json()
    except ValueError:
        raise RerankAPIError("invalid_json") from None
    ranked = parse_rerank_response(provider, payload, len(documents))
    # TEI không nhận top_n và trả điểm của mọi đoạn.
    return sorted(ranked, key=lambda item: -item[1])[:top_n] if provider == "tei" else ranked


def build_rerank_request(
    *,
    provider: str,
    base_url: str | None,
    model: str | None,
    api_key: str | None,
    query: str,
    documents: list[str],
    top_n: int,
) -> tuple[str, dict, dict]:
    """(url, headers, body) theo định dạng của từng dịch vụ; cấu hình thiếu/sai thì ``RerankAPIError``."""
    if provider not in API_RERANK_PROVIDERS:
        raise RerankAPIError("unsupported_provider")
    if not model:
        raise RerankAPIError("missing_config")
    if provider in KEY_REQUIRED_RERANK_PROVIDERS:
        if not api_key:
            raise RerankAPIError("missing_api_key")
        url = FIXED_RERANK_URLS[provider]
    else:
        if not base_url:
            raise RerankAPIError("missing_config")
        try:
            # Kiểm lại mỗi lần gọi: allowlist có thể đã bị thu hẹp sau khi lưu cấu hình.
            validate_llm_url(base_url)
        except ConfigValidationError:
            raise RerankAPIError("url_not_allowed") from None
        url = f"{base_url.rstrip('/')}/rerank"

    headers = {"Content-Type": "application/json"}
    if provider == "pinecone":
        headers["Api-Key"] = api_key
        headers["X-Pinecone-Api-Version"] = PINECONE_API_VERSION
    elif api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    if provider == "tei":
        body: dict[str, Any] = {"query": query, "texts": documents}
    elif provider == "voyage":
        body = {"model": model, "query": query, "documents": documents, "top_k": top_n}
    elif provider == "pinecone":
        body = {
            "model": model,
            "query": query,
            "documents": [{"text": text} for text in documents],
            "top_n": top_n,
            "return_documents": False,
        }
    else:
        body = {"model": model, "query": query, "documents": documents, "top_n": top_n}
        if provider == "jina":
            body["return_documents"] = False
    return url, headers, body


def parse_rerank_response(provider: str, payload: Any, count: int) -> list[tuple[int, float]]:
    """``[(index, điểm)]`` từ response; sai định dạng thì ``RerankAPIError``.

    Cohere, Jina, ``rerank_api``: ``results[].relevance_score``; Voyage: ``data[].relevance_score``;
    Pinecone: ``data[].score``; TEI: mảng ``[{index, score}]``.
    """
    if provider == "tei":
        results = payload
    elif isinstance(payload, dict):
        results = payload.get("data" if provider in ("voyage", "pinecone") else "results")
    else:
        results = None
    if not isinstance(results, list) or not results:
        raise RerankAPIError("invalid_response")
    score_field = "score" if provider in ("pinecone", "tei") else "relevance_score"
    ranked: list[tuple[int, float]] = []
    seen: set[int] = set()
    for result in results:
        index = result.get("index") if isinstance(result, dict) else None
        score = result.get(score_field) if isinstance(result, dict) else None
        if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < count or index in seen:
            raise RerankAPIError("invalid_index")
        if not isinstance(score, (int, float)) or isinstance(score, bool) or not math.isfinite(score):
            raise RerankAPIError("invalid_score")
        seen.add(index)
        ranked.append((index, float(score)))
    return ranked


def _log_fallback(provider: str, exc: Exception) -> None:
    """Cảnh báo khi quay về heuristic (D-04/D-05): chỉ provider, mô hình, host và loại lỗi."""
    reason = exc.reason if isinstance(exc, RerankAPIError) else type(exc).__name__
    host = None
    url = FIXED_RERANK_URLS.get(provider) or (
        settings.reranker_base_url if provider in BASE_URL_RERANK_PROVIDERS else None
    )
    if url:
        try:
            parts = urlsplit(url)
            host = parts.hostname
            if host and parts.port:
                host = f"{host}:{parts.port}"
        except ValueError:
            host = "invalid"
    logger.warning(
        "Reranker %s (model=%s, host=%s) lỗi: %s. Dùng heuristic cho câu hỏi này.",
        provider,
        settings.reranker_model,
        host or "-",
        reason,
    )


def heuristic_rerank(query: str, contexts: list[dict], top_k: int) -> list[dict]:
    """Rescore candidates from vector, BM25 and query-term coverage signals."""
    vector_scores = _normalize([context.get("vector_score") for context in contexts])
    bm25_scores = _normalize([context.get("bm25_score") for context in contexts])
    query_terms = set(_tokenize(query))
    reranked: list[dict] = []

    for index, context in enumerate(contexts):
        searchable_text = " ".join(
            str(context.get(field) or "")
            for field in ("heading", "section_path", "text")
        )
        document_terms = set(_tokenize(searchable_text))
        term_coverage = len(query_terms & document_terms) / max(len(query_terms), 1)
        rerank_score = (
            settings.reranker_vector_weight * vector_scores[index]
            + settings.reranker_bm25_weight * bm25_scores[index]
            + settings.reranker_lexical_weight * term_coverage
        )
        item = context.copy()
        item["rrf_score"] = context.get("score")
        item["rerank_score"] = rerank_score
        item["score"] = rerank_score
        reranked.append(item)

    reranked.sort(key=lambda item: -item["rerank_score"])
    return reranked[:top_k]


def _normalize(values: list[object]) -> list[float]:
    numeric = [float(value) if value is not None else 0.0 for value in values]
    minimum = min(numeric, default=0.0)
    maximum = max(numeric, default=0.0)
    if maximum == minimum:
        return [1.0 if value > 0 else 0.0 for value in numeric]
    return [(value - minimum) / (maximum - minimum) for value in numeric]


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.casefold(), flags=re.UNICODE)
