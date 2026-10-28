"""0006_app_config_overrides

Revision ID: 0006_app_config_overrides
Revises: 0005_users
Create Date: 2026-10-28 22:20:00.000 +07:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0006_app_config_overrides"
down_revision: Union[str, None] = "0005_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # init_db() runs Base.metadata.create_all on startup, so a hot-reloaded backend
    # may have created the table before this migration ran (see 0005_users).
    if sa.inspect(op.get_bind()).has_table("app_config_overrides"):
        return

    # Runtime config the admin changed from the UI, one row per Settings field.
    # API keys live only in encrypted_value (Fernet, key from CONFIG_ENCRYPTION_KEY).
    op.create_table(
        "app_config_overrides",
        sa.Column("key", sa.String(length=100), primary_key=True),
        sa.Column("value", sa.JSON(), nullable=True),
        sa.Column("encrypted_value", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("app_config_overrides")
