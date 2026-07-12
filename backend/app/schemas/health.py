from pydantic import BaseModel

from app.core.config import AppDatabaseProvider, VectorStoreProvider


class VectorStoreHealth(BaseModel):
    ok: bool
    detail: str


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    environment: str
    database_provider: AppDatabaseProvider
    vector_store_provider: VectorStoreProvider
    vector_store: VectorStoreHealth | None = None
