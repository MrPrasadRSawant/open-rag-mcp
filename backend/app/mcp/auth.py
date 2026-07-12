from dataclasses import dataclass

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken

from app.core.config import Settings
from app.core.database import get_session_maker
from app.models import ApiKey
from app.services.api_keys import authenticate_api_key

MCP_REQUIRED_SCOPES = ["documents:read"]


class McpAuthenticationError(ValueError):
    pass


@dataclass(frozen=True)
class McpAccessContext:
    api_key_id: str
    user_id: str
    group_id: str


class ApiKeyTokenVerifier:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def verify_token(self, token: str) -> AccessToken | None:
        session_maker = get_session_maker(self.settings.resolved_database_url)
        with session_maker() as session:
            api_key = authenticate_api_key(session, token)
            if api_key is None or api_key.group_id is None:
                return None

            return _access_token_from_api_key(api_key)


def get_authenticated_mcp_context() -> McpAccessContext:
    access_token = get_access_token()
    if access_token is None or access_token.claims is None:
        raise McpAuthenticationError("MCP request is not authenticated")

    api_key_id = access_token.claims.get("api_key_id")
    user_id = access_token.claims.get("user_id")
    group_id = access_token.claims.get("group_id")
    if not all(isinstance(value, str) and value for value in (api_key_id, user_id, group_id)):
        raise McpAuthenticationError("MCP token is missing document group scope")

    return McpAccessContext(
        api_key_id=api_key_id,
        user_id=user_id,
        group_id=group_id,
    )


def _access_token_from_api_key(api_key: ApiKey) -> AccessToken:
    return AccessToken(
        token=api_key.key_prefix,
        client_id=api_key.id,
        scopes=MCP_REQUIRED_SCOPES,
        subject=api_key.user_id,
        claims={
            "api_key_id": api_key.id,
            "user_id": api_key.user_id,
            "group_id": api_key.group_id,
        },
    )
