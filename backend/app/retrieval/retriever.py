from app.core.config import settings
from app.embeddings import EmbeddingModel, create_embedding_model
from app.retrieval.bm25 import BM25Search
from app.retrieval.hybrid import reciprocal_rank_fusion
from app.vectordb import ChromaVectorStore, VectorStore


class Retriever:
    def __init__(
        self,
        embedding_model: EmbeddingModel | None = None,
        vector_store: VectorStore | None = None,
        keyword_search: BM25Search | None = None,
    ) -> None:
        self.embedding_model = embedding_model or create_embedding_model()
        self.vector_store = vector_store or ChromaVectorStore(settings.vector_db_path)
        self.keyword_search = keyword_search or BM25Search()

    def retrieve(self, query: str, top_k: int = 4) -> list[dict]:
        candidate_count = max(top_k, top_k * settings.hybrid_candidate_multiplier)
        query_embedding = self.embedding_model.embed([query])[0]
        vector_results = self.vector_store.search(query_embedding, top_k=candidate_count)
        keyword_results = self.keyword_search.search(query, top_k=candidate_count)
        return reciprocal_rank_fusion(
            vector_results,
            keyword_results,
            top_k=top_k,
            vector_weight=settings.hybrid_vector_weight,
            rank_constant=settings.hybrid_rrf_k,
        )


retriever = Retriever()
