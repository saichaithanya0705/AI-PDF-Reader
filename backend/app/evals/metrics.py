"""Information-retrieval metrics for the RAG evals.

Relevance is judged at (document_id, page) granularity because that is what the
reader UI shows and navigates to. Several chunks can come from one page, so
rankings are de-duplicated by page before scoring: a page that appears twice
must not count as two hits.
"""
from __future__ import annotations

import math
from typing import Iterable, List, Sequence, Set, Tuple

PageKey = Tuple[str, int]


def dedupe_pages(ranked: Iterable[PageKey]) -> List[PageKey]:
    """Keep the first occurrence of each page, preserving rank order."""
    seen: Set[PageKey] = set()
    unique: List[PageKey] = []
    for key in ranked:
        if key not in seen:
            seen.add(key)
            unique.append(key)
    return unique


def hit_at_k(ranked: Sequence[PageKey], relevant: Set[PageKey], k: int) -> float:
    return 1.0 if any(key in relevant for key in ranked[:k]) else 0.0


def recall_at_k(ranked: Sequence[PageKey], relevant: Set[PageKey], k: int) -> float:
    if not relevant:
        return 0.0
    return len(relevant.intersection(ranked[:k])) / len(relevant)


def precision_at_k(ranked: Sequence[PageKey], relevant: Set[PageKey], k: int) -> float:
    if k <= 0:
        return 0.0
    return sum(1 for key in ranked[:k] if key in relevant) / k


def reciprocal_rank(ranked: Sequence[PageKey], relevant: Set[PageKey], k: int) -> float:
    for position, key in enumerate(ranked[:k], start=1):
        if key in relevant:
            return 1.0 / position
    return 0.0


def ndcg_at_k(ranked: Sequence[PageKey], relevant: Set[PageKey], k: int) -> float:
    """Binary-gain nDCG: 1 for a relevant page, 0 otherwise."""
    dcg = sum(
        1.0 / math.log2(position + 1)
        for position, key in enumerate(ranked[:k], start=1)
        if key in relevant
    )
    ideal_hits = min(len(relevant), k)
    idcg = sum(1.0 / math.log2(position + 1) for position in range(1, ideal_hits + 1))
    return dcg / idcg if idcg > 0 else 0.0


def answer_term_recall(context: str, answer_terms: Sequence[str]) -> float:
    """Share of expected answer terms present in the retrieved context.

    A cheap, LLM-free proxy for whether generation *could* answer correctly:
    if the facts are not in the context, the model can only hallucinate them.
    """
    if not answer_terms:
        return 0.0
    haystack = context.lower()
    return sum(1 for term in answer_terms if term.lower() in haystack) / len(answer_terms)


def percentile(values: Sequence[float], pct: float) -> float:
    """Linear-interpolated percentile (pct in 0..100)."""
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    rank = (pct / 100) * (len(ordered) - 1)
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return float(ordered[lower])
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (rank - lower)


def mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0
