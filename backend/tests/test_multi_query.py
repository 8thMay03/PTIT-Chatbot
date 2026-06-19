from app.generation.multi_query import VietnameseMultiQueryGenerator
from app.retrieval.multi_query import fuse_multi_query_results


def test_rule_based_multi_query_keeps_original_and_adds_domain_variants(monkeypatch) -> None:
    monkeypatch.setattr("app.generation.multi_query.settings.multi_query_enabled", True)
    monkeypatch.setattr("app.generation.multi_query.settings.multi_query_use_llm", False)
    monkeypatch.setattr("app.generation.multi_query.settings.multi_query_count", 3)

    queries = VietnameseMultiQueryGenerator().generate("học phí đóng khi nào")

    assert queries[0] == "học phí đóng khi nào"
    assert "học phí đóng" in queries
    assert any("mức thu" in query for query in queries)


def test_multi_query_fusion_promotes_chunks_found_by_multiple_queries() -> None:
    result_sets = [
        [
            {"chunk_id": "only-first", "score": 0.9, "vector_score": 0.8},
            {"chunk_id": "shared", "score": 0.8, "bm25_score": 4.0},
        ],
        [
            {"chunk_id": "shared", "score": 0.7, "vector_score": 0.7},
            {"chunk_id": "only-second", "score": 0.6, "bm25_score": 3.0},
        ],
    ]

    results = fuse_multi_query_results(result_sets, top_k=3)

    assert results[0]["chunk_id"] == "shared"
    assert results[0]["query_hits"] == 2
    assert results[0]["vector_score"] == 0.7
    assert results[0]["bm25_score"] == 4.0
