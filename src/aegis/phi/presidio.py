"""
Presidio-backed ``PHIAnonymizer`` implementation.

This module is the only place in the codebase permitted to import
``presidio_analyzer`` / ``presidio_anonymizer`` / spaCy. Presidio is an
infrastructure implementation detail behind the ``PHIAnonymizer``
application boundary (``aegis.phi.base``) — ``NormalizationService``
depends only on that abstraction and never on this module directly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

from aegis.phi.base import PHIAnonymizer

if TYPE_CHECKING:
    from collections.abc import Sequence

# Entity types relevant to physician-authored clinical narratives.
# `None` (the default) defers to Presidio's full set of registered
# recognizers instead of this fixed list.
DEFAULT_ENTITIES: tuple[str, ...] = (
    "PERSON",
    "DATE_TIME",
    "PHONE_NUMBER",
    "EMAIL_ADDRESS",
    "LOCATION",
    "US_SSN",
    "MEDICAL_LICENSE",
)


class PresidioPHIAnonymizer(PHIAnonymizer):
    """
    PHI anonymizer backed by Presidio's spaCy-based analyzer.

    Deterministic for a fixed model + entity configuration: identical
    input text always produces identical output, since detection uses
    no sampling and no external state.
    """

    def __init__(
        self,
        entities: Sequence[str] | None = DEFAULT_ENTITIES,
        language: str = "en",
    ) -> None:
        self._analyzer = AnalyzerEngine()
        self._anonymizer = AnonymizerEngine()  # type: ignore[no-untyped-call]
        self._entities = list(entities) if entities is not None else None
        self._language = language

    def anonymize(self, text: str) -> str:
        if not text:
            return text

        analyzer_results = self._analyzer.analyze(
            text=text,
            entities=self._entities,
            language=self._language,
        )

        anonymized_result = self._anonymizer.anonymize(
            text=text,
            # presidio-analyzer and presidio-anonymizer each declare their
            # own nominally distinct (structurally identical) RecognizerResult.
            analyzer_results=analyzer_results,  # type: ignore[arg-type]
        )

        return anonymized_result.text
