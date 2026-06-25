def fuse_multi_query_results(
    result_sets: list[list[dict]],
    top_k: int,
    rank_constant: int = 60,
) -> list[dict]:
    """Fuse rankings from query variants and reward chunks found by multiple queries."""
    fused: dict[str, dict] = {}

    for results in result_sets:
        for rank, result in enumerate(results, start=1):
            key = str(
                result.get("parent_id")
                or result.get("chunk_id")
                or f"{result.get('document_id', '')}:{result.get('chunk_index', '')}"
            )
            entry = fused.setdefault(
                key,
                {
                    "result": result.copy(),
                    "score": 0.0,
                    "query_hits": 0,
                    "vector_score": None,
                    "bm25_score": None,
                },
            )
            entry["score"] += 1.0 / (rank_constant + rank)
            entry["query_hits"] += 1
            entry["vector_score"] = _maximum(entry["vector_score"], result.get("vector_score"))
            entry["bm25_score"] = _maximum(entry["bm25_score"], result.get("bm25_score"))
            if float(result.get("score") or 0) > float(entry["result"].get("score") or 0):
                entry["result"] = result.copy()

    ordered = sorted(fused.values(), key=lambda entry: (-entry["score"], -entry["query_hits"]))
    output: list[dict] = []
    for entry in ordered[:top_k]:
        result = entry["result"]
        result["hybrid_score"] = result.get("score")
        result["score"] = entry["score"]
        result["multi_query_score"] = entry["score"]
        result["query_hits"] = entry["query_hits"]
        result["vector_score"] = entry["vector_score"]
        result["bm25_score"] = entry["bm25_score"]
        output.append(result)
    return output


def _maximum(current: object, candidate: object) -> float | None:
    values = [float(value) for value in (current, candidate) if value is not None]
    return max(values) if values else None
