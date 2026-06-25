from pathlib import Path
from hashlib import sha256

from app.core.config import PROJECT_ROOT, settings
from app.db.repositories import ChunkRecord, DocumentRecord, replace_knowledge_base
from app.db.session import SessionLocal, init_db
from app.embeddings import EmbeddingModel, create_embedding_model
from app.ingestion.chunker import Chunk, ParentChildChunk, split_parent_child, split_text
from app.ingestion.loaders import load_documents
from app.retrieval.bm25 import invalidate_bm25_cache
from app.vectordb import ChromaVectorStore, VectorStore


class IngestionPipeline:
    def __init__(
        self,
        embedding_model: EmbeddingModel | None = None,
        vector_store: VectorStore | None = None,
    ) -> None:
        self.embedding_model = embedding_model or create_embedding_model()
        self.vector_store = vector_store or ChromaVectorStore(settings.vector_db_path)

    def ingest_documents(self) -> dict:
        init_db()
        document_records, chunk_records, chunks_payload = self.build_chunks()

        self.vector_store.reset()
        if chunks_payload:
            embeddings = self.embedding_model.embed([item["text"] for item in chunks_payload])
            self.vector_store.add(chunks_payload, embeddings)

        with SessionLocal() as session:
            replace_knowledge_base(session, document_records, chunk_records)
            session.commit()

        # The next keyword search lazily rebuilds one shared in-memory BM25 index.
        invalidate_bm25_cache()

        return {
            "documents": len(document_records),
            "chunks": len(chunks_payload),
            "collection": self.vector_store.collection_name,
        }

    def build_chunks(self) -> tuple[list[DocumentRecord], list[ChunkRecord], list[dict]]:
        documents = load_documents(settings.documents_path)
        document_records: list[DocumentRecord] = []
        chunk_records: list[ChunkRecord] = []
        chunks_payload: list[dict] = []

        for document in documents:
            document_id = _document_id(document.path)
            source_path = _source_path(document.path)
            document_records.append(
                DocumentRecord(
                    id=document_id,
                    source_path=source_path,
                    title=document.path.stem,
                    file_type=document.path.suffix.lower().lstrip("."),
                    content_hash=_content_hash(document.text),
                    metadata={"source": source_path},
                )
            )

            chunks = _split_document(document.text)
            for chunk in chunks:
                if isinstance(chunk, ParentChildChunk):
                    parent_index = chunk.parent_index
                    child_index = chunk.child_index
                    parent_id = _parent_id(document.path, parent_index)
                    chunk_id = _child_id(document.path, parent_index, child_index)
                    parent_text = chunk.parent_text
                else:
                    parent_index = chunk.index
                    child_index = 0
                    chunk_id = _chunk_id(document.path, chunk.index)
                    parent_id = chunk_id
                    parent_text = chunk.text
                metadata = {
                    "source": source_path,
                    "source_name": document.path.name,
                    "document_id": document_id,
                    "chunk_id": chunk_id,
                    "heading": chunk.heading,
                    "heading_level": chunk.heading_level,
                    "section_path": chunk.section_path,
                    "chunk_index": chunk.index,
                    "parent_id": parent_id,
                    "parent_index": parent_index,
                    "child_index": child_index,
                    "parent_text": parent_text,
                    "chunk_type": "child",
                }
                chunk_records.append(
                    ChunkRecord(
                        id=chunk_id,
                        document_id=document_id,
                        chunk_index=chunk.index,
                        text=chunk.text,
                        token_count=_estimate_token_count(chunk.text),
                        vector_id=chunk_id,
                        metadata=metadata,
                    )
                )
                chunks_payload.append(
                    {
                        "id": chunk_id,
                        "text": chunk.text,
                        "metadata": metadata,
                    }
                )

        return document_records, chunk_records, chunks_payload


def _document_id(path: Path) -> str:
    return sha256(_source_path(path).encode("utf-8")).hexdigest()


def _source_path(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _content_hash(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _estimate_token_count(text: str) -> int:
    return max(1, len(text.split()))


def _chunk_id(path: Path, chunk_index: int) -> str:
    return f"{_source_path(path)}::chunk-{chunk_index}"


def _parent_id(path: Path, parent_index: int) -> str:
    return f"{_source_path(path)}::parent-{parent_index}"


def _child_id(path: Path, parent_index: int, child_index: int) -> str:
    return f"{_parent_id(path, parent_index)}::child-{child_index}"


def _split_document(text: str) -> list[Chunk | ParentChildChunk]:
    if settings.parent_child_chunking_enabled:
        return split_parent_child(
            text,
            parent_size=settings.chunk_size,
            parent_overlap=settings.chunk_overlap,
            child_size=settings.child_chunk_size,
            child_overlap=settings.child_chunk_overlap,
        )
    return split_text(text, settings.chunk_size, settings.chunk_overlap)


ingestion_pipeline = IngestionPipeline()
