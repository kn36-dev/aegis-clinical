"""
PersistenceService

Implements application_service_contracts/persistence_service.md.

Owns the durable-storage boundary of AEGIS: given the immutable
``ClinicalDecision`` produced by ``ClinicalDecisionService`` after
physician review, commit it to system-of-record storage through a
repository abstraction and report a deterministic ``PersistenceResult``.
It does not create clinical truth — it preserves truth already
established by physician approval.

This module intentionally has no dependency on SQLite, Redis, Upstash
Vector, embedding providers, LLM providers, CrewAI, or LangGraph.
Durable storage is expressed only through the ``ClinicalDecisionRepository``
protocol; concrete storage adapters are injected by the caller.

Scope note — Redis / cache projection (contract conflict): the contract's
"Projection Management" and "Redis Projection Boundary" sections describe
PersistenceService as also owning derived Redis projections and
coordinating cache repository operations ("determining when cache updates
occur", "coordinating cache repository operations"). This conflicts with
two higher-precedence sources (see CLAUDE.md's Architectural Authority
ordering): domain_contract_finalized.md's explicit service split
(PersistenceService writes SQLite; CacheService — already implemented at
``aegis/services/cache_service.py`` — separately consumes
``ClinicalDecision`` and writes Redis), and this task's explicit
instruction that PersistenceService must never call CacheService, update
Redis, or generate cache keys, with cache update instead deferred to
LangGraph orchestration after persistence succeeds. This implementation
therefore persists ``ClinicalDecision`` only and performs no
projection/cache work. The discrepancy in persistence_service.md was
surfaced to the user before implementation rather than silently resolved
or edited.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from aegis.models.base import DomainModel
from aegis.services.clinical_note_service import SystemClock

if TYPE_CHECKING:
    from aegis.models.clinical_decision import ClinicalDecision
    from aegis.services.clinical_note_service import Clock


class ClinicalDecisionRepository(Protocol):
    """
    Durable system-of-record persistence boundary for ``ClinicalDecision``.

    ``PersistenceService`` depends on this abstraction rather than on any
    storage technology, so the persistence mechanism can change without
    affecting the service.
    """

    def save(self, clinical_decision: ClinicalDecision) -> None: ...


class PersistenceResult(DomainModel):
    """
    Deterministic outcome of a durable persistence operation.

    Reports only that authoritative clinical truth was committed to
    system-of-record storage. It carries no cache/projection status —
    projection management belongs to ``CacheService``, not
    ``PersistenceService`` (see module docstring's scope note).
    """

    decision_id: UUID
    case_id: UUID
    persisted_at: datetime


class PersistenceService(ABC):
    """
    Application service boundary that durably commits an authoritative
    ``ClinicalDecision`` to system-of-record storage.

    Performs no clinical reasoning, cache/projection management, or
    workflow routing — see
    application_service_contracts/persistence_service.md for the full
    boundary (subject to the module docstring's scope note).
    """

    @abstractmethod
    def persist(self, clinical_decision: ClinicalDecision) -> PersistenceResult:
        """Durably commit ``clinical_decision`` and report the outcome."""
        raise NotImplementedError


class DefaultPersistenceService(PersistenceService):
    """
    Concrete ``PersistenceService`` implementation.

    Dependencies are injected so the service remains deterministic and
    independently testable: given the same ``ClinicalDecision``,
    repository, and clock, it always performs the same persistence
    behavior. Repository failures are not caught — they propagate to the
    caller unchanged, so that no partial or false-success outcome is ever
    reported (contract's Failure Handling / Durable Storage Failure
    section: "No authoritative truth should be considered persisted").
    """

    def __init__(
        self,
        repository: ClinicalDecisionRepository,
        clock: Clock | None = None,
    ) -> None:
        self._repository = repository
        self._clock = clock or SystemClock()

    def persist(self, clinical_decision: ClinicalDecision) -> PersistenceResult:
        self._repository.save(clinical_decision)

        return PersistenceResult(
            decision_id=clinical_decision.decision_id,
            case_id=clinical_decision.case_id,
            persisted_at=self._clock.now(),
        )
