"""0002_add_pgvector_and_chunk_embedding

Revision ID: 0002_add_pgvector_and_chunk_embedding
Revises: 0001_initial_schema
Create Date: 2026-08-31 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "0002_pgvector"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    if is_postgres:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # Add embedding column to chunks
    op.add_column("chunks", sa.Column("embedding", Vector(1536), nullable=True))

    # On PostgreSQL, create HNSW index for cosine distance
    if is_postgres:
        op.execute(
            "CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw "
            "ON chunks USING hnsw (embedding vector_cosine_ops);"
        )


def downgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    if is_postgres:
        op.execute("DROP INDEX IF EXISTS idx_chunks_embedding_hnsw;")

    op.drop_column("chunks", "embedding")
