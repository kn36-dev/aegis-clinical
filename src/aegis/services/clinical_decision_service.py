"""
ClinicalDecisionService

Implements application_service_contracts/clinical_decision_service.md.

Owns the physician authority boundary of AEGIS: given the ``CodingRecommendation``
previously produced by ``ClinicalReasoningService`` and a physician's reviewed
final ICD-11 selections, construct the immutable ``ClinicalDecision`` that
represents institutional clinical truth. AI recommendations remain advisory —
this service never treats them as truth, and the physician is never asked to
compute business classifications (accepted / added); those are derived
deterministically by this service, and only from what the physician actually
approved (see Approved-Codes Boundary and Modification Boundary below).

This module intentionally has no dependency on SQLite, Redis, Upstash Vector,
embedding providers, LLM providers, CrewAI, or LangGraph. ICD-11 code
existence is expressed only through the ``ICDCodeValidator`` abstraction;
concrete taxonomy-backed implementations are injected by the caller.

Architectural note on "referenced case/recommendation exists" and "workflow
state is correct" (application_service_contracts/clinical_decision_service.md,
Primary Responsibilities #1): this service has no repository or workflow
access, so it cannot perform an existence lookup itself. It instead trusts
that the ``CodingRecommendation`` handed to it by the caller was already
resolved from a real, existing case/recommendation, and defensively verifies
*referential consistency* between that object and the physician submission
(matching ``case_id`` and ``recommendation_id``) — i.e. that this submission
is actually reviewing the recommendation it claims to review.

Approved-Codes Boundary: ``ClinicalDecision.approved_icd_codes`` records only
codes the physician actually approved for the encounter — i.e. exactly
``submission.selected_icd_codes``, classified ``ACCEPTED`` (also present in
the AI recommendation) or ``ADDED`` (not present in it). AI codes the
physician did not select are rejected, not approved, and are therefore never
placed in ``approved_icd_codes`` — consistent with its name. This service
does not currently record a separate "rejected recommendations" trace
anywhere, because the frozen ``ClinicalDecision`` model
(``src/aegis/models/clinical_decision.py``) has no field for it and no
reference back to the originating ``CodingRecommendation`` (no
``recommendation_id``). An auditor who needs the rejected set must separately
hold the original ``CodingRecommendation`` (correlated by ``case_id``) and
diff its ``recommendations`` against ``approved_icd_codes`` themselves. This
is a real gap in the domain contract, not a decision this service can resolve
on its own — see the class docstring below and the contract review notes.

Modification Boundary: ``RecommendationDisposition.MODIFIED`` is a valid
value on the frozen ``ClinicalDecision`` model, but this service never
produces it. Distinguishing "the physician replaced AI code A with code B"
from "the physician independently rejected A and separately added B" requires
an explicit physician-declared mapping, and ``PhysicianDecisionSubmission``
carries only a flat list of final codes — the contract's Physician Input
Boundary explicitly keeps the physician from submitting business
classifications. Pairing a same-submission removal with a same-submission
addition would be *this service* inferring physician intent that was never
stated, which is exactly what the physician-as-sole-authority principle
forbids. Modification therefore remains unsupported: any code not in the AI
recommendation is classified ``ADDED``, full stop, until a future contract
revision defines an explicit way for the physician (or the review UI) to
declare a replacement.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from aegis.models.base import DomainModel, ICDCode
from aegis.models.clinical_decision import (
    ApprovedICDClassification,
    ClinicalDecision,
    RecommendationDisposition,
)
from aegis.services.clinical_note_service import SystemClock, UUID4IdentifierGenerator

if TYPE_CHECKING:
    from aegis.models.coding_recommendation import CodingRecommendation
    from aegis.services.clinical_note_service import Clock, IdentifierGenerator


class PhysicianDecisionSubmission(DomainModel):
    """
    Untrusted physician review of a ``CodingRecommendation``.

    The physician submits only the final approved ICD-11 codes for the
    encounter — never explanations or business classifications (see the
    contract's Physician Input Boundary). ``recommendation_id`` identifies
    which reasoning pass is being reviewed; ``case_id`` and
    ``patient_id_reference`` identify the encounter and patient boundary.
    ``normalization_version`` traces the decision back to the deterministic
    ``NormalizedClinicalNote`` that produced the evidence reasoned over
    (see ``ClinicalDecision``'s Normalization Traceability).
    """

    case_id: UUID
    recommendation_id: UUID
    patient_id_reference: UUID
    normalization_version: str
    selected_icd_codes: list[ICDCode]


class ICDCodeValidator(Protocol):
    """
    Boundary to ICD-11 taxonomy validity checking.

    ``ClinicalDecisionService`` depends on this abstraction rather than on
    any taxonomy storage technology (SQLite, in-memory fixture, ...), so
    the validation mechanism can change without affecting the service.
    """

    def is_valid(self, icd_code: str) -> bool: ...


class ClinicalDecisionService(ABC):
    """
    Application service boundary that transforms a physician's reviewed
    outcome of a ``CodingRecommendation`` into the immutable
    ``ClinicalDecision`` representing institutional clinical truth.

    Performs no persistence, clinical reasoning, or workflow routing — see
    application_service_contracts/clinical_decision_service.md for the full
    boundary.
    """

    @abstractmethod
    def decide(
        self,
        recommendation: CodingRecommendation,
        submission: PhysicianDecisionSubmission,
    ) -> ClinicalDecision:
        """Construct the ``ClinicalDecision`` for this physician submission."""
        raise NotImplementedError


class DefaultClinicalDecisionService(ClinicalDecisionService):
    """
    Concrete ``ClinicalDecisionService`` implementation.

    Dependencies are injected so the service remains deterministic and
    independently testable: given the same ``CodingRecommendation``,
    submission, ICD validity rules, identifier generation strategy, and
    clock, it always produces the same ``ClinicalDecision``.

    See the module docstring's Approved-Codes Boundary and Modification
    Boundary for why ``approved_icd_codes`` only ever carries ``ACCEPTED``
    or ``ADDED`` entries: rejected AI codes are excluded rather than
    recorded as ``REMOVED`` (the frozen model has no other place to put
    them), and ``MODIFIED`` is never inferred from a same-submission
    removal+addition, since doing so would attribute physician intent that
    was never explicitly stated.
    """

    def __init__(
        self,
        icd_code_validator: ICDCodeValidator,
        identifier_generator: IdentifierGenerator | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._icd_code_validator = icd_code_validator
        self._identifier_generator = identifier_generator or UUID4IdentifierGenerator()
        self._clock = clock or SystemClock()

    def decide(
        self,
        recommendation: CodingRecommendation,
        submission: PhysicianDecisionSubmission,
    ) -> ClinicalDecision:
        self._validate_references(recommendation, submission)
        selected_codes = self._validate_selection(submission.selected_icd_codes)

        return ClinicalDecision(
            decision_id=self._identifier_generator.generate(),
            case_id=submission.case_id,
            patient_id_reference=submission.patient_id_reference,
            approved_icd_codes=self._classify(recommendation, selected_codes),
            normalization_version=submission.normalization_version,
            created_at=self._clock.now(),
        )

    @staticmethod
    def _validate_references(
        recommendation: CodingRecommendation,
        submission: PhysicianDecisionSubmission,
    ) -> None:
        if submission.case_id != recommendation.case_id:
            raise ValueError(
                "Physician submission references clinical case "
                f"{submission.case_id}, but the supplied CodingRecommendation "
                f"belongs to case {recommendation.case_id}."
            )
        if submission.recommendation_id != recommendation.recommendation_id:
            raise ValueError(
                "Physician submission references recommendation "
                f"{submission.recommendation_id}, but the supplied "
                f"CodingRecommendation has id {recommendation.recommendation_id}."
            )

    def _validate_selection(self, selected_icd_codes: list[str]) -> list[str]:
        if len(set(selected_icd_codes)) != len(selected_icd_codes):
            raise ValueError("Physician submission contains duplicate ICD-11 codes.")

        for icd_code in selected_icd_codes:
            if not self._icd_code_validator.is_valid(icd_code):
                raise ValueError(f"{icd_code!r} is not a valid ICD-11 code.")

        return selected_icd_codes

    @staticmethod
    def _classify(
        recommendation: CodingRecommendation,
        selected_codes: list[str],
    ) -> list[ApprovedICDClassification]:
        """
        Classify each physician-approved code as ``ACCEPTED`` (also
        AI-recommended) or ``ADDED`` (not AI-recommended). Only codes in
        ``selected_codes`` are classified — an AI code the physician did
        not select is rejected, not approved, and never appears in the
        result (see the module docstring's Approved-Codes Boundary).
        ``MODIFIED`` is never produced (see Modification Boundary).
        """
        ai_codes = {item.icd_code for item in recommendation.recommendations}

        return [
            ApprovedICDClassification(
                icd_code=code,
                disposition=(
                    RecommendationDisposition.ACCEPTED
                    if code in ai_codes
                    else RecommendationDisposition.ADDED
                ),
            )
            for code in selected_codes
        ]
