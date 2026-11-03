"""0008_datasets

Revision ID: 0008_datasets
Revises: 0007_model_profiles
Create Date: 2026-11-03 00:00:00.000 +07:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0008_datasets"
down_revision: Union[str, None] = "0007_model_profiles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(bind, table: str, column: str) -> bool:
    return any(col["name"] == column for col in sa.inspect(bind).get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    is_postgres = bind.dialect.name == "postgresql"

    # init_db() (create_all) có thể đã tạo bảng datasets trước khi migration chạy.
    if not inspector.has_table("datasets"):
        op.create_table(
            "datasets",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("name", sa.String(length=100), nullable=False, unique=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("enabled", sa.Boolean(), server_default=sa.true() if is_postgres else "1", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
    # Dòng mặc định cho kho tài liệu hiện có.
    existing = bind.execute(sa.text("SELECT id FROM datasets WHERE id = 'default'")).first()
    if existing is None:
        # Postgres không ép int → boolean khi gán; tham số kiểu Boolean chạy được cả SQLite.
        bind.execute(
            sa.text(
                "INSERT INTO datasets (id, name, description, enabled) "
                "VALUES (:id, :name, NULL, :enabled)"
            ).bindparams(sa.bindparam("enabled", type_=sa.Boolean())),
            {"id": "default", "name": "Mặc định", "enabled": True},
        )

    if not _has_column(bind, "documents", "dataset_id"):
        if is_postgres:
            op.add_column("documents", sa.Column("dataset_id", sa.String(), nullable=True))
            op.execute("UPDATE documents SET dataset_id = 'default' WHERE dataset_id IS NULL")
            op.execute("ALTER TABLE documents ALTER COLUMN dataset_id SET NOT NULL")
            op.create_foreign_key(
                "fk_documents_dataset_id",
                "documents",
                "datasets",
                ["dataset_id"],
                ["id"],
                ondelete="RESTRICT",
            )
            op.create_index("idx_documents_dataset_id", "documents", ["dataset_id"], unique=False)
        else:
            # SQLite không hỗ trợ ALTER constraint; dùng batch (copy-and-move).
            with op.batch_alter_table("documents") as batch:
                batch.add_column(
                    sa.Column("dataset_id", sa.String(), nullable=False, server_default="default")
                )
                batch.create_foreign_key(
                    "fk_documents_dataset_id",
                    "datasets",
                    ["dataset_id"],
                    ["id"],
                    ondelete="RESTRICT",
                )
                batch.create_index("idx_documents_dataset_id", ["dataset_id"])
            op.execute("UPDATE documents SET dataset_id = 'default' WHERE dataset_id IS NULL")
    else:
        # Bảng đã có cột (init_db tạo từ model mới): vẫn bảo đảm backfill + index + FK.
        op.execute("UPDATE documents SET dataset_id = 'default' WHERE dataset_id IS NULL")
        if is_postgres:
            indexes = [idx["name"] for idx in inspector.get_indexes("documents")]
            if "idx_documents_dataset_id" not in indexes:
                op.create_index("idx_documents_dataset_id", "documents", ["dataset_id"], unique=False)
            fks = [fk["name"] for fk in inspector.get_foreign_keys("documents")]
            if "fk_documents_dataset_id" not in fks:
                op.create_foreign_key(
                    "fk_documents_dataset_id",
                    "documents",
                    "datasets",
                    ["dataset_id"],
                    ["id"],
                    ondelete="RESTRICT",
                )
        else:
            # SQLite + batch: chỉ tạo index nếu thiếu; FK đã có từ create_all hoặc bỏ qua.
            try:
                with op.batch_alter_table("documents") as batch:
                    indexes = [idx["name"] for idx in sa.inspect(bind).get_indexes("documents")]
                    if "idx_documents_dataset_id" not in indexes:
                        batch.create_index("idx_documents_dataset_id", ["dataset_id"])
            except Exception:
                pass


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    is_postgres = bind.dialect.name == "postgresql"
    if _has_column(bind, "documents", "dataset_id"):
        if is_postgres:
            try:
                op.drop_constraint("fk_documents_dataset_id", "documents", type_="foreignkey")
            except Exception:
                pass
            try:
                op.drop_index("idx_documents_dataset_id", table_name="documents")
            except Exception:
                pass
            op.drop_column("documents", "dataset_id")
        else:
            with op.batch_alter_table("documents") as batch:
                try:
                    batch.drop_constraint("fk_documents_dataset_id", type_="foreignkey")
                except Exception:
                    pass
                try:
                    batch.drop_index("idx_documents_dataset_id")
                except Exception:
                    pass
                batch.drop_column("dataset_id")
    if inspector.has_table("datasets"):
        op.drop_table("datasets")
