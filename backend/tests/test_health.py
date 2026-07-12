from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import app, create_app


def test_health_returns_configured_defaults() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["database_provider"] == "sqlite"
    assert response.json()["vector_store_provider"] == "chroma"


def test_cors_policy_allows_api_and_mcp_headers(tmp_path) -> None:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'app.db'}",
        cors_origins="http://localhost:9000",
    )

    with TestClient(create_app(settings), base_url="http://127.0.0.1:8000") as client:
        preflight = client.options(
            "/mcp/",
            headers={
                "Origin": "http://localhost:9000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": (
                    "authorization,mcp-session-id,mcp-protocol-version,content-type"
                ),
            },
        )
        health = client.get("/health", headers={"Origin": "http://localhost:9000"})

    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == "http://localhost:9000"
    assert "authorization" in preflight.headers["access-control-allow-headers"].lower()
    assert "mcp-session-id" in preflight.headers["access-control-allow-headers"].lower()
    assert health.status_code == 200
    assert "mcp-session-id" in health.headers["access-control-expose-headers"].lower()
