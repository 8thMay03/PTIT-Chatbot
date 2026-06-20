from app.retrieval.bm25 import BM25Search, invalidate_bm25_cache, rank_bm25
from app.retrieval.hybrid import reciprocal_rank_fusion


def test_bm25_ranks_exact_keyword_match_first() -> None:
    documents = [
        "Quy định chung về đào tạo.",
        "Mức học phí tín chỉ và thời hạn đóng học phí.",
        "Thông tin về thư viện.",
    ]

    ranked = rank_bm25("học phí", documents, top_k=3)

    assert ranked[0][0] == 1
    assert ranked[0][1] > 0


def test_bm25_search_builds_once_until_cache_is_invalidated(monkeypatch) -> None:
    search = BM25Search()
    chunks = [
        {"chunk_id": "1", "text": "quy định học phí"},
        {"chunk_id": "2", "text": "thông tin thư viện"},
        {"chunk_id": "3", "text": "lịch học sinh viên"},
    ]
    load_count = 0

    def load_chunks() -> list[dict]:
        nonlocal load_count
        load_count += 1
        return chunks

    monkeypatch.setattr(search, "_load_chunks", load_chunks)

    assert search.search("học phí", top_k=1)[0]["chunk_id"] == "1"
    search.search("thư viện", top_k=1)
    assert load_count == 1

    invalidate_bm25_cache()
    search.search("học phí", top_k=1)
    assert load_count == 2


def test_reciprocal_rank_fusion_combines_and_deduplicates_results() -> None:
    vector_results = [
        {"chunk_id": "semantic", "text": "semantic", "score": 0.9},
        {"chunk_id": "shared", "text": "shared", "score": 0.8},
    ]
    keyword_results = [
        {"chunk_id": "shared", "text": "shared", "score": 4.2},
        {"chunk_id": "exact", "text": "exact", "score": 3.1},
    ]

    results = reciprocal_rank_fusion(
        vector_results,
        keyword_results,
        top_k=3,
        vector_weight=0.5,
    )

    assert [result["chunk_id"] for result in results] == ["shared", "semantic", "exact"]
    assert results[0]["vector_score"] == 0.8
    assert results[0]["bm25_score"] == 4.2
