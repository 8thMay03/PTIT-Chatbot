"""0005_users

Revision ID: 0005_users
Revises: 0004_document_parsed_text
Create Date: 2026-10-28 01:00:00.000 +07:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0005_users"
down_revision: Union[str, None] = "0004_document_parsed_text"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Student accounts. Conversations reference them through the owner key
    # "user:<id>" in conversations.user_id, so there is no foreign key.
    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("email", sa.String(length=254), nullable=False, unique=True),
        sa.Column("full_name", sa.String(length=100), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("users")
