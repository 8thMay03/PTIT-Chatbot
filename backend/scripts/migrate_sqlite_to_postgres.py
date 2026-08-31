"""Migrate business data from SQLite to PostgreSQL.

Usage:
    python -m scripts.migrate_sqlite_to_postgres
    python -m scripts.migrate_sqlite_to_postgres --sqlite-path storage/ptit_chatbot.db --postgres-url postgresql+psycopg://user:pass@localhost:5432/ptit_chatbot
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Base, Chunk, Conversation, Document, Message, MessageSource


def get_sqlite_url(sqlite_path: str | Path | None = None) -> str:
    if sqlite_path:
        p = Path(sqlite_path).resolve()
        return f"sqlite:///{p.as_posix()}"
    if settings.database_url.startswith("sqlite"):
        return settings.database_url
    default_p = settings.database_path / "ptit_chatbot.db"
    return f"sqlite:///{default_p.as_posix()}"


def migrate_data(
    sqlite_url: str,
    postgres_url: str | None = None,
    truncate_target: bool = False,
    dry_run: bool = False,
) -> dict[str, int]:
    """Copy all records from SQLite to PostgreSQL preserving relations."""
    print(f"Connecting to source SQLite database: {sqlite_url}")
    src_engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})

    stats: dict[str, int] = {}

    if dry_run:
        with Session(src_engine) as src_session:
            conversations = src_session.scalars(select(Conversation)).all()
            messages = src_session.scalars(select(Message)).all()
            documents = src_session.scalars(select(Document)).all()
            chunks = src_session.scalars(select(Chunk)).all()
            sources = src_session.scalars(select(MessageSource)).all()
            stats["conversations"] = len(conversations)
            stats["messages"] = len(messages)
            stats["documents"] = len(documents)
            stats["chunks"] = len(chunks)
            stats["message_sources"] = len(sources)
            print("Dry run summary of source SQLite data:")
            for table, count in stats.items():
                print(f"  - {table}: {count} records")
            return stats

    if not postgres_url:
        raise ValueError("postgres_url must be provided for live migration.")

    print(f"Connecting to target PostgreSQL database: {postgres_url}")
    dst_engine = create_engine(postgres_url)

    # Ensure tables exist on target
    Base.metadata.create_all(bind=dst_engine)


    with Session(src_engine) as src_session, Session(dst_engine) as dst_session:
        try:
            if truncate_target and not dry_run:
                print("Truncating target PostgreSQL tables...")
                dst_session.execute(text("TRUNCATE TABLE message_sources, chunks, documents, messages, conversations CASCADE"))
                dst_session.flush()

            # 1. Migrate Conversations
            conversations = src_session.scalars(select(Conversation)).all()
            print(f"Found {len(conversations)} conversations in SQLite.")
            if not dry_run:
                for conv in conversations:
                    if not dst_session.get(Conversation, conv.id):
                        dst_session.add(
                            Conversation(
                                id=conv.id,
                                user_id=conv.user_id,
                                title=conv.title,
                                created_at=conv.created_at,
                                updated_at=conv.updated_at,
                            )
                        )
                dst_session.flush()
            stats["conversations"] = len(conversations)

            # 2. Migrate Messages
            messages = src_session.scalars(select(Message)).all()
            print(f"Found {len(messages)} messages in SQLite.")
            if not dry_run:
                for msg in messages:
                    if not dst_session.get(Message, msg.id):
                        dst_session.add(
                            Message(
                                id=msg.id,
                                conversation_id=msg.conversation_id,
                                role=msg.role,
                                content=msg.content,
                                message_metadata=msg.message_metadata,
                                created_at=msg.created_at,
                            )
                        )
                dst_session.flush()
            stats["messages"] = len(messages)

            # 3. Migrate Documents
            documents = src_session.scalars(select(Document)).all()
            print(f"Found {len(documents)} documents in SQLite.")
            if not dry_run:
                for doc in documents:
                    if not dst_session.get(Document, doc.id):
                        dst_session.add(
                            Document(
                                id=doc.id,
                                source_path=doc.source_path,
                                title=doc.title,
                                file_type=doc.file_type,
                                content_hash=doc.content_hash,
                                status=doc.status,
                                document_metadata=doc.document_metadata,
                                created_at=doc.created_at,
                                updated_at=doc.updated_at,
                            )
                        )
                dst_session.flush()
            stats["documents"] = len(documents)

            # 4. Migrate Chunks
            chunks = src_session.scalars(select(Chunk)).all()
            print(f"Found {len(chunks)} chunks in SQLite.")
            if not dry_run:
                for chunk in chunks:
                    if not dst_session.get(Chunk, chunk.id):
                        dst_session.add(
                            Chunk(
                                id=chunk.id,
                                document_id=chunk.document_id,
                                chunk_index=chunk.chunk_index,
                                text=chunk.text,
                                token_count=chunk.token_count,
                                vector_id=chunk.vector_id,
                                chunk_metadata=chunk.chunk_metadata,
                                created_at=chunk.created_at,
                            )
                        )
                dst_session.flush()
            stats["chunks"] = len(chunks)

            # 5. Migrate Message Sources
            sources = src_session.scalars(select(MessageSource)).all()
            print(f"Found {len(sources)} message sources in SQLite.")
            if not dry_run:
                for src in sources:
                    if not dst_session.get(MessageSource, src.id):
                        dst_session.add(
                            MessageSource(
                                id=src.id,
                                message_id=src.message_id,
                                chunk_id=src.chunk_id,
                                score=src.score,
                                excerpt=src.excerpt,
                                created_at=src.created_at,
                            )
                        )
                dst_session.flush()
            stats["message_sources"] = len(sources)

            if not dry_run:
                dst_session.commit()
                print("Migration committed successfully!")
            else:
                print("Dry run completed - no changes written to target.")

        except Exception:
            dst_session.rollback()
            print("Error during migration, transaction rolled back.", file=sys.stderr)
            raise

    return stats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate PTIT Chatbot data from SQLite to PostgreSQL")
    parser.add_argument(
        "--sqlite-path",
        type=str,
        default=None,
        help="Path to SQLite database file (defaults to settings.database_url or backend/storage/ptit_chatbot.db)",
    )
    parser.add_argument(
        "--postgres-url",
        type=str,
        default=None,
        help="Target PostgreSQL connection URL (defaults to DATABASE_URL if pointing to Postgres)",
    )
    parser.add_argument(
        "--truncate-target",
        action="store_true",
        help="Truncate target tables before inserting data",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scan and report records without writing to target",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sqlite_url = get_sqlite_url(args.sqlite_path)
    postgres_url = args.postgres_url or (
        settings.database_url if settings.is_postgres else "postgresql+psycopg://ptit_user:ptit_password@localhost:5432/ptit_chatbot"
    )

    print("==========================================")
    print("PTIT Chatbot - SQLite to PostgreSQL Data Migration")
    print("==========================================")
    stats = migrate_data(
        sqlite_url=sqlite_url,
        postgres_url=postgres_url,
        truncate_target=args.truncate_target,
        dry_run=args.dry_run,
    )

    print("\nMigration Summary:")
    for table, count in stats.items():
        print(f"  - {table}: {count} records")


if __name__ == "__main__":
    main()
