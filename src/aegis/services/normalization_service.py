"""
NormalizationService

Implements application_service_contracts/normalization_service.md.

Owns construction of the immutable ``NormalizedClinicalNote`` runtime
artifact — the deterministic preprocessing boundary that stands between
the physician-authored ``ClinicalNote`` and every downstream semantic
operation (embedding, retrieval, context assembly, AI reasoning).

This module intentionally has no dependency on SQLite, Redis, Upstash
Vector, LLM providers, CrewAI, LangGraph, or Presidio/spaCy directly.
Content retrieval is expressed only through the
``ClinicalNoteContentRepository`` protocol, and PHI anonymization only
through the ``PHIAnonymizer`` abstraction (``aegis.phi.base``); concrete
adapters are injected by the caller.
"""

from __future__ import annotations

import unicodedata
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Protocol

from aegis.models.normalized_clinical_note import NormalizedClinicalNote
from aegis.services.clinical_note_service import SystemClock

if TYPE_CHECKING:
    from aegis.models.clinical_note import ClinicalNote
    from aegis.phi.base import PHIAnonymizer
    from aegis.services.clinical_note_service import Clock

NORMALIZATION_VERSION = "1.0"


class ClinicalNoteContentRepository(Protocol):
    """
    Retrieval boundary for the original clinical narrative referenced by
    ``ClinicalNote.content_reference``.

    ``NormalizationService`` depends on this abstraction rather than on
    any storage technology, so the storage mechanism (SQLite, encrypted
    blob store, ...) can change without affecting the service.
    """

    def get_content(self, content_reference: str) -> str: ...


class NormalizationRuleSet(Protocol):
    """
    Deterministic text-cleanup rules applied ahead of PHI anonymization.

    ``version`` identifies the exact rule set used to produce a given
    ``NormalizedClinicalNote``, so that historical artifacts remain
    traceable to the specification version that generated them.
    """

    version: str

    def apply(self, text: str) -> str: ...


class DeterministicNormalizationRuleSet:
    """
    Default ``NormalizationRuleSet``.

    Applies, in order:

    1. Unicode normalization (NFC)
    2. Whitespace normalization (collapse runs of whitespace, strip ends)

    Deliberately does not alter clinical wording — normalization must
    never change clinical meaning (e.g. "no fever" must never become
    "fever").
    """

    version = NORMALIZATION_VERSION

    def apply(self, text: str) -> str:
        normalized = unicodedata.normalize("NFC", text)
        return " ".join(normalized.split())


class NormalizationService(ABC):
    """
    Application service boundary that converts an immutable
    ``ClinicalNote`` into the immutable ``NormalizedClinicalNote``
    runtime artifact.

    Performs no clinical interpretation, diagnosis, coding, or
    probabilistic reasoning — see
    application_service_contracts/normalization_service.md for the full
    boundary.
    """

    @abstractmethod
    def normalize(self, clinical_note: ClinicalNote) -> NormalizedClinicalNote:
        """Produce the immutable ``NormalizedClinicalNote`` for ``clinical_note``."""
        raise NotImplementedError


class DefaultNormalizationService(NormalizationService):
    """
    Concrete ``NormalizationService`` implementation.

    Dependencies are injected so the service remains deterministic and
    independently testable: given the same ``ClinicalNote``, source
    content, rule set, and PHI anonymizer, it always produces the same
    ``NormalizedClinicalNote``.
    """

    def __init__(
        self,
        content_repository: ClinicalNoteContentRepository,
        phi_anonymizer: PHIAnonymizer,
        rule_set: NormalizationRuleSet | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._content_repository = content_repository
        self._phi_anonymizer = phi_anonymizer
        self._rule_set = rule_set or DeterministicNormalizationRuleSet()
        self._clock = clock or SystemClock()

    def normalize(self, clinical_note: ClinicalNote) -> NormalizedClinicalNote:
        original_text = self._content_repository.get_content(clinical_note.content_reference)
        cleaned_text = self._rule_set.apply(original_text)
        anonymized_text = self._phi_anonymizer.anonymize(cleaned_text)

        return NormalizedClinicalNote(
            clinical_note=clinical_note,
            normalized_text=anonymized_text,
            normalization_version=self._rule_set.version,
            created_at=self._clock.now(),
        )
