from pathlib import Path

from app.services.vector_store.base import (
    ProviderHealth,
    VectorDocument,
    VectorSearchResult,
)


class ChromaVectorStore:
    provider_name = "chroma"

    def __init__(self, persist_directory: str, collection_name: str) -> None:
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)

    def _collection(self):
        try:
            import chromadb
        except ImportError as exc:
            raise RuntimeError(
                "ChromaDB is not installed. Install backend dependencies or select another "
                "VECTOR_STORE_PROVIDER."
            ) from exc

        client = chromadb.PersistentClient(path=self.persist_directory)
        return client.get_or_create_collection(name=self.collection_name)

    def health(self) -> ProviderHealth:
        try:
            collection = self._collection()
            collection.count()
        except Exception as exc:
            return ProviderHealth(ok=False, detail=str(exc))

        return ProviderHealth(ok=True, detail="ChromaDB is available")

    def add_documents(self, documents: list[VectorDocument]) -> None:
        if not documents:
            return

        collection = self._collection()
        collection.upsert(
            ids=[document.id for document in documents],
            documents=[document.text for document in documents],
            embeddings=[document.embedding for document in documents],
            metadatas=[document.metadata for document in documents],
        )

    def search(
        self,
        query_embedding: list[float],
        *,
        limit: int = 5,
        metadata_filter: dict[str, str | int | float | bool | None] | None = None,
    ) -> list[VectorSearchResult]:
        collection = self._collection()
        response = collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where=self._where(metadata_filter),
            include=["documents", "metadatas", "distances"],
        )

        ids = response.get("ids", [[]])[0]
        texts = response.get("documents", [[]])[0]
        metadatas = response.get("metadatas", [[]])[0]
        distances = response.get("distances", [[]])[0]

        return [
            VectorSearchResult(
                id=document_id,
                text=text,
                score=1.0 / (1.0 + distance),
                metadata=metadata or {},
            )
            for document_id, text, metadata, distance in zip(
                ids,
                texts,
                metadatas,
                distances,
                strict=False,
            )
        ]

    def delete_collection(self) -> None:
        try:
            import chromadb
        except ImportError as exc:
            raise RuntimeError("ChromaDB is not installed.") from exc

        client = chromadb.PersistentClient(path=self.persist_directory)
        client.delete_collection(name=self.collection_name)

    def delete_by_metadata(
        self,
        metadata_filter: dict[str, str | int | float | bool | None],
    ) -> None:
        where = self._where(metadata_filter)
        if not where:
            return

        collection = self._collection()
        collection.delete(where=where)

    def _where(
        self,
        metadata_filter: dict[str, str | int | float | bool | None] | None,
    ):
        if not metadata_filter:
            return None

        cleaned = {
            key: value
            for key, value in metadata_filter.items()
            if isinstance(value, str | int | float | bool)
        }
        if len(cleaned) <= 1:
            return cleaned or None

        return {"$and": [{key: value} for key, value in cleaned.items()]}
