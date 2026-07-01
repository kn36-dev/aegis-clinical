# ClinicalNote

# Owns

# note_id
# patient_id
# physician_id
# raw text
# timestamp

# Should not contain

# extracted symptoms
# ICD codes

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from aegis.models.base import ClinicalText, DomainModel


class ClinicalNote(DomainModel):
    """
    Canonical representation of a physician-authored clinical note.

    This model represents only the source document that enters the AI
    pipeline. It intentionally contains no extracted symptoms,
    diagnoses, reasoning, or workflow state.
    """

    note_id: UUID
    patient_id: UUID
    physician_id: UUID
    raw_text: ClinicalText
    created_at: datetime
