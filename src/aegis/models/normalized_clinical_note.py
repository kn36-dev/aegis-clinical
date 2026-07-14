# NormalizedClinicalNote
#
# Shape defined by runtime_domain_contracts/normalized_clinical_note.md (authoritative).
#
# Owns
#
# clinical_note (reference to the originating immutable ClinicalNote)
# normalized_text
# normalization_version
# created_at
#
# Should not contain
#
# cache hashes / Redis keys
# embeddings
# vector identifiers
# retrieval candidates
# workflow state
# ICD classifications
# AI-generated reasoning
# physician decisions

from __future__ import annotations

from datetime import datetime

from aegis.models.base import ClinicalText, DomainModel
from aegis.models.clinical_note import ClinicalNote


class NormalizedClinicalNote(DomainModel):
    """
    Canonical deterministic representation of an anonymized clinical note.

    Produced exclusively by ``NormalizationService`` from an immutable
    ``ClinicalNote``. Preserves the clinical meaning of the physician's
    documentation while removing PHI and formatting inconsistencies, so
    that downstream deterministic and probabilistic components always
    operate on reproducible input.

    ``clinical_note`` embeds the full originating artifact (rather than
    only its identifier) because ``ClinicalNote`` is itself immutable —
    this keeps traceability self-contained without a second repository
    lookup, at the cost of a small amount of duplicated data.
    """

    clinical_note: ClinicalNote
    normalized_text: ClinicalText
    normalization_version: str
    created_at: datetime
