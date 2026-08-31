from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from app.api.routes import router
from app.core.config import Settings
from app.db.models import Base, Chunk, Conversation, Document, Message, MessageSource
from app.db.repositories import (
    ChunkRecord,
    DocumentRecord,
    add_message,
    add_message_sources,
    delete_document,
    ensure_conversation,
    get_document_chunks,
    get_document_with_chunk_count,
    get_recent_conversation_history,
    list_documents,
    replace_knowledge_base,
    upsert_document,
)
from app.db.session import check_db_health, create_app_engine, get_engine_options
from app.main import app
from scripts.migrate_sqlite_to_postgres import migrate_data


@pytest.fixture
def memory_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_database_url_normalization() -> None:
    s1 = Settings(DATABASE_URL="postgres://usr:pwd@host:5432/db")
    assert s1.database_url == "postgresql+psycopg://usr:pwd@host:5432/db"
    assert s1.is_postgres is True
    assert s1.is_sqlite is False

    s2 = Settings(DATABASE_URL="postgresql://usr:pwd@host:5432/db")
    assert s2.database_url == "postgresql+psycopg://usr:pwd@host:5432/db"
    assert s2.is_postgres is True

    s3 = Settings(DATABASE_URL="postgresql+psycopg://usr:pwd@host:5432/db")
    assert s3.database_url == "postgresql+psycopg://usr:pwd@host:5432/db"

    s4 = Settings(DATABASE_URL="sqlite:///test.db")
    assert s4.is_sqlite is True
    assert s4.is_postgres is False


def test_get_engine_options_for_postgres_and_sqlite() -> None:
    pg_opts = get_engine_options("postgresql+psycopg://user:pass@localhost:5432/db")
    assert pg_opts["pool_pre_ping"] is True
    assert "pool_size" in pg_opts
    assert "max_overflow" in pg_opts
    assert "connect_args" not in pg_opts

    sqlite_opts = get_engine_options("sqlite:///test.db")
    assert sqlite_opts["connect_args"] == {"check_same_thread": False}
    assert "pool_size" not in sqlite_opts


def test_check_db_health_with_valid_connection(monkeypatch) -> None:
    test_engine = create_engine("sqlite:///:memory:")
    monkeypatch.setattr("app.db.session.engine", test_engine)

    health = check_db_health()
    assert health["status"] == "ok"
    assert health["database"] == "connected"
    assert health["dialect"] == "sqlite"


def test_health_endpoint_reports_database_status(monkeypatch) -> None:
    test_engine = create_engine("sqlite:///:memory:")
    monkeypatch.setattr("app.db.session.engine", test_engine)

    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"
    assert data["database_type"] == "sqlite"


def test_alembic_upgrade_check_and_downgrade_cycle(tmp_path: Path) -> None:
    db_file = tmp_path / "alembic_test.db"
    db_url = f"sqlite:///{db_file.as_posix()}"

    alembic_ini_path = Path(__file__).resolve().parents[1] / "alembic.ini"
    cfg = Config(str(alembic_ini_path))
    cfg.set_main_option("sqlalchemy.url", db_url)

    command.upgrade(cfg, "head")
    command.check(cfg)

    # Verify tables created
    engine = create_engine(db_url)
    with engine.connect() as conn:
        tables = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table'")
        ).scalars().all()
        assert "conversations" in tables
        assert "messages" in tables
        assert "documents" in tables
        assert "chunks" in tables
        assert "message_sources" in tables

    command.downgrade(cfg, "base")


def test_repository_conversation_and_messages_lifecycle(memory_db: Session) -> None:
    session = memory_db
    conv = ensure_conversation(session, None, user_id="user-1", title="Hỏi học phí")
    assert conv.id is not None
    assert conv.user_id == "user-1"
    assert conv.title == "Hỏi học phí"

    # Add messages
    m1 = add_message(session, conv.id, "user", "Học phí năm nay thế nào?")
    m2 = add_message(session, conv.id, "assistant", "Học phí là 20 triệu/năm.")
    session.commit()

    history = get_recent_conversation_history(session, conv.id, max_messages=10, max_chars=5000)
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"


def test_repository_document_and_chunks_upsert_and_cascade(memory_db: Session) -> None:
    session = memory_db
    doc_id = "doc-test-1"
    doc = DocumentRecord(
        id=doc_id,
        source_path="data/quy-che.md",
        title="Quy chế đào tạo",
        file_type="md",
        content_hash="hash123",
        metadata={"size_bytes": 1024},
    )
    chunks = [
        ChunkRecord(
            id="chunk-1",
            document_id=doc_id,
            chunk_index=0,
            text="Điều 1. Quy định chung",
            vector_id="vec-1",
            token_count=10,
            metadata={"heading": "Điều 1"},
        ),
        ChunkRecord(
            id="chunk-2",
            document_id=doc_id,
            chunk_index=1,
            text="Điều 2. Thời gian đào tạo",
            vector_id="vec-2",
            token_count=12,
            metadata={"heading": "Điều 2"},
        ),
    ]

    upsert_document(session, doc, chunks)
    session.commit()

    docs = list_documents(session)
    assert len(docs) == 1
    assert docs[0][0].id == doc_id
    assert docs[0][1] == 2

    # Add a conversation message referencing chunk-1
    conv = ensure_conversation(session, None, title="Test citation")
    msg = add_message(session, conv.id, "assistant", "Theo Điều 1.")
    add_message_sources(
        session,
        msg.id,
        [{"chunk_id": "chunk-1", "score": 0.95, "text": "Điều 1. Quy định chung"}],
    )
    session.commit()

    sources = session.scalars(select(MessageSource).where(MessageSource.message_id == msg.id)).all()
    assert len(sources) == 1
    assert sources[0].chunk_id == "chunk-1"

    # Delete document should cascade delete chunks and set message_sources.chunk_id to NULL
    delete_document(session, doc_id)
    session.commit()

    assert session.get(Document, doc_id) is None
    assert session.scalars(select(Chunk).where(Chunk.document_id == doc_id)).all() == []
    # Source record remains with chunk_id=None or excerpt intact
    updated_source = session.get(MessageSource, sources[0].id)
    if updated_source is not None:
        assert updated_source.chunk_id is None


def test_repository_replace_knowledge_base(memory_db: Session) -> None:
    session = memory_db
    docs = [
        DocumentRecord(
            id="doc-a",
            source_path="data/a.md",
            title="A",
            file_type="md",
            content_hash="h1",
        )
    ]
    chunks = [
        ChunkRecord(
            id="c-a-1",
            document_id="doc-a",
            chunk_index=0,
            text="Nội dung A",
            vector_id="v-a-1",
        )
    ]
    replace_knowledge_base(session, docs, chunks)
    session.commit()

    assert len(list_documents(session)) == 1

    # Replace with new set
    docs2 = [
        DocumentRecord(
            id="doc-b",
            source_path="data/b.md",
            title="B",
            file_type="md",
            content_hash="h2",
        )
    ]
    chunks2 = [
        ChunkRecord(
            id="c-b-1",
            document_id="doc-b",
            chunk_index=0,
            text="Nội dung B",
            vector_id="v-b-1",
        )
    ]
    replace_knowledge_base(session, docs2, chunks2)
    session.commit()

    listed = list_documents(session)
    assert len(listed) == 1
    assert listed[0][0].id == "doc-b"


def test_sqlite_to_postgres_migration_flow(tmp_path: Path) -> None:
    src_db_file = tmp_path / "src.db"
    dst_db_file = tmp_path / "dst.db"
    src_url = f"sqlite:///{src_db_file.as_posix()}"
    dst_url = f"sqlite:///{dst_db_file.as_posix()}"

    # Setup source data
    src_engine = create_engine(src_url)
    Base.metadata.create_all(src_engine)

    with Session(src_engine) as session:
        conv = Conversation(id="conv-mig-1", user_id="u1", title="Test Mig")
        session.add(conv)
        msg = Message(id="msg-mig-1", conversation_id="conv-mig-1", role="user", content="Hello")
        session.add(msg)
        doc = Document(
            id="doc-mig-1",
            source_path="data/test.md",
            title="Test",
            file_type="md",
            content_hash="hash",
            status="active",
        )
        session.add(doc)
        chunk = Chunk(
            id="chunk-mig-1",
            document_id="doc-mig-1",
            chunk_index=0,
            text="Chunk content",
            vector_id="vec-mig-1",
        )
        session.add(chunk)
        src = MessageSource(
            id="src-mig-1",
            message_id="msg-mig-1",
            chunk_id="chunk-mig-1",
            score=0.9,
            excerpt="Chunk excerpt",
        )
        session.add(src)
        session.commit()

    # Run migration
    stats = migrate_data(src_url, dst_url)
    assert stats["conversations"] == 1
    assert stats["messages"] == 1
    assert stats["documents"] == 1
    assert stats["chunks"] == 1
    assert stats["message_sources"] == 1

    # Verify target data
    dst_engine = create_engine(dst_url)
    with Session(dst_engine) as dst_session:
        assert dst_session.get(Conversation, "conv-mig-1") is not None
        assert dst_session.get(Message, "msg-mig-1") is not None
        assert dst_session.get(Document, "doc-mig-1") is not None
        assert dst_session.get(Chunk, "chunk-mig-1") is not None
        assert dst_session.get(MessageSource, "src-mig-1") is not None
