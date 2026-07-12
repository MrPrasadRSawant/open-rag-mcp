"""Map document groups to immutable typed LLM configs.

Revision ID: 0004_group_embedding_configs
Revises: 0003_llm_provider_configs
Create Date: 2026-07-12
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa

from alembic import op

revision: str = "0004_group_embedding_configs"
down_revision: str | None = "0003_llm_provider_configs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("llm_provider_configs") as batch_op:
        batch_op.alter_column("encrypted_api_key", existing_type=sa.Text(), nullable=True)
        batch_op.alter_column(
            "api_key_hint", existing_type=sa.String(length=32), nullable=True
        )
        batch_op.add_column(sa.Column("chat_model", sa.String(length=200), nullable=True))
        batch_op.create_unique_constraint("uq_llm_config_user_name", ["user_id", "name"])

    with op.batch_alter_table("document_groups") as batch_op:
        batch_op.add_column(sa.Column("llm_config_id", sa.String(length=36), nullable=True))
        batch_op.create_index("ix_document_groups_llm_config_id", ["llm_config_id"])
        batch_op.create_foreign_key(
            "fk_document_groups_llm_config_id",
            "llm_provider_configs",
            ["llm_config_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    connection = op.get_bind()
    now = datetime.now(UTC)
    owners = connection.execute(sa.text("SELECT DISTINCT owner_id FROM document_groups")).fetchall()
    for (owner_id,) in owners:
        config_id = str(uuid4())
        name = "Default"
        duplicate = connection.execute(
            sa.text(
                "SELECT 1 FROM llm_provider_configs "
                "WHERE user_id = :user_id AND lower(name) = 'default'"
            ),
            {"user_id": owner_id},
        ).first()
        if duplicate:
            name = "Default (Internal)"
        connection.execute(
            sa.text(
                "INSERT INTO llm_provider_configs "
                "(id, user_id, name, provider, purpose, encrypted_api_key, api_key_hint, "
                "base_url, embedding_model, chat_model, is_active, created_at, updated_at) "
                "VALUES (:id, :user_id, :name, 'internal', 'embedding', NULL, NULL, NULL, "
                ":model, NULL, 1, :created_at, :updated_at)"
            ),
            {
                "id": config_id,
                "user_id": owner_id,
                "name": name,
                "model": "BAAI/bge-small-en-v1.5",
                "created_at": now,
                "updated_at": now,
            },
        )
        connection.execute(
            sa.text(
                "UPDATE document_groups SET llm_config_id = :config_id "
                "WHERE owner_id = :owner_id AND llm_config_id IS NULL"
            ),
            {"config_id": config_id, "owner_id": owner_id},
        )


def downgrade() -> None:
    with op.batch_alter_table("document_groups") as batch_op:
        batch_op.drop_constraint("fk_document_groups_llm_config_id", type_="foreignkey")
        batch_op.drop_index("ix_document_groups_llm_config_id")
        batch_op.drop_column("llm_config_id")
    with op.batch_alter_table("llm_provider_configs") as batch_op:
        batch_op.drop_constraint("uq_llm_config_user_name", type_="unique")
        batch_op.drop_column("chat_model")
        batch_op.alter_column(
            "api_key_hint", existing_type=sa.String(length=32), nullable=False
        )
        batch_op.alter_column("encrypted_api_key", existing_type=sa.Text(), nullable=False)
