"""
ClinicalNoteService

Implements application_service_contracts/clinical_note_service.md.

Owns construction and lifecycle establishment of the immutable
``ClinicalNote`` domain artifact — the first trusted boundary in AEGIS,
where an external clinical submission becomes a stable, identifiable
artifact that every downstream deterministic and probabilistic process
derives from.

This module intentionally has no dependency on SQLite, FastAPI,
LangGraph, CrewAI, Redis, or Upstash Vector. Persistence is expressed
only through the ``ClinicalNoteRepository`` protocol; concrete storage
adapters live elsewhere and are injected by the caller.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Protocol
from uuid import UUID, uuid4

from aegis.models.clinical_note import ClinicalNote

if TYPE_CHECKING:
    from aegis.models.workflow_commands import ClinicalNoteSubmission


class IdentifierGenerator(Protocol):
    """Generates the unique identity assigned to a new ``ClinicalNote``."""

    def generate(self) -> UUID: ...


class Clock(Protocol):
    """Supplies the creation timestamp assigned to a new ``ClinicalNote``."""

    def now(self) -> datetime: ...


class UUID4IdentifierGenerator:
    """Default identifier generator, using random UUID4 values."""

    def generate(self) -> UUID:
        return uuid4()


class SystemClock:
    """Default clock, using the current UTC wall-clock time."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class ClinicalNoteRepository(Protocol):
    """
    Persistence boundary for ``ClinicalNote``.

    ``ClinicalNoteService`` depends on this abstraction rather than on
    any storage technology, so the storage mechanism can change without
    affecting the service.
    """

    def save(self, clinical_note: ClinicalNote) -> None: ...


class ClinicalNoteService(ABC):
    """
    Application service boundary that converts an external clinical
    submission into the immutable ``ClinicalNote`` source artifact.

    Does not normalize, anonymize, interpret, classify, or orchestrate
    workflow — see application_service_contracts/clinical_note_service.md
    for the full boundary.
    """

    @abstractmethod
    def create_clinical_note(self, submission: ClinicalNoteSubmission) -> ClinicalNote:
        """Construct, persist, and return a new immutable ``ClinicalNote``."""
        raise NotImplementedError


class DefaultClinicalNoteService(ClinicalNoteService):
    """
    Concrete ``ClinicalNoteService`` implementation.

    Dependencies are injected so the service remains deterministic and
    independently testable: given the same submission, identifier
    generation strategy, and clock, it always produces the same type of
    immutable artifact.
    """

    def __init__(
        self,
        repository: ClinicalNoteRepository,
        identifier_generator: IdentifierGenerator | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._repository = repository
        self._identifier_generator = identifier_generator or UUID4IdentifierGenerator()
        self._clock = clock or SystemClock()

    def create_clinical_note(self, submission: ClinicalNoteSubmission) -> ClinicalNote:
        clinical_note = ClinicalNote(
            case_id=self._identifier_generator.generate(),
            patient_id=submission.patient_id,
            content_reference=submission.content_reference,
            created_at=self._clock.now(),
        )

        self._repository.save(clinical_note)

        return clinical_note
