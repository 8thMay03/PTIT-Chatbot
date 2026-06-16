from typing import Protocol


class VectorStore(Protocol):
    collection_name: str

    def reset(self) -> None:
        ...

    def add(self, chunks: list[dict], embeddings: list[list[float]]) -> None:
        ...

    def search(self, query_embedding: list[float], top_k: int) -> list[dict]:
        ...
