from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_engine, get_session, get_session_maker
from app.main import app
from app.models import Base, LlmProviderConfig
from app.services.llm_configs import read_llm_provider_api_key


def test_user_can_store_list_and_delete_encrypted_llm_config(tmp_path) -> None:
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
            json={"email": "llm@example.com", "password": "strong-password"},
        )
        auth_response.raise_for_status()
        user_id = auth_response.json()["user"]["id"]
        headers = {"Authorization": f"Bearer {auth_response.json()['access_token']}"}

        create_response = client.post(
            "/llm-configs",
            headers=headers,
            json={
                "name": "Gemini embeddings",
                "provider": "google",
                "config_type": "embedding",
                "api_key": "sk-test-secret-key",
                "embedding_model": "gemini-embedding-2",
            },
        )
        create_response.raise_for_status()
        created = create_response.json()

        list_response = client.get("/llm-configs", headers=headers)
        list_response.raise_for_status()

        with session_maker() as session:
            stored_config = session.get(LlmProviderConfig, created["id"])
            decrypted_key = read_llm_provider_api_key(
                session,
                user_id=user_id,
                config_id=created["id"],
                secret_key=settings.secret_key,
            )

        delete_response = client.delete(f"/llm-configs/{created['id']}", headers=headers)
        delete_response.raise_for_status()

        missing_response = client.get("/llm-configs", headers=headers)
        missing_response.raise_for_status()
    finally:
        app.dependency_overrides.clear()

    assert created["provider"] == "google"
    assert created["api_key_hint"] == "sk-t...-key"
    assert "api_key" not in created
    listed_config = next(item for item in list_response.json() if item["id"] == created["id"])
    assert listed_config["api_key_hint"] == "sk-t...-key"
    assert "api_key" not in listed_config
    assert stored_config is not None
    assert stored_config.encrypted_api_key != "sk-test-secret-key"
    assert decrypted_key == "sk-test-secret-key"
    assert delete_response.json()["id"] == created["id"]
    assert [config["name"] for config in missing_response.json()] == ["Default"]


def test_config_used_by_document_group_cannot_be_deleted(tmp_path) -> None:
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
        auth = client.post(
            "/auth/register",
            json={"email": "mapped@example.com", "password": "strong-password"},
        )
        auth.raise_for_status()
        headers = {"Authorization": f"Bearer {auth.json()['access_token']}"}
        config = client.post(
            "/llm-configs",
            headers=headers,
            json={
                "name": "Mapped embeddings",
                "provider": "google",
                "config_type": "embedding",
                "api_key": "sk-mapped-secret-key",
                "embedding_model": "gemini-embedding-2",
            },
        )
        config.raise_for_status()
        group = client.post(
            "/document-groups",
            headers=headers,
            json={"name": "Mapped group", "llm_config_id": config.json()["id"]},
        )
        group.raise_for_status()
        blocked = client.delete(f"/llm-configs/{config.json()['id']}", headers=headers)
    finally:
        app.dependency_overrides.clear()

    assert group.json()["llm_config_name"] == "Mapped embeddings"
    assert blocked.status_code == 409
    assert "document groups" in blocked.json()["detail"]
