"""
ContextAssembler

Implements application_service_contracts/context_assembler.md.

Owns construction of the immutable ``ReasoningContext`` runtime
artifact — the deterministic boundary between semantic retrieval
evidence (``RetrievalResult``) and probabilistic AI reasoning.

This module intentionally has no dependency on SQLite, Redis, Upstash
Vector, embedding providers, LLM providers, CrewAI, LangGraph, or
prompt templates. It operates only on already-produced domain
artifacts (``NormalizedClinicalNote``, ``RetrievalResult``) and a
deterministic ``ContextAssemblyPolicy``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from pydantic import Field

from aegis.models.base import DomainModel
from aegis.models.reasoning_context import CandidateConcept, ReasoningContext

if TYPE_CHECKING:
    from aegis.models.normalized_clinical_note import NormalizedClinicalNote
    from aegis.models.retrieval import RetrievalCandidate, RetrievalResult

DEFAULT_MAX_CANDIDATES = 5


class ContextAssemblyPolicy(DomainModel):
    """
    Deterministic configuration for candidate bounding.

    ``max_candidates`` caps how many ``CandidateConcept`` entries a
    ``ReasoningContext`` may carry — the token/context budgeting knob
    the contract assigns to ``ContextAssembler`` (candidate count
    limits), kept as explicit configuration rather than a hardcoded
    constant so it can be tuned without touching assembly logic.
    """

    max_candidates: int = Field(gt=0, default=DEFAULT_MAX_CANDIDATES)


class ContextAssembler(ABC):
    """
    Application service boundary that converts a ``NormalizedClinicalNote``
    and its ``RetrievalResult`` into the immutable ``ReasoningContext``
    consumed by ``ClinicalReasoningService``.

    Performs no clinical reasoning, ranking, prompt construction, or
    infrastructure access — see
    application_service_contracts/context_assembler.md for the full
    boundary.
    """

    @abstractmethod
    def assemble(
        self,
        retrieval_result: RetrievalResult,
        normalized_note: NormalizedClinicalNote,
    ) -> ReasoningContext:
        """Produce the immutable ``ReasoningContext`` for these artifacts."""
        raise NotImplementedError


class DefaultContextAssembler(ContextAssembler):
    """
    Concrete ``ContextAssembler`` implementation.

    Stateless aside from its injected ``ContextAssemblyPolicy``: given
    the same ``RetrievalResult``, ``NormalizedClinicalNote``, and
    policy, it always produces the same ``ReasoningContext``.
    """

    def __init__(self, policy: ContextAssemblyPolicy | None = None) -> None:
        self._policy = policy or ContextAssemblyPolicy()

    def assemble(
        self,
        retrieval_result: RetrievalResult,
        normalized_note: NormalizedClinicalNote,
    ) -> ReasoningContext:
        if retrieval_result.normalized_note != normalized_note:
            raise ValueError(
                "retrieval_result was not produced from the given normalized_note."
            )

        return ReasoningContext(
            case_id=normalized_note.clinical_note.case_id,
            anonymized_clinical_text=normalized_note.normalized_text,
            candidates=self._select_candidates(retrieval_result.candidates),
        )

    def _select_candidates(
        self, candidates: list[RetrievalCandidate]
    ) -> list[CandidateConcept]:
        """
        Deterministically curate retrieval candidates for reasoning.

        Preserves retrieval order (no clinical ranking), drops
        duplicate ICD codes defensively — ``RetrievalResult`` already
        enforces uniqueness, but this boundary does not rely on that
        invariant holding upstream — and truncates to
        ``policy.max_candidates`` before projecting each survivor down
        to its ``CandidateConcept`` (dropping ``similarity_score`` and
        ``retrieval_metadata``).
        """
        seen_codes: set[str] = set()
        deduplicated: list[RetrievalCandidate] = []
        for candidate in candidates:
            if candidate.icd_code in seen_codes:
                continue
            seen_codes.add(candidate.icd_code)
            deduplicated.append(candidate)

        bounded = deduplicated[: self._policy.max_candidates]

        return [
            CandidateConcept(
                icd_code=candidate.icd_code,
                title=candidate.title,
                hierarchy_context=candidate.hierarchy_context,
                semantic_representation=candidate.semantic_representation,
            )
            for candidate in bounded
        ]
