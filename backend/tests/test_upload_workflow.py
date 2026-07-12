from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.dependencies import get_vector_store_dependency
from app.core.config import Settings, VectorStoreProvider, get_settings
from app.core.database import get_engine, get_session, get_session_maker
from app.main import app
from app.models import Base
from app.services.vector_store.factory import get_vector_store


def test_text_file_upload_is_ingested_and_searchable(tmp_path) -> None:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'app.db'}",
        vector_store_provider=VectorStoreProvider.sqlite,
        sqlite_vector_database_url=f"sqlite:///{tmp_path / 'vectors.db'}",
        upload_directory=str(tmp_path / "uploads"),
        embedding_dimension=64,
        chunk_size=120,
        chunk_overlap=20,
    )
    Base.metadata.create_all(bind=get_engine(settings.resolved_database_url))
    session_maker = get_session_maker(settings.resolved_database_url)
    vector_store = get_vector_store(settings)

    def override_settings() -> Settings:
        return settings

    def override_session() -> Generator[Session]:
        with session_maker() as session:
            yield session

    def override_vector_store():
        return vector_store

    app.dependency_overrides[get_settings] = override_settings
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_vector_store_dependency] = override_vector_store

    try:
        client = TestClient(app)
        auth_response = client.post(
            "/auth/register",
            json={"email": "upload@example.com", "password": "strong-password"},
        )
        auth_response.raise_for_status()
        headers = {"Authorization": f"Bearer {auth_response.json()['access_token']}"}

        group_response = client.post(
            "/document-groups",
            json={"name": "Uploads"},
            headers=headers,
        )
        group_response.raise_for_status()
        group_id = group_response.json()["id"]

        upload_response = client.post(
            f"/document-groups/{group_id}/documents/upload",
            headers=headers,
            data={"title": "Upload notes"},
            files={
                "file": (
                    "notes.txt",
                    b"Vector search upload pipeline handles text files.",
                    "text/plain",
                )
            },
        )
        upload_response.raise_for_status()
        job_id = upload_response.json()["processing_job_id"]
        job_response = client.get(f"/jobs/{job_id}", headers=headers)
        job_response.raise_for_status()

        search_response = client.post(
            "/search",
            headers=headers,
            json={"query": "upload vector pipeline", "group_ids": [group_id]},
        )
        search_response.raise_for_status()
    finally:
        app.dependency_overrides.clear()

    assert upload_response.json()["status"] == "queued"
    assert upload_response.json()["source_name"] == "notes.txt"
    assert job_response.json()["status"] == "completed"
    assert search_response.json()["results"]
