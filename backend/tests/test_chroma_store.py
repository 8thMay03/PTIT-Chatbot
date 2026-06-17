from pathlib import Path

from app.vectordb.chroma_store import ChromaVectorStore


class FakeChromaClient:
    def __init__(self) -> None:
        self.collection = FakeChromaCollection()
        self.deleted_collections: list[str] = []

    def get_or_create_collection(self, **kwargs):
        self.collection.create_kwargs = kwargs
        return self.collection

    def delete_collection(self, name: str) -> None:
        self.deleted_collections.append(name)


class FakeChromaCollection:
    def __init__(self) -> None:
        self.create_kwargs = {}
        self.add_kwargs = {}

    def add(self, **kwargs) -> None:
        self.add_kwargs = kwargs

    def query(self, **kwargs):
        self.query_kwargs = kwargs
        return {
            "documents": [["first chunk"]],
            "metadatas": [[{"source": "data/source.md", "chunk_index": 2}]],
            "distances": [[0.25]],
        }


def test_chroma_vector_store_adds_precomputed_embeddings(tmp_path: Path) -> None:
    client = FakeChromaClient()
    store = ChromaVectorStore(tmp_path, client=client)

    store.add(
        [{"id": "doc-1", "text": "first chunk", "metadata": {"source": "data/source.md"}}],
        [[0.1, 0.2]],
    )

    assert client.collection.create_kwargs["embedding_function"] is None
    assert client.collection.add_kwargs == {
        "ids": ["doc-1"],
        "documents": ["first chunk"],
        "metadatas": [{"source": "data/source.md"}],
        "embeddings": [[0.1, 0.2]],
    }


def test_chroma_vector_store_search_maps_results(tmp_path: Path) -> None:
    store = ChromaVectorStore(tmp_path, client=FakeChromaClient())

    results = store.search([0.1, 0.2], top_k=4)

    assert results == [
        {
            "source": "data/source.md",
            "chunk_index": 2,
            "text": "first chunk",
            "score": 0.75,
        }
    ]
