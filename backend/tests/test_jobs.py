from app.core.config import Settings, VectorStoreProvider
from app.core.database import get_engine, get_session_maker
from app.models import Base
from app.schemas.documents import DocumentCreate
from app.services.documents import create_document_group, create_queued_text_document
from app.services.jobs import process_job
from app.services.vector_store.factory import get_vector_store


def test_processing_job_updates_document_and_indexes_text(tmp_path) -> None:
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

    with session_maker() as session:
        group = create_document_group(session, name="Jobs")
        document, job = create_queued_text_document(
            session,
            group_id=group.id,
            owner_id="local",
            payload=DocumentCreate(
                title="Queued",
                text="Background processing indexes queued text documents.",
            ),
        )

    process_job(job.id, settings)

    with session_maker() as session:
        processed_document = session.get(type(document), document.id)
        processed_job = session.get(type(job), job.id)

    vector_store = get_vector_store(settings)
    results = vector_store.search([1.0] + [0.0] * 63, limit=1)

    assert processed_document is not None
    assert processed_document.status == "processed"
    assert processed_job is not None
    assert processed_job.status == "completed"
    assert results
