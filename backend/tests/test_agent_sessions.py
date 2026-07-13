from agno.run.agent import RunInput, RunOutput
from agno.run.base import RunStatus
from agno.session.agent import AgentSession

from app.core.config import Settings
from app.core.database import get_engine, get_session_maker
from app.models import AgentProfile, Base
from app.services.agent_runtime import get_agent_db
from app.services.agent_sessions import (
    delete_agent_session,
    get_agent_session,
    internal_session_id,
    list_agent_sessions,
    playground_user_id,
    rename_agent_session,
)


def test_playground_session_history_lifecycle(tmp_path) -> None:
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'app.db'}")
    Base.metadata.create_all(bind=get_engine(settings.resolved_database_url))
    session_maker = get_session_maker(settings.resolved_database_url)
    profile = AgentProfile(
        id="agent-1",
        user_id="user-1",
        group_id="group-1",
        llm_config_id="config-1",
        name="Test agent",
        instructions="Test",
        public_key="pk_agent_test",
        allowed_origins=[],
        history_enabled=True,
        num_history_runs=5,
    )
    external_session_id = "conversation-1"
    get_agent_db(settings).upsert_session(
        AgentSession(
            session_id=internal_session_id(profile, external_session_id),
            agent_id=profile.id,
            user_id=playground_user_id(profile),
            session_data={"session_name": "First conversation"},
            created_at=1_700_000_000,
            updated_at=1_700_000_001,
            runs=[
                    RunOutput(
                        run_id="run-1",
                        agent_id=profile.id,
                        session_id=internal_session_id(profile, external_session_id),
                        user_id=playground_user_id(profile),
                        input=RunInput(input_content="What is indexed?"),
                        content="The group contains one document.",
                        status=RunStatus.completed,
                )
            ],
        )
    )

    with session_maker() as session:
        summaries = list_agent_sessions(session, profile=profile, settings=settings)
        detail = get_agent_session(
            session,
            profile=profile,
            settings=settings,
            session_id=external_session_id,
        )
        renamed = rename_agent_session(
            profile=profile,
            settings=settings,
            session_id=external_session_id,
            name="Renamed conversation",
        )
        deleted = delete_agent_session(
            profile=profile,
            settings=settings,
            session_id=external_session_id,
        )

    assert summaries[0].id == external_session_id
    assert summaries[0].name == "First conversation"
    assert detail is not None
    assert [(message.role, message.content) for message in detail.messages] == [
        ("user", "What is indexed?"),
        ("assistant", "The group contains one document."),
    ]
    assert renamed is not None
    assert renamed.name == "Renamed conversation"
    assert deleted is True
