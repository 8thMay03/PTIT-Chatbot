from app.retrieval.reranker import heuristic_rerank


def test_heuristic_reranker_promotes_exact_query_coverage() -> None:
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
