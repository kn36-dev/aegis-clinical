# src/aegis/api/schemas/review.py
"""
API schemas for the physician review boundary
(GET/POST /api/v1/reviews/{thread_id}...).

These are HTTP boundary DTOs, not domain models: ``ReviewStateResponse``
translates the ``AegisWorkflowState`` a suspended-or-completed workflow
holds (read via ``graph.aget_state``) into what a review UI needs, and
``PhysicianDecisionSubmissionRequest`` translates an external physician's
decision into the ``aegis.services.clinical_decision_service
.PhysicianDecisionSubmission`` resume payload. Domain models
(``CodingRecommendation``, ``ClinicalDecision``, ``PhysicianDecisionSubmission``,
...) are never returned directly from, or accepted directly by, the router.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field

from aegis.models.base import ICDCode


class ReviewWorkflowStatus(str, Enum):
    """State of a single workflow run, as observed by the review router."""

    PENDING_REVIEW = "pending_review"
    COMPLETED = "completed"


class RecommendedICDCodeResponse(BaseModel):
    """One AI-recommended ICD-11 code, as surfaced to the review UI."""

    icd_code: ICDCode
    justification: str
    model_confidence: float
    supporting_findings: list[str]
    conflicting_findings: list[str]


class ApprovedICDCodeResponse(BaseModel):
    icd_code: ICDCode
    disposition: str


class ReviewStateResponse(BaseModel):
    """
    Current pending-or-completed state of a workflow's review boundary.

    ``status == PENDING_REVIEW`` means the workflow is suspended at the
    ``human_review_pending`` interrupt; ``recommendation_id``,
    ``reasoning_summary``, ``normalized_note_text``, and
    ``recommended_icd_codes`` are the ``CodingRecommendation``/
    ``NormalizedClinicalNote`` content a physician needs to decide, and
    ``decision_id``/``approved_icd_codes`` are absent. ``status ==
    COMPLETED`` means a ``ClinicalDecision`` already exists (this
    workflow's review was already resolved); ``decision_id`` and
    ``approved_icd_codes`` are present and the pending-review fields are
    absent.

    ``normalized_note_text`` is ``NormalizedClinicalNote.normalized_text``
    -- already PHI-anonymized by ``NormalizationService`` (via
    ``PHIAnonymizer``) before it ever reaches graph state, never the raw
    physician-authored note -- so exposing it here does not cross the
    anonymization boundary the deterministic pipeline already enforces.
    """

    workflow_id: UUID
    case_id: UUID
    status: ReviewWorkflowStatus

    recommendation_id: UUID | None = None
    reasoning_summary: str | None = None
    normalized_note_text: str | None = None
    recommended_icd_codes: list[RecommendedICDCodeResponse] | None = None

    decision_id: UUID | None = None
    approved_icd_codes: list[ApprovedICDCodeResponse] | None = None


class PendingReviewSummaryResponse(BaseModel):
    """
    One entry in the review queue (``GET /api/v1/reviews``).

    Deliberately thin -- carries only what a physician needs to select a
    case to open, not the recommendation content ``ReviewStateResponse``
    already exposes at ``GET /api/v1/reviews/{thread_id}``. ``status`` is
    always ``PENDING_REVIEW`` here: this listing never surfaces completed
    cases (see ``aegis.api.routers.review.list_pending_reviews``).
    """

    workflow_id: UUID
    case_id: UUID
    patient_id: UUID
    status: ReviewWorkflowStatus
    submitted_at: datetime


class PhysicianDecisionSubmissionRequest(BaseModel):
    """
    External physician review submission for a suspended workflow.

    Only the physician's final set of approved ICD-11 codes is accepted
    here -- case/recommendation/patient/normalization identity is read
    from the workflow's own suspended state (keyed by ``thread_id``), not
    trusted from the request, so a submission cannot be misattributed to
    the wrong case. Whether each code counts as accepted/added/removed/
    modified is decided by ``ClinicalDecisionService`` once the workflow
    resumes, never by this schema or the router.
    """

    selected_icd_codes: list[ICDCode] = Field(default_factory=list)


class ReviewDecisionResponse(BaseModel):
    """Result of resuming a suspended workflow with a physician decision."""

    workflow_id: UUID
    case_id: UUID
    decision_id: UUID
    approved_icd_codes: list[ApprovedICDCodeResponse]
