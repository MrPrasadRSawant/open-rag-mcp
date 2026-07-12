from app.services.retrieval import RetrievalOptions, rerank_vector_results
from app.services.vector_store.base import VectorSearchResult


def test_lexical_reranking_can_promote_keyword_match() -> None:
    results = [
        VectorSearchResult(
            id="semantic",
            text="General finance planning and quarterly operating notes.",
            score=0.9,
            metadata={},
        ),
        VectorSearchResult(
            id="keyword",
            text="Cloud rollback runbook with health checks and service logs.",
            score=0.7,
            metadata={},
        ),
    ]

    ranked = rerank_vector_results(
        query="cloud rollback health",
        results=results,
        options=RetrievalOptions(limit=2, candidate_limit=2, lexical_weight=0.6),
    )

    assert [item.result.id for item in ranked] == ["keyword", "semantic"]
    assert ranked[0].lexical_score > ranked[1].lexical_score


def test_diversity_reranking_reduces_near_duplicate_results() -> None:
    results = [
        VectorSearchResult(
            id="primary",
            text="Cloud deployment rollback health checks service logs.",
            score=0.95,
            metadata={},
        ),
        VectorSearchResult(
            id="duplicate",
            text="Cloud deployment rollback health checks service logs repeated.",
            score=0.94,
            metadata={},
        ),
        VectorSearchResult(
            id="different",
            text="Database migration backup restore validation checklist.",
            score=0.8,
            metadata={},
        ),
    ]

    ranked = rerank_vector_results(
        query="cloud deployment rollback health",
        results=results,
        options=RetrievalOptions(
            limit=2,
            candidate_limit=3,
            lexical_weight=0.2,
            diversity=True,
            diversity_lambda=0.35,
        ),
    )

    assert ranked[0].result.id == "primary"
    assert ranked[1].result.id == "different"


def test_rerank_can_be_disabled_without_breaking_vector_results() -> None:
    results = [
        VectorSearchResult(
            id="first",
            text="No exact keyword match here.",
            score=0.9,
            metadata={},
        ),
        VectorSearchResult(
            id="second",
            text="Cloud rollback health exact keyword match.",
            score=0.7,
            metadata={},
        ),
    ]

    ranked = rerank_vector_results(
        query="cloud rollback health",
        results=results,
        options=RetrievalOptions(limit=2, candidate_limit=2, rerank=False),
    )

    assert [item.result.id for item in ranked] == ["first", "second"]
    assert ranked[0].final_score == 0.9
    assert ranked[0].lexical_score == 0.0
