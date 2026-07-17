"""
FakeClinicalDecisionCacheRepository

Deterministic in-memory ``ClinicalDecisionCacheRepository`` adapter
(``aegis.services.cache_service``).

Lives under ``src/aegis`` rather than ``tests/`` because the demo
profile's composition root (``aegis.api.bootstrap.build_cache_repository``)
constructs it at application startup -- real shipped source cannot
depend on the ``tests/`` tree being importable at runtime. This is a
relocation of the class the test suite has used as a test double since
``tests/application/fakes.py`` re-exports it from here; the code is
unchanged, only its home moved so both the demo profile and tests share
one implementation instead of two.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aegis.models.clinical_decision import ClinicalDecision


class FakeClinicalDecisionCacheRepository:
    """In-memory stand-in for ``ClinicalDecisionCacheRepository``."""

    def __init__(self) -> None:
        self._store: dict[str, ClinicalDecision] = {}

    def get(self, cache_key: str) -> ClinicalDecision | None:
        return self._store.get(cache_key)

    def set(self, cache_key: str, decision: ClinicalDecision) -> None:
        self._store[cache_key] = decision
