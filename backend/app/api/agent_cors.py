from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import Settings
from app.core.database import get_session_maker
from app.services.agent_runtime import is_origin_allowed
from app.services.agents import get_agent_by_public_key


class PublicAgentCorsMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, settings: Settings) -> None:
        super().__init__(app)
        self.settings = settings

    async def dispatch(self, request: Request, call_next):
        public_key = _public_key_from_path(request.url.path)
        origin = request.headers.get("origin")
        if public_key is None or origin is None:
            return await call_next(request)

        session_maker = get_session_maker(self.settings.resolved_database_url)
        with session_maker() as session:
            profile = get_agent_by_public_key(session, public_key)
            allowed = profile is not None and is_origin_allowed(profile, origin)
        if not allowed:
            return JSONResponse(
                {"detail": f"Origin not allowed: {origin}"},
                status_code=403,
                headers=_cors_headers(origin),
            )

        headers = _cors_headers(origin)
        if request.method == "OPTIONS":
            return Response(status_code=204, headers=headers)
        response = await call_next(request)
        response.headers.update(headers)
        return response


def _public_key_from_path(path: str) -> str | None:
    prefix = "/agent-runtime/public/"
    suffix = "/runs"
    if not path.startswith(prefix) or not path.endswith(suffix):
        return None
    value = path.removeprefix(prefix).removesuffix(suffix).strip("/")
    return value or None


def _cors_headers(origin: str) -> dict[str, str]:
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Methods": "POST,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Max-Age": "600",
        "Vary": "Origin",
    }
