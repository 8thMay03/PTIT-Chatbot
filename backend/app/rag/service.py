from pathlib import Path

from app.core.config import settings
from app.rag.chunker import split_text
from app.rag.document_loader import load_documents
from app.rag.embeddings import create_embedding_model
from app.rag.llm import answer_with_llm
from app.rag.vector_store import VectorStore


class RagService:
    def __init__(self) -> None:
        self.embedding_model = create_embedding_model()
        self.vector_store = VectorStore(settings.vector_db_path)

    def ingest_documents(self) -> dict:
        documents = load_documents(settings.documents_path)
        chunks_payload: list[dict] = []

        for document in documents:
            chunks = split_text(document.text, settings.chunk_size, settings.chunk_overlap)
            for chunk in chunks:
                chunks_payload.append(
                    {
                        "id": _chunk_id(document.path, chunk.index),
                        "text": chunk.text,
                        "metadata": {
                            "source": str(document.path),
                            "chunk_index": chunk.index,
                        },
                    }
                )

        if chunks_payload:
            embeddings = self.embedding_model.embed([item["text"] for item in chunks_payload])
            self.vector_store.reset()
            self.vector_store.add(chunks_payload, embeddings)

        return {
            "documents": len(documents),
            "chunks": len(chunks_payload),
            "collection": self.vector_store.collection_name,
        }

    def answer(self, question: str, top_k: int = 4) -> dict:
        question_embedding = self.embedding_model.embed([question])[0]
        contexts = self.vector_store.search(question_embedding, top_k=top_k)
        answer = answer_with_llm(question, contexts)

        return {
            "answer": answer,
            "sources": contexts,
        }


def _chunk_id(path: Path, chunk_index: int) -> str:
    safe_path = str(path).replace("\\", "/")
    return f"{safe_path}::chunk-{chunk_index}"


rag_service = RagService()
