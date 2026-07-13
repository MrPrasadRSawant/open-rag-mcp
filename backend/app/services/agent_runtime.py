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

CITATION_INSTRUCTIONS = """When search_knowledge returns results, cite every factual claim
that depends on those results using the result's citation label, for example [1] or [2].
Place citations immediately after the supported sentence. Use only citation labels returned by
the tool. Never invent a citation. If no result supports a claim, clearly say so."""
NO_CITATION_INSTRUCTIONS = """Do not include citation labels, source numbers, or a sources
section in the answer. Use retrieved information normally without exposing retrieval metadata."""


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
        citations_enabled=profile.citations_enabled,
    )
    return Agent(
        id=profile.id,
        name=profile.name,
        model=Gemini(id=config.chat_model, api_key=provider_api_key),
        instructions=(
            [profile.instructions, CITATION_INSTRUCTIONS]
            if profile.citations_enabled
            else [profile.instructions, NO_CITATION_INSTRUCTIONS]
        ),
        tools=[search_tool],
        db=get_agent_db(settings) if profile.history_enabled else None,
        add_history_to_context=profile.history_enabled,
        num_history_runs=profile.num_history_runs,
        markdown=True,
        metadata={"citations_enabled": profile.citations_enabled},
        telemetry=False,
    )


async def stream_agent_response(
    agent: Agent,
    *,
    message: str,
    session_id: str,
    user_id: str,
) -> AsyncIterator[str]:
    citations_enabled = bool(
        (getattr(agent, "metadata", None) or {}).get("citations_enabled", True)
    )
    yield _sse(
        "citation_config",
        {"event": "citation_config", "enabled": citations_enabled},
    )
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
            citations = (
                _citations_from_tool_event(payload)
                if citations_enabled
                else []
            )
            if citations:
                yield _sse("citations", {"event": "citations", "citations": citations})
            yield _sse(str(payload.get("event", "message")), payload)
    except Exception as exc:
        yield _sse("error", {"event": "error", "message": str(exc)})


def is_origin_allowed(profile: AgentProfile, origin: str | None) -> bool:
    if not origin:
        return False
    normalized = origin.rstrip("/")
    return "*" in profile.allowed_origins or normalized in profile.allowed_origins


def _build_group_search_tool(
    *, settings: Settings, owner_id: str, group_id: str, citations_enabled: bool
):
    citation_counter = 0

    def search_knowledge(query: str, limit: int = 5) -> str:
        """Search the agent's private document group for relevant information."""
        nonlocal citation_counter
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
        records = []
        for result in results:
            citation_counter += 1
            record = {
                    "text": result.text,
                    "title": result.metadata.get("title"),
                    "source_name": result.metadata.get("source_name"),
                    "document_id": result.document_id,
                    "chunk_id": result.chunk_id,
                    "score": result.score,
                }
            if citations_enabled:
                record["citation"] = f"[{citation_counter}]"
            records.append(record)
        return json.dumps(records)

    return search_knowledge


def get_agent_db(settings: Settings):
    kwargs: dict[str, Any] = {
        "db_url": settings.resolved_database_url,
        "session_table": "agent_history",
    }
    if settings.resolved_database_url.startswith("postgresql"):
        return PostgresDb(**kwargs)
    return SqliteDb(**kwargs)


def _sse(event: str, payload: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, default=str)}\n\n"


def _citations_from_tool_event(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if payload.get("event") != "ToolCallCompleted":
        return []
    tool = payload.get("tool") or {}
    if tool.get("tool_name") != "search_knowledge":
        return []
    result = tool.get("result")
    try:
        records = json.loads(result) if isinstance(result, str) else result
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(records, list):
        return []
    return [
        {
            "number": index,
            "label": record.get("citation", f"[{index}]"),
            "document_id": record.get("document_id"),
            "chunk_id": record.get("chunk_id"),
            "title": record.get("title") or record.get("source_name") or "Document",
            "excerpt": str(record.get("text", ""))[:360],
            "score": record.get("score"),
        }
        for index, record in enumerate(records, start=1)
        if isinstance(record, dict) and record.get("document_id")
    ]
