from sqlalchemy.orm import Session

from app.core.config import Settings, VectorStoreProvider
from app.core.database import get_engine, get_session_maker
from app.models import Base
from app.schemas.documents import DocumentCreate
from app.services.documents import (
    create_document_group,
    ingest_text_document,
    list_documents,
    search_documents,
)
from app.services.vector_store.factory import get_vector_store


def test_text_document_can_be_ingested_and_searched(tmp_path) -> None:
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

    with session_maker() as session:
        assert isinstance(session, Session)
        group = create_document_group(
            session,
            name="Finance",
            description="Finance planning documents",
        )

        document = ingest_text_document(
            session,
            vector_store=vector_store,
            settings=settings,
            group_id=group.id,
            payload=DocumentCreate(
                title="Budget plan",
                text=(
                    "The quarterly budget forecast includes cloud costs, "
                    "headcount planning, and operating expenses."
                ),
                metadata={"department": "finance"},
            ),
        )

        chunk_count = len(document.chunks)
        documents = list_documents(session, group_id=group.id)

        results = search_documents(
            session=session,
            vector_store=vector_store,
            settings=settings,
            query="cloud budget forecast",
            group_ids=[group.id],
            limit=3,
        )

        assert document.status == "processed"
        assert chunk_count == 1
        assert [item.id for item in documents] == [document.id]
        assert results
        assert results[0].document_id == document.id
        assert results[0].metadata["department"] == "finance"
