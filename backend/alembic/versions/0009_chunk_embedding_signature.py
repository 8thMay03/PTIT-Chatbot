"""0009_chunk_embedding_signature

Revision ID: 0009_chunk_embedding_signature
Revises: 0008_datasets
Create Date: 2026-11-24 23:30:00.000 +07:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0009_chunk_embedding_signature"
down_revision: Union[str, None] = "0008_datasets"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(bind, table: str, column: str) -> bool:
    return any(col["name"] == column for col in sa.inspect(bind).get_columns(table))


def upgrade() -> None:
    # Đoạn cũ để NULL: lúc khởi động, app gán chữ ký của mô hình đang chạy
    # (app.ingestion.pipeline.adopt_unsigned_vectors) nên nâng cấp không bắt nhúng lại.
    if not _has_column(op.get_bind(), "chunks", "embedding_signature"):
        op.add_column("chunks", sa.Column("embedding_signature", sa.String(), nullable=True))


def downgrade() -> None:
    if _has_column(op.get_bind(), "chunks", "embedding_signature"):
        with op.batch_alter_table("chunks") as batch:
            batch.drop_column("embedding_signature")
