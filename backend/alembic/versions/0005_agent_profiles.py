"""Add group-scoped AI agent profiles.

Revision ID: 0005_agent_profiles
Revises: 0004_group_embedding_configs
Create Date: 2026-07-12
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_agent_profiles"
down_revision: str | None = "0004_group_embedding_configs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("group_id", sa.String(length=36), nullable=False),
        sa.Column("llm_config_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column("public_key", sa.String(length=80), nullable=False),
        sa.Column("allowed_origins", sa.JSON(), nullable=False),
        sa.Column("history_enabled", sa.Boolean(), nullable=False),
        sa.Column("num_history_runs", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["document_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["llm_config_id"], ["llm_provider_configs.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_key", name="uq_agent_profile_public_key"),
        sa.UniqueConstraint("user_id", "name", name="uq_agent_profile_user_name"),
    )
    op.create_index("ix_agent_profiles_group_id", "agent_profiles", ["group_id"])
    op.create_index("ix_agent_profiles_is_active", "agent_profiles", ["is_active"])
    op.create_index("ix_agent_profiles_llm_config_id", "agent_profiles", ["llm_config_id"])
    op.create_index("ix_agent_profiles_public_key", "agent_profiles", ["public_key"])
    op.create_index("ix_agent_profiles_user_id", "agent_profiles", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_profiles_user_id", table_name="agent_profiles")
    op.drop_index("ix_agent_profiles_public_key", table_name="agent_profiles")
    op.drop_index("ix_agent_profiles_llm_config_id", table_name="agent_profiles")
    op.drop_index("ix_agent_profiles_is_active", table_name="agent_profiles")
    op.drop_index("ix_agent_profiles_group_id", table_name="agent_profiles")
    op.drop_table("agent_profiles")
