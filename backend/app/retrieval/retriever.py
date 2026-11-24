from app.core.config import settings
from app.embeddings import EmbeddingModel, embed_signed, runtime_embedding_model
from app.retrieval.bm25 import BM25Search
from app.retrieval.hybrid import reciprocal_rank_fusion
from app.retrieval.parent_child import collapse_parent_results
from app.vectordb import VectorStore, create_vector_store


class Retriever:
    def __init__(
        self,
        embedding_model: EmbeddingModel | None = None,
        vector_store: VectorStore | None = None,
        keyword_search: BM25Search | None = None,
    ) -> None:
        self.embedding_model = embedding_model or runtime_embedding_model
        self.vector_store = vector_store or create_vector_store()
        self.keyword_search = keyword_search or BM25Search()

    def retrieve(self, query: str, top_k: int = 4, dataset_ids: list[str] | None = None) -> list[dict]:
        candidate_count = max(top_k, top_k * settings.hybrid_candidate_multiplier)
        vectors, signature = embed_signed(self.embedding_model, [query], query=True)
        # Chỉ so với vector của cùng mô hình (D-02): đoạn chưa nhúng lại sau khi đổi mô hình
        # chỉ còn được tìm bằng BM25. Mô hình không có chữ ký (fake trong test) thì không lọc.
        search_options = {"embedding_signature": signature} if signature is not None else {}
        vector_results = self.vector_store.search(
            vectors[0], top_k=candidate_count, dataset_ids=dataset_ids, **search_options
        )
        keyword_results = self.keyword_search.search(query, top_k=candidate_count, dataset_ids=dataset_ids)
        fused_children = reciprocal_rank_fusion(
            vector_results,
            keyword_results,
            top_k=candidate_count,
            vector_weight=settings.hybrid_vector_weight,
            rank_constant=settings.hybrid_rrf_k,
        )
        return collapse_parent_results(fused_children, top_k=top_k)


retriever = Retriever()
