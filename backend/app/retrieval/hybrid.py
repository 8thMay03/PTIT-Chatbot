def reciprocal_rank_fusion(
    vector_results: list[dict],
    keyword_results: list[dict],
    top_k: int,
    vector_weight: float,
    rank_constant: int = 60,
) -> list[dict]:
    """Fuse vector and keyword rankings while preserving complete chunk metadata."""
    if top_k <= 0:
        return []

    keyword_weight = 1.0 - vector_weight
    fused: dict[str, dict] = {}

    for label, results, weight in (
        ("vector", vector_results, vector_weight),
        ("keyword", keyword_results, keyword_weight),
    ):
        for rank, result in enumerate(results, start=1):
            key = _result_key(result)
            entry = fused.setdefault(
                key,
                {"result": result.copy(), "score": 0.0, "vector_score": None, "bm25_score": None},
            )
            entry["score"] += weight / (rank_constant + rank)
            entry[f"{label if label == 'vector' else 'bm25'}_score"] = result.get("score")

    ordered = sorted(fused.values(), key=lambda entry: -entry["score"])
    results: list[dict] = []
    for entry in ordered[:top_k]:
        result = entry["result"]
        result["score"] = entry["score"]
        result["vector_score"] = entry["vector_score"]
        result["bm25_score"] = entry["bm25_score"]
        results.append(result)
    return results


def _result_key(result: dict) -> str:
    return str(
        result.get("chunk_id")
        or f"{result.get('document_id', '')}:{result.get('chunk_index', '')}"
    )
