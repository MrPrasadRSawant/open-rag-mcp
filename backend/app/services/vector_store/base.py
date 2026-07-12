from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class VectorDocument:
    id: str
    text: str
    embedding: list[float]
    metadata: dict[str, str | int | float | bool | None] = field(default_factory=dict)


@dataclass(frozen=True)
class VectorSearchResult:
    id: str
    text: str
    score: float
    metadata: dict[str, str | int | float | bool | None]


@dataclass(frozen=True)
class ProviderHealth:
    ok: bool
    detail: str


class VectorStore(Protocol):
    provider_name: str

    def health(self) -> ProviderHealth:
        raise NotImplementedError

    def add_documents(self, documents: list[VectorDocument]) -> None:
        raise NotImplementedError

    def search(
        self,
        query_embedding: list[float],
        *,
        limit: int = 5,
        metadata_filter: dict[str, str | int | float | bool | None] | None = None,
    ) -> list[VectorSearchResult]:
        raise NotImplementedError

    def delete_by_metadata(
        self,
        metadata_filter: dict[str, str | int | float | bool | None],
    ) -> None:
        raise NotImplementedError

    def delete_collection(self) -> None:
        raise NotImplementedError
