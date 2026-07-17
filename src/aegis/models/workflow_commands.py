from __future__ import annotations

from uuid import UUID

from aegis.models.base import DomainModel, ICDCode


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


class ClinicalNoteSubmission(DomainModel):
    """
    Untrusted external submission data, as provided by an ingress layer
    (FastAPI, a message consumer, batch ingestion, ...).

    This is deliberately not a ``ClinicalNote`` — it has no identity or
    creation timestamp yet. ``ClinicalNoteService`` is the only
    component that may turn a submission into a ``ClinicalNote``.
    """

    patient_id: UUID
    content_reference: str
