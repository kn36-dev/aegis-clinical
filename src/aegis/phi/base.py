"""
Abstract PHI anonymization boundary.

``PHIAnonymizer`` expresses the application-facing capability
"given clinical text, return anonymized clinical text" without
exposing any detail of the underlying detection/anonymization
technology (Presidio, spaCy, or otherwise) to callers such as
``NormalizationService``.

Concrete implementations include:

- Presidio (spaCy-backed NER + rule-based recognizers)
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class PHIAnonymizer(ABC):
    """
    Provider-agnostic PHI anonymization interface.

    Implementations must be deterministic: given identical input text,
    the same implementation must always return identical output.
    """

    @abstractmethod
    def anonymize(self, text: str) -> str:
        """Return ``text`` with protected health information anonymized."""
        raise NotImplementedError
