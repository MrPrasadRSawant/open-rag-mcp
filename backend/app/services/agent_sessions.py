import json
from typing import Any

from agno.db.base import SessionType
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import AgentProfile
from app.schemas.agents import (
    AgentHistoryMessage,
    AgentSessionDetail,
    AgentSessionSummary,
)
from app.services.agent_runtime import get_agent_db


def playground_user_id(profile: AgentProfile) -> str:
    return f"{profile.id}:playground:{profile.user_id}"


def internal_session_id(profile: AgentProfile, session_id: str) -> str:
    return f"{profile.id}:{session_id}"


def list_agent_sessions(
    session: Session, *, profile: AgentProfile, settings: Settings
) -> list[AgentSessionSummary]:
    if not profile.history_enabled:
        return []
    records = get_agent_db(settings).get_sessions(
        session_type=SessionType.AGENT,
        user_id=playground_user_id(profile),
        component_id=profile.id,
        limit=100,
        sort_by="updated_at",
        sort_order="desc",
    )
    return [_session_summary(record, profile) for record in records]


def get_agent_session(
    session: Session,
    *,
    profile: AgentProfile,
    settings: Settings,
    session_id: str,
) -> AgentSessionDetail | None:
    if not profile.history_enabled:
        return None
    record = get_agent_db(settings).get_session(
        internal_session_id(profile, session_id),
        session_type=SessionType.AGENT,
        user_id=playground_user_id(profile),
    )
    if record is None or record.agent_id != profile.id:
        return None
    summary = _session_summary(record, profile)
    messages: list[AgentHistoryMessage] = []
    for run in record.runs or []:
        input_content = getattr(getattr(run, "input", None), "input_content", None)
        if input_content is not None:
            messages.append(
                AgentHistoryMessage(
                    role="user",
                    content=_content_text(input_content),
                    created_at=getattr(run, "created_at", None),
                )
            )
        content = getattr(run, "content", None)
        if content is not None:
            metrics = getattr(run, "metrics", None)
            messages.append(
                AgentHistoryMessage(
                    role="assistant",
                    content=_content_text(content),
                    created_at=getattr(run, "created_at", None),
                    latency=getattr(metrics, "duration", None),
                    input_tokens=getattr(metrics, "input_tokens", None),
                    output_tokens=getattr(metrics, "output_tokens", None),
                )
            )
    return AgentSessionDetail(**summary.model_dump(), messages=messages)


def rename_agent_session(
    *, profile: AgentProfile, settings: Settings, session_id: str, name: str
) -> AgentSessionSummary | None:
    record = get_agent_db(settings).rename_session(
        internal_session_id(profile, session_id),
        session_type=SessionType.AGENT,
        session_name=name.strip(),
        user_id=playground_user_id(profile),
    )
    if record is None or record.agent_id != profile.id:
        return None
    return _session_summary(record, profile)


def delete_agent_session(
    *, profile: AgentProfile, settings: Settings, session_id: str
) -> bool:
    database = get_agent_db(settings)
    record = database.get_session(
        internal_session_id(profile, session_id),
        session_type=SessionType.AGENT,
        user_id=playground_user_id(profile),
    )
    if record is None or record.agent_id != profile.id:
        return False
    return database.delete_session(record.session_id, user_id=playground_user_id(profile))


def _session_summary(record, profile: AgentProfile) -> AgentSessionSummary:
    external_id = record.session_id.removeprefix(f"{profile.id}:")
    data = record.session_data or {}
    name = data.get("session_name") or data.get("name") or "Conversation"
    message_count = sum(
        int(getattr(getattr(run, "input", None), "input_content", None) is not None)
        + int(getattr(run, "content", None) is not None)
        for run in record.runs or []
    )
    return AgentSessionSummary(
        id=external_id,
        name=str(name),
        created_at=record.created_at,
        updated_at=record.updated_at,
        message_count=message_count,
    )


def _content_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if hasattr(value, "content"):
        return str(value.content)
    try:
        return json.dumps(value, default=str)
    except TypeError:
        return str(value)
