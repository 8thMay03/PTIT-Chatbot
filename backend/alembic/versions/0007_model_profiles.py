"""0007_model_profiles

Revision ID: 0007_model_profiles
Revises: 0006_app_config_overrides
Create Date: 2026-10-30 09:10:00.000 +07:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0007_model_profiles"
down_revision: Union[str, None] = "0006_app_config_overrides"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # init_db() runs Base.metadata.create_all on startup, so a hot-reloaded backend
    # may have created the table before this migration ran (see 0005_users).
    if sa.inspect(op.get_bind()).has_table("model_profiles"):
        return

    # Model configurations the admin entered on the Models screen (LLM, embedding,
    # reranker). API keys live only in encrypted_api_key (Fernet, CONFIG_ENCRYPTION_KEY).
    op.create_table(
        "model_profiles",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=True),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("encrypted_api_key", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("kind", "name", name="uq_model_profiles_kind_name"),
    )


def downgrade() -> None:
    op.drop_table("model_profiles")
