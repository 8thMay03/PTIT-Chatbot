from app.core.config import settings
from app.generation.confidence import has_strong_context
from app.generation.llm import answer_with_llm
from app.generation.citations import public_citations
from app.generation.multi_query import VietnameseMultiQueryGenerator
from app.generation.query_rewriter import VietnameseQueryRewriter
from app.retrieval import Retriever, retriever
from app.retrieval.multi_query import fuse_multi_query_results
from app.retrieval.reranker import Reranker

NO_CONTEXT_ANSWER = "Chưa tìm thấy thông tin này trong tài liệu."


class RagChain:
    def __init__(
        self,
        retriever_: Retriever | None = None,
        query_rewriter: VietnameseQueryRewriter | None = None,
        multi_query_generator: VietnameseMultiQueryGenerator | None = None,
        reranker: Reranker | None = None,
    ) -> None:
        self.retriever = retriever_ or retriever
        self.query_rewriter = query_rewriter or VietnameseQueryRewriter()
        self.multi_query_generator = multi_query_generator or VietnameseMultiQueryGenerator()
        self.reranker = reranker or Reranker()

    def answer(
        self,
        question: str,
        top_k: int = 4,
        history: list[dict[str, str]] | None = None,
    ) -> dict:
        history = history or []
        rewritten_query = self.query_rewriter.rewrite(question, history=history)
        queries = self.multi_query_generator.generate(rewritten_query)
        candidate_count = (
            max(top_k, top_k * settings.reranker_candidate_multiplier)
            if settings.reranker_enabled
            else top_k
        )
        result_sets = [
            self.retriever.retrieve(query, top_k=candidate_count)
            for query in queries
        ]
        contexts = fuse_multi_query_results(result_sets, top_k=candidate_count)
        if settings.reranker_enabled:
            contexts = self.reranker.rerank(rewritten_query, contexts, top_k=top_k)
        else:
            contexts = contexts[:top_k]
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

        answer = answer_with_llm(question, contexts, history=history)

        return {
            "answer": answer,
            "sources": public_citations(contexts),
            "contexts": contexts,
        }


rag_chain = RagChain()
