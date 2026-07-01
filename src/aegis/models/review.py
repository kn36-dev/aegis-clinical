# src/aegis/models/review.py
# PhysicianReview

# Owns

# suggested codes
# approved codes
# comments
# approval timestamp

# ApprovedCode
# RejectedCode
# PhysicianReview

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from aegis.models.base import DomainModel
from aegis.models.icd import ICDConcept


class ReviewStatus(str, Enum):
    """
    Final outcome of physician review.
    """

    APPROVED = "approved"
    AMENDED = "amended"
    REJECTED = "rejected"


class PhysicianReview(DomainModel):
    """
    Human review of AI-generated ICD suggestions.

    Represents the final clinical decision made by a physician.
    """

    patient_id: UUID

    physician_id: UUID

    review_status: ReviewStatus

    suggested_codes: tuple[ICDConcept, ...]

    approved_codes: tuple[ICDConcept, ...]

    amended_codes: tuple[ICDConcept, ...] = ()

    comments: str | None = None

    reviewed_at: datetime
