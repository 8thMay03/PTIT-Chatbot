from app.core.config import settings
from app.embeddings import EmbeddingModel, create_embedding_model
from app.vectordb import ChromaVectorStore, VectorStore


class Retriever:
    def __init__(
        self,
        embedding_model: EmbeddingModel | None = None,
        vector_store: VectorStore | None = None,
    ) -> None:
        self.embedding_model = embedding_model or create_embedding_model()
        self.vector_store = vector_store or ChromaVectorStore(settings.vector_db_path)

    def retrieve(self, query: str, top_k: int = 4) -> list[dict]:
        query_embedding = self.embedding_model.embed([query])[0]
        return self.vector_store.search(query_embedding, top_k=top_k)


retriever = Retriever()
