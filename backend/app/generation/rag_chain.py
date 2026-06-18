from app.core.config import settings
from app.generation.confidence import has_strong_context
from app.generation.llm import answer_with_llm
from app.generation.citations import public_citations
from app.generation.query_rewriter import VietnameseQueryRewriter
from app.retrieval import Retriever, retriever
from app.retrieval.reranker import Reranker

NO_CONTEXT_ANSWER = "Chưa tìm thấy thông tin này trong tài liệu."


class RagChain:
    def __init__(
        self,
        retriever_: Retriever | None = None,
        query_rewriter: VietnameseQueryRewriter | None = None,
        reranker: Reranker | None = None,
    ) -> None:
        self.retriever = retriever_ or retriever
        self.query_rewriter = query_rewriter or VietnameseQueryRewriter()
        self.reranker = reranker or Reranker()

    def answer(self, question: str, top_k: int = 4) -> dict:
        rewritten_query = self.query_rewriter.rewrite(question)
        candidate_count = (
            max(top_k, top_k * settings.reranker_candidate_multiplier)
            if settings.reranker_enabled
            else top_k
        )
        contexts = self.retriever.retrieve(rewritten_query, top_k=candidate_count)
        if settings.reranker_enabled:
            contexts = self.reranker.rerank(rewritten_query, contexts, top_k=top_k)
        if not has_strong_context(
            contexts,
            min_vector_score=settings.retrieval_min_vector_score,
            min_bm25_score=settings.retrieval_min_bm25_score,
        ):
            return {
                "answer": NO_CONTEXT_ANSWER,
                "sources": [],
                "contexts": [],
            }

        answer = answer_with_llm(question, contexts)

        return {
            "answer": answer,
            "sources": public_citations(contexts),
            "contexts": contexts,
        }


rag_chain = RagChain()
