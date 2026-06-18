from __future__ import annotations

import re
from typing import Any

from app.core.config import settings


class Reranker:
    """Rerank hybrid candidates with a local heuristic or optional CrossEncoder."""

    def __init__(self) -> None:
        self._cross_encoder: Any | None = None

    def rerank(self, query: str, contexts: list[dict], top_k: int) -> list[dict]:
        if not contexts or top_k <= 0:
            return []

        if settings.reranker_provider == "cross-encoder":
            try:
                return self._cross_encoder_rerank(query, contexts, top_k)
            except Exception:
                pass

        return heuristic_rerank(query, contexts, top_k)

    def _cross_encoder_rerank(
        self,
        query: str,
        contexts: list[dict],
        top_k: int,
    ) -> list[dict]:
        if self._cross_encoder is None:
            from sentence_transformers import CrossEncoder

            self._cross_encoder = CrossEncoder(settings.reranker_model)

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
