from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_engine, get_session, get_session_maker
from app.main import app
from app.models import Base


def test_user_can_register_login_and_read_profile(tmp_path) -> None:
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
        register_response = client.post(
            "/auth/register",
            json={
                "email": "person@example.com",
                "password": "strong-password",
                "full_name": "Person Example",
            },
        )
        register_response.raise_for_status()

        login_response = client.post(
            "/auth/login",
            json={"email": "person@example.com", "password": "strong-password"},
        )
        login_response.raise_for_status()

        profile_response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {login_response.json()['access_token']}"},
        )
        profile_response.raise_for_status()
    finally:
        app.dependency_overrides.clear()

    assert register_response.json()["user"]["email"] == "person@example.com"
    assert login_response.json()["token_type"] == "bearer"
    assert profile_response.json()["email"] == "person@example.com"
