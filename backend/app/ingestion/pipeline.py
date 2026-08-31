from pathlib import Path
from hashlib import sha256

from app.core.config import PROJECT_ROOT, settings
from app.db.repositories import (
    ChunkRecord,
    DocumentRecord,
    delete_document,
    get_document_vector_ids,
    replace_knowledge_base,
    serialize_document,
    upsert_document,
)
from app.db.session import SessionLocal, init_db
from app.embeddings import EmbeddingModel, create_embedding_model
from app.ingestion.chunker import Chunk, ParentChildChunk, split_parent_child, split_text
from app.ingestion.loaders import SourceDocument, load_documents
from app.ingestion.uploads import delete_source_file, prepare_upload
from app.retrieval.bm25 import invalidate_bm25_cache
from app.vectordb import VectorStore, create_vector_store


class IngestionPipeline:
    def __init__(
        self,
        embedding_model: EmbeddingModel | None = None,
        vector_store: VectorStore | None = None,
    ) -> None:
        self.embedding_model = embedding_model or create_embedding_model()
        self.vector_store = vector_store or create_vector_store()

    def ingest_documents(self) -> dict:
        init_db()
        document_records, chunk_records, chunks_payload = self.build_chunks()

        embeddings: list[list[float]] = []
        if chunks_payload:
            embeddings = self.embedding_model.embed([item["text"] for item in chunks_payload])
            chunk_records = [
                ChunkRecord(
                    id=record.id,
                    document_id=record.document_id,
                    chunk_index=record.chunk_index,
                    text=record.text,
                    vector_id=record.vector_id,
                    token_count=record.token_count,
                    metadata=record.metadata,
                    embedding=emb,
                )
                for record, emb in zip(chunk_records, embeddings)
            ]

        with SessionLocal() as session:
            replace_knowledge_base(session, document_records, chunk_records)
            session.commit()

        if hasattr(self.vector_store, "add") and not hasattr(self.vector_store, "session_factory"):
            self.vector_store.reset()
            if chunks_payload and embeddings:
                self.vector_store.add(chunks_payload, embeddings)

        # The next keyword search lazily rebuilds one shared in-memory BM25 index.
        invalidate_bm25_cache()

        return {
            "documents": len(document_records),
            "chunks": len(chunks_payload),
            "collection": self.vector_store.collection_name,
        }

    def ingest_upload(self, filename: str, content: bytes) -> dict:
        path = prepare_upload(filename, content, settings.documents_path)
        return self.ingest_path(path)

    def ingest_path(self, path: Path) -> dict:
        init_db()
        text = path.read_text(encoding="utf-8")
        document_record, chunk_records, chunks_payload = _records_for_document(
            SourceDocument(path=path, text=text)
        )

        embeddings: list[list[float]] = []
        if chunks_payload:
            embeddings = self.embedding_model.embed([chunk["text"] for chunk in chunks_payload])
            chunk_records = [
                ChunkRecord(
                    id=record.id,
                    document_id=record.document_id,
                    chunk_index=record.chunk_index,
                    text=record.text,
                    vector_id=record.vector_id,
                    token_count=record.token_count,
                    metadata=record.metadata,
                    embedding=emb,
                )
                for record, emb in zip(chunk_records, embeddings)
            ]

        with SessionLocal() as session:
            existing_ids = get_document_vector_ids(session, document_record.id)
            if existing_ids:
                self.vector_store.delete(existing_ids)
            stored = upsert_document(session, document_record, chunk_records)
            session.commit()
            session.refresh(stored)
            document_item = serialize_document(stored, len(chunk_records), _file_size(path))

        if hasattr(self.vector_store, "add") and not hasattr(self.vector_store, "session_factory"):
            if chunks_payload and embeddings:
                self.vector_store.add(chunks_payload, embeddings)

        invalidate_bm25_cache()
        return document_item

    def delete_ingested_document(self, document_id: str) -> dict | None:
        init_db()
        with SessionLocal() as session:
            vector_ids = get_document_vector_ids(session, document_id)
            document = delete_document(session, document_id)
            if document is None:
                return None
            source_path = document.source_path
            self.vector_store.delete(vector_ids)
            session.commit()

        delete_source_file(source_path)
        invalidate_bm25_cache()
        return {"id": document_id, "deleted": True}

    def build_chunks(self) -> tuple[list[DocumentRecord], list[ChunkRecord], list[dict]]:
        documents = load_documents(settings.documents_path)
        document_records: list[DocumentRecord] = []
        chunk_records: list[ChunkRecord] = []
        chunks_payload: list[dict] = []

        for document in documents:
            record, chunks, payload = _records_for_document(document)
            document_records.append(record)
            chunk_records.extend(chunks)
            chunks_payload.extend(payload)

        return document_records, chunk_records, chunks_payload


def _records_for_document(document: SourceDocument) -> tuple[DocumentRecord, list[ChunkRecord], list[dict]]:
    document_id = _document_id(document.path)
    source_path = _source_path(document.path)
    size_bytes = _file_size(document.path)
    document_record = DocumentRecord(
        id=document_id,
        source_path=source_path,
        title=document.path.stem,
        file_type=document.path.suffix.lower().lstrip("."),
        content_hash=_content_hash(document.text),
        metadata={
            "source": source_path,
            "file_name": document.path.name,
            "size_bytes": size_bytes,
        },
    )

    chunk_records: list[ChunkRecord] = []
    chunks_payload: list[dict] = []
    for chunk in _split_document(document.text):
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

    return document_record, chunk_records, chunks_payload


def _file_size(path: Path) -> int | None:
    try:
        return path.stat().st_size
    except OSError:
        return None


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
