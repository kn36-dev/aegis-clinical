import pytest
from pydantic import ValidationError

from aegis.models.symptom import (
    Severity,
    Symptom,
    SymptomExtraction,
)


@pytest.fixture
def symptom():
    return Symptom(
        name="productive cough",
        present=True,
        severity=Severity.SEVERE,
        duration="5 days",
    )


@pytest.fixture
def extraction(symptom):
    return SymptomExtraction(
        symptoms=(symptom,),
    )


def test_symptom_construction(symptom):
    assert symptom.present is True
    assert symptom.severity == Severity.SEVERE


def test_symptom_requires_name():
    with pytest.raises(ValidationError):
        Symptom.model_validate(
            {
                "present": True,
            }
        )


def test_symptom_extraction_contains_symptoms(extraction):
    assert len(extraction.symptoms) == 1


def test_symptom_is_immutable(symptom):
    with pytest.raises(ValidationError):
        symptom.name = "fever"


def test_extraction_round_trip(extraction):
    restored = SymptomExtraction.model_validate(extraction.model_dump())

    assert restored == extraction


def test_extraction_json_round_trip(extraction):
    restored = SymptomExtraction.model_validate_json(extraction.model_dump_json())

    assert restored == extraction
