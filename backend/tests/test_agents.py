import asyncio
from collections.abc import AsyncIterator, Generator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api import dependencies
from app.api.routes import agent_runtime
from app.core.config import Settings, get_settings
from app.core.database import get_engine, get_session, get_session_maker
from app.main import create_app
from app.models import Base
from app.services.agent_runtime import stream_agent_response as stream_runtime_response


class FakeAgent:
    pass


class FakeStreamingAgent:
    def arun(self, *args, **kwargs):
        async def events():
            class Event:
                def to_dict(self):
                    return {"event": "RunContent", "content": "streamed"}

            yield Event()

        return events()


async def fake_stream(*args, **kwargs) -> AsyncIterator[str]:
    yield 'event: RunContent\ndata: {"content":"answer"}\n\n'


def test_agno_async_stream_is_iterated_without_awaiting_generator() -> None:
    async def collect() -> list[str]:
        return [
            chunk
            async for chunk in stream_runtime_response(
                FakeStreamingAgent(),
                message="Question",
                session_id="session",
                user_id="user",
            )
        ]

    chunks = asyncio.run(collect())

    assert "streamed" in chunks[0]


def test_agent_crud_public_origin_and_private_group_auth(tmp_path, monkeypatch) -> None:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'app.db'}",
        secret_key="agent-test-secret",
    )
    Base.metadata.create_all(bind=get_engine(settings.resolved_database_url))
    session_maker = get_session_maker(settings.resolved_database_url)

    def override_settings() -> Settings:
        return settings

    def override_session() -> Generator[Session]:
        with session_maker() as session:
            yield session

    app = create_app(settings)
    app.dependency_overrides[get_settings] = override_settings
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[dependencies.get_session] = override_session
    monkeypatch.setattr(agent_runtime, "build_agent_runtime", lambda *args, **kwargs: FakeAgent())
    monkeypatch.setattr(agent_runtime, "stream_agent_response", fake_stream)

    with TestClient(app) as client:
        auth = client.post(
            "/auth/register",
            json={"email": "agent@example.com", "password": "strong-password"},
        )
        auth.raise_for_status()
        headers = {"Authorization": f"Bearer {auth.json()['access_token']}"}
        embedding = client.get("/llm-configs", headers=headers).json()[0]
        group = client.post(
            "/document-groups",
            headers=headers,
            json={"name": "Agent docs", "llm_config_id": embedding["id"]},
        )
        group.raise_for_status()
        chat = client.post(
            "/llm-configs",
            headers=headers,
            json={
                "name": "Gemini chat",
                "provider": "google",
                "config_type": "chat_llm",
                "api_key": "gemini-secret-key",
                "chat_model": "gemini-2.5-flash",
            },
        )
        chat.raise_for_status()
        created = client.post(
            "/agents",
            headers=headers,
            json={
                "name": "Support agent",
                "group_id": group.json()["id"],
                "llm_config_id": chat.json()["id"],
                "allowed_origins": ["https://client.example.com"],
            },
        )
        created.raise_for_status()
        agent = created.json()
        api_key = client.post(
            "/api-keys",
            headers=headers,
            json={"name": "Agent API", "group_id": group.json()["id"]},
        )
        api_key.raise_for_status()

        blocked_origin = client.post(
            f"/agent-runtime/public/{agent['public_key']}/runs",
            headers={"Origin": "https://blocked.example.com"},
            json={"message": "Question", "session_id": "thread-1"},
        )
        sdk = client.get("/agent-runtime/sdk.js")
        test_page = client.get("/test-web")
        public_run = client.post(
            f"/agent-runtime/public/{agent['public_key']}/runs",
            headers={"Origin": "https://client.example.com"},
            json={"message": "Question", "session_id": "thread-1"},
        )
        private_run = client.post(
            f"/agent-runtime/{agent['id']}/runs",
            headers={"Authorization": f"Bearer {api_key.json()['api_key']}"},
            json={"message": "Question", "session_id": "thread-2"},
        )
        blocked_delete = client.delete(f"/llm-configs/{chat.json()['id']}", headers=headers)
        deleted = client.delete(f"/agents/{agent['id']}", headers=headers)

    assert agent["public_key"].startswith("pk_agent_")
    assert blocked_origin.status_code == 403
    assert sdk.status_code == 200
    assert sdk.headers["access-control-allow-origin"] == "*"
    assert "OpenRagAgent" in sdk.text
    assert test_page.status_code == 200
    assert "pk_agent_SiH_CEFL8mv9hQnddXbe_toNf4EGBhd9" in test_page.text
    assert public_run.status_code == 200
    assert public_run.headers["access-control-allow-origin"] == "https://client.example.com"
    assert "answer" in public_run.text
    assert private_run.status_code == 200
    assert blocked_delete.status_code == 409
    assert deleted.status_code == 200
