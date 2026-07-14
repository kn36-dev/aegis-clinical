# ClinicalNote
#
# Shape defined by runtime_domain_contracts/clinical_note.md (authoritative).
#
# Owns
#
# case_id
# patient_id
# content_reference
# created_at
#
# Should not contain
#
# extracted symptoms
# ICD codes
# raw clinical text (referenced via content_reference, not stored inline)

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from aegis.models.base import DomainModel


class ClinicalNote(DomainModel):
    """
    Canonical representation of a physician-authored clinical note.

    This model represents only the source document that enters the AI
    pipeline. It intentionally contains no extracted symptoms,
    diagnoses, reasoning, or workflow state, and no inline raw text —
    ``content_reference`` is an opaque pointer to the encrypted clinical
    note contents, owned by the domain rather than by the storage
    implementation behind it.
    """

    case_id: UUID
    patient_id: UUID
    content_reference: str = Field(min_length=1)
    created_at: datetime
