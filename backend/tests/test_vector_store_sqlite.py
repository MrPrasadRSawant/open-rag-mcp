from app.services.vector_store.base import VectorDocument
from app.services.vector_store.sqlite import SQLiteVectorStore


def test_sqlite_vector_store_searches_by_cosine_similarity(tmp_path) -> None:
    store = SQLiteVectorStore(f"sqlite:///{tmp_path / 'vectors.db'}")
    store.add_documents(
        [
            VectorDocument(
                id="first",
                text="First document",
                embedding=[1.0, 0.0],
                metadata={"group_id": "alpha"},
            ),
            VectorDocument(
                id="second",
                text="Second document",
                embedding=[0.0, 1.0],
                metadata={"group_id": "beta"},
            ),
        ]
    )

    results = store.search([1.0, 0.0], metadata_filter={"group_id": "alpha"})

    assert [result.id for result in results] == ["first"]
    assert results[0].score == 1.0
