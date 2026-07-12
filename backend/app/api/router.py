from fastapi import APIRouter

from app.api.routes import (
    api_keys,
    auth,
    document_groups,
    documents,
    health,
    jobs,
    llm_configs,
    search,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(api_keys.router)
api_router.include_router(document_groups.router)
api_router.include_router(documents.router)
api_router.include_router(jobs.router)
api_router.include_router(llm_configs.router)
api_router.include_router(search.router)
