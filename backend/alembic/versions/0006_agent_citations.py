"""Add per-agent citation setting.

Revision ID: 0006_agent_citations
Revises: 0005_agent_profiles
Create Date: 2026-07-13
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006_agent_citations"
down_revision: str | None = "0005_agent_profiles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "agent_profiles",
        sa.Column("citations_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("agent_profiles", "citations_enabled")
