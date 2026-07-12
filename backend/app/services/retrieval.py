from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.vector_store.base import VectorSearchResult

TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9]+")


@dataclass(frozen=True)
class RetrievalOptions:
    limit: int = 5
    candidate_limit: int = 30
    rerank: bool = True
    lexical_weight: float = 0.35
    diversity: bool = False
    diversity_lambda: float = 0.75
    min_score: float | None = None

    def normalized(self) -> RetrievalOptions:
        limit = max(1, min(self.limit, 25))
        candidate_limit = max(limit, min(self.candidate_limit, 100))
        return RetrievalOptions(
            limit=limit,
            candidate_limit=candidate_limit,
            rerank=self.rerank,
            lexical_weight=max(0.0, min(self.lexical_weight, 1.0)),
            diversity=self.diversity,
            diversity_lambda=max(0.0, min(self.diversity_lambda, 1.0)),
            min_score=self.min_score,
        )


@dataclass(frozen=True)
class RankedSearchResult:
    result: VectorSearchResult
    final_score: float
    vector_score: float
    lexical_score: float


def rerank_vector_results(
    *,
    query: str,
    results: list[VectorSearchResult],
    options: RetrievalOptions,
) -> list[RankedSearchResult]:
    options = options.normalized()
    ranked = [
        _rank_result(query=query, result=result, lexical_weight=options.lexical_weight)
        for result in results
    ]

    if not options.rerank:
        ranked = [
            RankedSearchResult(
                result=item,
                final_score=_normalize_vector_score(item.score),
                vector_score=item.score,
                lexical_score=0.0,
            )
            for item in results
        ]

    if options.min_score is not None:
        ranked = [item for item in ranked if item.final_score >= options.min_score]

    ranked = sorted(ranked, key=lambda item: item.final_score, reverse=True)
    if options.diversity:
        ranked = _apply_mmr(ranked, options=options)

    return ranked[: options.limit]


def _rank_result(
    *,
    query: str,
    result: VectorSearchResult,
    lexical_weight: float,
) -> RankedSearchResult:
    vector_score = _normalize_vector_score(result.score)
    lexical_score = _lexical_score(query, result.text)
    final_score = ((1.0 - lexical_weight) * vector_score) + (lexical_weight * lexical_score)
    return RankedSearchResult(
        result=result,
        final_score=round(final_score, 6),
        vector_score=result.score,
        lexical_score=round(lexical_score, 6),
    )


def _apply_mmr(
    ranked: list[RankedSearchResult],
    *,
    options: RetrievalOptions,
) -> list[RankedSearchResult]:
    selected: list[RankedSearchResult] = []
    remaining = ranked.copy()

    while remaining and len(selected) < options.limit:
        best = max(
            remaining,
            key=lambda item: (
                options.diversity_lambda * item.final_score
                - (1.0 - options.diversity_lambda) * _max_similarity(item, selected)
            ),
        )
        selected.append(best)
        remaining.remove(best)

    return selected


def _max_similarity(
    candidate: RankedSearchResult,
    selected: list[RankedSearchResult],
) -> float:
    if not selected:
        return 0.0
    candidate_tokens = set(_tokenize(candidate.result.text))
    return max(_jaccard(candidate_tokens, set(_tokenize(item.result.text))) for item in selected)


def _lexical_score(query: str, text: str) -> float:
    query_terms = set(_tokenize(query))
    if not query_terms:
        return 0.0

    text_terms = _tokenize(text)
    if not text_terms:
        return 0.0

    text_term_set = set(text_terms)
    matched_terms = query_terms.intersection(text_term_set)
    coverage = len(matched_terms) / len(query_terms)
    density = sum(1 for term in text_terms if term in query_terms) / len(text_terms)
    phrase_boost = 0.15 if query.strip().lower() in text.lower() else 0.0
    return min(1.0, (coverage * 0.8) + (density * 0.2) + phrase_boost)


def _tokenize(value: str) -> list[str]:
    return [_normalize_token(token) for token in TOKEN_PATTERN.findall(value.lower())]


def _normalize_token(token: str) -> str:
    for suffix in ("ing", "ed", "es", "s"):
        if len(token) > len(suffix) + 3 and token.endswith(suffix):
            return token[: -len(suffix)]
    return token


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left.intersection(right)) / len(left.union(right))


def _normalize_vector_score(score: float) -> float:
    if score < 0:
        return max(0.0, min((score + 1.0) / 2.0, 1.0))
    return max(0.0, min(score, 1.0))
