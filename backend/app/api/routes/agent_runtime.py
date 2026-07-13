from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Request, Response, status
from fastapi.responses import FileResponse, StreamingResponse

from app.api.dependencies import SessionDependency, SettingsDependency
from app.models import AgentProfile
from app.schemas.agents import AgentRunRequest
from app.services.agent_runtime import (
    build_agent_runtime,
    is_origin_allowed,
    stream_agent_response,
)
from app.services.agents import get_agent, get_agent_by_public_key
from app.services.api_keys import authenticate_api_key

router = APIRouter(prefix="/agent-runtime", tags=["agent-runtime"])


@router.get("/sdk.js", include_in_schema=False)
def agent_browser_sdk() -> FileResponse:
    return FileResponse(
        Path(__file__).resolve().parents[2] / "static" / "open-rag-agent.js",
        media_type="text/javascript",
        headers={"Access-Control-Allow-Origin": "*", "Cache-Control": "no-store"},
    )


@router.get("/test-web", include_in_schema=False)
def agent_test_page() -> FileResponse:
    return FileResponse(
        Path(__file__).resolve().parents[4] / "test_web.html",
        media_type="text/html",
        headers={"Cache-Control": "no-store"},
    )


@router.options("/public/{public_key}/runs")
def public_agent_preflight(
    public_key: str,
    request: Request,
    session: SessionDependency,
) -> Response:
    profile = get_agent_by_public_key(session, public_key)
    origin = request.headers.get("origin")
    if profile is None or not is_origin_allowed(profile, origin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Origin not allowed")
    return Response(status_code=status.HTTP_204_NO_CONTENT, headers=_cors_headers(origin))


@router.post("/public/{public_key}/runs")
def run_public_agent(
    public_key: str,
    payload: AgentRunRequest,
    request: Request,
    session: SessionDependency,
    settings: SettingsDependency,
) -> StreamingResponse:
    profile = get_agent_by_public_key(session, public_key)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    origin = request.headers.get("origin")
    if not is_origin_allowed(profile, origin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Origin not allowed")
    runtime = _runtime_or_http_error(session, profile, settings)
    end_user_id = payload.user_id or f"public:{public_key[-12:]}"
    return StreamingResponse(
        stream_agent_response(
            runtime,
            message=payload.message,
            session_id=f"{profile.id}:{payload.session_id}",
            user_id=f"{profile.id}:{end_user_id}",
        ),
        media_type="text/event-stream",
        headers={**_stream_headers(), **_cors_headers(origin)},
    )


@router.post("/{agent_id}/runs")
def run_private_agent(
    agent_id: str,
    payload: AgentRunRequest,
    session: SessionDependency,
    settings: SettingsDependency,
    authorization: Annotated[str | None, Header()] = None,
) -> StreamingResponse:
    raw_key = _bearer_token(authorization)
    api_key = authenticate_api_key(session, raw_key)
    if api_key is None or api_key.group_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    profile = get_agent(session, user_id=api_key.user_id, agent_id=agent_id)
    if profile is None or profile.group_id != api_key.group_id or not profile.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Agent access denied")
    runtime = _runtime_or_http_error(session, profile, settings)
    return StreamingResponse(
        stream_agent_response(
            runtime,
            message=payload.message,
            session_id=f"{profile.id}:{payload.session_id}",
            user_id=f"{profile.id}:{payload.user_id or api_key.user_id}",
        ),
        media_type="text/event-stream",
        headers=_stream_headers(),
    )


def _runtime_or_http_error(session, profile: AgentProfile, settings):
    try:
        return build_agent_runtime(session, profile=profile, settings=settings)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


def _bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer API key required"
        )
    return authorization.split(" ", 1)[1].strip()


def _stream_headers() -> dict[str, str]:
    return {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


def _cors_headers(origin: str | None) -> dict[str, str]:
    if not origin:
        return {}
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Methods": "POST,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
        "Vary": "Origin",
    }
