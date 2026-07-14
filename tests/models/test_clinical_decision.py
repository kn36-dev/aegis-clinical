from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from aegis.models.clinical_decision import (
    ApprovedICDClassification,
    ClinicalDecision,
    RecommendationDisposition,
)


@pytest.fixture
def clinical_decision():
    return ClinicalDecision(
        decision_id=uuid4(),
        case_id=uuid4(),
        patient_id_reference=uuid4(),
        approved_icd_codes=[
            ApprovedICDClassification(
                icd_code="1A00", disposition=RecommendationDisposition.ACCEPTED
            )
        ],
        normalization_version="1.0",
        created_at=datetime.now(timezone.utc),
    )


def test_clinical_decision_construction(clinical_decision):
    assert clinical_decision.decision_id is not None
    assert clinical_decision.approved_icd_codes[0].icd_code == "1A00"


def test_clinical_decision_requires_approved_icd_codes():
    with pytest.raises(ValidationError):
        ClinicalDecision.model_validate(
            {
                "decision_id": uuid4(),
                "case_id": uuid4(),
                "patient_id_reference": uuid4(),
                "normalization_version": "1.0",
                "created_at": datetime.now(timezone.utc),
            }
        )


def test_clinical_decision_is_immutable(clinical_decision):
    with pytest.raises(ValidationError):
        clinical_decision.normalization_version = "2.0"


def test_clinical_decision_serialization_round_trip(clinical_decision):
    dumped = clinical_decision.model_dump()

    restored = ClinicalDecision.model_validate(dumped)

    assert restored == clinical_decision


def test_clinical_decision_json_round_trip(clinical_decision):
    json_data = clinical_decision.model_dump_json()

    restored = ClinicalDecision.model_validate_json(json_data)

    assert restored == clinical_decision


def test_approved_icd_classification_is_immutable():
    classification = ApprovedICDClassification(
        icd_code="1A00", disposition=RecommendationDisposition.ADDED
    )

    with pytest.raises(ValidationError):
        classification.disposition = RecommendationDisposition.REMOVED
