"""0003_add_chunk_search_text

Revision ID: 0003_chunk_search_text
Revises: 0002_pgvector
Create Date: 2026-10-25 09:35:00.000 +07:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0003_chunk_search_text"
down_revision: Union[str, None] = "0002_pgvector"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Embedding/BM25 field: contextual header (document title > section path) + text.
    op.add_column(
        "chunks",
        sa.Column("search_text", sa.Text(), nullable=False, server_default=""),
    )
    # Rows indexed before RAG-06 have no header context yet; re-ingestion rebuilds
    # them with the real composed value. Backfill keeps consumers non-empty.
    op.execute("UPDATE chunks SET search_text = text WHERE search_text = ''")


def downgrade() -> None:
    op.drop_column("chunks", "search_text")
