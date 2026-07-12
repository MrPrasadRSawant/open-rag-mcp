import hashlib
import math
import re
from typing import Protocol

from app.core.config import EmbeddingProvider, Settings


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
