import hashlib
import math
import re
from typing import Any, Protocol

import httpx
from sqlalchemy.orm import Session

from app.core.config import EmbeddingProvider, Settings
from app.core.security import decrypt_secret
from app.models import DocumentGroup, LlmProviderConfig


class EmbeddingService(Protocol):
    def embed_document(self, text: str) -> list[float]:
        raise NotImplementedError

    def embed_query(self, text: str) -> list[float]:
        raise NotImplementedError


class HashingEmbeddingService:
    """Deterministic local embeddings for development and tests.

    This is intentionally simple and dependency-light. It gives the retrieval
    pipeline stable vectors now, while leaving room to replace it with a real
    sentence embedding model behind the same service boundary.
    """

    def __init__(self, dimension: int) -> None:
        if dimension <= 0:
            raise ValueError("embedding dimension must be greater than zero")
        self.dimension = dimension

    def embed_document(self, text: str) -> list[float]:
        return self.embed(text)

    def embed_query(self, text: str) -> list[float]:
        return self.embed(text)

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        tokens = re.findall(r"[a-zA-Z0-9]+", text.lower())
        if not tokens:
            return vector

        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector

        return [value / norm for value in vector]


class SentenceTransformerEmbeddingService:
    def __init__(
        self,
        *,
        model_name: str,
        dimension: int,
        query_instruction: str,
        device: str | None,
        batch_size: int,
    ) -> None:
        self.model_name = model_name
        self.dimension = dimension
        self.query_instruction = query_instruction
        self.device = device
        self.batch_size = batch_size
        self._model = None

    def embed_document(self, text: str) -> list[float]:
        return self._embed(text)

    def embed_query(self, text: str) -> list[float]:
        return self._embed(f"{self.query_instruction}{text}")

    def _embed(self, text: str) -> list[float]:
        model = self._get_model()
        embedding = model.encode(
            [text],
            batch_size=self.batch_size,
            normalize_embeddings=True,
        )[0]
        vector = embedding.tolist() if hasattr(embedding, "tolist") else list(embedding)
        if len(vector) != self.dimension:
            raise ValueError(
                f"Embedding model returned {len(vector)} dimensions, "
                f"but EMBEDDING_DIMENSION is {self.dimension}."
            )
        return [float(value) for value in vector]

    def _get_model(self):
        if self._model is not None:
            return self._model

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is not installed. Install embedding dependencies with "
                "`pip install -e backend[embeddings]` or set EMBEDDING_PROVIDER=hashing."
            ) from exc

        kwargs = {}
        if self.device:
            kwargs["device"] = self.device
        self._model = SentenceTransformer(self.model_name, **kwargs)
        return self._model


def get_embedding_service(settings: Settings) -> EmbeddingService:
    if settings.embedding_provider == EmbeddingProvider.hashing:
        return HashingEmbeddingService(settings.embedding_dimension)
    if settings.embedding_provider == EmbeddingProvider.sentence_transformers:
        return SentenceTransformerEmbeddingService(
            model_name=settings.embedding_model_name,
            dimension=settings.embedding_dimension,
            query_instruction=settings.embedding_query_instruction,
            device=settings.embedding_device,
            batch_size=settings.embedding_batch_size,
        )

    raise ValueError(f"Unsupported embedding provider: {settings.embedding_provider}")


class RemoteEmbeddingService:
    def __init__(
        self,
        *,
        provider: str,
        model: str,
        api_key: str,
        base_url: str | None = None,
        output_dimension: int | None = None,
    ) -> None:
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.output_dimension = output_dimension

    def embed_document(self, text: str) -> list[float]:
        return self._embed(text, input_type="document")

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text, input_type="query")

    def _embed(self, text: str, *, input_type: str) -> list[float]:
        url, headers, payload = self._request(text, input_type=input_type)
        response = httpx.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        return self._extract(response.json())

    def _request(self, text: str, *, input_type: str) -> tuple[str, dict[str, str], dict[str, Any]]:
        if self.provider == "google":
            base = self.base_url or "https://generativelanguage.googleapis.com/v1beta"
            google_text = (
                f"title: none | text: {text}"
                if input_type == "document" and self.model == "gemini-embedding-2"
                else f"task: search result | query: {text}"
                if self.model == "gemini-embedding-2"
                else text
            )
            payload: dict[str, Any] = {
                "model": f"models/{self.model}",
                "content": {"parts": [{"text": google_text}]},
            }
            if self.output_dimension is not None:
                payload["output_dimensionality"] = self.output_dimension
            return (
                f"{base.rstrip('/')}/models/{self.model}:embedContent",
                {"x-goog-api-key": self.api_key},
                payload,
            )
        if self.provider == "cohere":
            return (
                f"{(self.base_url or 'https://api.cohere.com/v2').rstrip('/')}/embed",
                {"Authorization": f"Bearer {self.api_key}"},
                {
                    "model": self.model,
                    "texts": [text],
                    "input_type": "search_document" if input_type == "document" else "search_query",
                    "embedding_types": ["float"],
                },
            )
        if self.provider == "azure_openai":
            if not self.base_url:
                raise ValueError("Azure OpenAI requires a base URL")
            return (
                f"{self.base_url.rstrip('/')}/openai/deployments/{self.model}/embeddings"
                "?api-version=2024-02-01",
                {"api-key": self.api_key},
                {"input": [text]},
            )
        defaults = {
            "openai": "https://api.openai.com/v1",
            "mistral": "https://api.mistral.ai/v1",
            "voyage": "https://api.voyageai.com/v1",
        }
        base = self.base_url or defaults.get(self.provider)
        if not base:
            raise ValueError("Custom embedding provider requires a base URL")
        return (
            f"{base.rstrip('/')}/embeddings",
            {"Authorization": f"Bearer {self.api_key}"},
            {"model": self.model, "input": [text]},
        )

    def _extract(self, payload: dict[str, Any]) -> list[float]:
        if self.provider == "google":
            return [float(value) for value in payload["embedding"]["values"]]
        if self.provider == "cohere":
            return [float(value) for value in payload["embeddings"]["float"][0]]
        return [float(value) for value in payload["data"][0]["embedding"]]


class DimensionNormalizedEmbeddingService:
    def __init__(self, service: EmbeddingService, dimension: int) -> None:
        self.service = service
        self.dimension = dimension

    def embed_document(self, text: str) -> list[float]:
        return self._normalize(self.service.embed_document(text))

    def embed_query(self, text: str) -> list[float]:
        return self._normalize(self.service.embed_query(text))

    def _normalize(self, vector: list[float]) -> list[float]:
        if not vector:
            raise ValueError("Embedding provider returned an empty vector")
        folded = [0.0] * self.dimension
        for index, value in enumerate(vector):
            folded[index % self.dimension] += value
        norm = math.sqrt(sum(value * value for value in folded))
        return [value / norm for value in folded] if norm else folded


def get_embedding_service_for_group(
    session: Session, group_id: str, settings: Settings
) -> EmbeddingService:
    group = session.get(DocumentGroup, group_id)
    config = session.get(LlmProviderConfig, group.llm_config_id) if group else None
    if config is None:
        return get_embedding_service(settings)
    if config.purpose != "embedding" or not config.embedding_model:
        raise ValueError("Document group is not mapped to a valid embedding config")
    if config.provider == "internal":
        return get_embedding_service(settings)
    if not config.encrypted_api_key:
        raise ValueError("Embedding config has no API key")
    return DimensionNormalizedEmbeddingService(
        RemoteEmbeddingService(
            provider=config.provider,
            model=config.embedding_model,
            api_key=decrypt_secret(config.encrypted_api_key, secret_key=settings.secret_key),
            base_url=config.base_url,
            output_dimension=settings.embedding_dimension,
        ),
        settings.embedding_dimension,
    )
