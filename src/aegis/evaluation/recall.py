"""
Recall@K.

Pure function -- no I/O, no service dependencies. Operates only on a
ranked list of retrieved ICD-11 codes and a ground-truth relevant-code
set, so it is unit-testable in isolation from every real service this
package otherwise orchestrates.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


def recall_at_k(retrieved_codes: Sequence[str], relevant_codes: set[str], k: int) -> float:
    """
    Fraction of ``relevant_codes`` present in the top ``k`` retrieved codes.

    Returns 0.0 when ``relevant_codes`` is empty (nothing to recall) rather
    than raising or dividing by zero.
    """
    if not relevant_codes:
        return 0.0

    top_k = set(retrieved_codes[:k])
    return len(top_k & relevant_codes) / len(relevant_codes)
