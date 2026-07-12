from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DocumentGroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    llm_config_id: str | None = None


class DocumentGroupUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None


class DocumentGroupRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    name: str
    description: str | None
    llm_config_id: str | None
    llm_config_name: str | None = None
    created_at: datetime
    updated_at: datetime


class DocumentGroupDeleteRead(BaseModel):
    id: str
    deleted: bool
    documents_deleted: int
    api_keys_deleted: int


class DocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    text: str = Field(min_length=1)
    source_name: str | None = Field(default=None, max_length=255)
    content_type: str = "text/plain"
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    group_id: str
    title: str
    source_name: str | None
    content_type: str
    status: str
    error_message: str | None
    extra_metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    chunk_count: int = 0
    processing_job_id: str | None = None


class DocumentDeleteRead(BaseModel):
    id: str
    group_id: str
    deleted: bool
    chunks_deleted: int
    jobs_deleted: int


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    group_ids: list[str] | None = None
    limit: int = Field(default=5, ge=1, le=25)
    candidate_limit: int | None = Field(default=None, ge=1, le=100)
    rerank: bool | None = None
    lexical_weight: float | None = Field(default=None, ge=0, le=1)
    diversity: bool | None = None
    diversity_lambda: float | None = Field(default=None, ge=0, le=1)
    min_score: float | None = Field(default=None, ge=0, le=1)


class SearchResult(BaseModel):
    chunk_id: str
    document_id: str
    group_id: str
    text: str
    score: float
    vector_score: float | None = None
    lexical_score: float | None = None
    metadata: dict[str, Any]


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]


class ProcessingJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    document_id: str
    job_type: str
    status: str
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    updated_at: datetime
