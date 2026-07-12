from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class LlmProvider(StrEnum):
    internal = "internal"
    openai = "openai"
    azure_openai = "azure_openai"
    anthropic = "anthropic"
    google = "google"
    cohere = "cohere"
    mistral = "mistral"
    voyage = "voyage"
    custom = "custom"


class LlmConfigType(StrEnum):
    embedding = "embedding"
    chat_llm = "chat_llm"


class LlmProviderConfigCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    provider: LlmProvider
    config_type: LlmConfigType = LlmConfigType.embedding
    api_key: str = Field(min_length=1, max_length=4000)
    base_url: str | None = Field(default=None, max_length=500)
    embedding_model: str | None = Field(default=None, max_length=200)
    chat_model: str | None = Field(default=None, max_length=200)


class LlmProviderConfigRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    provider: LlmProvider
    purpose: LlmConfigType
    api_key_hint: str | None
    base_url: str | None
    embedding_model: str | None
    chat_model: str | None
    in_use_by_groups: int = 0
    is_active: bool
    created_at: datetime
    updated_at: datetime
