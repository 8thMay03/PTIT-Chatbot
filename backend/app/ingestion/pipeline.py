from pathlib import Path

from app.core.config import settings
from app.embeddings import EmbeddingModel, create_embedding_model
from app.ingestion.chunker import split_text
from app.ingestion.loaders import load_documents
from app.vectordb import JsonVectorStore, VectorStore


class IngestionPipeline:
    def __init__(
        self,
        embedding_model: EmbeddingModel | None = None,
        vector_store: VectorStore | None = None,
    ) -> None:
        self.embedding_model = embedding_model or create_embedding_model()
        self.vector_store = vector_store or JsonVectorStore(settings.vector_db_path)

    def ingest_documents(self) -> dict:
        document_count, chunks_payload = self.build_chunks()

        self.vector_store.reset()
        if chunks_payload:
            embeddings = self.embedding_model.embed([item["text"] for item in chunks_payload])
            self.vector_store.add(chunks_payload, embeddings)

        return {
            "documents": document_count,
            "chunks": len(chunks_payload),
            "collection": self.vector_store.collection_name,
        }

    def build_chunks(self) -> tuple[int, list[dict]]:
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

        return len(documents), chunks_payload


def _chunk_id(path: Path, chunk_index: int) -> str:
    safe_path = str(path).replace("\\", "/")
    return f"{safe_path}::chunk-{chunk_index}"


ingestion_pipeline = IngestionPipeline()
