from fastapi import APIRouter, HTTPException, Response, status
from fastapi.responses import StreamingResponse

from app.api.dependencies import CurrentUserDependency, SessionDependency, SettingsDependency
from app.schemas.agents import (
    AgentRunRequest,
    AgentSessionDetail,
    AgentSessionRename,
    AgentSessionSummary,
)
from app.services.agent_runtime import build_agent_runtime, stream_agent_response
from app.services.agent_sessions import (
    delete_agent_session,
    get_agent_session,
    internal_session_id,
    list_agent_sessions,
    playground_user_id,
    rename_agent_session,
)
from app.services.agents import get_agent

router = APIRouter(prefix="/agent-playground", tags=["agent-playground"])


@router.post("/agents/{agent_id}/runs")
def run_agent_in_playground(
    agent_id: str,
    payload: AgentRunRequest,
    session: SessionDependency,
    settings: SettingsDependency,
    current_user: CurrentUserDependency,
) -> StreamingResponse:
    profile = _owned_agent(session, user_id=current_user.id, agent_id=agent_id)
    if not profile.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Agent is inactive")
    try:
        runtime = build_agent_runtime(session, profile=profile, settings=settings)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return StreamingResponse(
        stream_agent_response(
            runtime,
            message=payload.message,
            session_id=internal_session_id(profile, payload.session_id),
            user_id=playground_user_id(profile),
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/agents/{agent_id}/sessions", response_model=list[AgentSessionSummary])
def list_sessions(
    agent_id: str,
    session: SessionDependency,
    settings: SettingsDependency,
    current_user: CurrentUserDependency,
) -> list[AgentSessionSummary]:
    profile = _owned_agent(session, user_id=current_user.id, agent_id=agent_id)
    return list_agent_sessions(session, profile=profile, settings=settings)


@router.get("/agents/{agent_id}/sessions/{session_id}", response_model=AgentSessionDetail)
def get_session_history(
    agent_id: str,
    session_id: str,
    session: SessionDependency,
    settings: SettingsDependency,
    current_user: CurrentUserDependency,
) -> AgentSessionDetail:
    profile = _owned_agent(session, user_id=current_user.id, agent_id=agent_id)
    detail = get_agent_session(
        session, profile=profile, settings=settings, session_id=session_id
    )
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return detail


@router.patch(
    "/agents/{agent_id}/sessions/{session_id}", response_model=AgentSessionSummary
)
def rename_session(
    agent_id: str,
    session_id: str,
    payload: AgentSessionRename,
    session: SessionDependency,
    settings: SettingsDependency,
    current_user: CurrentUserDependency,
) -> AgentSessionSummary:
    profile = _owned_agent(session, user_id=current_user.id, agent_id=agent_id)
    renamed = rename_agent_session(
        profile=profile, settings=settings, session_id=session_id, name=payload.name
    )
    if renamed is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return renamed


@router.delete("/agents/{agent_id}/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session_history(
    agent_id: str,
    session_id: str,
    session: SessionDependency,
    settings: SettingsDependency,
    current_user: CurrentUserDependency,
) -> Response:
    profile = _owned_agent(session, user_id=current_user.id, agent_id=agent_id)
    if not delete_agent_session(profile=profile, settings=settings, session_id=session_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _owned_agent(session, *, user_id: str, agent_id: str):
    profile = get_agent(session, user_id=user_id, agent_id=agent_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return profile
