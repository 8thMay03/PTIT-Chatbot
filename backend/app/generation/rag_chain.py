from app.generation.llm import answer_with_llm
from app.retrieval import Retriever, retriever


class RagChain:
    def __init__(self, retriever_: Retriever | None = None) -> None:
        self.retriever = retriever_ or retriever

    def answer(self, question: str, top_k: int = 4) -> dict:
        contexts = self.retriever.retrieve(question, top_k=top_k)
        answer = answer_with_llm(question, contexts)

        return {
            "answer": answer,
            "sources": contexts,
        }


rag_chain = RagChain()
