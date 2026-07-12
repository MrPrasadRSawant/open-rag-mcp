from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


class AppDatabaseProvider(StrEnum):
    sqlite = "sqlite"
    postgresql = "postgresql"


class VectorStoreProvider(StrEnum):
    chroma = "chroma"
    postgresql = "postgresql"
    sqlite = "sqlite"


class OcrProvider(StrEnum):
    disabled = "disabled"
    paddle = "paddle"


class EmbeddingProvider(StrEnum):
    hashing = "hashing"
    sentence_transformers = "sentence_transformers"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Open RAG MCP"
    app_version: str = "0.1.0"
    app_env: str = "development"
    secret_key: str = "change-this-development-secret"
    access_token_expire_minutes: int = 60
    auto_create_tables: bool = False
    cors_origins: str = (
        "http://localhost:9000,http://127.0.0.1:9000,"
        "http://localhost:9001,http://127.0.0.1:9001"
    )
    cors_allow_credentials: bool = True
    cors_allow_methods: str = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
    cors_allow_headers: str = (
        "Accept,Authorization,Content-Type,Last-Event-ID,"
        "Mcp-Session-Id,MCP-Protocol-Version,mcp-session-id,mcp-protocol-version"
    )
    cors_expose_headers: str = (
        "Mcp-Session-Id,MCP-Session-Id,mcp-session-id,WWW-Authenticate"
    )
    cors_max_age: int = 600
    mcp_issuer_url: str = "http://127.0.0.1:8000"
    mcp_resource_server_url: str = "http://127.0.0.1:8000/mcp"
    mcp_enable_dns_rebinding_protection: bool = True
    mcp_allowed_hosts: str = "127.0.0.1:8000,localhost:8000"
    mcp_allowed_origins: str = ""

    app_database_provider: AppDatabaseProvider = AppDatabaseProvider.sqlite
    database_url: str = "sqlite:///./data/open_rag_mcp.db"

    vector_store_provider: VectorStoreProvider = VectorStoreProvider.chroma
    chroma_persist_directory: str = "./data/chroma"
    chroma_collection_name: str = "open_rag_documents"

    pgvector_database_url: str | None = Field(default=None)
    sqlite_vector_database_url: str = "sqlite:///./data/vectors.db"

    embedding_dimension: int = 384
    embedding_provider: EmbeddingProvider = EmbeddingProvider.hashing
    embedding_model_name: str = "BAAI/bge-small-en-v1.5"
    embedding_query_instruction: str = (
        "Represent this sentence for searching relevant passages: "
    )
    embedding_device: str | None = None
    embedding_batch_size: int = 32
    chunk_size: int = 1200
    chunk_overlap: int = 150
    upload_directory: str = "./data/uploads"
    max_upload_size_mb: int = 25
    ocr_provider: OcrProvider = OcrProvider.disabled
    ocr_language: str = "en"
    ocr_pdf_dpi: int = 200

    @property
    def resolved_database_url(self) -> str:
        return self._resolve_sqlite_url(self.database_url)

    @property
    def resolved_chroma_persist_directory(self) -> str:
        return str(self._resolve_path(self.chroma_persist_directory))

    @property
    def resolved_upload_directory(self) -> Path:
        return self._resolve_path(self.upload_directory)

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def allowed_cors_origins(self) -> list[str]:
        return self._split_csv(self.cors_origins)

    @property
    def allowed_cors_methods(self) -> list[str]:
        return self._split_csv(self.cors_allow_methods)

    @property
    def allowed_cors_headers(self) -> list[str]:
        return self._split_csv(self.cors_allow_headers)

    @property
    def exposed_cors_headers(self) -> list[str]:
        return self._split_csv(self.cors_expose_headers)

    @property
    def allowed_mcp_hosts(self) -> list[str]:
        return self._split_csv(self.mcp_allowed_hosts)

    @property
    def allowed_mcp_origins(self) -> list[str]:
        return self._split_csv(self.mcp_allowed_origins)

    @property
    def resolved_sqlite_vector_database_url(self) -> str:
        return self._resolve_sqlite_url(self.sqlite_vector_database_url)

    def _resolve_path(self, value: str) -> Path:
        path = Path(value)
        if path.is_absolute():
            return path
        return REPOSITORY_ROOT / path

    def _resolve_sqlite_url(self, value: str) -> str:
        prefix = "sqlite:///"
        if not value.startswith(prefix):
            return value

        raw_path = value.removeprefix(prefix)
        resolved_path = self._resolve_path(raw_path)
        return f"{prefix}{resolved_path.as_posix()}"

    def _split_csv(self, value: str) -> list[str]:
        return [item.strip() for item in value.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
