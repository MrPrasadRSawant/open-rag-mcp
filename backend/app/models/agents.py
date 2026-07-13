from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def new_id() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(UTC)


class AgentProfile(Base):
    __tablename__ = "agent_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_agent_profile_user_name"),
        UniqueConstraint("public_key", name="uq_agent_profile_public_key"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    group_id: Mapped[str] = mapped_column(
        ForeignKey("document_groups.id", ondelete="CASCADE"), index=True
    )
    llm_config_id: Mapped[str] = mapped_column(
        ForeignKey("llm_provider_configs.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    public_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    allowed_origins: Mapped[list[str]] = mapped_column(JSON, default=list)
    history_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    citations_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    num_history_runs: Mapped[int] = mapped_column(Integer, default=5)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
