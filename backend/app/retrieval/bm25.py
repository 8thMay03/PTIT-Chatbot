from __future__ import annotations

import re

from rank_bm25 import BM25Okapi
from sqlalchemy import select

from app.db.models import Chunk
from app.db.session import SessionLocal


class BM25Search:
    """Keyword retrieval over persisted chunks using Okapi BM25."""

    def search(self, query: str, top_k: int) -> list[dict]:
        if top_k <= 0:
            return []

        with SessionLocal() as session:
            chunks = list(session.scalars(select(Chunk).order_by(Chunk.chunk_index)))

        ranked = rank_bm25(query, [chunk.text for chunk in chunks], top_k)
        results: list[dict] = []
        for document_index, score in ranked:
            chunk = chunks[document_index]
            metadata = chunk.chunk_metadata or {}
            results.append(
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
                    "score": score,
                }
            )
        return results


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
