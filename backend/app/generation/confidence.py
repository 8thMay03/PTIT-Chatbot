def has_strong_context(
    contexts: list[dict],
    min_vector_score: float,
    min_bm25_score: float,
) -> bool:
    """Return whether at least one retrieved chunk clears either confidence threshold."""
    for context in contexts:
        vector_score = context.get("vector_score")
        bm25_score = context.get("bm25_score")

        # Preserve compatibility with vector-only retrievers.
        if vector_score is None and bm25_score is None:
            vector_score = context.get("score")

        if vector_score is not None and float(vector_score) >= min_vector_score:
            return True
        if bm25_score is not None and float(bm25_score) >= min_bm25_score:
            return True

    return False
