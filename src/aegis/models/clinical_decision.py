# ClinicalDecision
#
# Shape defined by runtime_domain_contracts/clinical_decision.md (authoritative).
#
# Owns
#
# decision_id
# case_id
# patient_id_reference
# approved_icd_codes (per-code recommendation disposition)
# normalization_version (traceability to the NormalizedClinicalNote used)
# created_at
#
# Should not contain
#
# raw clinical text
# normalized text
# cache keys
# infrastructure identifiers
# confidence scores
# retrieval candidates
# embeddings
# prompt context
#
# Note on scope: the contract's "Recommendation Traceability" section
# describes linking each approved code back to the CodingRecommendation
# that proposed it. CodingRecommendation is not yet implemented (it
# belongs to the AI reasoning subsystem, out of scope for this change),
# so ``ApprovedICDClassification`` records only the disposition
# (accepted/added/removed/modified) per code rather than a structural
# reference to that not-yet-existing artifact. This is the minimal shape
# needed for the domain model to compile against its contract; it is not
# a redesign of the contract and should be revisited once
# ClinicalDecisionService/CodingRecommendation exist.
#
# Note on normalization traceability: the contract's example field name
# is `normalized_note_id`, but NormalizedClinicalNote (see
# runtime_domain_contracts/normalized_clinical_note.md) intentionally has
# no identity field of its own. Introducing a synthetic id here would
# require inventing identity the contract doesn't define. Since
# normalization is deterministic, `case_id` (already required) together
# with `normalization_version` is sufficient to trace back to the exact
# NormalizedClinicalNote used, without embedding normalized text or a
# fabricated identifier.

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from aegis.models.base import DomainModel, ICDCode


class RecommendationDisposition(str, Enum):
    """How an approved ICD-11 code relates to the AI recommendation reviewed by the physician."""

    ACCEPTED = "accepted"
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"


class ApprovedICDClassification(DomainModel):
    """A single physician-approved ICD-11 code and its recommendation provenance."""

    icd_code: ICDCode
    disposition: RecommendationDisposition


class ClinicalDecision(DomainModel):
    """
    Immutable, physician-approved clinical truth.

    Produced exclusively by ``ClinicalDecisionService`` (not yet
    implemented) after physician review of a ``CodingRecommendation``.
    ``CacheService`` consumes and stores this artifact but never
    constructs, modifies, or derives one.
    """

    decision_id: UUID
    case_id: UUID
    patient_id_reference: UUID
    approved_icd_codes: list[ApprovedICDClassification]
    normalization_version: str
    created_at: datetime
