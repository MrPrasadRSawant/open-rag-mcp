from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.dependencies import get_vector_store_dependency
from app.core.config import Settings, VectorStoreProvider, get_settings
from app.core.database import get_engine, get_session, get_session_maker
from app.main import app
from app.models import Base
from app.services.vector_store.factory import get_vector_store


def test_api_can_create_group_ingest_document_and_search(tmp_path) -> None:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'app.db'}",
        vector_store_provider=VectorStoreProvider.sqlite,
        sqlite_vector_database_url=f"sqlite:///{tmp_path / 'vectors.db'}",
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
            json={
                "email": "engineer@example.com",
                "password": "correct-password",
                "full_name": "Engineer",
            },
        )
        auth_response.raise_for_status()
        headers = {
            "Authorization": f"Bearer {auth_response.json()['access_token']}",
        }

        group_response = client.post(
            "/document-groups",
            json={"name": "Engineering", "description": "Engineering docs"},
            headers=headers,
        )
        group_response.raise_for_status()
        group_id = group_response.json()["id"]

        document_response = client.post(
            f"/document-groups/{group_id}/documents",
            json={
                "title": "Runbook",
                "text": "Deployments use health checks, rollback steps, and service logs.",
                "metadata": {"team": "platform"},
            },
            headers=headers,
        )
        document_response.raise_for_status()
        document_id = document_response.json()["id"]
        job_id = document_response.json()["processing_job_id"]
        job_response = client.get(f"/jobs/{job_id}", headers=headers)
        job_response.raise_for_status()

        search_response = client.post(
            "/search",
            json={"query": "service health rollback", "group_ids": [group_id]},
            headers=headers,
        )
        search_response.raise_for_status()

        group_update_response = client.patch(
            f"/document-groups/{group_id}",
            json={"name": "Engineering Updated", "description": "Updated docs"},
            headers=headers,
        )
        group_update_response.raise_for_status()

        document_update_response = client.patch(
            f"/document-groups/{group_id}/documents/{document_id}",
            json={"title": "Runbook Updated"},
            headers=headers,
        )
        document_update_response.raise_for_status()

        document_delete_response = client.delete(
            f"/document-groups/{group_id}/documents/{document_id}",
            headers=headers,
        )
        document_delete_response.raise_for_status()

        vector_results_after_delete = vector_store.search(
            [1.0] + [0.0] * (settings.embedding_dimension - 1),
            metadata_filter={"document_id": document_id},
        )

        stale_search_response = client.post(
            "/search",
            json={"query": "service health rollback", "group_ids": [group_id]},
            headers=headers,
        )
        stale_search_response.raise_for_status()

        group_delete_response = client.delete(
            f"/document-groups/{group_id}",
            headers=headers,
        )
        group_delete_response.raise_for_status()

        archive_group_response = client.post(
            "/document-groups",
            json={"name": "Archive"},
            headers=headers,
        )
        archive_group_response.raise_for_status()
        archive_group_id = archive_group_response.json()["id"]

        archive_document_response = client.post(
            f"/document-groups/{archive_group_id}/documents",
            json={
                "title": "Archive Runbook",
                "text": "Archive retention policies include deletion and restore procedures.",
            },
            headers=headers,
        )
        archive_document_response.raise_for_status()

        archive_search_response = client.post(
            "/search",
            json={"query": "archive retention restore", "group_ids": [archive_group_id]},
            headers=headers,
        )
        archive_search_response.raise_for_status()

        archive_group_delete_response = client.delete(
            f"/document-groups/{archive_group_id}",
            headers=headers,
        )
        archive_group_delete_response.raise_for_status()

        archive_vector_results_after_delete = vector_store.search(
            [1.0] + [0.0] * (settings.embedding_dimension - 1),
            metadata_filter={"group_id": archive_group_id},
        )

        archive_stale_search_response = client.post(
            "/search",
            json={"query": "archive retention restore", "group_ids": [archive_group_id]},
            headers=headers,
        )
        archive_stale_search_response.raise_for_status()
    finally:
        app.dependency_overrides.clear()

    assert document_response.json()["status"] == "queued"
    assert document_response.json()["chunk_count"] == 0
    assert job_response.json()["status"] == "completed"
    assert search_response.json()["results"]
    assert search_response.json()["results"][0]["metadata"]["team"] == "platform"
    assert group_update_response.json()["name"] == "Engineering Updated"
    assert document_update_response.json()["title"] == "Runbook Updated"
    assert document_delete_response.status_code == 200
    assert document_delete_response.json()["deleted"] is True
    assert document_delete_response.json()["id"] == document_id
    assert document_delete_response.json()["group_id"] == group_id
    assert document_delete_response.json()["chunks_deleted"] == 1
    assert document_delete_response.json()["jobs_deleted"] == 1
    assert vector_results_after_delete == []
    assert stale_search_response.json()["results"] == []
    assert group_delete_response.status_code == 200
    assert group_delete_response.json()["deleted"] is True
    assert group_delete_response.json()["id"] == group_id
    assert archive_document_response.json()["status"] == "queued"
    assert archive_search_response.json()["results"]
    assert archive_group_delete_response.json()["documents_deleted"] == 1
    assert archive_vector_results_after_delete == []
    assert archive_stale_search_response.json()["results"] == []
