"""0004_document_parsed_text

Revision ID: 0004_document_parsed_text
Revises: 0003_chunk_search_text
Create Date: 2026-10-26 23:40:00.000 +07:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0004_document_parsed_text"
down_revision: Union[str, None] = "0003_chunk_search_text"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Parse and chunk are separate steps: the chunk step reads the stored Markdown.
    # Documents indexed earlier stay NULL until they are parsed again.
    op.add_column("documents", sa.Column("parsed_text", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("parsed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "parsed_at")
    op.drop_column("documents", "parsed_text")
