"""Ingestion in two steps: parse stores a document's Markdown, chunk indexes it.

The parse step (parser + normalization, or a manual edit) writes documents.parsed_text
and leaves existing chunks serving retrieval. The chunk step splits that stored text,
embeds the chunks and replaces the document's index. Only a full rebuild runs both.
"""

from contextlib import nullcontext
from dataclasses import dataclass, replace
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import select
from sqlalchemy.orm import undefer

from app.core.config import PROJECT_ROOT, settings
from app.db.models import Document
from app.db.repositories import (
    ChunkRecord,
    DocumentRecord,
    delete_document,
    get_document_id_by_source_path,
    get_document_parsers,
    get_document_vector_ids,
    get_document_with_chunk_count,
    get_edited_markdown,
    replace_document_chunks,
    replace_knowledge_base,
    save_parsed_document,
    serialize_document,
    serialize_markdown,
)
from app.db.session import SessionLocal, init_db
from app.embeddings import EmbeddingModel, create_embedding_model
from app.ingestion.chunker import (
    Chunk,
    ParentChildChunk,
    compose_search_text,
    split_parent_child,
    split_text,
)
from app.parsers import DocumentParseError, get_parser_name, read_document_text
from app.ingestion.loaders import SourceDocument, load_documents
from app.ingestion.uploads import delete_source_file, prepare_upload, publish_upload
from app.retrieval.bm25 import invalidate_bm25_cache
from app.vectordb import VectorStore, create_vector_store


class DocumentStateError(RuntimeError):
    """The document's stored state does not allow the requested step."""


@dataclass(frozen=True)
class _ParsedDocument:
    """Stored parse result read before the slow embedding work, checked again after."""

    id: str
    source_path: str
    title: str
    text: str | None
    content_hash: str

    @classmethod
    def from_model(cls, document: Document) -> "_ParsedDocument":
        return cls(
            id=document.id,
            source_path=document.source_path,
            title=document.title or Path(document.source_path).stem,
            text=document.parsed_text,
            content_hash=document.content_hash,
        )


class IngestionPipeline:
    def __init__(
        self,
        embedding_model: EmbeddingModel | None = None,
        vector_store: VectorStore | None = None,
    ) -> None:
        self.embedding_model = embedding_model or create_embedding_model()
        self.vector_store = vector_store or create_vector_store()

    # ---- Full rebuild: parse + chunk every source file ----

    def ingest_documents(self) -> dict:
        init_db()
        document_records, chunk_records, chunks_payload = self.build_chunks()
        chunk_records, embeddings = self._embed(chunk_records, chunks_payload)

        with SessionLocal() as session:
            replace_knowledge_base(session, document_records, chunk_records)
            session.commit()

        if self._uses_external_store():
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

    def build_chunks(self) -> tuple[list[DocumentRecord], list[ChunkRecord], list[dict]]:
        document_records: list[DocumentRecord] = []
        chunk_records: list[ChunkRecord] = []
        chunks_payload: list[dict] = []

        for document in _load_sources():
            record, chunks, payload = _records_for_document(document)
            document_records.append(record)
            chunk_records.extend(chunks)
            chunks_payload.extend(payload)

        return document_records, chunk_records, chunks_payload

    # ---- Parse step ----

    def parse_documents(self) -> dict:
        """Parse every source file and store its Markdown; chunks are left untouched."""
        init_db()
        documents = _load_sources()
        with SessionLocal() as session:
            for document in documents:
                document_id = get_document_id_by_source_path(session, _source_path(document.path))
                save_parsed_document(session, _document_record(document, document_id=document_id))
            session.commit()
        return {"documents": len(documents)}

    def parse_upload(self, filename: str, content: bytes, *, parser_name: str | None = None) -> dict:
        # Parse outside the document tree so neither a replacement nor an
        # in-progress upload can affect existing sources or a concurrent scan.
        options = {"parser_name": parser_name} if parser_name is not None else {}
        with TemporaryDirectory(prefix="ptit-upload-") as folder:
            staged_path = prepare_upload(filename, content, Path(folder))
            text = read_document_text(staged_path, **options) or ""
            if not text.strip():
                raise DocumentParseError(f"{staged_path.name} không có nội dung văn bản.")
            path = settings.documents_path / staged_path.name
            document = SourceDocument(path=path, text=text, parser_name=get_parser_name(staged_path, parser_name))
            return self._save_parsed(document, staged_path=staged_path)

    def parse_path(self, path: Path, *, document_id: str | None = None, parser_name: str | None = None) -> dict:
        options = {"parser_name": parser_name} if parser_name is not None else {}
        text = read_document_text(path, **options) or ""
        if not text.strip():
            raise DocumentParseError(f"{path.name} không có nội dung văn bản.")
        document = SourceDocument(path=path, text=text, parser_name=get_parser_name(path, parser_name))
        return self._save_parsed(document, document_id=document_id)

    def save_markdown(self, document_id: str, text: str, *, base_hash: str | None = None) -> dict | None:
        """Replace a document's parsed Markdown with a manual edit; chunking stays separate.

        Returns the stored Markdown with its new content_hash for the editor's next save.
        """
        init_db()
        with SessionLocal() as session:
            document = session.get(Document, document_id)
            if document is None:
                return None
            if document.parsed_text is None:
                raise DocumentStateError("Tài liệu chưa có bản parse đã lưu; hãy parse lại trước khi sửa Markdown.")
            if base_hash is not None and base_hash != document.content_hash:
                raise DocumentStateError(
                    "Markdown của tài liệu đã thay đổi kể từ khi mở trình sửa; hãy tải lại rồi sửa tiếp."
                )
            content_hash = _content_hash(text)
            metadata = dict(document.document_metadata or {})
            if content_hash != document.content_hash:
                metadata["markdown_edited"] = True
            record = DocumentRecord(
                id=document.id,
                source_path=document.source_path,
                title=document.title,
                file_type=document.file_type,
                content_hash=content_hash,
                metadata=metadata,
                parsed_text=text,
            )
            stored = save_parsed_document(session, record)
            session.commit()
            session.refresh(stored)
            return serialize_markdown(stored)

    def _save_parsed(
        self,
        document: SourceDocument,
        *,
        document_id: str | None = None,
        staged_path: Path | None = None,
    ) -> dict:
        init_db()
        path = document.path
        with SessionLocal() as session:
            if document_id is None:
                # A repaired source path can differ from the path that originally
                # generated the stored ID. Reuse that identity for uploads as well.
                document_id = get_document_id_by_source_path(session, _source_path(path))
            record = _document_record(document, document_id=document_id, size_bytes=_file_size(staged_path or path))
            stored = save_parsed_document(session, record)
            # Parsing and the DB flush have succeeded before publication.
            # A failed commit rolls back both the stored text and the source file.
            publication = publish_upload(staged_path, path) if staged_path is not None else nullcontext()
            with publication:
                session.commit()
            return _serialize(session, stored, _file_size(path))

    # ---- Chunk step ----

    def chunk_document(self, document_id: str) -> dict | None:
        """Split, embed and index one document from its stored Markdown."""
        init_db()
        with SessionLocal() as session:
            document = session.get(Document, document_id)
            if document is None:
                return None
            parsed = _ParsedDocument.from_model(document)
        if parsed.text is None:
            raise DocumentStateError("Tài liệu chưa có bản parse đã lưu; hãy parse lại trước khi chia đoạn.")

        chunk_records, chunks_payload = _chunk_records(parsed.id, parsed.source_path, parsed.title, parsed.text)
        chunk_records, embeddings = self._embed(chunk_records, chunks_payload)

        with SessionLocal() as session:
            document = _current_document(session, parsed)
            existing_ids = get_document_vector_ids(session, document_id)
            replace_document_chunks(session, document, chunk_records)
            session.commit()
            item = _serialize(session, document)

        self._replace_vectors(existing_ids, chunks_payload, embeddings)
        invalidate_bm25_cache()
        return item

    def chunk_documents(self) -> dict:
        """Re-chunk every parsed document from its stored Markdown, without parsing.

        Documents indexed before parse results were stored have no Markdown to read
        and are skipped; parsing them again stores it.
        """
        init_db()
        with SessionLocal() as session:
            documents = session.scalars(select(Document).options(undefer(Document.parsed_text))).all()
            parsed = [_ParsedDocument.from_model(item) for item in documents if item.parsed_text is not None]
            skipped = len(documents) - len(parsed)

        records_by_document: dict[str, list[ChunkRecord]] = {}
        chunk_records: list[ChunkRecord] = []
        chunks_payload: list[dict] = []
        for item in parsed:
            records, payload = _chunk_records(item.id, item.source_path, item.title, item.text)
            chunk_records.extend(records)
            chunks_payload.extend(payload)
        chunk_records, embeddings = self._embed(chunk_records, chunks_payload)
        for record in chunk_records:
            records_by_document.setdefault(record.document_id, []).append(record)

        # One transaction: either every document gets its new chunks or none does.
        existing_ids: list[str] = []
        with SessionLocal() as session:
            for item in parsed:
                document = _current_document(session, item)
                existing_ids.extend(get_document_vector_ids(session, item.id))
                replace_document_chunks(session, document, records_by_document.get(item.id, []))
            session.commit()

        self._replace_vectors(existing_ids, chunks_payload, embeddings)
        invalidate_bm25_cache()
        return {
            "documents": len(parsed),
            "chunks": len(chunks_payload),
            "skipped": skipped,
            "collection": self.vector_store.collection_name,
        }

    # ---- Removal ----

    def delete_ingested_document(self, document_id: str) -> dict | None:
        init_db()
        with SessionLocal() as session:
            vector_ids = get_document_vector_ids(session, document_id)
            document = delete_document(session, document_id)
            if document is None:
                return None
            source_path = document.source_path
            session.commit()

        if self._uses_external_store() and vector_ids:
            self.vector_store.delete(vector_ids)

        delete_source_file(source_path)
        invalidate_bm25_cache()
        return {"id": document_id, "deleted": True}

    # ---- Helpers ----

    def _embed(
        self, chunk_records: list[ChunkRecord], chunks_payload: list[dict]
    ) -> tuple[list[ChunkRecord], list[list[float]]]:
        if not chunks_payload:
            return chunk_records, []
        embeddings = self.embedding_model.embed([_embedding_input(item) for item in chunks_payload])
        return [replace(record, embedding=emb) for record, emb in zip(chunk_records, embeddings)], embeddings

    def _uses_external_store(self) -> bool:
        # pgvector stores embeddings in the chunk rows written above.
        return not hasattr(self.vector_store, "session_factory")

    def _replace_vectors(self, old_ids: list[str], chunks_payload: list[dict], embeddings: list[list[float]]) -> None:
        if not self._uses_external_store():
            return
        if old_ids:
            self.vector_store.delete(old_ids)
        if chunks_payload and embeddings:
            self.vector_store.add(chunks_payload, embeddings)


def _load_sources() -> list[SourceDocument]:
    # A bulk parse keeps each document's parser choice (e.g. LlamaParse) instead of
    # silently re-reading it with the format default, and keeps manual Markdown edits.
    with SessionLocal() as session:
        stored_parsers = get_document_parsers(session)
        edited_markdown = get_edited_markdown(session)
    return load_documents(
        settings.documents_path,
        parser_for=lambda path: stored_parsers.get(_source_path(path)),
        edited_text_for=lambda path: edited_markdown.get(_source_path(path)),
    )


def _current_document(session, parsed: _ParsedDocument) -> Document:
    """Return the document if its Markdown is still the one that was chunked."""
    document = session.get(Document, parsed.id)
    if document is None or document.content_hash != parsed.content_hash:
        raise DocumentStateError(
            "Tài liệu vừa được parse lại, sửa hoặc xóa trong lúc chia đoạn; hãy chia đoạn lại."
        )
    return document


def _serialize(session, document: Document, size_bytes: int | None = None) -> dict:
    session.refresh(document)
    _document, chunk_count = get_document_with_chunk_count(session, document.id)
    return serialize_document(document, chunk_count, size_bytes)


def _records_for_document(
    document: SourceDocument, *, document_id: str | None = None, size_bytes: int | None = None
) -> tuple[DocumentRecord, list[ChunkRecord], list[dict]]:
    document_record = _document_record(document, document_id=document_id, size_bytes=size_bytes)
    chunk_records, chunks_payload = _chunk_records(
        document_record.id,
        document_record.source_path,
        document_record.title or document.path.stem,
        document.text,
    )
    return document_record, chunk_records, chunks_payload


def _document_record(
    document: SourceDocument, *, document_id: str | None = None, size_bytes: int | None = None
) -> DocumentRecord:
    if document_id is None:
        document_id = _document_id(document.path)
    source_path = _source_path(document.path)
    if size_bytes is None:
        size_bytes = _file_size(document.path)
    metadata = {
        "source": source_path,
        "file_name": document.path.name,
        "size_bytes": size_bytes,
        "parser": document.parser_name,
    }
    if document.markdown_edited:
        metadata["markdown_edited"] = True
    return DocumentRecord(
        id=document_id,
        source_path=source_path,
        title=document.path.stem,
        file_type=document.path.suffix.lower().lstrip("."),
        content_hash=_content_hash(document.text),
        metadata=metadata,
        parsed_text=document.text,
    )


def _chunk_records(
    document_id: str, source_path: str, document_title: str, text: str
) -> tuple[list[ChunkRecord], list[dict]]:
    chunk_records: list[ChunkRecord] = []
    chunks_payload: list[dict] = []
    source_name = Path(source_path).name
    for chunk in _split_document(text):
        if isinstance(chunk, ParentChildChunk):
            parent_index = chunk.parent_index
            child_index = chunk.child_index
            parent_id = _parent_id(source_path, parent_index)
            chunk_id = _child_id(source_path, parent_index, child_index)
            parent_text = chunk.parent_text
        else:
            parent_index = chunk.index
            child_index = 0
            chunk_id = _chunk_id(source_path, chunk.index)
            parent_id = chunk_id
            parent_text = chunk.text
        search_text = compose_search_text(document_title, chunk.section_path, chunk.text)
        metadata = {
            "source": source_path,
            "source_name": source_name,
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
                search_text=search_text,
                token_count=_estimate_token_count(chunk.text),
                vector_id=chunk_id,
                metadata=metadata,
            )
        )
        chunks_payload.append(
            {
                "id": chunk_id,
                "text": chunk.text,
                "search_text": search_text,
                "metadata": metadata,
            }
        )

    return chunk_records, chunks_payload


def _embedding_input(chunk_payload: dict) -> str:
    """Pick the field fed to the embedding model according to configuration."""
    field = settings.embedding_input_field.strip().lower()
    if field == "search_text":
        return chunk_payload["search_text"]
    return chunk_payload["text"]


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


def _chunk_id(source_path: str, chunk_index: int) -> str:
    return f"{source_path}::chunk-{chunk_index}"


def _parent_id(source_path: str, parent_index: int) -> str:
    return f"{source_path}::parent-{parent_index}"


def _child_id(source_path: str, parent_index: int, child_index: int) -> str:
    return f"{_parent_id(source_path, parent_index)}::child-{child_index}"


def _split_document(text: str) -> list[Chunk | ParentChildChunk]:
    if settings.parent_child_chunking_enabled:
        return split_parent_child(
            text,
            parent_size=settings.chunk_size,
            parent_overlap=settings.chunk_overlap,
            child_size=settings.child_chunk_size,
            child_overlap=settings.child_chunk_overlap,
            min_child_size=settings.min_child_chunk_chars,
        )
    return split_text(text, settings.chunk_size, settings.chunk_overlap)


ingestion_pipeline = IngestionPipeline()
