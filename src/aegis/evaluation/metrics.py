"""
Retrieval metric facade.

Each metric's algorithm lives in its own single-purpose module
(``recall.py``, ``hit_rate.py``, ``mrr.py`` -- ``precision.py`` and
``ndcg.py`` remain the deferred, not-yet-implemented stubs they already
were; see ``docs/testing_and_evaluations.md``'s roadmap). This module is
the single import surface ``retrieval_eval.py`` uses, plus the small
cross-case aggregation helpers (``mean``, ``compute_case_metrics``) that
don't belong to any one metric.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from aegis.evaluation.hit_rate import hit_rate_at_k
from aegis.evaluation.mrr import mrr
from aegis.evaluation.recall import recall_at_k

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

__all__ = ["recall_at_k", "hit_rate_at_k", "mrr", "mean", "CaseMetrics", "compute_case_metrics"]


def mean(values: Iterable[float]) -> float:
    """Arithmetic mean of ``values``, or 0.0 if empty."""
    values_list = list(values)
    if not values_list:
        return 0.0
    return sum(values_list) / len(values_list)


@dataclass(frozen=True)
class CaseMetrics:
    """Recall@K/Hit Rate@K (per configured K) and MRR for one evaluated case."""

    recall_at_k: dict[int, float]
    hit_rate_at_k: dict[int, float]
    mrr: float


def compute_case_metrics(
    retrieved_codes: Sequence[str],
    relevant_codes: set[str],
    top_k_values: Sequence[int],
) -> CaseMetrics:
    """Compute Recall@K/Hit Rate@K for every configured K, plus MRR, for one case."""
    return CaseMetrics(
        recall_at_k={k: recall_at_k(retrieved_codes, relevant_codes, k) for k in top_k_values},
        hit_rate_at_k={k: hit_rate_at_k(retrieved_codes, relevant_codes, k) for k in top_k_values},
        mrr=mrr(retrieved_codes, relevant_codes),
    )
