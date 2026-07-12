"""LLM provider configs.

Revision ID: 0003_llm_provider_configs
Revises: 0002_group_scoped_api_keys
Create Date: 2026-07-12
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_llm_provider_configs"
down_revision: str | None = "0002_group_scoped_api_keys"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "llm_provider_configs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("purpose", sa.String(length=40), nullable=False),
        sa.Column("encrypted_api_key", sa.Text(), nullable=False),
        sa.Column("api_key_hint", sa.String(length=32), nullable=False),
        sa.Column("base_url", sa.String(length=500), nullable=True),
        sa.Column("embedding_model", sa.String(length=200), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_llm_provider_configs_is_active"),
        "llm_provider_configs",
        ["is_active"],
        unique=False,
    )
    op.create_index(
        op.f("ix_llm_provider_configs_provider"),
        "llm_provider_configs",
        ["provider"],
        unique=False,
    )
    op.create_index(
        op.f("ix_llm_provider_configs_purpose"),
        "llm_provider_configs",
        ["purpose"],
        unique=False,
    )
    op.create_index(
        op.f("ix_llm_provider_configs_user_id"),
        "llm_provider_configs",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_llm_provider_configs_user_id"), table_name="llm_provider_configs")
    op.drop_index(op.f("ix_llm_provider_configs_purpose"), table_name="llm_provider_configs")
    op.drop_index(op.f("ix_llm_provider_configs_provider"), table_name="llm_provider_configs")
    op.drop_index(op.f("ix_llm_provider_configs_is_active"), table_name="llm_provider_configs")
    op.drop_table("llm_provider_configs")
