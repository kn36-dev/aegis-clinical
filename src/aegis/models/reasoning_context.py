# ReasoningContext
#
# Shape defined by runtime_domain_contracts/reasoning_context.md (authoritative).
#
# Owns
#
# case_id (reference to the originating ClinicalNote, for traceability only)
# anonymized_clinical_text (the deterministic, PHI-scrubbed observation to reason over)
# candidates (bounded ICD-11 CandidateConcept collection, in retrieval order)
#
# Should not contain
#
# patient identity (patient_id, or any embedded ClinicalNote/NormalizedClinicalNote
# object that would carry it along)
# raw PHI
# similarity scores
# confidence values
# retrieval provider metadata / infrastructure details
# cache information
# previous physician decisions
# workflow state
# prompt instructions

from __future__ import annotations

from uuid import UUID

from aegis.models.base import ClinicalText, DomainModel, ICDCode


class CandidateConcept(DomainModel):
    """
    One ICD-11 taxonomy concept made available to reasoning.

    A deliberately narrower projection of ``RetrievalCandidate``: it
    carries only the clinical knowledge needed for comparison
    (``icd_code``, ``title``, ``hierarchy_context``,
    ``semantic_representation``) and drops every retrieval signal
    (``similarity_score``, ``retrieval_metadata``) so the reasoning
    system cannot see ranking evidence.
    """

    icd_code: ICDCode
    title: str
    hierarchy_context: str | None = None
    semantic_representation: str


class ReasoningContext(DomainModel):
    """
    Deterministic evidence package handed to probabilistic reasoning.

    Produced exclusively by ``ContextAssembler`` from a
    ``NormalizedClinicalNote`` and a ``RetrievalResult``. ``case_id`` is
    carried for explainability/audit only — deliberately not
    ``patient_id`` or the full ``ClinicalNote``/``NormalizedClinicalNote``,
    since either would smuggle patient identity past the reasoning
    boundary this contract exists to enforce.
    """

    case_id: UUID
    anonymized_clinical_text: ClinicalText
    candidates: list[CandidateConcept]
