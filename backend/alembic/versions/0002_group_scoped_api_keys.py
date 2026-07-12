"""Group scoped API keys.

Revision ID: 0002_group_scoped_api_keys
Revises: 0001_initial_schema
Create Date: 2026-07-11
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_group_scoped_api_keys"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("api_keys") as batch_op:
        batch_op.add_column(sa.Column("group_id", sa.String(length=36), nullable=True))
        batch_op.create_index(batch_op.f("ix_api_keys_group_id"), ["group_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_api_keys_group_id_document_groups",
            "document_groups",
            ["group_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    with op.batch_alter_table("api_keys") as batch_op:
        batch_op.drop_constraint("fk_api_keys_group_id_document_groups", type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_api_keys_group_id"))
        batch_op.drop_column("group_id")
