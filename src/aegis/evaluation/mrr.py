"""
Mean Reciprocal Rank.

Pure function, following the same one-metric-per-file convention as
``recall.py``/``hit_rate.py``. Named ``mrr`` (rather than ``mean_reciprocal_rank``)
to match the acronym already used throughout ``CLAUDE.md``/``current_plan.md``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


def mrr(retrieved_codes: Sequence[str], relevant_codes: set[str]) -> float:
    """Reciprocal rank of the first relevant code in ``retrieved_codes``, or 0.0 if none appear."""
    for rank, code in enumerate(retrieved_codes, start=1):
        if code in relevant_codes:
            return 1.0 / rank
    return 0.0
