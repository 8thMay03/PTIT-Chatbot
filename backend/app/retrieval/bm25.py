from __future__ import annotations

import re
from threading import RLock

from rank_bm25 import BM25Okapi
from sqlalchemy import select

from app.db.models import Chunk
from app.db.session import SessionLocal


_cache_generation = 0
_generation_lock = RLock()


def invalidate_bm25_cache() -> None:
    """Mark all in-memory BM25 indexes stale after the knowledge base changes."""
    global _cache_generation
    with _generation_lock:
        _cache_generation += 1


class BM25Search:
    """Keyword retrieval backed by a lazily built, reusable in-memory index."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._generation = -1
        self._chunks: list[dict] = []
        self._scorer: BM25Okapi | None = None

    def search(self, query: str, top_k: int) -> list[dict]:
        if top_k <= 0:
            return []

        query_terms = _tokenize(query)
        if not query_terms:
            return []

        with self._lock:
            self._ensure_index()
            if self._scorer is None:
                return []

            scores = self._scorer.get_scores(query_terms)
            ranked = [(index, float(score)) for index, score in enumerate(scores) if score > 0]
            ranked.sort(key=lambda item: (-item[1], item[0]))

            results: list[dict] = []
            for document_index, score in ranked[:top_k]:
                chunk = self._chunks[document_index]
                result = chunk.copy()
                result["score"] = score
                results.append(result)
            return results

    def _ensure_index(self) -> None:
        """Build once and rebuild only after ingestion invalidates the cache."""
        with _generation_lock:
            current_generation = _cache_generation
        if self._generation == current_generation:
            return

        with self._lock:
            with _generation_lock:
                current_generation = _cache_generation
            if self._generation == current_generation:
                return

            chunks = self._load_chunks()
            tokenized_documents = [_tokenize(chunk["text"]) for chunk in chunks]
            self._chunks = chunks
            self._scorer = BM25Okapi(tokenized_documents) if tokenized_documents else None
            self._generation = current_generation

    @staticmethod
    def _load_chunks() -> list[dict]:
        """Load detached chunk snapshots so the cache does not retain a DB session."""
        with SessionLocal() as session:
            chunks = list(session.scalars(select(Chunk).order_by(Chunk.chunk_index)))

        snapshots: list[dict] = []
        for chunk in chunks:
            metadata = chunk.chunk_metadata or {}
            snapshots.append(
                {
                    "source": metadata.get("source", ""),
                    "source_name": metadata.get("source_name", ""),
                    "document_id": chunk.document_id,
                    "chunk_id": chunk.id,
                    "heading": metadata.get("heading", ""),
                    "heading_level": metadata.get("heading_level"),
                    "section_path": metadata.get("section_path", ""),
                    "chunk_index": chunk.chunk_index,
                    "text": chunk.text,
                }
            )
        return snapshots


def rank_bm25(query: str, documents: list[str], top_k: int) -> list[tuple[int, float]]:
    """Rank document indexes with rank-bm25's Okapi BM25 implementation."""
    query_terms = _tokenize(query)
    tokenized_documents = [_tokenize(document) for document in documents]
    if not query_terms or not tokenized_documents or top_k <= 0:
        return []

    scorer = BM25Okapi(tokenized_documents)
    scores = scorer.get_scores(query_terms)
    ranked = [(index, float(score)) for index, score in enumerate(scores) if score > 0]
    ranked.sort(key=lambda item: (-item[1], item[0]))
    return ranked[:top_k]


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.casefold(), flags=re.UNICODE)
