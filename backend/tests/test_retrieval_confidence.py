from app.generation.confidence import has_strong_context


def test_context_is_weak_when_all_retrieval_scores_are_below_thresholds() -> None:
    contexts = [
        {"vector_score": 0.12, "bm25_score": 0.8},
        {"vector_score": 0.29, "bm25_score": None},
    ]

    assert not has_strong_context(contexts, min_vector_score=0.30, min_bm25_score=2.0)


def test_context_is_strong_when_either_retriever_clears_its_threshold() -> None:
    vector_context = [{"vector_score": 0.42, "bm25_score": None}]
    keyword_context = [{"vector_score": 0.1, "bm25_score": 4.5}]

    assert has_strong_context(vector_context, min_vector_score=0.30, min_bm25_score=2.0)
    assert has_strong_context(keyword_context, min_vector_score=0.30, min_bm25_score=2.0)


def test_vector_only_context_uses_legacy_score() -> None:
    assert has_strong_context([{"score": 0.7}], min_vector_score=0.30, min_bm25_score=2.0)
