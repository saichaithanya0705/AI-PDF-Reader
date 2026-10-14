import math

import pytest

from backend.app.evals.metrics import (
    answer_term_recall,
    dedupe_pages,
    hit_at_k,
    ndcg_at_k,
    percentile,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)

A1, A2, B1, B2 = ("a", 1), ("a", 2), ("b", 1), ("b", 2)


def test_dedupe_keeps_first_occurrence_order():
    assert dedupe_pages([A1, A1, B1, A1, A2]) == [A1, B1, A2]


def test_rank_metrics_on_known_ranking():
    ranked = [B2, A1, B1]
    relevant = {A1, B1}

    assert hit_at_k(ranked, relevant, 1) == 0.0
    assert hit_at_k(ranked, relevant, 2) == 1.0
    assert reciprocal_rank(ranked, relevant, 3) == 0.5
    assert recall_at_k(ranked, relevant, 2) == 0.5
    assert recall_at_k(ranked, relevant, 3) == 1.0
    assert precision_at_k(ranked, relevant, 3) == pytest.approx(2 / 3)
    expected_dcg = 1 / math.log2(3) + 1 / math.log2(4)
    expected_idcg = 1 / math.log2(2) + 1 / math.log2(3)
    assert ndcg_at_k(ranked, relevant, 3) == pytest.approx(expected_dcg / expected_idcg)


def test_perfect_and_empty_rankings():
    assert ndcg_at_k([A1, B1], {A1, B1}, 5) == pytest.approx(1.0)
    assert ndcg_at_k([], {A1}, 5) == 0.0
    assert reciprocal_rank([B2], {A1}, 5) == 0.0


def test_answer_term_recall_is_case_insensitive():
    assert answer_term_recall("ATP Synthase uses a proton gradient", ["atp synthase", "proton", "NADH"]) == pytest.approx(2 / 3)
    assert answer_term_recall("anything", []) == 0.0


def test_percentile_interpolates():
    assert percentile([10, 20, 30, 40], 50) == 25
    assert percentile([5], 95) == 5
    assert percentile([], 95) == 0.0
