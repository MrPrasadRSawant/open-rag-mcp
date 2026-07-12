from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.schemas.health import HealthResponse, VectorStoreHealth
from app.services.vector_store.factory import get_vector_store

router = APIRouter()
SettingsDependency = Annotated[Settings, Depends(get_settings)]


@router.get("/health", response_model=HealthResponse)
def health(settings: SettingsDependency) -> HealthResponse:
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        database_provider=settings.app_database_provider,
        vector_store_provider=settings.vector_store_provider,
    )


@router.get("/ready", response_model=HealthResponse)
def ready(settings: SettingsDependency) -> HealthResponse:
    vector_store = get_vector_store(settings)
    provider_health = vector_store.health()

    return HealthResponse(
        status="ok" if provider_health.ok else "degraded",
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        database_provider=settings.app_database_provider,
        vector_store_provider=settings.vector_store_provider,
        vector_store=VectorStoreHealth(
            ok=provider_health.ok,
            detail=provider_health.detail,
        ),
    )
