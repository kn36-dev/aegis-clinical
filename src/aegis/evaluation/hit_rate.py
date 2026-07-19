"""
Hit Rate@K.

Pure function, following the same one-metric-per-file convention as
``recall.py``/``mrr.py``. Distinct from Recall@K: Recall@K measures what
fraction of all relevant codes were found, Hit Rate@K measures only
whether *any* relevant code was found at all in the top ``k``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


def hit_rate_at_k(retrieved_codes: Sequence[str], relevant_codes: set[str], k: int) -> float:
    """1.0 if any ``relevant_codes`` member appears in the top ``k`` retrieved codes, else 0.0."""
    if not relevant_codes:
        return 0.0

    top_k = set(retrieved_codes[:k])
    return 1.0 if top_k & relevant_codes else 0.0
