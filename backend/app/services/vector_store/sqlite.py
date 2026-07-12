import json
import math
import sqlite3
from pathlib import Path

from app.services.vector_store.base import (
    ProviderHealth,
    VectorDocument,
    VectorSearchResult,
)


class SQLiteVectorStore:
    provider_name = "sqlite"

    def __init__(self, database_url: str) -> None:
        self.database_path = self._database_path_from_url(database_url)

    def _database_path_from_url(self, database_url: str) -> Path:
        if not database_url.startswith("sqlite:///"):
            raise ValueError("SQLite vector URL must start with sqlite:///")
        return Path(database_url.removeprefix("sqlite:///"))

    def _connect(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path)
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS vector_documents (
                id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                embedding TEXT NOT NULL,
                metadata TEXT NOT NULL
            )
            """
        )
        return connection

    def health(self) -> ProviderHealth:
        try:
            with self._connect() as connection:
                connection.execute("SELECT 1").fetchone()
        except Exception as exc:
            return ProviderHealth(ok=False, detail=str(exc))

        return ProviderHealth(ok=True, detail="SQLite vector store is available")

    def add_documents(self, documents: list[VectorDocument]) -> None:
        if not documents:
            return

        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO vector_documents (id, text, embedding, metadata)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    text = excluded.text,
                    embedding = excluded.embedding,
                    metadata = excluded.metadata
                """,
                [
                    (
                        document.id,
                        document.text,
                        json.dumps(document.embedding),
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
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, text, embedding, metadata FROM vector_documents"
            ).fetchall()

        results: list[VectorSearchResult] = []
        for document_id, text, embedding_json, metadata_json in rows:
            metadata = json.loads(metadata_json)
            if metadata_filter and any(
                value is not None and metadata.get(key) != value
                for key, value in metadata_filter.items()
            ):
                continue

            embedding = json.loads(embedding_json)
            results.append(
                VectorSearchResult(
                    id=document_id,
                    text=text,
                    score=self._cosine_similarity(query_embedding, embedding),
                    metadata=metadata,
                )
            )

        return sorted(results, key=lambda result: result.score, reverse=True)[:limit]

    def delete_collection(self) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM vector_documents")

    def delete_by_metadata(
        self,
        metadata_filter: dict[str, str | int | float | bool | None],
    ) -> None:
        cleaned = {
            key: value
            for key, value in metadata_filter.items()
            if isinstance(value, str | int | float | bool)
        }
        if not cleaned:
            return

        with self._connect() as connection:
            rows = connection.execute("SELECT id, metadata FROM vector_documents").fetchall()
            ids_to_delete = [
                document_id
                for document_id, metadata_json in rows
                if self._metadata_matches(json.loads(metadata_json), cleaned)
            ]
            if ids_to_delete:
                connection.executemany(
                    "DELETE FROM vector_documents WHERE id = ?",
                    [(document_id,) for document_id in ids_to_delete],
                )

    def _cosine_similarity(self, left: list[float], right: list[float]) -> float:
        if len(left) != len(right) or not left:
            return 0.0

        dot_product = sum(
            left_item * right_item for left_item, right_item in zip(left, right, strict=False)
        )
        left_norm = math.sqrt(sum(item * item for item in left))
        right_norm = math.sqrt(sum(item * item for item in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0

        return dot_product / (left_norm * right_norm)

    def _metadata_matches(
        self,
        metadata: dict[str, str | int | float | bool | None],
        metadata_filter: dict[str, str | int | float | bool],
    ) -> bool:
        return all(metadata.get(key) == value for key, value in metadata_filter.items())
