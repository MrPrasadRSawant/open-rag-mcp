from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.agent_cors import PublicAgentCorsMiddleware
from app.api.router import api_router
from app.api.routes.agent_runtime import agent_test_page
from app.core.config import Settings, get_settings
from app.core.database import init_database
from app.mcp.server import create_mcp_server
from app.services.documentation import load_documentation_cache


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    init_database(settings)
    mcp_server = create_mcp_server(settings)
    mcp_http_app = mcp_server.streamable_http_app()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        load_documentation_cache()
        async with mcp_server.session_manager.run():
            yield

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.allowed_cors_methods,
        allow_headers=settings.allowed_cors_headers,
        expose_headers=settings.exposed_cors_headers,
        max_age=settings.cors_max_age,
    )
    app.add_middleware(PublicAgentCorsMiddleware, settings=settings)
    app.include_router(api_router)
    app.add_api_route("/test-web", agent_test_page, include_in_schema=False)
    app.mount("/mcp", mcp_http_app)
    return app


app = create_app()
