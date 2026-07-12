import json
from collections.abc import AsyncIterator
from typing import Any

from agno.agent import Agent
from agno.db.postgres import PostgresDb
from agno.db.sqlite import SqliteDb
from agno.models.google import Gemini
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.database import get_session_maker
from app.core.security import decrypt_secret
from app.models import AgentProfile, LlmProviderConfig
from app.services.documents import search_documents
from app.services.vector_store.factory import get_vector_store


def build_agent_runtime(
    session: Session, *, profile: AgentProfile, settings: Settings
) -> Agent:
    config = session.get(LlmProviderConfig, profile.llm_config_id)
    if (
        config is None
        or config.purpose != "chat_llm"
        or config.provider != "google"
        or not config.chat_model
        or not config.encrypted_api_key
        or not config.is_active
    ):
        raise ValueError("Agent Chat LLM configuration is unavailable")

    provider_api_key = decrypt_secret(
        config.encrypted_api_key, secret_key=settings.secret_key
    )
    search_tool = _build_group_search_tool(
        settings=settings,
        owner_id=profile.user_id,
        group_id=profile.group_id,
    )
    return Agent(
        id=profile.id,
        name=profile.name,
        model=Gemini(id=config.chat_model, api_key=provider_api_key),
        instructions=profile.instructions,
        tools=[search_tool],
        db=_get_agent_db(settings) if profile.history_enabled else None,
        add_history_to_context=profile.history_enabled,
        num_history_runs=profile.num_history_runs,
        markdown=True,
        telemetry=False,
    )


async def stream_agent_response(
    agent: Agent,
    *,
    message: str,
    session_id: str,
    user_id: str,
) -> AsyncIterator[str]:
    try:
        events = agent.arun(
            message,
            stream=True,
            stream_events=True,
            session_id=session_id,
            user_id=user_id,
        )
        async for event in events:
            payload = event.to_dict()
            yield _sse(str(payload.get("event", "message")), payload)
    except Exception as exc:
        yield _sse("error", {"event": "error", "message": str(exc)})


def is_origin_allowed(profile: AgentProfile, origin: str | None) -> bool:
    if not origin:
        return False
    normalized = origin.rstrip("/")
    return "*" in profile.allowed_origins or normalized in profile.allowed_origins


def _build_group_search_tool(*, settings: Settings, owner_id: str, group_id: str):
    def search_knowledge(query: str, limit: int = 5) -> str:
        """Search the agent's private document group for relevant information."""
        session_maker = get_session_maker(settings.resolved_database_url)
        with session_maker() as session:
            results = search_documents(
                session=session,
                vector_store=get_vector_store(settings),
                settings=settings,
                query=query,
                group_ids=[group_id],
                limit=max(1, min(limit, 10)),
                owner_id=owner_id,
            )
        return json.dumps(
            [
                {
                    "text": result.text,
                    "title": result.metadata.get("title"),
                    "document_id": result.document_id,
                    "score": result.score,
                }
                for result in results
            ]
        )

    return search_knowledge


def _get_agent_db(settings: Settings):
    kwargs: dict[str, Any] = {
        "db_url": settings.resolved_database_url,
        "session_table": "agent_history",
    }
    if settings.resolved_database_url.startswith("postgresql"):
        return PostgresDb(**kwargs)
    return SqliteDb(**kwargs)


def _sse(event: str, payload: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, default=str)}\n\n"
