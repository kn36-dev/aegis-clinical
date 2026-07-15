# CodingRecommendation
#
# Shape defined by runtime_domain_contracts/coding_recommendation.md (authoritative).
#
# Owns
#
# recommendation_id
# case_id (reference to the originating ReasoningContext, for traceability only)
# recommendations (per-code structured findings, justification, model confidence)
# reasoning_summary
# evidence_reference (EvidenceReference — see below)
# metadata (model/prompt/temperature/timestamp — reproducibility, not clinical truth)
#
# Should not contain
#
# raw clinical text
# patient identity
# ReasoningContext, RetrievalResult, or RetrievalCandidate/CandidateConcept
# objects (referenced by identifier via EvidenceReference, never embedded)
# retrieval infrastructure details (similarity scores, vector ids, cache keys)
# physician decisions
# persisted/authoritative ICD codes
#
# Note on scope: the contract's "Recommendation Structure" describes each
# recommendation as carrying a "RetrievalCandidate reference". By the time
# reasoning happens, ClinicalReasoningService only has a ReasoningContext
# (a ContextAssembler-curated projection of RetrievalResult), which exposes
# CandidateConcept rather than RetrievalCandidate — RetrievalResult and
# RetrievalCandidate are not available at this boundary at all (see
# runtime_domain_contracts/coding_recommendation.md's Architectural
# Boundary). Per-recommendation, `icd_code` is used as that reference —
# mirroring how ClinicalDecision's ApprovedICDClassification references a
# recommendation by icd_code rather than embedding the recommendation object
# itself. At the CodingRecommendation level, `evidence_reference` (see
# `EvidenceReference` below) additionally records the full set of ICD-11
# codes the ReasoningContext made available, not just the ones recommended
# — the "which reasoning context was used" axis of traceability, kept as an
# identifier list rather than by embedding ReasoningContext itself. The
# invariant "must only recommend ICD-11 codes present in
# ReasoningContext.candidates" is enforced by ClinicalReasoningService
# (checked at construction time), not by this model, since the model has no
# independent access to the ReasoningContext it was produced from.
#
# Note on findings: the contract asks for "structured observations rather
# than free-form narrative whenever possible". A list of discrete finding
# strings is the minimal structured shape that satisfies this without
# inventing a richer Finding sub-model the contract does not ask for.

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from aegis.models.base import DomainModel, ICDCode


class ICDCodeRecommendation(DomainModel):
    """
    One AI-recommended ICD-11 code, with structured supporting evidence.

    ``model_confidence`` is the reasoning model's own self-assessment
    only — it must never be interpreted as clinical confidence,
    diagnostic probability, or workflow authority.
    """

    icd_code: ICDCode
    supporting_findings: list[str] = Field(default_factory=list)
    conflicting_findings: list[str] = Field(default_factory=list)
    justification: str
    model_confidence: float = Field(ge=0.0, le=1.0)


class ReasoningMetadata(DomainModel):
    """
    Operational metadata enabling reproducible (not deterministic)
    reasoning environments, per the contract's Determinism Classification.
    """

    model_name: str
    prompt_version: str
    temperature: float
    generated_at: datetime


class EvidenceReference(DomainModel):
    """
    Lightweight, identifier-only pointer back to the bounded evidence a
    ``CodingRecommendation`` was reasoned over.

    Carries the ICD-11 codes present in the originating
    ``ReasoningContext.candidates`` — a superset of, or equal to, the
    codes actually recommended — so a reviewer can answer "why was this
    recommended, and out of what alternatives?" without
    ``CodingRecommendation`` embedding ``ReasoningContext``,
    ``RetrievalResult``, or ``RetrievalCandidate``/``CandidateConcept``
    objects. ``case_id`` (already a ``CodingRecommendation`` field)
    identifies the clinical case; this reference identifies the
    candidate evidence that reasoning pass had available.
    """

    candidate_icd_codes: list[ICDCode]


class CodingRecommendation(DomainModel):
    """
    Advisory, AI-generated ICD-11 coding recommendation.

    Produced exclusively by ``ClinicalReasoningService`` from a
    ``ReasoningContext``. Not a clinical fact, not persisted as clinical
    truth, and never itself a ``ClinicalDecision`` — it exists solely to
    support physician review.
    """

    recommendation_id: UUID
    case_id: UUID
    recommendations: list[ICDCodeRecommendation]
    reasoning_summary: str
    evidence_reference: EvidenceReference
    metadata: ReasoningMetadata
