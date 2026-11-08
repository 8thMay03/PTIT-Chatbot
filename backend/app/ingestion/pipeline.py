"""Ingestion in two steps: parse stores a document's Markdown, chunk indexes it.

The parse step (parser + normalization, or a manual edit) writes documents.parsed_text
and leaves existing chunks serving retrieval. The chunk step splits that stored text,
embeds the chunks and replaces the document's index. Only a full rebuild runs both.
"""

import logging
from contextlib import nullcontext
from dataclasses import dataclass, replace
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import undefer

from app.core.config import PROJECT_ROOT, settings
from app.db.models import Document
from app.db.repositories import (
    ChunkRecord,
    DatasetConflict,
    DatasetNotFound,
    DocumentRecord,
    apply_document_move,
    delete_dataset_records,
    delete_document,
    get_document_id_by_source_path,
    get_document_identities,
    get_document_parsers,
    get_document_vector_ids,
    get_document_with_chunk_count,
    get_documents_by_ids,
    get_edited_markdown,
    list_dataset_filenames,
    replace_document_chunks,
    replace_knowledge_base,
    save_parsed_document,
    serialize_document,
    serialize_markdown,
)
from app.db.session import SessionLocal, init_db
from app.embeddings import EmbeddingModel, runtime_embedding_model
from app.ingestion.chunker import (
    Chunk,
    ParentChildChunk,
    compose_search_text,
    count_recognized_tables,
    find_table_coverage_issues,
    split_parent_child,
    split_text,
    table_row_search_index,
    table_search_body,
)
from app.ingestion.cleaner import clean_text
from app.ingestion.legal_units import legal_metadata
from app.ingestion.loaders import SourceDocument, load_documents
from app.ingestion.uploads import (
    delete_source_file,
    prepare_upload,
    publish_upload,
    resolve_source_path,
)
from app.parsers import (
    DocumentParseError,
    ProgressCallback,
    get_parser_name,
    read_document_text,
    resolve_parser_name,
)
from app.retrieval.bm25 import invalidate_bm25_cache
from app.vectordb import VectorStore, create_vector_store


logger = logging.getLogger("app.ingestion")


class DocumentStateError(RuntimeError):
    """The document's stored state does not allow the requested step."""


def dataset_dir(dataset_id: str) -> Path:
    """Thư mục chứa file nguồn của một dataset."""
    return settings.documents_path / "datasets" / dataset_id


def dataset_id_from_path(path: Path) -> str | None:
    """Suy dataset từ đường dẫn datasets/<id>/...; None nếu không phải."""
    try:
        rel = path.resolve().relative_to(settings.documents_path.resolve())
    except (OSError, ValueError):
        try:
            rel = Path(_source_path(path)).relative_to("data")
        except ValueError:
            return None
    parts = rel.parts
    if len(parts) >= 3 and parts[0] == "datasets":
        candidate = parts[1]
        if candidate and all(ch.isalnum() or ch in "-_" for ch in candidate):
            return candidate
    # Dạng source_path "data/datasets/<id>/..." khi resolve ngoài documents_path.
    try:
        posix = _source_path(path)
        pparts = Path(posix).parts
        if len(pparts) >= 4 and pparts[0] == "data" and pparts[1] == "datasets":
            return pparts[2]
    except Exception:
        return None
    return None


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
        self.embedding_model = embedding_model or runtime_embedding_model
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

        with SessionLocal() as session:
            identities = get_document_identities(session)
            from app.db.models import Dataset as _Dataset

            dataset_ids = set(session.scalars(select(_Dataset.id)))
        for document in _load_sources():
            built = _records_for_document(
                document, identities=identities, known_datasets=dataset_ids
            )
            if built is None:
                continue
            record, chunks, payload = built
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
            identities = get_document_identities(session)
            from app.db.models import Dataset as _Dataset

            dataset_ids = set(session.scalars(select(_Dataset.id)))
            parsed = 0
            for document in documents:
                resolved = _resolve_identity(document.path, identities, dataset_ids)
                if resolved is None:
                    continue
                document_id, dataset_id = resolved
                parsed += 1
                save_parsed_document(
                    session,
                    _document_record(
                        document, document_id=document_id, dataset_id=dataset_id
                    ),
                )
            session.commit()
        return {"documents": parsed}

    def parse_upload(
        self,
        filename: str,
        content: bytes,
        *,
        dataset_id: str,
        parser_name: str | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> dict:
        # Parse outside the document tree so neither a replacement nor an
        # in-progress upload can affect existing sources or a concurrent scan.
        with TemporaryDirectory(prefix="ptit-upload-") as folder:
            staged_path = prepare_upload(filename, content, Path(folder))
            return self.parse_staged_upload(
                staged_path, dataset_id=dataset_id, parser_name=parser_name, on_progress=on_progress
            )

    def parse_staged_upload(
        self,
        staged_path: Path,
        *,
        dataset_id: str,
        parser_name: str | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> dict:
        """Parse a validated upload staged outside the document tree, then publish it."""
        options = {"parser_name": parser_name} if parser_name is not None else {}
        text = read_document_text(staged_path, on_progress=on_progress, **options) or ""
        if not text.strip():
            raise DocumentParseError(f"{staged_path.name} không có nội dung văn bản.")
        if on_progress is not None:
            on_progress(96, "Đang lưu kết quả parse")
        path = dataset_dir(dataset_id) / staged_path.name
        document = SourceDocument(path=path, text=text, parser_name=get_parser_name(staged_path, parser_name))
        return self._save_parsed(document, staged_path=staged_path, dataset_id=dataset_id)

    def parse_path(
        self,
        path: Path,
        *,
        document_id: str | None = None,
        dataset_id: str | None = None,
        parser_name: str | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> dict:
        """Parse a file on disk; a new document needs ``dataset_id``, an existing one keeps its dataset."""
        options = {"parser_name": parser_name} if parser_name is not None else {}
        text = read_document_text(path, on_progress=on_progress, **options) or ""
        if not text.strip():
            raise DocumentParseError(f"{path.name} không có nội dung văn bản.")
        if on_progress is not None:
            on_progress(96, "Đang lưu kết quả parse")
        document = SourceDocument(path=path, text=text, parser_name=get_parser_name(path, parser_name))
        return self._save_parsed(document, document_id=document_id, dataset_id=dataset_id)

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
        dataset_id: str | None = None,
    ) -> dict:
        init_db()
        path = document.path
        with SessionLocal() as session:
            if dataset_id is not None:
                from app.db.models import Dataset as _Dataset

                if session.get(_Dataset, dataset_id) is None:
                    raise DatasetNotFound("Không tìm thấy dataset.")
            if document_id is None:
                # A repaired source path can differ from the path that originally
                # generated the stored ID. Reuse that identity for uploads as well.
                document_id = get_document_id_by_source_path(session, _source_path(path))
                if document_id is None and staged_path is not None and dataset_id is not None:
                    # Tài liệu cùng tên của dataset có thể nằm ngoài datasets/<id>/
                    # (kho cũ ở data/raw/...): bản tải lên thay thế nó tại chỗ.
                    same_name = _same_name_document(session, dataset_id, path.name)
                    if same_name is not None:
                        document_id, stored_path = same_name
                        path = _replacement_path(stored_path, path)
                        document = replace(document, path=path)
            elif session.get(Document, document_id) is None:
                # A background parse must not recreate a document deleted while
                # the parser was running. Dataset may itself have been deleted.
                if dataset_id is not None:
                    raise DatasetNotFound("Dataset đã bị xóa trong lúc parse; hãy tải lại danh sách.")
                raise DocumentStateError("Tài liệu đã bị xóa trong lúc parse; hãy tải lại danh sách.")
            resolved_dataset = dataset_id
            if document_id is not None and dataset_id is None:
                existing_doc = session.get(Document, document_id)
                if existing_doc is not None:
                    resolved_dataset = existing_doc.dataset_id
            if resolved_dataset is None:
                raise DocumentStateError("Tài liệu chưa thuộc dataset nào.")
            record = _document_record(
                document,
                document_id=document_id,
                dataset_id=resolved_dataset,
                size_bytes=_file_size(staged_path or path),
            )
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

    def chunk_documents(self, dataset_id: str | None = None) -> dict:
        """Re-chunk every parsed document from its stored Markdown, without parsing.

        Documents indexed before parse results were stored have no Markdown to read
        and are skipped; parsing them again stores it.
        """
        init_db()
        with SessionLocal() as session:
            query = select(Document).options(undefer(Document.parsed_text))
            if dataset_id is not None:
                from app.db.models import Dataset as _Dataset

                if session.get(_Dataset, dataset_id) is None:
                    raise DatasetNotFound("Không tìm thấy dataset.")
                query = query.where(Document.dataset_id == dataset_id)
            documents = session.scalars(query).all()
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

    def delete_dataset(self, dataset_id: str) -> dict:
        """Xóa dataset cùng tài liệu, chunk và file nguồn (sau commit)."""
        from app.ingestion.jobs import parse_jobs as _parse_jobs

        init_db()
        with SessionLocal() as session:
            from app.db.models import Dataset as _Dataset

            if session.get(_Dataset, dataset_id) is None:
                raise DatasetNotFound("Không tìm thấy dataset.")
            doc_ids = list(
                session.scalars(select(Document.id).where(Document.dataset_id == dataset_id))
            )
            for doc_id in doc_ids:
                if _parse_jobs.active_for_document(doc_id) is not None:
                    raise DatasetConflict(
                        "Dataset còn tài liệu đang parse; hãy chờ job hiện tại xong."
                    )
            count, source_paths, vector_ids = delete_dataset_records(session, dataset_id)
            session.commit()

        for source_path in source_paths:
            delete_source_file(source_path)
        # Dọn thư mục rỗng của dataset (file cũ ngoài datasets/ không bị ảnh hưởng).
        try:
            target = dataset_dir(dataset_id)
            if target.is_dir() and target.resolve().is_relative_to(
                settings.documents_path.resolve()
            ):
                try:
                    next(target.iterdir())
                except StopIteration:
                    target.rmdir()
        except OSError:
            pass
        if self._uses_external_store() and vector_ids:
            self.vector_store.delete(vector_ids)
        invalidate_bm25_cache()
        return {"id": dataset_id, "deleted": True, "documents": count}

    def move_documents(self, document_ids: list[str], target_id: str) -> dict:
        """Chuyển tài liệu sang dataset khác, giữ nguyên id/chunk/embedding."""
        from app.ingestion.jobs import parse_jobs as _parse_jobs

        init_db()
        if not document_ids or len(document_ids) > 500:
            raise DatasetConflict("Chọn từ 1 đến 500 tài liệu để chuyển.")
        with SessionLocal() as session:
            from app.db.models import Dataset as _Dataset

            if session.get(_Dataset, target_id) is None:
                raise DatasetNotFound("Không tìm thấy dataset đích.")
            documents = get_documents_by_ids(session, list(dict.fromkeys(document_ids)))
            if len(documents) != len(set(document_ids)):
                raise DatasetNotFound("Không tìm thấy một số tài liệu cần chuyển.")
            for document in documents:
                if _parse_jobs.active_for_document(document.id) is not None:
                    raise DatasetConflict(
                        f"Tài liệu “{Path(document.source_path).name}” đang parse; hãy chờ job xong."
                    )
            # Trùng tên ở đích → 409, không đổi gì (so cả lô với nhau và với tài liệu sẵn có).
            existing_names = list_dataset_filenames(session, target_id)
            moving_names: dict[str, str] = {}
            for document in documents:
                if document.dataset_id == target_id:
                    continue
                lowered = Path(document.source_path).name.casefold()
                if lowered in moving_names:
                    raise DatasetConflict(
                        f"Có nhiều tài liệu cùng tên “{Path(document.source_path).name}” trong lô chuyển."
                    )
                owner = existing_names.get(lowered)
                if owner is not None and owner not in {d.id for d in documents}:
                    raise DatasetConflict(
                        f"Dataset đích đã có file “{Path(document.source_path).name}”."
                    )
                moving_names[lowered] = document.id

            moves: list[tuple[Document, Path, Path]] = []
            for document in documents:
                if document.dataset_id == target_id:
                    continue
                file_name = Path(document.source_path).name
                dest = dataset_dir(target_id) / file_name
                dest.parent.mkdir(parents=True, exist_ok=True)
                src_resolved = resolve_source_path(document.source_path)
                moves.append((document, src_resolved, dest) if src_resolved else (document, None, dest))

            new_paths: dict[str, str] = {}
            for document, _src, dest in moves:
                new_paths[document.id] = _source_path(dest)

            renamed: list[tuple[Path, Path, bool]] = []
            try:
                for document, src, dest in moves:
                    if src is not None and src.is_file():
                        if dest.exists():
                            raise DatasetConflict(
                                f"Dataset đích đã có file “{dest.name}”."
                            )
                        try:
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            src.replace(dest)
                        except OSError as exc:
                            raise DatasetConflict(
                                "File đang được sử dụng, không thể chuyển lúc này."
                            ) from exc
                        renamed.append((src, dest, True))
                    for doc_row in documents:
                        if doc_row.id == document.id:
                            apply_document_move(session, doc_row, target_id, new_paths[document.id])
                            break
                session.commit()
            except Exception:
                session.rollback()
                for src, dest, _done in reversed(renamed):
                    try:
                        if dest.is_file():
                            dest.replace(src)
                    except OSError:
                        pass
                raise
        invalidate_bm25_cache()
        moved = len(moves)
        return {"moved": moved, "dataset_id": target_id}

    def enqueue_dataset_parse(self, dataset_id: str) -> dict:
        """Đưa mỗi tài liệu của dataset vào job parse nền với parser đã lưu.

        Bỏ qua Markdown sửa tay; tài liệu đang có job hoặc mất file nguồn tính vào
        ``skipped_busy``. ``jobs`` là các ``ParseJob`` vừa tạo.
        """
        from app.ingestion.jobs import ParseJobConflict
        from app.ingestion.jobs import parse_jobs as _parse_jobs

        init_db()
        with SessionLocal() as session:
            from app.db.models import Dataset as _Dataset

            if session.get(_Dataset, dataset_id) is None:
                raise DatasetNotFound("Không tìm thấy dataset.")
            rows = session.execute(
                select(
                    Document.id,
                    Document.source_path,
                    Document.document_metadata,
                ).where(Document.dataset_id == dataset_id)
            ).all()
        jobs = []
        skipped_edited = 0
        skipped_busy = 0
        for doc_id, source_path, metadata in rows:
            metadata = metadata if isinstance(metadata, dict) else {}
            if metadata.get("markdown_edited"):
                skipped_edited += 1
                continue
            if _parse_jobs.active_for_document(doc_id) is not None:
                skipped_busy += 1
                continue
            path = resolve_source_path(source_path)
            if path is None or not path.is_file():
                skipped_busy += 1
                continue
            stored_parser = metadata.get("parser")
            try:
                job = _parse_jobs.enqueue_parse(
                    doc_id,
                    path,
                    file_name=Path(source_path).name,
                    parser_name=resolve_parser_name(
                        path, stored_parser if isinstance(stored_parser, str) else None
                    ),
                )
            except ParseJobConflict:
                # Một parse khác vừa nhận tài liệu này giữa lúc kiểm tra và enqueue.
                skipped_busy += 1
                continue
            jobs.append(job)
        return {"jobs": jobs, "skipped_edited": skipped_edited, "skipped_busy": skipped_busy}

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


def _same_name_document(session, dataset_id: str, file_name: str) -> tuple[str, str] | None:
    """(id, source_path) của tài liệu trong dataset có cùng tên file, không phân biệt hoa/thường."""
    wanted = file_name.casefold()
    rows = session.execute(
        select(Document.id, Document.source_path)
        .where(Document.dataset_id == dataset_id)
        .order_by(Document.source_path)
    )
    for doc_id, source_path in rows:
        if Path(source_path).name.casefold() == wanted:
            return doc_id, source_path
    return None


def _replacement_path(source_path: str, fallback: Path) -> Path:
    """Đường dẫn đã lưu của tài liệu bị thay thế, chỉ khi nó nằm trong DOCUMENTS_PATH."""
    stored = Path(source_path)
    candidate = stored if stored.is_absolute() else PROJECT_ROOT / stored
    try:
        candidate.resolve().relative_to(settings.documents_path.resolve())
    except (OSError, ValueError):
        return fallback
    return candidate


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


def _resolve_identity(
    path: Path,
    identities: dict[str, tuple[str, str]],
    known_datasets: set[str],
) -> tuple[str | None, str] | None:
    """(document_id|None, dataset_id) của một file khi quét kho; None nếu chưa thuộc dataset nào.

    Tài liệu đã có trong DB giữ dataset cũ; file mới chỉ nhận khi nằm dưới
    datasets/<id>/ của một dataset tồn tại, còn lại bị bỏ qua.
    """
    source_path = _source_path(path)
    identity = identities.get(source_path)
    if identity is not None:
        return identity
    inferred = dataset_id_from_path(path)
    if inferred is not None and inferred in known_datasets:
        return None, inferred
    logger.warning("Bỏ qua %s: file chưa thuộc dataset nào.", source_path)
    return None


def _records_for_document(
    document: SourceDocument,
    *,
    identities: dict[str, tuple[str, str]],
    known_datasets: set[str],
) -> tuple[DocumentRecord, list[ChunkRecord], list[dict]] | None:
    resolved = _resolve_identity(document.path, identities, known_datasets)
    if resolved is None:
        return None
    document_id, dataset_id = resolved
    document_record = _document_record(document, document_id=document_id, dataset_id=dataset_id)
    chunk_records, chunks_payload = _chunk_records(
        document_record.id,
        document_record.source_path,
        document_record.title or document.path.stem,
        document.text,
    )
    return document_record, chunk_records, chunks_payload


def _document_record(
    document: SourceDocument,
    *,
    document_id: str | None = None,
    dataset_id: str | None = None,
    size_bytes: int | None = None,
) -> DocumentRecord:
    if document_id is None:
        # Tài liệu mới dùng uuid để chuyển dataset không đổi identity (D-01, S-02).
        document_id = uuid4().hex
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
        dataset_id=dataset_id,
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
    cleaned = clean_text(text)
    row_index = table_row_search_index(cleaned)
    for chunk in _split_document(text):
        if isinstance(chunk, ParentChildChunk):
            parent_index = chunk.parent_index
            child_index = chunk.child_index
            parent_id = _parent_id(document_id, parent_index)
            chunk_id = _child_id(document_id, parent_index, child_index)
            parent_text = chunk.parent_text
        else:
            parent_index = chunk.index
            child_index = 0
            chunk_id = _chunk_id(document_id, chunk.index)
            parent_id = chunk_id
            parent_text = chunk.text
        search_text = compose_search_text(
            document_title, chunk.section_path, table_search_body(chunk.text, row_index)
        )
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
            **legal_metadata(chunk),
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

    _log_table_coverage(document_id, cleaned, [record.text for record in chunk_records])
    return chunk_records, chunks_payload


def _log_table_coverage(document_id: str, cleaned: str, child_texts: list[str]) -> None:
    """Cảnh báo khi bảng có nguy cơ mất dữ liệu (không chặn ingest).

    ``cleaned`` là văn bản đã qua ``clean_text``. Hai dấu hiệu: tài liệu có
    nhiều dòng bắt đầu bằng ``|`` nhưng chunker không nhận ra bảng nào, hoặc
    bất biến bảo toàn hàng S-02 báo vi phạm.
    """
    pipe_lines = sum(1 for line in cleaned.splitlines() if line.strip().startswith("|"))
    if pipe_lines < 5:
        return
    tables = count_recognized_tables(cleaned)
    if tables == 0:
        logger.warning(
            "Tài liệu %s có %d dòng bắt đầu bằng '|' nhưng chunker không nhận ra bảng nào.",
            document_id,
            pipe_lines,
        )
        return
    issues = find_table_coverage_issues(cleaned, child_texts)
    if issues:
        by_kind: dict[str, int] = {}
        for issue in issues:
            by_kind[issue.kind] = by_kind.get(issue.kind, 0) + 1
        summary = ", ".join(f"{kind}={count}" for kind, count in sorted(by_kind.items()))
        logger.warning(
            "Tài liệu %s vi phạm bất biến bảng (%d bảng, %s).",
            document_id,
            tables,
            summary,
        )


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
    # ID mới dùng uuid để chuyển dataset không đổi identity; tài liệu cũ giữ ID.
    return uuid4().hex


def _source_path(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _content_hash(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _estimate_token_count(text: str) -> int:
    return max(1, len(text.split()))


def _chunk_id(document_id: str, chunk_index: int) -> str:
    return f"{document_id}::chunk-{chunk_index}"


def _parent_id(document_id: str, parent_index: int) -> str:
    return f"{document_id}::parent-{parent_index}"


def _child_id(document_id: str, parent_index: int, child_index: int) -> str:
    return f"{_parent_id(document_id, parent_index)}::child-{child_index}"


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
