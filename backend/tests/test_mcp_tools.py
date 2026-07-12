import asyncio

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, VectorStoreProvider
from app.core.database import get_engine, get_session_maker
from app.main import create_app
from app.mcp.auth import ApiKeyTokenVerifier, McpAccessContext
from app.mcp.server import create_mcp_http_app, create_mcp_server
from app.mcp.tools import (
    McpAuthenticationError,
    list_document_groups_tool,
    search_documents_tool,
)
from app.models import Base
from app.schemas.auth import UserCreate
from app.schemas.documents import DocumentCreate
from app.services.api_keys import create_api_key
from app.services.auth import create_user
from app.services.documents import create_document_group, ingest_text_document
from app.services.vector_store.factory import get_vector_store


def test_mcp_tools_authenticate_api_key_and_scope_results(tmp_path) -> None:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'app.db'}",
        vector_store_provider=VectorStoreProvider.sqlite,
        sqlite_vector_database_url=f"sqlite:///{tmp_path / 'vectors.db'}",
        embedding_dimension=64,
        chunk_size=120,
        chunk_overlap=20,
    )
    Base.metadata.create_all(bind=get_engine(settings.resolved_database_url))
    session_maker = get_session_maker(settings.resolved_database_url)
    vector_store = get_vector_store(settings)

    with session_maker() as session:
        user = create_user(
            session,
            UserCreate(email="mcp@example.com", password="strong-password"),
        )
        group = create_document_group(session, name="MCP docs", owner_id=user.id)
        other_group = create_document_group(session, name="Other docs", owner_id=user.id)
        api_key, raw_api_key = create_api_key(
            session,
            user_id=user.id,
            group_id=group.id,
            name="MCP",
        )
        ingest_text_document(
            session,
            vector_store=vector_store,
            settings=settings,
            group_id=group.id,
            owner_id=user.id,
            payload=DocumentCreate(
                title="MCP note",
                text="MCP clients can search document groups with scoped API keys.",
            ),
        )
        ingest_text_document(
            session,
            vector_store=vector_store,
            settings=settings,
            group_id=other_group.id,
            owner_id=user.id,
            payload=DocumentCreate(
                title="Other note",
                text="Unrelated tenant content must not be returned by scoped keys.",
            ),
        )
        access_token = asyncio.run(ApiKeyTokenVerifier(settings).verify_token(raw_api_key))
        invalid_token = asyncio.run(ApiKeyTokenVerifier(settings).verify_token("invalid"))
        assert access_token is not None
        assert access_token.client_id == api_key.id
        assert access_token.claims is not None
        assert access_token.claims["group_id"] == group.id
        assert invalid_token is None

        access = McpAccessContext(api_key_id=api_key.id, user_id=user.id, group_id=group.id)

        groups = list_document_groups_tool(session=session, access=access)
        search = search_documents_tool(
            session=session,
            settings=settings,
            vector_store=vector_store,
            access=access,
            query="scoped mcp search",
        )

        with pytest.raises(McpAuthenticationError):
            list_document_groups_tool(
                session=session,
                access=McpAccessContext(
                    api_key_id="invalid",
                    user_id=user.id,
                    group_id="missing",
                ),
            )

    assert groups[0]["id"] == group.id
    assert len(groups) == 1
    assert search["results"]
    assert search["group_id"] == group.id
    assert search["results"][0]["document_id"]


def test_mcp_http_requires_bearer_auth_and_hides_api_key_schema(tmp_path) -> None:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'app.db'}",
        mcp_issuer_url="http://127.0.0.1:8000",
        mcp_resource_server_url="http://127.0.0.1:8000/mcp",
    )
    Base.metadata.create_all(bind=get_engine(settings.resolved_database_url))
    session_maker = get_session_maker(settings.resolved_database_url)

    with session_maker() as session:
        user = create_user(
            session,
            UserCreate(email="schema@example.com", password="strong-password"),
        )
        group = create_document_group(session, name="Schema docs", owner_id=user.id)
        _, raw_api_key = create_api_key(
            session,
            user_id=user.id,
            group_id=group.id,
            name="MCP",
        )

    server = create_mcp_server(settings)
    for tool in server._tool_manager._tools.values():
        assert "api_key" not in tool.parameters.get("properties", {})

    initialize_request = {
        "jsonrpc": "2.0",
        "id": "init",
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "pytest", "version": "0.1"},
        },
    }
    base_headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }

    with TestClient(
        create_mcp_http_app(settings),
        base_url="http://127.0.0.1:8000",
    ) as client:
        unauthenticated = client.post("/", headers=base_headers, json=initialize_request)
        authenticated = client.post(
            "/",
            headers={**base_headers, "Authorization": f"Bearer {raw_api_key}"},
            json=initialize_request,
        )

    assert unauthenticated.status_code == 401
    assert authenticated.status_code == 200


def test_mounted_mcp_app_uses_parent_lifespan_session_manager(tmp_path) -> None:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'app.db'}",
        mcp_issuer_url="https://home-8000.prasadsawant.site",
        mcp_resource_server_url="https://home-8000.prasadsawant.site/mcp",
        mcp_allowed_hosts=(
            "127.0.0.1:8000,localhost:8000,home-8000.prasadsawant.site"
        ),
    )
    Base.metadata.create_all(bind=get_engine(settings.resolved_database_url))
    session_maker = get_session_maker(settings.resolved_database_url)

    with session_maker() as session:
        user = create_user(
            session,
            UserCreate(email="mounted@example.com", password="strong-password"),
        )
        group = create_document_group(session, name="Mounted docs", owner_id=user.id)
        _, raw_api_key = create_api_key(
            session,
            user_id=user.id,
            group_id=group.id,
            name="Mounted MCP",
        )

    initialize_request = {
        "jsonrpc": "2.0",
        "id": "init",
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "pytest", "version": "0.1"},
        },
    }
    headers = {
        "Accept": "application/json, text/event-stream",
        "Authorization": f"Bearer {raw_api_key}",
        "Content-Type": "application/json",
    }

    with TestClient(
        create_app(settings),
        base_url="https://home-8000.prasadsawant.site",
    ) as client:
        response = client.post("/mcp/", headers=headers, json=initialize_request)

    assert response.status_code == 200
