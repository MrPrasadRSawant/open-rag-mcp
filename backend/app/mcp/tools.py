from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.mcp.auth import McpAccessContext, McpAuthenticationError
from app.services.documents import (
    document_with_chunk_count,
    get_document_group,
    list_document_groups,
    list_documents,
    search_documents,
)
from app.services.vector_store.base import VectorStore


def list_document_groups_tool(
    *,
    session: Session,
    access: McpAccessContext,
) -> list[dict[str, Any]]:
    group_id = _scoped_group_id(session, access)
    groups = [
        group
        for group in list_document_groups(session, owner_id=access.user_id)
        if group.id == group_id
    ]
    return [
        {
            "id": group.id,
            "name": group.name,
            "description": group.description,
            "created_at": group.created_at.isoformat(),
            "updated_at": group.updated_at.isoformat(),
        }
        for group in groups
    ]


def list_documents_tool(
    *,
    session: Session,
    access: McpAccessContext,
) -> list[dict[str, Any]]:
    group_id = _scoped_group_id(session, access)
    documents = list_documents(session, group_id=group_id, owner_id=access.user_id)
    return [
        _serialize_value(document_with_chunk_count(document))
        for document in documents
    ]


def search_documents_tool(
    *,
    session: Session,
    settings: Settings,
    vector_store: VectorStore,
    access: McpAccessContext,
    query: str,
    limit: int = 5,
    candidate_limit: int | None = None,
    rerank: bool | None = None,
    lexical_weight: float | None = None,
    diversity: bool | None = None,
    diversity_lambda: float | None = None,
    min_score: float | None = None,
) -> dict[str, Any]:
    group_id = _scoped_group_id(session, access)
    results = search_documents(
        session=session,
        vector_store=vector_store,
        settings=settings,
        query=query,
        group_ids=[group_id],
        limit=limit,
        owner_id=access.user_id,
        candidate_limit=candidate_limit,
        rerank=rerank,
        lexical_weight=lexical_weight,
        diversity=diversity,
        diversity_lambda=diversity_lambda,
        min_score=min_score,
    )
    return {
        "query": query,
        "group_id": group_id,
        "results": [result.model_dump() for result in results],
    }


def _scoped_group_id(session: Session, access: McpAccessContext) -> str:
    group = get_document_group(session, group_id=access.group_id, owner_id=access.user_id)
    if group is None:
        raise McpAuthenticationError("API key document group is no longer available")
    return group.id


def _serialize_value(value: dict[str, Any]) -> dict[str, Any]:
    return {
        key: item.isoformat() if hasattr(item, "isoformat") else item
        for key, item in value.items()
    }
