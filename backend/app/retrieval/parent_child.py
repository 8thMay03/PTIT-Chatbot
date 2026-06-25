from __future__ import annotations


def collapse_parent_results(results: list[dict], top_k: int) -> list[dict]:
    """Group child hits by parent and expose parent text with child evidence."""
    if top_k <= 0:
        return []

    grouped: dict[str, dict] = {}
    for result in results:
        parent_id = str(result.get("parent_id") or result.get("chunk_id") or "")
        if not parent_id:
            parent_id = f"{result.get('document_id', '')}:{result.get('chunk_index', '')}"

        score = float(result.get("score") or 0.0)
        entry = grouped.get(parent_id)
        if entry is None:
            item = result.copy()
            child_text = str(result.get("text") or "")
            item["parent_id"] = parent_id
            item["text"] = str(result.get("parent_text") or child_text)
            item["evidence_text"] = child_text
            item["matched_child_ids"] = [result.get("chunk_id")] if result.get("chunk_id") else []
            item["matched_child_count"] = 1
            item["score"] = score
            item["_best_child_score"] = score
            grouped[parent_id] = item
            continue

        entry["matched_child_count"] += 1
        child_id = result.get("chunk_id")
        if child_id and child_id not in entry["matched_child_ids"]:
            entry["matched_child_ids"].append(child_id)

        entry["vector_score"] = _maximum(entry.get("vector_score"), result.get("vector_score"))
        entry["bm25_score"] = _maximum(entry.get("bm25_score"), result.get("bm25_score"))
        entry["score"] = max(float(entry.get("score") or 0.0), score)

        if score > float(entry.get("_best_child_score") or 0.0):
            entry["chunk_id"] = result.get("chunk_id")
            entry["chunk_index"] = result.get("chunk_index")
            entry["child_index"] = result.get("child_index")
            entry["evidence_text"] = str(result.get("text") or "")
            entry["_best_child_score"] = score

    output = list(grouped.values())
    for item in output:
        item.pop("_best_child_score", None)
    output.sort(
        key=lambda item: (
            -float(item.get("score") or 0.0),
            -int(item.get("matched_child_count") or 0),
        )
    )
    return output[:top_k]


def _maximum(current: object, candidate: object) -> float | None:
    values = [float(value) for value in (current, candidate) if value is not None]
    return max(values) if values else None
