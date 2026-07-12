import json

from app.services.vector_store.base import (
    ProviderHealth,
    VectorDocument,
    VectorSearchResult,
)


class PgVectorStore:
    provider_name = "postgresql"

    def __init__(self, database_url: str | None, *, embedding_dimension: int) -> None:
        if not database_url:
            raise ValueError("PGVECTOR_DATABASE_URL is required for the PostgreSQL vector store")
        self.database_url = database_url
        self.embedding_dimension = embedding_dimension

    def health(self) -> ProviderHealth:
        try:
            with self._connect() as connection:
                connection.execute("SELECT 1").fetchone()
        except Exception as exc:
            return ProviderHealth(ok=False, detail=str(exc))

        return ProviderHealth(ok=True, detail="PostgreSQL/pgvector is available")

    def add_documents(self, documents: list[VectorDocument]) -> None:
        if not documents:
            return

        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO vector_documents (id, text, embedding, metadata)
                VALUES (%s, %s, %s::vector, %s::jsonb)
                ON CONFLICT (id) DO UPDATE SET
                    text = EXCLUDED.text,
                    embedding = EXCLUDED.embedding,
                    metadata = EXCLUDED.metadata
                """,
                [
                    (
                        document.id,
                        document.text,
                        self._embedding_literal(document.embedding),
                        json.dumps(document.metadata),
                    )
                    for document in documents
                ],
            )

    def search(
        self,
        query_embedding: list[float],
        *,
        limit: int = 5,
        metadata_filter: dict[str, str | int | float | bool | None] | None = None,
    ) -> list[VectorSearchResult]:
        where_sql, params = self._metadata_where(metadata_filter)
        query = f"""
            SELECT
                id,
                text,
                metadata,
                embedding <=> %s::vector AS distance
            FROM vector_documents
            {where_sql}
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """
        embedding = self._embedding_literal(query_embedding)

        with self._connect() as connection:
            rows = connection.execute(query, [embedding, *params, embedding, limit]).fetchall()

        return [
            VectorSearchResult(
                id=row[0],
                text=row[1],
                metadata=row[2] or {},
                score=1.0 / (1.0 + float(row[3])),
            )
            for row in rows
        ]

    def delete_collection(self) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM vector_documents")

    def _connect(self):
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError("psycopg is not installed.") from exc

        connection = psycopg.connect(self.database_url)
        self._ensure_schema(connection)
        return connection

    def _ensure_schema(self, connection) -> None:
        connection.execute("CREATE EXTENSION IF NOT EXISTS vector")
        connection.execute(
            f"""
            CREATE TABLE IF NOT EXISTS vector_documents (
                id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                embedding vector({self.embedding_dimension}) NOT NULL,
                metadata JSONB NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_vector_documents_metadata
            ON vector_documents USING GIN (metadata)
            """
        )

    def _embedding_literal(self, embedding: list[float]) -> str:
        return "[" + ",".join(str(value) for value in embedding) + "]"

    def _metadata_where(
        self,
        metadata_filter: dict[str, str | int | float | bool | None] | None,
    ) -> tuple[str, list[str]]:
        if not metadata_filter:
            return "", []

        clauses = []
        params: list[str] = []
        for key, value in metadata_filter.items():
            if value is None:
                continue
            clauses.append("metadata ->> %s = %s")
            params.extend([key, str(value)])

        if not clauses:
            return "", []

        return "WHERE " + " AND ".join(clauses), params
