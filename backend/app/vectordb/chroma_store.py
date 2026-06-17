from pathlib import Path
from typing import Any


class ChromaVectorStore:
    collection_name = "ptit_documents"

    def __init__(self, persist_path: Path, client: Any | None = None) -> None:
        persist_path.mkdir(parents=True, exist_ok=True)
        self.client = client or _create_persistent_client(persist_path)
        self.collection = self._get_or_create_collection()

    def reset(self) -> None:
        # Rebuild the collection from scratch during ingest so stale chunks are removed.
        try:
            self.client.delete_collection(name=self.collection_name)
        except Exception:
            pass

        self.collection = self._get_or_create_collection()

    def add(self, chunks: list[dict], embeddings: list[list[float]]) -> None:
        if not chunks:
            return

        # Embeddings are computed by app.embeddings, so Chroma only persists and indexes them.
        self.collection.add(
            ids=[item["id"] for item in chunks],
            documents=[item["text"] for item in chunks],
            metadatas=[item["metadata"] for item in chunks],
            embeddings=embeddings,
        )

    def search(self, query_embedding: list[float], top_k: int) -> list[dict]:
        if top_k <= 0:
            return []

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        documents = _first_result_batch(results.get("documents"))
        metadatas = _first_result_batch(results.get("metadatas"))
        distances = _first_result_batch(results.get("distances"))

        contexts: list[dict] = []
        for document, metadata, distance in zip(documents, metadatas, distances):
            metadata = metadata or {}
            contexts.append(
                {
                    "source": metadata.get("source", ""),
                    "source_name": metadata.get("source_name", ""),
                    "document_id": metadata.get("document_id", ""),
                    "chunk_id": metadata.get("chunk_id", ""),
                    "heading": metadata.get("heading", ""),
                    "heading_level": metadata.get("heading_level"),
                    "section_path": metadata.get("section_path", ""),
                    "chunk_index": int(metadata.get("chunk_index", 0)),
                    "text": document or "",
                    # With cosine space, Chroma distance is 1 - cosine similarity.
                    "score": 1.0 - float(distance),
                }
            )

        return contexts

    def _get_or_create_collection(self) -> Any:
        return self.client.get_or_create_collection(
            name=self.collection_name,
            # Keep embedding ownership in this app instead of Chroma's default embedder.
            embedding_function=None,
            configuration={"hnsw": {"space": "cosine"}},
        )


def _create_persistent_client(persist_path: Path) -> Any:
    try:
        import chromadb
    except ImportError as exc:
        raise RuntimeError(
            "ChromaDB is required for vector storage. Install backend dependencies with "
            '`pip install -e ".[dev]"` or `pip install chromadb`.'
        ) from exc

    return chromadb.PersistentClient(path=str(persist_path))


def _first_result_batch(value: Any) -> list:
    # Chroma query results are grouped by query; this app always sends one query at a time.
    if not value:
        return []
    return value[0] or []
