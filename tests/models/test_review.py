from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from aegis.models.icd import ICDConcept
from aegis.models.review import (
    PhysicianReview,
    ReviewStatus,
)


@pytest.fixture
def pneumonia():
    return ICDConcept(
        code="CA40",
        title="Pneumonia",
    )


@pytest.fixture
def physician_review(pneumonia):
    return PhysicianReview(
        patient_id=uuid4(),
        physician_id=uuid4(),
        review_status=ReviewStatus.APPROVED,
        suggested_codes=(pneumonia,),
        approved_codes=(pneumonia,),
        comments="Diagnosis confirmed.",
        reviewed_at=datetime.now(timezone.utc),
    )


def test_review_construction(physician_review):
    assert physician_review.review_status is ReviewStatus.APPROVED
    assert len(physician_review.approved_codes) == 1
    assert physician_review.comments == "Diagnosis confirmed."


def test_review_requires_physician():
    with pytest.raises(ValidationError):
        PhysicianReview.model_validate(
            {
                "patient_id": uuid4(),
                "review_status": ReviewStatus.APPROVED,
                "suggested_codes": [],
                "approved_codes": [],
                "reviewed_at": datetime.now(timezone.utc),
            }
        )


def test_review_requires_status(pneumonia):
    with pytest.raises(ValidationError):
        PhysicianReview.model_validate(
            {
                "patient_id": uuid4(),
                "physician_id": uuid4(),
                "suggested_codes": [pneumonia.model_dump()],
                "approved_codes": [pneumonia.model_dump()],
                "reviewed_at": datetime.now(timezone.utc),
            }
        )


def test_review_is_immutable(physician_review):
    with pytest.raises(ValidationError):
        physician_review.comments = "Changed"


def test_review_serialization_round_trip(physician_review):
    restored = PhysicianReview.model_validate(physician_review.model_dump())

    assert restored == physician_review


def test_review_json_round_trip(physician_review):
    restored = PhysicianReview.model_validate_json(physician_review.model_dump_json())

    assert restored == physician_review
