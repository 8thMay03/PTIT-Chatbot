from app.core.config import settings
from app.generation.confidence import has_strong_context
from app.generation.llm import answer_with_llm
from app.generation.citations import public_citations
from app.retrieval import Retriever, retriever

NO_CONTEXT_ANSWER = "Chưa tìm thấy thông tin này trong tài liệu."


class RagChain:
    def __init__(self, retriever_: Retriever | None = None) -> None:
        self.retriever = retriever_ or retriever

    def answer(self, question: str, top_k: int = 4) -> dict:
        contexts = self.retriever.retrieve(question, top_k=top_k)
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
