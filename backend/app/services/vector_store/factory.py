from app.core.config import Settings, VectorStoreProvider
from app.services.vector_store.base import VectorStore


def get_vector_store(settings: Settings) -> VectorStore:
    match settings.vector_store_provider:
        case VectorStoreProvider.chroma:
            from app.services.vector_store.chroma import ChromaVectorStore

            return ChromaVectorStore(
                persist_directory=settings.resolved_chroma_persist_directory,
                collection_name=settings.chroma_collection_name,
            )
        case VectorStoreProvider.postgresql:
            from app.services.vector_store.postgres import PgVectorStore

            return PgVectorStore(
                database_url=settings.pgvector_database_url,
                embedding_dimension=settings.embedding_dimension,
            )
        case VectorStoreProvider.sqlite:
            from app.services.vector_store.sqlite import SQLiteVectorStore

            return SQLiteVectorStore(database_url=settings.resolved_sqlite_vector_database_url)

    raise ValueError(f"Unsupported vector store provider: {settings.vector_store_provider}")
