import secrets

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AgentProfile, LlmProviderConfig
from app.schemas.agents import AgentCreate, AgentUpdate
from app.services.documents import get_document_group


def create_agent(session: Session, *, user_id: str, payload: AgentCreate) -> AgentProfile:
    if get_document_group(session, group_id=payload.group_id, owner_id=user_id) is None:
        raise ValueError("Document group not found")
    config = session.scalar(
        select(LlmProviderConfig).where(
            LlmProviderConfig.id == payload.llm_config_id,
            LlmProviderConfig.user_id == user_id,
            LlmProviderConfig.purpose == "chat_llm",
            LlmProviderConfig.is_active.is_(True),
        )
    )
    if config is None:
        raise ValueError("Select a valid Chat LLM config")
    duplicate = session.scalar(
        select(AgentProfile.id).where(
            AgentProfile.user_id == user_id,
            func.lower(AgentProfile.name) == payload.name.strip().lower(),
        )
    )
    if duplicate:
        raise ValueError("An agent with this name already exists")
    agent = AgentProfile(
        user_id=user_id,
        group_id=payload.group_id,
        llm_config_id=payload.llm_config_id,
        name=payload.name.strip(),
        instructions=payload.instructions.strip(),
        public_key=f"pk_agent_{secrets.token_urlsafe(24)}",
        allowed_origins=payload.allowed_origins,
        history_enabled=payload.history_enabled,
        num_history_runs=payload.num_history_runs,
    )
    session.add(agent)
    session.commit()
    session.refresh(agent)
    return agent


def list_agents(
    session: Session, *, user_id: str, group_id: str | None = None
) -> list[AgentProfile]:
    query = select(AgentProfile).where(AgentProfile.user_id == user_id)
    if group_id:
        query = query.where(AgentProfile.group_id == group_id)
    return list(session.scalars(query.order_by(AgentProfile.created_at.desc())))


def get_agent(session: Session, *, user_id: str, agent_id: str) -> AgentProfile | None:
    return session.scalar(
        select(AgentProfile).where(
            AgentProfile.id == agent_id, AgentProfile.user_id == user_id
        )
    )


def get_agent_by_public_key(session: Session, public_key: str) -> AgentProfile | None:
    return session.scalar(
        select(AgentProfile).where(
            AgentProfile.public_key == public_key, AgentProfile.is_active.is_(True)
        )
    )


def update_agent(
    session: Session, *, user_id: str, agent_id: str, payload: AgentUpdate
) -> AgentProfile | None:
    agent = get_agent(session, user_id=user_id, agent_id=agent_id)
    if agent is None:
        return None
    changes = payload.model_dump(exclude_unset=True)
    if "name" in changes:
        changes["name"] = changes["name"].strip()
        duplicate = session.scalar(
            select(AgentProfile.id).where(
                AgentProfile.user_id == user_id,
                AgentProfile.id != agent_id,
                func.lower(AgentProfile.name) == changes["name"].lower(),
            )
        )
        if duplicate:
            raise ValueError("An agent with this name already exists")
    if "instructions" in changes:
        changes["instructions"] = changes["instructions"].strip()
    for field, value in changes.items():
        setattr(agent, field, value)
    session.commit()
    session.refresh(agent)
    return agent


def delete_agent(session: Session, *, user_id: str, agent_id: str) -> AgentProfile | None:
    agent = get_agent(session, user_id=user_id, agent_id=agent_id)
    if agent is None:
        return None
    session.delete(agent)
    session.commit()
    return agent


def count_config_agents(session: Session, *, config_id: str, user_id: str) -> int:
    return int(
        session.scalar(
            select(func.count()).select_from(AgentProfile).where(
                AgentProfile.llm_config_id == config_id, AgentProfile.user_id == user_id
            )
        )
        or 0
    )
