from collections.abc import Generator
from functools import lru_cache
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.models import Base


def _sqlite_path_from_url(database_url: str) -> Path | None:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        return None

    return Path(database_url.removeprefix(prefix))


@lru_cache
def get_engine(database_url: str) -> Engine:
    sqlite_path = _sqlite_path_from_url(database_url)
    connect_args = {}
    if sqlite_path is not None:
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        connect_args = {"check_same_thread": False}

    return create_engine(database_url, connect_args=connect_args)


@lru_cache
def get_session_maker(database_url: str) -> sessionmaker[Session]:
    return sessionmaker(
        bind=get_engine(database_url),
        autoflush=False,
        expire_on_commit=False,
    )


def init_database(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=get_engine(settings.resolved_database_url))


def get_session() -> Generator[Session]:
    settings = get_settings()
    session_maker = get_session_maker(settings.resolved_database_url)
    with session_maker() as session:
        yield session
