from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_engine, get_session, get_session_maker
from app.main import app
from app.models import Base
from app.services.api_keys import authenticate_api_key


def test_user_can_create_list_and_revoke_api_key(tmp_path) -> None:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'app.db'}",
        secret_key="test-secret",
    )
    Base.metadata.create_all(bind=get_engine(settings.resolved_database_url))
    session_maker = get_session_maker(settings.resolved_database_url)

    def override_settings() -> Settings:
        return settings

    def override_session() -> Generator[Session]:
        with session_maker() as session:
            yield session

    app.dependency_overrides[get_settings] = override_settings
    app.dependency_overrides[get_session] = override_session

    try:
        client = TestClient(app)
        auth_response = client.post(
            "/auth/register",
            json={"email": "keys@example.com", "password": "strong-password"},
        )
        auth_response.raise_for_status()
        headers = {"Authorization": f"Bearer {auth_response.json()['access_token']}"}
        group_response = client.post(
            "/document-groups",
            headers=headers,
            json={"name": "MCP docs"},
        )
        group_response.raise_for_status()
        group_id = group_response.json()["id"]

        create_response = client.post(
            "/api-keys",
            headers=headers,
            json={"name": "MCP client", "group_id": group_id},
        )
        create_response.raise_for_status()
        created_key = create_response.json()

        list_response = client.get("/api-keys", headers=headers)
        list_response.raise_for_status()

        with session_maker() as session:
            authenticated = authenticate_api_key(session, created_key["api_key"])

        revoke_response = client.delete(
            f"/api-keys/{created_key['id']}",
            headers=headers,
        )
        revoke_response.raise_for_status()

        with session_maker() as session:
            revoked_authentication = authenticate_api_key(session, created_key["api_key"])
    finally:
        app.dependency_overrides.clear()

    assert created_key["api_key"].startswith("ormcp_")
    assert created_key["group_id"] == group_id
    assert created_key["key_prefix"] in created_key["api_key"]
    assert "api_key" not in list_response.json()[0]
    assert authenticated is not None
    assert revoke_response.json()["revoked_at"] is not None
    assert revoked_authentication is None
