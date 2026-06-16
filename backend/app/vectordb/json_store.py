from pathlib import Path
import json
import math


class JsonVectorStore:
    collection_name = "ptit_documents"

    def __init__(self, persist_path: Path) -> None:
        persist_path.mkdir(parents=True, exist_ok=True)
        self.index_path = persist_path / "index.json"

    def reset(self) -> None:
        self.index_path.write_text("[]", encoding="utf-8")

    def add(self, chunks: list[dict], embeddings: list[list[float]]) -> None:
        records = []
        for item, embedding in zip(chunks, embeddings):
            records.append(
                {
                    "id": item["id"],
                    "text": item["text"],
                    "metadata": item["metadata"],
                    "embedding": embedding,
                }
            )

        self.index_path.write_text(
            json.dumps(records, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def search(self, query_embedding: list[float], top_k: int) -> list[dict]:
        records = self._load_records()
        if not records:
            return []

        ranked = sorted(
            records,
            key=lambda record: _cosine_similarity(query_embedding, record["embedding"]),
            reverse=True,
        )[:top_k]

        contexts: list[dict] = []
        for record in ranked:
            metadata = record["metadata"]
            contexts.append(
                {
                    "source": metadata.get("source", ""),
                    "chunk_index": int(metadata.get("chunk_index", 0)),
                    "text": record["text"],
                    "score": _cosine_similarity(query_embedding, record["embedding"]),
                }
            )

        return contexts

    def _load_records(self) -> list[dict]:
        if not self.index_path.exists():
            return []
        return json.loads(self.index_path.read_text(encoding="utf-8"))


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left)) or 1.0
    right_norm = math.sqrt(sum(value * value for value in right)) or 1.0
    return dot / (left_norm * right_norm)
