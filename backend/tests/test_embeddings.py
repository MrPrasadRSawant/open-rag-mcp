import math
import sys
from types import SimpleNamespace

from app.core.config import EmbeddingProvider, Settings
from app.services.embeddings import (
    DimensionNormalizedEmbeddingService,
    RemoteEmbeddingService,
    get_embedding_service,
)


class FakeEmbedding(list):
    def tolist(self):
        return list(self)


class FakeSentenceTransformer:
    instances = []

    def __init__(self, model_name: str, **kwargs) -> None:
        self.model_name = model_name
        self.kwargs = kwargs
        self.inputs: list[str] = []
        FakeSentenceTransformer.instances.append(self)

    def encode(self, texts, *, batch_size: int, normalize_embeddings: bool):
        self.inputs.extend(texts)
        assert batch_size == 4
        assert normalize_embeddings is True
        return [FakeEmbedding([0.1, 0.2, 0.3])]


def test_sentence_transformer_provider_uses_query_instruction(monkeypatch) -> None:
    FakeSentenceTransformer.instances.clear()
    monkeypatch.setitem(
        sys.modules,
        "sentence_transformers",
        SimpleNamespace(SentenceTransformer=FakeSentenceTransformer),
    )
    settings = Settings(
        embedding_provider=EmbeddingProvider.sentence_transformers,
        embedding_model_name="BAAI/bge-small-en-v1.5",
        embedding_dimension=3,
        embedding_query_instruction="Represent this sentence for searching relevant passages: ",
        embedding_device="cpu",
        embedding_batch_size=4,
    )

    service = get_embedding_service(settings)
    document_vector = service.embed_document("passage text")
    query_vector = service.embed_query("query text")

    instance = FakeSentenceTransformer.instances[0]
    assert instance.model_name == "BAAI/bge-small-en-v1.5"
    assert instance.kwargs == {"device": "cpu"}
    assert document_vector == [0.1, 0.2, 0.3]
    assert query_vector == [0.1, 0.2, 0.3]
    assert instance.inputs == [
        "passage text",
        "Represent this sentence for searching relevant passages: query text",
    ]


class VariableDimensionService:
    def embed_document(self, text: str) -> list[float]:
        return [1.0, 2.0, 3.0, 4.0]

    def embed_query(self, text: str) -> list[float]:
        return [1.0, 2.0, 3.0, 4.0]


def test_remote_embeddings_are_normalized_to_vector_store_dimension() -> None:
    service = DimensionNormalizedEmbeddingService(VariableDimensionService(), 2)

    vector = service.embed_query("query")

    assert len(vector) == 2
    assert math.isclose(sum(value * value for value in vector), 1.0)


def test_gemini_embedding_request_uses_header_and_configured_dimension() -> None:
    service = RemoteEmbeddingService(
        provider="google",
        model="gemini-embedding-2",
        api_key="gemini-secret",
        base_url="https://generativelanguage.googleapis.com/v1beta",
        output_dimension=384,
    )

    url, headers, payload = service._request("meaning of life", input_type="query")

    assert url.endswith("/models/gemini-embedding-2:embedContent")
    assert "gemini-secret" not in url
    assert headers == {"x-goog-api-key": "gemini-secret"}
    assert payload["model"] == "models/gemini-embedding-2"
    assert payload["output_dimensionality"] == 384
    assert payload["content"]["parts"][0]["text"].startswith("task: search result")
