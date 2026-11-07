from __future__ import annotations

import math
import re
from threading import RLock

from rank_bm25 import BM25Okapi
from sqlalchemy import select

from app.db.models import Chunk
from app.db.session import SessionLocal


_cache_generation = 0
_UNSEEN_TERM_MODE = "df1"
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

    def search(self, query: str, top_k: int, dataset_ids: list[str] | None = None) -> list[dict]:
        if top_k <= 0:
            return []

        query_terms = _tokenize(query)
        if not query_terms:
            return []

        with self._lock:
            self._ensure_index()
            if self._scorer is None:
                return []

            # Lọc dataset trước khi cắt top_k; snapshot đã chỉ chứa dataset đang bật.
            candidates = self._chunks
            if dataset_ids is not None:
                wanted = set(dataset_ids)
                candidates = [c for c in candidates if c.get("dataset_id") in wanted]
            if not candidates:
                return []
            # Tính điểm trên toàn index rồi lọc theo dataset để giữ IDF ổn định,
            # sau đó cắt top_k trong tập được phép.
            scores = self._scorer.get_scores(query_terms)
            scored_all = {self._chunks[i].get("chunk_id"): float(score) for i, score in enumerate(scores) if score > 0}
            ranked = [
                (chunk, scored_all.get(chunk.get("chunk_id"), 0.0))
                for chunk in candidates
                if scored_all.get(chunk.get("chunk_id"), 0.0) > 0
            ]
            ranked.sort(key=lambda item: (-item[1], item[0].get("chunk_index", 0)))

            upper_bound = _score_upper_bound(self._scorer, query_terms)
            results: list[dict] = []
            for chunk, score in ranked[:top_k]:
                result = chunk.copy()
                result["score"] = score
                result["bm25_norm_score"] = normalize_bm25_score(score, upper_bound)
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
            tokenized_documents = [
                _tokenize(chunk.get("search_text") or chunk["text"]) for chunk in chunks
            ]
            self._chunks = chunks
            self._scorer = BM25Okapi(tokenized_documents) if tokenized_documents else None
            self._generation = current_generation

    @staticmethod
    def _load_chunks() -> list[dict]:
        """Load detached chunk snapshots so the cache does not retain a DB session."""
        with SessionLocal() as session:
            from app.db.models import Dataset, Document

            rows = session.execute(
                select(Chunk, Document.dataset_id)
                .join(Document, Chunk.document_id == Document.id)
                .join(Dataset, Document.dataset_id == Dataset.id)
                .where(Dataset.enabled.is_(True))
                .order_by(Chunk.chunk_index)
            ).all()

        snapshots: list[dict] = []
        for chunk, dataset_id in rows:
            metadata = chunk.chunk_metadata or {}
            snapshots.append(
                {
                    "source": metadata.get("source", ""),
                    "source_name": metadata.get("source_name", ""),
                    "document_id": chunk.document_id,
                    "dataset_id": dataset_id,
                    "chunk_id": chunk.id,
                    "heading": metadata.get("heading", ""),
                    "heading_level": metadata.get("heading_level"),
                    "section_path": metadata.get("section_path", ""),
                    "chunk_index": chunk.chunk_index,
                    "text": chunk.text,
                    "search_text": chunk.search_text or chunk.text,
                    "parent_id": metadata.get("parent_id", chunk.id),
                    "parent_index": metadata.get("parent_index", chunk.chunk_index),
                    "child_index": metadata.get("child_index", 0),
                    "parent_text": metadata.get("parent_text", chunk.text),
                    "chunk_type": metadata.get("chunk_type", "child"),
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


def normalize_bm25_score(score: float, upper_bound: float) -> float:
    """Đưa điểm BM25 thô về [0, 1] bằng cận trên lý thuyết của chính query."""
    if upper_bound <= 0:
        return 0.0
    return max(0.0, min(1.0, float(score) / upper_bound))


def _score_upper_bound(scorer: BM25Okapi, query_terms: list[str]) -> float:
    """Cận trên BM25 Okapi của query: Σ idf(t)·(k1 + 1) khi tf → ∞ ở mọi term.

    Cộng theo từng token kể cả token lặp, đúng như ``BM25Okapi.get_scores``, nên
    điểm thô không bao giờ vượt cận này. Term không có trong kho được tính với
    idf của df = 1: query nhắc tới thứ kho không có thì điểm chuẩn hóa thấp, thay
    vì được bỏ qua như trong điểm thô. Điểm chuẩn hóa vì vậy chỉ phụ thuộc mức độ
    chunk phủ các term của query (có trọng số idf), không phụ thuộc độ dài query
    hay kích thước kho như điểm thô.
    """
    # Cùng công thức và sàn epsilon như BM25Okapi._calc_idf để kho rất nhỏ không ra idf âm.
    unseen_idf = max(
        math.log(scorer.corpus_size - 1 + 0.5) - math.log(1 + 0.5),
        scorer.epsilon * scorer.average_idf,
    )
    if _UNSEEN_TERM_MODE == "skip":  # RAG-18 S-04: biến thể đo so sánh, xóa sau khi chọn.
        query_terms = [term for term in query_terms if term in scorer.idf]
    total_idf = sum(scorer.idf.get(term, unseen_idf) for term in query_terms)
    return total_idf * (scorer.k1 + 1)


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.casefold(), flags=re.UNICODE)
