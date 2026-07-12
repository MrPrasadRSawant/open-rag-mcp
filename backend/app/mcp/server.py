try:
    from mcp.server.auth.settings import AuthSettings
    from mcp.server.fastmcp import FastMCP
    from mcp.server.transport_security import TransportSecuritySettings
except ImportError as exc:  # pragma: no cover - exercised only when dependency is missing.
    raise RuntimeError("Install backend dependencies to run the MCP server.") from exc

from app.core.config import Settings, get_settings
from app.core.database import get_session_maker, init_database
from app.mcp.auth import (
    MCP_REQUIRED_SCOPES,
    ApiKeyTokenVerifier,
    get_authenticated_mcp_context,
)
from app.mcp.tools import (
    list_document_groups_tool,
    list_documents_tool,
    search_documents_tool,
)
from app.services.vector_store.factory import get_vector_store

settings = get_settings()
init_database(settings)


def create_mcp_server(runtime_settings: Settings) -> FastMCP:
    server = FastMCP(
        "Open RAG MCP",
        json_response=True,
        streamable_http_path="/",
        token_verifier=ApiKeyTokenVerifier(runtime_settings),
        auth=AuthSettings(
            issuer_url=runtime_settings.mcp_issuer_url,
            resource_server_url=runtime_settings.mcp_resource_server_url,
            required_scopes=MCP_REQUIRED_SCOPES,
        ),
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=(
                runtime_settings.mcp_enable_dns_rebinding_protection
            ),
            allowed_hosts=runtime_settings.allowed_mcp_hosts,
            allowed_origins=runtime_settings.allowed_mcp_origins,
        ),
    )

    @server.tool()
    def list_document_groups() -> list[dict]:
        """Return the single document group allowed by the bearer token."""
        access = get_authenticated_mcp_context()
        session_maker = get_session_maker(runtime_settings.resolved_database_url)
        with session_maker() as session:
            return list_document_groups_tool(session=session, access=access)

    @server.tool()
    def list_documents() -> list[dict]:
        """List documents in the document group assigned to the bearer token."""
        access = get_authenticated_mcp_context()
        session_maker = get_session_maker(runtime_settings.resolved_database_url)
        with session_maker() as session:
            return list_documents_tool(session=session, access=access)

    @server.tool()
    def search_documents(
        query: str,
        limit: int = 5,
        candidate_limit: int | None = None,
        rerank: bool | None = None,
        lexical_weight: float | None = None,
        diversity: bool | None = None,
        diversity_lambda: float | None = None,
        min_score: float | None = None,
    ) -> dict:
        """Search only the document group assigned to the bearer token."""
        access = get_authenticated_mcp_context()
        session_maker = get_session_maker(runtime_settings.resolved_database_url)
        vector_store = get_vector_store(runtime_settings)
        with session_maker() as session:
            return search_documents_tool(
                session=session,
                settings=runtime_settings,
                vector_store=vector_store,
                access=access,
                query=query,
                limit=limit,
                candidate_limit=candidate_limit,
                rerank=rerank,
                lexical_weight=lexical_weight,
                diversity=diversity,
                diversity_lambda=diversity_lambda,
                min_score=min_score,
            )

    return server


def create_mcp_http_app(runtime_settings: Settings):
    return create_mcp_server(runtime_settings).streamable_http_app()


mcp = create_mcp_server(settings)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
