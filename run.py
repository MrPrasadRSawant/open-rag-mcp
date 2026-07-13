import argparse
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = REPOSITORY_ROOT / "backend"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Open RAG MCP services.")
    parser.add_argument(
        "service",
        nargs="?",
        choices=["api", "mcp"],
        default="api",
        help="Service to run. Defaults to api.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host for the API server.")
    parser.add_argument("--port", type=int, default=8000, help="Port for the API server.")
    parser.add_argument(
        "--reload",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable API auto-reload. Use --no-reload to disable.",
    )
    parser.add_argument(
        "--migrate",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Apply database migrations before starting the API. Use --no-migrate to skip.",
    )
    args = parser.parse_args()

    _add_backend_to_path()

    if args.service == "api":
        run_api(host=args.host, port=args.port, reload=args.reload, migrate=args.migrate)
    elif args.service == "mcp":
        run_mcp()


def run_api(*, host: str, port: int, reload: bool, migrate: bool) -> None:
    import uvicorn

    if migrate:
        from app.core.migrations import upgrade_database

        upgrade_database()

    uvicorn.run(
        "app.main:app",
        app_dir=str(BACKEND_DIR),
        host=host,
        port=port,
        reload=reload,
        reload_dirs=[str(BACKEND_DIR), str(REPOSITORY_ROOT)] if reload else None,
    )


def run_mcp() -> None:
    from app.mcp.server import mcp

    mcp.run(transport="streamable-http")


def _add_backend_to_path() -> None:
    backend_path = str(BACKEND_DIR)
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)


if __name__ == "__main__":
    main()
