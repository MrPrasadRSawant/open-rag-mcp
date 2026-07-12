from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import CurrentUserDependency, SessionDependency
from app.schemas.agents import AgentCreate, AgentRead, AgentUpdate
from app.services.agents import create_agent, delete_agent, list_agents, update_agent

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("", response_model=AgentRead, status_code=status.HTTP_201_CREATED)
def create_agent_profile(
    payload: AgentCreate,
    session: SessionDependency,
    current_user: CurrentUserDependency,
) -> AgentRead:
    try:
        return create_agent(session, user_id=current_user.id, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("", response_model=list[AgentRead])
def list_agent_profiles(
    session: SessionDependency,
    current_user: CurrentUserDependency,
    group_id: str | None = Query(default=None),
) -> list[AgentRead]:
    return list_agents(session, user_id=current_user.id, group_id=group_id)


@router.patch("/{agent_id}", response_model=AgentRead)
def update_agent_profile(
    agent_id: str,
    payload: AgentUpdate,
    session: SessionDependency,
    current_user: CurrentUserDependency,
) -> AgentRead:
    try:
        agent = update_agent(
            session, user_id=current_user.id, agent_id=agent_id, payload=payload
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent


@router.delete("/{agent_id}", response_model=AgentRead)
def delete_agent_profile(
    agent_id: str,
    session: SessionDependency,
    current_user: CurrentUserDependency,
) -> AgentRead:
    agent = delete_agent(session, user_id=current_user.id, agent_id=agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent
