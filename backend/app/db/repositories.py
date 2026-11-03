from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from pathlib import Path

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.db.models import (
    DEFAULT_DATASET_ID,
    DEFAULT_DATASET_NAME,
    Chunk,
    Conversation,
    Dataset,
    Document,
    Message,
    MessageSource,
    User,
)


class DatasetNotFound(RuntimeError):
    """Dataset không tồn tại."""


class DatasetConflict(RuntimeError):
    """Tên dataset trùng hoặc thao tác bị cấm (mặc định / còn job)."""


def validate_dataset_name(name: str) -> str:
    """Trim và kiểm tra tên dataset; raise ValueError (422) khi không hợp lệ."""
    cleaned = str(name or "").strip()
    if not cleaned or len(cleaned) > 100:
        raise ValueError("Tên dataset phải từ 1 đến 100 ký tự.")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in cleaned):
        raise ValueError("Tên dataset không được chứa ký tự điều khiển.")
    return cleaned


def validate_dataset_description(description: str | None) -> str | None:
    if description is None:
        return None
    text = str(description).strip()
    if not text:
        return None
    if len(text) > 500:
        raise ValueError("Mô tả dataset tối đa 500 ký tự.")
    return text


def ensure_default_dataset(session: Session) -> Dataset:
    """Tạo dataset mặc định nếu chưa có (idempotent cho init_db và SQLite test)."""
    existing = session.get(Dataset, DEFAULT_DATASET_ID)
    if existing is not None:
        return existing
    dataset = Dataset(
        id=DEFAULT_DATASET_ID,
        name=DEFAULT_DATASET_NAME,
        description=None,
        enabled=True,
    )
    session.add(dataset)
    session.flush()
    return dataset


def get_dataset(session: Session, dataset_id: str) -> Dataset | None:
    return session.get(Dataset, dataset_id)


def get_dataset_by_name_ci(session: Session, name: str) -> Dataset | None:
    cleaned = str(name or "").strip()
    if not cleaned:
        return None
    lowered = cleaned.casefold()
    for dataset in session.scalars(select(Dataset)):
        if (dataset.name or "").strip().casefold() == lowered:
            return dataset
    return None


def list_datasets(session: Session) -> list[Dataset]:
    rows = list(session.scalars(select(Dataset)))
    rows.sort(key=lambda d: (d.id != DEFAULT_DATASET_ID, (d.name or "").casefold()))
    return rows


def create_dataset(session: Session, name: str, description: str | None = None) -> Dataset:
    cleaned = validate_dataset_name(name)
    if get_dataset_by_name_ci(session, cleaned) is not None:
        raise DatasetConflict(f"Dataset “{cleaned}” đã tồn tại.")
    dataset = Dataset(
        id=uuid4().hex,
        name=cleaned,
        description=validate_dataset_description(description),
        enabled=True,
    )
    session.add(dataset)
    session.flush()
    return dataset


def update_dataset(
    session: Session,
    dataset_id: str,
    *,
    name: str | None = None,
    description: str | None = None,
    enabled: bool | None = None,
    _clear_description: bool = False,
) -> Dataset:
    dataset = session.get(Dataset, dataset_id)
    if dataset is None:
        raise DatasetNotFound("Không tìm thấy dataset.")
    if name is not None:
        cleaned = validate_dataset_name(name)
        other = get_dataset_by_name_ci(session, cleaned)
        if other is not None and other.id != dataset.id:
            raise DatasetConflict(f"Dataset “{cleaned}” đã tồn tại.")
        dataset.name = cleaned
    if _clear_description or description is not None:
        dataset.description = validate_dataset_description(description) if not _clear_description else None
    if enabled is not None:
        dataset.enabled = bool(enabled)
    dataset.updated_at = datetime.now(timezone.utc)
    session.flush()
    return dataset


def get_dataset_stats(
    session: Session, dataset_id: str
) -> tuple[int, int, int, int | None]:
    """Trả (số tài liệu, số đoạn, số chờ chia đoạn, dung lượng bytes|None)."""
    from sqlalchemy import func as sa_func

    doc_count = session.scalar(
        select(sa_func.count()).select_from(Document).where(Document.dataset_id == dataset_id)
    ) or 0
    chunk_count = session.scalar(
        select(sa_func.count())
        .select_from(Chunk)
        .join(Document, Chunk.document_id == Document.id)
        .where(Document.dataset_id == dataset_id)
    ) or 0
    pending_count = session.scalar(
        select(sa_func.count())
        .select_from(Document)
        .where(Document.dataset_id == dataset_id, Document.status != "active")
    ) or 0
    size_bytes: int | None = None
    total = 0
    has_size = False
    for (metadata,) in session.execute(
        select(Document.document_metadata).where(Document.dataset_id == dataset_id)
    ):
        raw = (metadata or {}).get("size_bytes") if isinstance(metadata, dict) else None
        if isinstance(raw, int):
            total += raw
            has_size = True
    if has_size:
        size_bytes = total
    return doc_count, chunk_count, pending_count, size_bytes


def serialize_dataset(
    dataset: Dataset,
    document_count: int,
    chunk_count: int,
    pending_count: int,
    size_bytes: int | None,
) -> dict:
    return {
        "id": dataset.id,
        "name": dataset.name,
        "description": dataset.description,
        "enabled": bool(dataset.enabled),
        "is_default": dataset.id == DEFAULT_DATASET_ID,
        "document_count": document_count,
        "chunk_count": chunk_count,
        "pending_count": pending_count,
        "size_bytes": size_bytes,
        "created_at": dataset.created_at,
        "updated_at": dataset.updated_at,
    }


def list_datasets_with_stats(session: Session) -> list[dict]:
    ensure_default_dataset(session)
    payloads: list[dict] = []
    for dataset in list_datasets(session):
        doc_count, chunk_count, pending_count, size_bytes = get_dataset_stats(session, dataset.id)
        payloads.append(
            serialize_dataset(dataset, doc_count, chunk_count, pending_count, size_bytes)
        )
    return payloads


def get_dataset_with_stats(session: Session, dataset_id: str) -> dict | None:
    dataset = session.get(Dataset, dataset_id)
    if dataset is None:
        return None
    doc_count, chunk_count, pending_count, size_bytes = get_dataset_stats(session, dataset.id)
    return serialize_dataset(dataset, doc_count, chunk_count, pending_count, size_bytes)


def get_enabled_dataset_ids(session: Session) -> list[str]:
    return list(
        session.scalars(select(Dataset.id).where(Dataset.enabled.is_(True)))
    )


def dataset_has_enabled(session: Session, dataset_id: str) -> bool:
    return (
        session.scalar(select(Dataset.enabled).where(Dataset.id == dataset_id)) is True
    )


@dataclass(frozen=True)
class DocumentRecord:
    id: str
    source_path: str
    title: str | None
    file_type: str | None
    content_hash: str
    metadata: dict | None = None
    parsed_text: str | None = None
    dataset_id: str | None = None


@dataclass(frozen=True)
class ChunkRecord:
    id: str
    document_id: str
    chunk_index: int
    text: str
    vector_id: str
    search_text: str = ""
    token_count: int | None = None
    metadata: dict | None = None
    embedding: list[float] | None = None


def replace_knowledge_base(
    session: Session,
    documents: list[DocumentRecord],
    chunks: list[ChunkRecord],
) -> None:
    ensure_default_dataset(session)
    session.execute(delete(Document))
    session.flush()

    parsed_at = datetime.now(timezone.utc)
    session.add_all(
        Document(
            id=document.id,
            dataset_id=document.dataset_id or DEFAULT_DATASET_ID,
            source_path=document.source_path,
            title=document.title,
            file_type=document.file_type,
            content_hash=document.content_hash,
            status="active",
            parsed_text=document.parsed_text,
            parsed_at=parsed_at if document.parsed_text is not None else None,
            document_metadata=document.metadata,
        )
        for document in documents
    )
    session.flush()
    session.add_all(_chunk_model(chunk) for chunk in chunks)
    session.flush()



def list_documents(
    session: Session, dataset_id: str | None = None
) -> list[tuple[Document, int]]:
    chunk_count = func.count(Chunk.id).label("chunk_count")
    query = (
        select(Document, chunk_count)
        .outerjoin(Chunk, Chunk.document_id == Document.id)
        .group_by(Document.id)
        .order_by(Document.updated_at.desc(), Document.title.asc())
    )
    if dataset_id is not None:
        query = query.where(Document.dataset_id == dataset_id)
    rows = session.execute(query).all()
    return [(document, count) for document, count in rows]


def get_document_with_chunk_count(session: Session, document_id: str) -> tuple[Document, int] | None:
    chunk_count = func.count(Chunk.id).label("chunk_count")
    row = session.execute(
        select(Document, chunk_count)
        .outerjoin(Chunk, Chunk.document_id == Document.id)
        .where(Document.id == document_id)
        .group_by(Document.id)
    ).first()
    if row is None:
        return None
    return row[0], row[1]


def get_document_vector_ids(session: Session, document_id: str) -> list[str]:
    return list(session.scalars(select(Chunk.vector_id).where(Chunk.document_id == document_id)))


def get_document_id_by_source_path(session: Session, source_path: str) -> str | None:
    return session.scalar(select(Document.id).where(Document.source_path == source_path))


def get_document_parsers(session: Session) -> dict[str, str]:
    """Map source_path to the parser recorded at ingestion, for documents that have one."""
    parsers: dict[str, str] = {}
    for source_path, metadata in session.execute(select(Document.source_path, Document.document_metadata)):
        parser = (metadata or {}).get("parser")
        if isinstance(parser, str) and parser:
            parsers[source_path] = parser
    return parsers


def get_document_identities(session: Session) -> dict[str, tuple[str, str]]:
    """Map source_path to (id, dataset_id) để rebuild giữ identity khi nạp lại toàn bộ."""
    return {
        source_path: (doc_id, dataset_id)
        for source_path, doc_id, dataset_id in session.execute(
            select(Document.source_path, Document.id, Document.dataset_id)
        )
    }


def get_documents_by_ids(session: Session, document_ids: list[str]) -> list[Document]:
    if not document_ids:
        return []
    return list(session.scalars(select(Document).where(Document.id.in_(document_ids))))


def list_dataset_filenames(session: Session, dataset_id: str) -> dict[str, str]:
    """Map tên file (casefold) tới document id trong một dataset."""
    mapping: dict[str, str] = {}
    for doc_id, source_path in session.execute(
        select(Document.id, Document.source_path).where(Document.dataset_id == dataset_id)
    ):
        mapping[Path(source_path).name.casefold()] = doc_id
    return mapping


def get_edited_markdown(session: Session) -> dict[str, str]:
    """Map source_path to manually edited Markdown, which bulk re-parsing must keep."""
    rows = session.execute(
        select(Document.source_path, Document.parsed_text, Document.document_metadata).where(
            Document.parsed_text.is_not(None)
        )
    )
    return {
        source_path: text
        for source_path, text, metadata in rows
        if (metadata or {}).get("markdown_edited")
    }


def save_parsed_document(session: Session, document: DocumentRecord) -> Document:
    """Store a parse result or manual edit without touching the document's chunks.

    Existing chunks keep serving retrieval until the chunk step replaces them. The
    document stays "active" only when its text is unchanged since they were built.
    """
    now = datetime.now(timezone.utc)
    existing = session.get(Document, document.id)
    if existing is None:
        ensure_default_dataset(session)
        existing = Document(
            id=document.id,
            dataset_id=document.dataset_id or DEFAULT_DATASET_ID,
            status="parsed",
        )
        session.add(existing)
    else:
        if existing.status != "active" or existing.content_hash != document.content_hash:
            existing.status = "parsed"
        existing.updated_at = now
        if document.dataset_id is not None:
            existing.dataset_id = document.dataset_id
    existing.source_path = document.source_path
    existing.title = document.title
    existing.file_type = document.file_type
    existing.content_hash = document.content_hash
    existing.parsed_text = document.parsed_text
    existing.parsed_at = now
    existing.document_metadata = document.metadata
    session.flush()
    return existing


def replace_document_chunks(session: Session, document: Document, chunks: list[ChunkRecord]) -> None:
    """Replace every chunk of a document; its chunks now match its parsed text."""
    session.execute(delete(Chunk).where(Chunk.document_id == document.id))
    session.flush()
    session.add_all(_chunk_model(chunk) for chunk in chunks)
    document.status = "active"
    document.updated_at = datetime.now(timezone.utc)
    session.flush()


def _chunk_model(chunk: ChunkRecord) -> Chunk:
    return Chunk(
        id=chunk.id,
        document_id=chunk.document_id,
        chunk_index=chunk.chunk_index,
        text=chunk.text,
        search_text=chunk.search_text or chunk.text,
        token_count=chunk.token_count,
        vector_id=chunk.vector_id,
        embedding=chunk.embedding,
        chunk_metadata=chunk.metadata,
    )


def delete_document(session: Session, document_id: str) -> Document | None:
    document = session.get(Document, document_id)
    if document is None:
        return None
    session.delete(document)
    session.flush()
    return document


def apply_document_move(
    session: Session,
    document: Document,
    target_id: str,
    new_source_path: str,
) -> None:
    """Cập nhật dataset/source của một tài liệu và chunk metadata đi kèm (không commit)."""
    document.dataset_id = target_id
    document.source_path = new_source_path
    metadata = dict(document.document_metadata or {})
    metadata["source"] = new_source_path
    metadata["file_name"] = Path(new_source_path).name
    document.document_metadata = metadata
    document.updated_at = datetime.now(timezone.utc)
    chunks = list(session.scalars(select(Chunk).where(Chunk.document_id == document.id)))
    for chunk in chunks:
        chunk_meta = dict(chunk.chunk_metadata or {})
        chunk_meta["source"] = new_source_path
        chunk_meta["source_name"] = Path(new_source_path).name
        chunk.chunk_metadata = chunk_meta
    session.flush()


def delete_dataset_records(session: Session, dataset_id: str) -> tuple[int, list[str], list[str]]:
    """Xóa tài liệu + dataset trong một transaction; trả (số tài liệu, source_paths, vector_ids).

    Không xóa file/vector ngoài ở đây — pipeline làm sau commit. Cấm xóa dataset mặc định.
    """
    if dataset_id == DEFAULT_DATASET_ID:
        raise DatasetConflict("Không thể xóa dataset mặc định.")
    dataset = session.get(Dataset, dataset_id)
    if dataset is None:
        raise DatasetNotFound("Không tìm thấy dataset.")
    rows = list(
        session.execute(
            select(Document.id, Document.source_path).where(Document.dataset_id == dataset_id)
        )
    )
    document_ids = [row[0] for row in rows]
    source_paths = [row[1] for row in rows]
    vector_ids: list[str] = []
    if document_ids:
        vector_ids = list(
            session.scalars(select(Chunk.vector_id).where(Chunk.document_id.in_(document_ids)))
        )
        session.execute(delete(Document).where(Document.dataset_id == dataset_id))
        session.flush()
    session.delete(dataset)
    session.flush()
    return len(document_ids), source_paths, vector_ids


def get_document_preview_text(session: Session, document_id: str, limit: int = 2500) -> str | None:
    texts = list(
        session.scalars(
            select(Chunk.text)
            .where(Chunk.document_id == document_id)
            .order_by(Chunk.chunk_index)
            .limit(4)
        )
    )
    if not texts:
        return None
    joined = "\n\n".join(texts)
    if len(joined) <= limit:
        return joined
    return joined[:limit].rstrip() + "…"


def get_document_full_text(session: Session, document_id: str) -> str | None:
    """Tái tạo toàn văn tài liệu từ tất cả các đoạn (chunks) trong cơ sở dữ liệu."""
    texts = list(
        session.scalars(
            select(Chunk.text)
            .where(Chunk.document_id == document_id)
            .order_by(Chunk.chunk_index.asc())
        ).all()
    )
    if not texts:
        return None
    return "\n\n".join(texts)


def get_document_chunks(
    session: Session,
    document_id: str,
    offset: int = 0,
    limit: int = 100,
) -> list[Chunk]:
    return list(
        session.scalars(
            select(Chunk)
            .where(Chunk.document_id == document_id)
            .order_by(Chunk.chunk_index)
            .offset(offset)
            .limit(limit)
        )
    )


def serialize_document(document: Document, chunk_count: int, size_bytes: int | None = None) -> dict:
    metadata = document.document_metadata if isinstance(getattr(document, "document_metadata", None), dict) else (getattr(document, "document_metadata", None) or {})
    # Tương thích test cũ dùng SimpleNamespace chưa có dataset_id.
    dataset_id = getattr(document, "dataset_id", None) or DEFAULT_DATASET_ID
    file_name = Path(document.source_path).name
    if size_bytes is None:
        raw_size = metadata.get("size_bytes") if isinstance(metadata, dict) else None
        size_bytes = raw_size if isinstance(raw_size, int) else None
    return {
        "id": document.id,
        "dataset_id": dataset_id,
        "title": document.title or Path(document.source_path).stem,
        "file_name": file_name,
        "source_path": document.source_path,
        "file_type": document.file_type,
        "status": document.status,
        "markdown_edited": bool(metadata.get("markdown_edited")),
        # Set only once Markdown is stored, so clients know whether it can be edited or chunked.
        "parsed_at": document.parsed_at,
        "chunk_count": chunk_count,
        "size_bytes": size_bytes,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
    }


def serialize_markdown(document: Document) -> dict:
    """A document's stored Markdown with the hash an editor sends back to detect conflicts."""
    return {
        "document_id": document.id,
        "text": document.parsed_text,
        "content_hash": document.content_hash,
        "status": document.status,
        "parsed_at": document.parsed_at,
        "markdown_edited": bool((document.document_metadata or {}).get("markdown_edited")),
    }


def ensure_conversation(
    session: Session,
    conversation_id: str | None,
    user_id: str | None = None,
    title: str | None = None,
) -> Conversation | None:
    """Trả hội thoại theo id nếu thuộc owner (user_id), hoặc tạo mới.

    Nếu hội thoại tồn tại mà ``user_id`` khác ``conversations.user_id`` trả về
    None: caller (route chat) phải trả 404, tránh nối tiếp hội thoại của phiên
    khác. ``user_id`` lúc này là owner key của phiên ẩn danh, không phải giá trị
    client tự khai.
    """
    if conversation_id:
        conversation = session.get(Conversation, conversation_id)
        if conversation is not None:
            if user_id is not None and conversation.user_id != user_id:
                return None
            return conversation

    conversation = Conversation(id=conversation_id or str(uuid4()), user_id=user_id, title=title)
    session.add(conversation)
    session.flush()
    return conversation


def add_message(
    session: Session,
    conversation_id: str,
    role: str,
    content: str,
    metadata: dict | None = None,
) -> Message:
    message = Message(
        id=str(uuid4()),
        conversation_id=conversation_id,
        role=role,
        content=content,
        message_metadata=metadata,
        created_at=datetime.now(timezone.utc),
    )
    session.add(message)
    session.execute(
        update(Conversation)
        .where(Conversation.id == conversation_id)
        .values(updated_at=func.now())
    )
    session.flush()
    return message


def get_recent_conversation_history(
    session: Session,
    conversation_id: str,
    max_messages: int,
    max_chars: int,
) -> list[dict[str, str]]:
    if max_messages <= 0 or max_chars <= 0:
        return []

    messages = list(
        session.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(max_messages)
        )
    )
    chronological = [
        {"role": message.role, "content": message.content}
        for message in reversed(messages)
        if message.role in {"user", "assistant"}
    ]
    return limit_history(chronological, max_messages=max_messages, max_chars=max_chars)


def limit_history(
    messages: list[dict[str, str]],
    max_messages: int,
    max_chars: int,
) -> list[dict[str, str]]:
    """Keep the newest complete messages that fit within both memory limits."""
    if max_messages <= 0 or max_chars <= 0:
        return []

    selected: list[dict[str, str]] = []
    remaining_chars = max_chars
    for message in reversed(messages[-max_messages:]):
        content = message.get("content", "").strip()
        if not content or remaining_chars <= 0:
            continue
        if len(content) > remaining_chars:
            content = content[:remaining_chars].rstrip()
        selected.append({"role": message.get("role", "user"), "content": content})
        remaining_chars -= len(content)
    return list(reversed(selected))


def add_message_sources(session: Session, message_id: str, sources: list[dict]) -> None:
    if not sources:
        return

    chunk_ids = [source.get("chunk_id") for source in sources if source.get("chunk_id")]
    existing_chunk_ids = set(
        session.scalars(select(Chunk.id).where(Chunk.id.in_(chunk_ids))).all()
    ) if chunk_ids else set()

    session.add_all(
        MessageSource(
            id=str(uuid4()),
            message_id=message_id,
            chunk_id=source.get("chunk_id") if source.get("chunk_id") in existing_chunk_ids else None,
            score=source.get("score"),
            excerpt=source.get("text"),
        )
        for source in sources
    )


# ==========================================
# Lịch sử hội thoại
# ==========================================
def list_conversations(
    session: Session,
    limit: int = 50,
    offset: int = 0,
    user_id: str | None = None,
) -> tuple[list[tuple[Conversation, int]], int]:
    """Trả về các hội thoại kèm số tin nhắn, mới cập nhật trước.

    Bỏ qua hội thoại rỗng: mỗi lần mở màn chat mà không hỏi gì cũng có thể tạo ra
    một bản ghi, và chúng sẽ làm nhiễu danh sách bên thanh bên.
    """
    message_count = (
        select(Message.conversation_id, func.count(Message.id).label("total"))
        .group_by(Message.conversation_id)
        .subquery()
    )

    base = (
        select(Conversation, func.coalesce(message_count.c.total, 0))
        .join(message_count, message_count.c.conversation_id == Conversation.id)
        .where(message_count.c.total > 0)
    )
    if user_id:
        base = base.where(Conversation.user_id == user_id)

    total = session.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = session.execute(
        base.order_by(Conversation.updated_at.desc()).limit(limit).offset(offset)
    ).all()
    return [(row[0], row[1]) for row in rows], total


def get_conversation(session: Session, conversation_id: str) -> Conversation | None:
    return session.get(Conversation, conversation_id)


def get_owned_conversation(
    session: Session,
    conversation_id: str,
    owner_key: str,
) -> Conversation | None:
    """Hội thoại chỉ khi thuộc owner key cho trước; ngược lại None (route trả 404)."""
    conversation = session.get(Conversation, conversation_id)
    if conversation is None or conversation.user_id != owner_key:
        return None
    return conversation


def get_conversation_messages(session: Session, conversation_id: str) -> list[Message]:
    return list(
        session.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        ).all()
    )


def rename_conversation(session: Session, conversation_id: str, title: str) -> Conversation | None:
    conversation = session.get(Conversation, conversation_id)
    if conversation is None:
        return None
    conversation.title = title
    session.flush()
    return conversation


def delete_conversation(session: Session, conversation_id: str) -> bool:
    conversation = session.get(Conversation, conversation_id)
    if conversation is None:
        return False
    # Message và MessageSource có ondelete="CASCADE" nên bị xoá theo.
    session.delete(conversation)
    session.flush()
    return True


# ==========================================
# Tài khoản người dùng (landing-user-auth)
# ==========================================
def get_user_by_email(session: Session, email: str) -> User | None:
    """Tra theo email đã chuẩn hoá (trim + chữ thường)."""
    return session.scalar(select(User).where(User.email == email))


def create_user(session: Session, email: str, full_name: str, password_hash: str) -> User:
    user = User(id=str(uuid4()), email=email, full_name=full_name, password_hash=password_hash)
    session.add(user)
    session.flush()
    return user


def claim_anonymous_conversations(session: Session, anon_owner: str, user_owner: str) -> int:
    """Chuyển hội thoại của phiên ẩn danh hiện tại sang tài khoản; trả số hội thoại đã chuyển.

    Chỉ đụng hội thoại của đúng owner ẩn danh truyền vào (sid của trình duyệt đang
    đăng nhập). Giữ nguyên updated_at để thứ tự sidebar không đổi.
    """
    if not anon_owner.startswith("anon:") or anon_owner == user_owner:
        return 0
    result = session.execute(
        update(Conversation)
        .where(Conversation.user_id == anon_owner)
        .values(user_id=user_owner, updated_at=Conversation.updated_at)
        .execution_options(synchronize_session="fetch")
    )
    return result.rowcount or 0
